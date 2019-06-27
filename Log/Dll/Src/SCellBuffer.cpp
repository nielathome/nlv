//
// Copyright (C) 2017-2018 Niel Clausen. All rights reserved.
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program. If not, see <https://www.gnu.org/licenses/>.
//

// Nlog includes
#include "StdAfx.h"
#include "Nline.h"
#include "Match.h"
#include "SCellBuffer.h"

// C++ includes
#include <chrono>
#include <memory>



/*-----------------------------------------------------------------------
 * SViewCellBuffer - New
 -----------------------------------------------------------------------*/

vint_t SViewCellBuffer::GetGlobalTrackerLine( unsigned idx ) const
{
	const GlobalTracker & tracker{ GlobalTrackers::GetGlobalTracker( idx ) };
	if( !tracker.IsInUse() )
		return -1;

	ViewTimecodeAccessor accessor{ * m_ViewAccessor };
	const NTimecode & target{ tracker.GetUtcTimecode() };

	vint_t low_idx{ 0 }, high_idx{ m_NumLinesOrOne - 1 };
	do
	{
		const vint_t idx{ (high_idx + low_idx + 1) / 2 }; 	// Round high
		const NTimecode value{ accessor.GetUtcTimecode( idx ) };
		if( target < value )
			high_idx = idx - 1;
		else
			low_idx = idx;
	} while( low_idx < high_idx );


	if( tracker.IsNearest( low_idx, m_NumLinesOrOne, accessor ) )
		return low_idx;
	else
		return low_idx + 1;
}


// identify Scintilla marker's to be displayed against the given line
int SViewCellBuffer::MarkValue( vint_t line_no, int bit ) const
{
	int res{ 0 };
	const ViewTimecodeAccessor accessor{ * m_ViewAccessor };
	const vint_t max_line_no{ m_NumLinesOrOne - 1 };

	for( const GlobalTracker & tracker : GlobalTrackers::GetTrackers() )
	{
		bit <<= 1;
		if( tracker.IsInUse() && tracker.IsNearest( line_no, max_line_no, accessor ) )
			res |= bit;
	}

	return res;
}


vint_t SViewCellBuffer::PositionToViewLine( vint_t want_pos ) const
{
	return NLine::Lookup( m_Lines, m_NumLinesOrOne, want_pos );
}


char SViewCellBuffer::CharAt( e_LineData type, vint_t position ) const
{
	if( BadRange( position ) )
		return '\0';

	vint_t view_line_no; vint_t offset;
	PositionToInfo( position, &view_line_no, &offset );
	return GetLine( type, view_line_no).First()[ offset ];
}


void SViewCellBuffer::GetRange( e_LineData type, char * buffer, vint_t position, vint_t lengthRetrieve ) const
{
	if( BadRange( position, lengthRetrieve ) )
		return;

	// fetch view co-ordinates of the starting position
	vint_t view_line_no; vint_t first_offset;
	PositionToInfo( position, &view_line_no, &first_offset );

	// break the copy down into line parts
	vint_t at{ position };
	vint_t end{ at + lengthRetrieve };

	while( at < end )
	{
		vint_t len{ GetLineLength( view_line_no ) - first_offset };
		if( (at + len) > end )
			len = end - at;

		// unsafe copy - have to assume Scintilla has allocated sufficient space
		const LineBuffer & line{ GetLine( type, view_line_no ) };
		const char * first{ line.First() + first_offset };
		memcpy( buffer, first, len );

		first_offset = 0;
		at += len;
		buffer += len;
		view_line_no += 1;
	}
}



/*-----------------------------------------------------------------------
 * SViewCellBuffer - Filtering
 -----------------------------------------------------------------------*/

void SViewCellBuffer::Filter( Selector * selector, bool add_irregular )
{
	PerfTimer timer;
	ViewMap view_map{
		m_ViewAccessor->Filter( selector, m_LineAdornmentsProvider, m_FieldViewMask, add_irregular )
	};

	m_Lines = std::move( view_map.f_Lines );
	m_TextLen = view_map.f_TextLen;

	// an empty document in Scintilla requires a line count of one
	m_IsEmpty = view_map.f_IsEmpty;

	// set to one for either empty, or a real line count of one ...
	// use m_IsEmpty to distinguish the two cases
	m_NumLinesOrOne = view_map.f_NumLinesOrOne;

	// record the change
	m_Tracker.RecordEvent();

	// write out performance data
	TraceDebug( "time:%.2fs per_line:%.3fus", timer.Overall(), timer.PerItem( m_NumLinesOrOne ) );
}


void SViewCellBuffer::SetFieldMask( uint64_t field_mask )
{
	// record the change
	m_Tracker.RecordEvent();
	m_FieldViewMask = field_mask;

	if( !m_IsEmpty )
	{
		PerfTimer timer;

		// TODO: parallelise
		vint_t pos{ 0 };
		for( vint_t line_no = 0; line_no < m_NumLinesOrOne; ++line_no )
		{
			m_Lines[ line_no ] = pos;
			pos += GetLineLength( line_no );
		}

		m_TextLen = m_Lines[ m_NumLinesOrOne ] = pos;

		// write out performance data
		TraceDebug( "time:%.2fs per_line:%.3fus", timer.Overall(), timer.PerItem( m_NumLinesOrOne ) );
	}
}



/*-----------------------------------------------------------------------
 * SViewCellBuffer - Searching
 -----------------------------------------------------------------------*/

// the search implementation is adapted from the filter implementation
// search a single view line; must be thread safe
struct SearchTask : public LineVisitor::Task
{
	// line data for the lines proccessed within this task
	std::vector<nlineno_t> f_Map;
	Selector * f_Selector;

	const SViewCellBuffer & f_CellBuffer;
	SearchTask( const SViewCellBuffer & cell_buffer, Selector * selector, nlineno_t num_lines )
		: f_Selector{ selector }, f_CellBuffer{ cell_buffer }
	{
		f_Map.reserve( num_lines );
	}

	void Action( const LineAccessor & line, nlineno_t visit_line_no ) override
	{
		LineAdornmentsAccessor adornments{ f_CellBuffer.GetLineAdornmentsProvider(), line.GetLineNo() };
		if( f_Selector->Hit( line, adornments ) )
			f_Map.push_back( visit_line_no );
	}
};


// search all view lines
struct SearchVisitor : public LineVisitor::Visitor
{
	// line data for all lines
	std::vector<nlineno_t> f_Map;
	Selector * f_Selector;
	const SViewCellBuffer & f_CellBuffer;

	using task_ptr_t = LineVisitor::task_ptr_t;

	SearchVisitor( const SViewCellBuffer & cell_buffer, Selector * selector, nlineno_t num_view_lines )
		: f_Selector{ selector }, f_CellBuffer{ cell_buffer }
	{
		f_Map.reserve( num_view_lines );
	}

	task_ptr_t MakeTask( nlineno_t num_lines ) override
	{
		return std::make_shared<SearchTask>( f_CellBuffer, f_Selector, num_lines );
	}

	void Join( task_ptr_t line_task ) override
	{
		SearchTask *filter_task{ dynamic_cast<SearchTask*>(line_task.get()) };

		for( nlineno_t log_line_no : filter_task->f_Map )
			f_Map.push_back( log_line_no );
	}
};


std::vector<nlineno_t> SViewCellBuffer::Search( Selector * selector ) const
{
	SearchVisitor visitor{ *this, selector, m_NumLinesOrOne };

	if( !m_IsEmpty )
	{
		PerfTimer timer;
		m_ViewAccessor->VisitLines( visitor, m_FieldViewMask, true );
		TraceDebug( "time:%.2fs per_line:%.3fus", timer.Overall(), timer.PerItem( m_NumLinesOrOne ) );
	}

	return visitor.f_Map;
}



/*-----------------------------------------------------------------------
 * SViewCellBuffer - Scintilla
 -----------------------------------------------------------------------*/

char SViewCellBuffer::CharAt( vint_t position ) const
{
	return CharAt( e_LineData::Text, position );
}


void SViewCellBuffer::GetCharRange( char * buffer, vint_t position, vint_t lengthRetrieve ) const
{
	return GetRange( e_LineData::Text, buffer, position, lengthRetrieve );
}


char SViewCellBuffer::StyleAt( vint_t position ) const
{
	return CharAt( e_LineData::Style, position );
}


void SViewCellBuffer::GetStyleRange( unsigned char * buffer, vint_t position, vint_t lengthRetrieve ) const
{
	return GetRange( e_LineData::Style, reinterpret_cast<char*>(buffer), position, lengthRetrieve );
}


vint_t SViewCellBuffer::Length() const
{
	return m_TextLen;
}


// fetch number of lines in this view of the log file
vint_t SViewCellBuffer::Lines() const
{
	return m_NumLinesOrOne;
}


vint_t SViewCellBuffer::LineStart( vint_t line ) const
{
	if( line < 0 )
		return 0;

	else if( line >= m_NumLinesOrOne )
		return m_TextLen;

	else
		return m_Lines[line];
}


vint_t SViewCellBuffer::LineFromPosition( vint_t want_pos ) const
{
	if( m_NumLinesOrOne <= 1 )
		return 0;

	if( want_pos >= m_TextLen )
		return m_NumLinesOrOne - 1 - 1; // whyy -2 ?

	return PositionToViewLine( want_pos );
}


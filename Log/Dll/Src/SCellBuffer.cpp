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

	ViewTimecodeAccessor accessor{ this, m_LogAccessor };
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


	if( tracker.IsNearest( low_idx, m_NumLinesOrOne, &accessor ) )
		return low_idx;
	else
		return low_idx + 1;
}


// identify Scintilla marker's to be displayed against the given line
int SViewCellBuffer::MarkValue( vint_t line_no, int bit ) const
{
	int res{ 0 };
	const ViewTimecodeAccessor accessor{ this, m_LogAccessor };
	const vint_t max_line_no{ m_NumLinesOrOne - 1 };

	for( const GlobalTracker & tracker : GlobalTrackers::GetTrackers() )
	{
		bit <<= 1;
		if( tracker.IsInUse() && tracker.IsNearest( line_no, max_line_no, &accessor ) )
			res |= bit;
	}

	return res;
}


vint_t SViewCellBuffer::PositionToViewLine( vint_t want_pos ) const
{
	return NLine::Lookup( m_Lines, m_NumLinesOrOne, want_pos );
}


// fetch nearest preceding view line number to the supplied log line
vint_t SViewCellBuffer::LogLineToViewLine( vint_t log_line_no, bool exact ) const
{
	return NLine::Lookup( m_LineMap, m_NumLinesOrOne, log_line_no, exact );
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

// filter a single log file line; must be thread safe
struct FilterTask : public LineVisitor::Task
{
	// line data for the lines proccessed within this task
	std::vector<nlineno_t> f_Lines;
	std::vector<nlineno_t> f_Map;
	nlineno_t f_ViewPos{ 0 };
	const bool f_AddIrregular{ true };
	Selector * f_Selector{ nullptr };
	LineAdornmentsProvider * f_LineAdornmentsProvider{ nullptr };

	FilterTask( Selector * selector, LineAdornmentsProvider * provider, nlineno_t num_lines, bool add_irregular )
		:
		f_Selector{ selector },
		f_LineAdornmentsProvider{ provider },
		f_AddIrregular{ add_irregular }
	{
		f_Lines.reserve( num_lines );
		f_Map.reserve( num_lines );
	}

	void Action( const LineAccessor & line, nlineno_t visit_line_no ) override
	{
		LineAdornmentsAccessor adornments{ f_LineAdornmentsProvider, line.GetLineNo() };
		if( !f_Selector->Hit( line, adornments ) )
			return;

		// add the selected line
		f_Lines.push_back( f_ViewPos );
		f_Map.push_back( visit_line_no++ );
		f_ViewPos += line.GetLength();

		// if requested, add in any irregular continuation lines
		// add the selected line and all of its continuations
		if( !f_AddIrregular )
			return;

		const LineAccessorIrregular * add{ nullptr };
		while( (add = line.NextIrregular()) != nullptr )
		{
			f_Lines.push_back( f_ViewPos );
			f_Map.push_back( visit_line_no++ );
			f_ViewPos += add->GetLength();
		};
	}
};


// filter all log file lines
struct FilterVisitor : public LineVisitor::Visitor
{
	// line data for all lines
	std::vector<nlineno_t> f_Lines;
	std::vector<nlineno_t> f_Map;
	nlineno_t f_ViewPos{ 0 };
	const bool f_AddIrregular{ true };
	Selector * f_Selector;
	LineAdornmentsProvider * f_LineAdornmentsProvider{ nullptr };

	using task_t = LineVisitor::task_t;

	FilterVisitor( Selector * selector, LineAdornmentsProvider * provider, nlineno_t num_log_lines, bool add_irregular )
		:
		f_Selector{ selector },
		f_LineAdornmentsProvider{ provider },
		f_AddIrregular{ add_irregular }
	{
		f_Lines.reserve( num_log_lines + 1 );
		f_Map.reserve( num_log_lines + 1 );
	}

	task_t MakeTask( nlineno_t num_lines ) override
	{
		return std::make_shared<FilterTask>( f_Selector, f_LineAdornmentsProvider, num_lines, f_AddIrregular );
	}

	void Join( task_t line_task ) override
	{
		FilterTask *filter_task{ dynamic_cast<FilterTask*>(line_task.get()) };

		for( nlineno_t line_pos : filter_task->f_Lines )
			f_Lines.push_back( f_ViewPos + line_pos );

		for( nlineno_t log_line_no : filter_task->f_Map )
			f_Map.push_back( log_line_no );

		f_ViewPos += filter_task->f_ViewPos;
	}

	void Finish( void )
	{
		// add a "one past end of file" entry; e.g. needed to find line lengths
		// which look at the next line in the document
		const bool empty{ f_Lines.empty() };
		nlineno_t last_log_lineno{ empty ? 0 : f_Map.back() + 1 };
		f_Lines.push_back( f_ViewPos );
		f_Map.push_back( last_log_lineno );
	}
};


void SViewCellBuffer::Filter( Selector * selector, bool add_irregular )
{
	PerfTimer timer;
	FilterVisitor visitor{ selector, m_LineAdornmentsProvider, m_LogAccessor->GetNumLines(), add_irregular };
	m_LogAccessor->VisitLines( visitor, m_FieldViewMask, false );
	visitor.Finish();

	m_Lines = visitor.f_Lines;
	m_LineMap = visitor.f_Map;
	m_TextLen = visitor.f_ViewPos;

	// an empty document in Scintilla requires a line count of one
	m_IsEmpty = visitor.f_Map.size() <= 1;

	// set to one for either empty, or a real line count of one ...
	// use m_IsEmpty to distinguish the two cases
	m_NumLinesOrOne = vint_cast( !m_IsEmpty ? visitor.f_Map.size() - 1 : 1 );

	// record the change
	m_Tracker.RecordEvent();

	// write out performance data
	TraceDebug( "time:%.2fs per_line:%.3fus", timer.Overall(), timer.PerItem( m_LogAccessor->GetNumLines() ) );
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

	nlineno_t VisitLineToLogLine( nlineno_t visit_line_no ) const override {
		return f_CellBuffer.ViewLineToLogLine( visit_line_no );
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

	using task_t = LineVisitor::task_t;

	SearchVisitor( const SViewCellBuffer & cell_buffer, Selector * selector, nlineno_t num_view_lines )
		: f_Selector{ selector }, f_CellBuffer{ cell_buffer }
	{
		f_Map.reserve( num_view_lines );
	}

	task_t MakeTask( nlineno_t num_lines ) override
	{
		return std::make_shared<SearchTask>( f_CellBuffer, f_Selector, num_lines );
	}

	void Join( task_t line_task ) override
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
		m_LogAccessor->VisitLines( visitor, m_FieldViewMask, true, m_NumLinesOrOne );
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


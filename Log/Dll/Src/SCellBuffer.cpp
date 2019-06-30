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

	vint_t low_idx{ 0 }, high_idx{ m_ViewMap->m_NumLinesOrOne - 1 };
	do
	{
		const vint_t idx{ (high_idx + low_idx + 1) / 2 }; 	// Round high
		const NTimecode value{ accessor.GetUtcTimecode( idx ) };
		if( target < value )
			high_idx = idx - 1;
		else
			low_idx = idx;
	} while( low_idx < high_idx );


	if( tracker.IsNearest( low_idx, m_ViewMap->m_NumLinesOrOne, accessor ) )
		return low_idx;
	else
		return low_idx + 1;
}


// identify Scintilla marker's to be displayed against the given line
int SViewCellBuffer::MarkValue( vint_t line_no, int bit ) const
{
	int res{ 0 };
	const ViewTimecodeAccessor accessor{ * m_ViewAccessor };
	const vint_t max_line_no{ m_ViewMap->m_NumLinesOrOne - 1 };

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
	return NLine::Lookup( m_ViewMap->m_Lines, m_ViewMap->m_NumLinesOrOne, want_pos );
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
		vint_t len{ m_ViewAccessor->GetLineLength( view_line_no ) - first_offset };
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
	return m_ViewMap->m_TextLen;
}


// fetch number of lines in this view of the log file
vint_t SViewCellBuffer::Lines() const
{
	return m_ViewMap->m_NumLinesOrOne;
}


vint_t SViewCellBuffer::LineStart( vint_t line ) const
{
	if( line < 0 )
		return 0;

	else if( line >= m_ViewMap->m_NumLinesOrOne )
		return m_ViewMap->m_TextLen;

	else
		return m_ViewMap->m_Lines[line];
}


vint_t SViewCellBuffer::LineFromPosition( vint_t want_pos ) const
{
	if( m_ViewMap->m_NumLinesOrOne <= 1 )
		return 0;

	if( want_pos >= m_ViewMap->m_TextLen )
		return m_ViewMap->m_NumLinesOrOne - 1 - 1; // whyy -2 ?

	return PositionToViewLine( want_pos );
}


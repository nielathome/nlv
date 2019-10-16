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
#include "Nlog.h"



/*-----------------------------------------------------------------------
 * SLineMarkers
 -----------------------------------------------------------------------*/

int SLineMarkers::HistoryLineMarkValue( vint_t view_line_no )
{
	return view_line_no == m_HistoryLineNo ? 0x1 << MarkerNumber::e_MarkerNumberHistory : 0;
}


int SLineMarkers::ViewMarkValue( vint_t view_line_no )
{
	int res{ 0 }, bit{ 0x1 << MarkerNumber::e_MarkerNumberTrackerBase };

	const ViewTimecode * timecode_accessor{ m_ViewAccessor->GetTimecode() };
	const vint_t max_line_no{ m_ViewMap->m_NumLinesOrOne - 1 };

	for( const GlobalTracker & tracker : GlobalTrackers::GetTrackers() )
	{
		bit <<= 1;
		if( tracker.IsInUse() && tracker.IsNearest( view_line_no, max_line_no, timecode_accessor ) )
			res |= bit;
	}

	return res;
}

vint_t SLineMarkers::MarkValue( vint_t view_line_no )
{
	// most markers come from the logfile
	const vint_t log_line_no{ m_ViewLineTranslation->ViewLineToLogLine( view_line_no ) };
	int log_markers{ 0 };
	m_ViewAccessor->VisitLine( view_line_no, [&log_markers, log_line_no, this] ( const LineAccessor & line ) {
		log_markers = m_Adornments->LogMarkValue( log_line_no, line );
	} );
	
	// the global timecode markers
	const int global_markers{ ViewMarkValue( view_line_no ) };
	
	// history line marker
	const int history_marker{ HistoryLineMarkValue( view_line_no ) };
	return history_marker | log_markers | global_markers;
}



/*-----------------------------------------------------------------------
 * SLineMarginText
 -----------------------------------------------------------------------*/

void SLineMarginText::CreateOffsetText_MsecDotNsec( int64_t sec, int64_t nsec, std::ostringstream & strm )
{
	constexpr int64_t c_Million{ 1'000'000 };
	const int64_t msec{ nsec / c_Million };
	nsec -= msec * c_Million;

	strm << std::setfill( '0' ) << sec << '.'
		<< std::setw( 3 ) << msec << '.'
		<< std::setw( 6 ) << nsec;
}


void SLineMarginText::CreateOffsetText_Usec( int64_t sec, int64_t nsec, std::ostringstream & strm )
{
	const int64_t usec{ nsec / 1'000 };
	strm << std::setfill( '0' ) << sec << '.'
		<< std::setw( 6 ) << usec;
}


void SLineMarginText::CreateOffsetText_Msec( int64_t sec, int64_t nsec, std::ostringstream & strm )
{
	constexpr int64_t c_Million{ 1'000'000 };
	const int64_t msec{ nsec / c_Million };
	strm << std::setfill( '0' ) << sec << '.'
		<< std::setw( 3 ) << msec;
}


void SLineMarginText::CreateOffsetText_Sec( int64_t sec, int64_t nsec, std::ostringstream & strm )
{
	strm << sec;
}


void SLineMarginText::CreateOffsetText_MinSec( int64_t sec, int64_t nsec, std::ostringstream & strm )
{
	const int64_t min{ sec / 60 };
	sec -= min * 60;

	strm << std::setfill( '0' ) << min << ':'
		<< std::setw( 2 ) << sec;
}


void SLineMarginText::CreateOffsetText_HourMinSec( int64_t sec, int64_t nsec, std::ostringstream & strm )
{
	const int64_t hour{ sec / (60 * 60) };
	sec -= hour * (60 * 60);

	const int64_t min{ sec / 60 };
	sec -= min * 60;

	strm << std::setfill( '0' ) << hour << ':'
		<< std::setw( 2 ) << min << ':'
		<< std::setw( 2 ) << sec;
}


void SLineMarginText::CreateOffsetText_DayHourMinSec( int64_t sec, int64_t nsec, std::ostringstream & strm )
{
	const int64_t day{ sec / (24 * 60 * 60) };
	sec -= day * (24 * 60 * 60);

	const int64_t hour{ sec / (60 * 60) };
	sec -= hour * (60 * 60);

	const int64_t min{ sec / 60 };
	sec -= min * 60;

	strm << std::setfill( '0' ) << day << ':' 
		<< std::setw( 2 ) << hour << ':'
		<< std::setw( 2 ) << min << ':'
		<< std::setw( 2 ) << sec;
}


void SLineMarginText::CreateLineNumberText( vint_t line, std::ostringstream & strm ) const
{
	strm << line;
}


void SLineMarginText::CreateOffsetText( vint_t line, std::ostringstream & strm ) const
{
	int64_t offset{ 0 };

	m_ViewAccessor->VisitLine( line, [&offset, this] ( const LineAccessor & line ) {
		offset = line.GetFieldValue( m_DateFieldId ).As<int64_t>();
	} );

	if( offset != 0 )
	{
		constexpr int64_t c_Billion{ 1'000'000'000 };
		const int64_t sec{ offset / c_Billion };
		const int64_t nsec{ offset - (sec * c_Billion) };

		(*m_CreateOffsetTextFunc)(sec, nsec, strm);
	}
}


void SLineMarginText::UpdateLineText( vint_t line ) const
{
	if( m_CreateTextFunc != nullptr )
	{
		std::ostringstream strm;
		(this->*m_CreateTextFunc)(line, strm);
		m_LineNumber = line;
		m_LineText = strm.str();
	}
}


void SLineMarginText::Setup( Type type, Precision prec )
{
	switch( type )
	{
	case Type::e_None:
		m_CreateTextFunc = nullptr;
		m_LineText = "";
		break;

	case Type::e_LineNumber:
		m_CreateTextFunc = & SLineMarginText::CreateLineNumberText;
		break;

	case Type::e_Offset:
		m_CreateTextFunc = &SLineMarginText::CreateOffsetText;

		switch( prec )
		{
			case e_MsecDotNsec:
				m_CreateOffsetTextFunc = &CreateOffsetText_MsecDotNsec;
				break;

			case e_Usec:
				m_CreateOffsetTextFunc = &CreateOffsetText_Usec;
				break;

			case e_Msec:
				m_CreateOffsetTextFunc = &CreateOffsetText_Msec;
				break;

			case e_Sec:
				m_CreateOffsetTextFunc = &CreateOffsetText_Sec;
				break;

			case e_MinSec:
				m_CreateOffsetTextFunc = &CreateOffsetText_MinSec;
				break;

			case e_HourMinSec:
				m_CreateOffsetTextFunc = &CreateOffsetText_HourMinSec;
				break;

			case e_DayHourMinSec:
				m_CreateOffsetTextFunc = &CreateOffsetText_DayHourMinSec;
				break;
		}
		break;
	}
}


const std::string & SLineMarginText::GetLineText( vint_t line ) const
{
	if( line != m_LineNumber )
		UpdateLineText( line );
	return m_LineText;
}


vint_t SLineMarginText::Style( vint_t line ) const
{
	// STYLE_LINENUMBER
	return 33;
}


const char *SLineMarginText::Text( vint_t line ) const
{
	return GetLineText( line ).c_str();
}


vint_t SLineMarginText::Length( vint_t line ) const
{
	return vint_cast( GetLineText( line ).size() );
}



/*-----------------------------------------------------------------------
 * SLineAnnotation
 -----------------------------------------------------------------------*/

bool SLineAnnotation::HasStateChanged( void ) const
{
	const bool annotations_changed{ m_LogAnnotationsTracker.CompareTo( m_LogAnnotations->GetTracker() ) };
	const bool cellbuffer_changed{ m_ViewTracker.CompareTo( m_ViewAccessor->GetProperties()->GetTracker() ) };
	return annotations_changed || cellbuffer_changed;
}


// fetch a list of annotation sizes associated with this view of the log file
annotationsizes_list_t SLineAnnotation::GetAnnotationSizes( void ) const
{
	const annotationsizes_list_t logfile_sizes{ m_LogAnnotations->GetAnnotationSizes() };

	annotationsizes_list_t view_sizes;
	view_sizes.reserve( logfile_sizes.size() );

	for( const annotationsizes_list_t::value_type & elem : logfile_sizes )
	{
		const vint_t log_line{ elem.first };
		const vint_t nearest_view_line{ m_ViewLineTranslation->LogLineToViewLine( log_line ) };
		const vint_t nearest_log_line{ m_ViewLineTranslation->ViewLineToLogLine( nearest_view_line ) };

		if( nearest_log_line == log_line )
			// the log file annotation is visible in this view
			view_sizes.emplace_back( nearest_view_line, elem.second );
	}

	return view_sizes;
}


const NAnnotation * SLineAnnotation::GetAnnotation( vint_t line ) const
{
	return m_LogAnnotations->GetAnnotation( m_ViewLineTranslation->ViewLineToLogLine( line ) );
}


vint_t SLineAnnotation::Style( vint_t line ) const
{
	vint_t ret{ 0 };

	const NAnnotation * annotation{ GetAnnotation( line ) };
	if( annotation != nullptr )
		ret = annotation->GetStyle();

	return ret;
}


void SLineAnnotation::SetStyle( vint_t line, vint_t style )
{
	m_LogAnnotations->SetAnnotationStyle( m_ViewLineTranslation->ViewLineToLogLine( line ), style );
}


const char *SLineAnnotation::Text( vint_t line ) const
{
	const char *ret{ nullptr };

	const NAnnotation * annotation{ GetAnnotation( line ) };
	if( annotation != nullptr )
		ret = annotation->GetText();

	return ret;
}


void SLineAnnotation::SetText( vint_t line, const char * text )
{
	m_LogAnnotations->SetAnnotationText( m_ViewLineTranslation->ViewLineToLogLine( line ), text );
}


vint_t SLineAnnotation::Length( vint_t line ) const
{
	vint_t ret{ 0 };

	const NAnnotation * annotation{ GetAnnotation( line ) };
	if( annotation != nullptr )
		ret = annotation->GetTextLength();

	return ret;
}


vint_t SLineAnnotation::Lines( vint_t line ) const
{
	vint_t ret{ 0 };

	const NAnnotation * annotation{ GetAnnotation( line ) };
	if( annotation != nullptr )
		ret = annotation->GetNumLines();

	return ret;
}



/*-----------------------------------------------------------------------
 * SContractionState
 -----------------------------------------------------------------------*/

CacheStatistics SContractionState::s_DisplayFromDocStats{ "ContractionState/DisplayFromDoc" };;
CacheStatistics SContractionState::s_DocFromDisplayStats{ "ContractionState/DocFromDisplay" };;
CacheStatistics SContractionState::s_HeightStats{ "ContractionState/Height" };;


// count number of lines in all annotations up to the provided view line number
vint_t SContractionState::SumAnnotationSizes( vint_t line ) const
{
	vint_t sum{ 0 };

	for( const annotationsizes_list_t::value_type & elem : m_AnnotationSizes )
	{
		if( elem.first < line )
			sum += elem.second;
		else
			break;
	}

	return sum;
}


// check cache validity, and re-build if needed
void SContractionState::ValidateCache( void ) const
{
	// statistics
	static CacheStatistics cache_stats{ "ContractionState" };

	// cache management
	cache_stats.Lookup();
	if( !m_Annotations->HasStateChanged() )
		return;

	cache_stats.Miss();
	m_AnnotationSizes = std::move( m_Annotations->GetAnnotationSizes() );
	m_DisplayFromDoc.Clear();
	m_DocFromDisplay.Clear();
	m_Height.Clear();

	m_LinesinDocument = m_ViewAccessor->GetNumLines();
	const vint_t annotation_lines{ SumAnnotationSizes( m_LinesinDocument ) };
	m_LinesDisplayed = m_LinesinDocument + annotation_lines;
}


vint_t SContractionState::LinesInDoc() const
{
	ValidateCache();
	return m_LinesinDocument;
}


// fetch the total number of lines to display, both log file view lines and
// annotation lines
vint_t SContractionState::LinesDisplayed() const
{
	ValidateCache();
	return m_LinesDisplayed;
}


// translate a log file view line number to a display line number
vint_t SContractionState::DisplayFromDoc( vint_t lineDoc ) const
{
	ValidateCache();

	return * m_DisplayFromDoc.Fetch( lineDoc, [ this ]( vint_t lineDoc ) -> vint_t
	{
		const vint_t annotation_lines{ SumAnnotationSizes( lineDoc ) };
		return lineDoc + annotation_lines;
	} ).second;
}


// appears to be the line number of the last annotation line at a site
vint_t SContractionState::DisplayLastFromDoc( vint_t lineDoc ) const
{
	return DisplayFromDoc( lineDoc ) + GetHeight( lineDoc ) - 1;
}


// translate a display line number (including annotation lines) to its log file view line number
vint_t SContractionState::DocFromDisplay( vint_t lineDisplay ) const
{
	ValidateCache();

	return * m_DocFromDisplay.Fetch( lineDisplay, [ this ]( vint_t lineDisplay ) -> vint_t
	{
		vint_t lineDoc{ lineDisplay };

		for( const annotationsizes_list_t::value_type & elem : m_AnnotationSizes )
		{
			const vint_t size{ elem.second };
			const vint_t first_line{ elem.first };
			const vint_t last_line{ first_line + size };

			if( (first_line < lineDoc) && (lineDoc <= last_line) )
			{
				lineDoc -= lineDoc - first_line;
				break;
			}
			else if( last_line < lineDoc )
				lineDoc -= size;
			else
				break;
		}

		return lineDoc;
	} ).second;
}


// fetch the height of the given log file view line
vint_t SContractionState::GetHeight( vint_t lineDoc ) const
{
	ValidateCache();

	return * m_Height.Fetch( lineDoc, [this] ( vint_t lineDoc ) -> vint_t
	{
		// default line height is 1
		vint_t height{ 1 };
		for( const annotationsizes_list_t::value_type & elem : m_AnnotationSizes )
		{
			// if the given line has an annotation, include it in the height
			if( elem.first == lineDoc )
				height += elem.second;

			// only interested in annotation lines up to (and including) the given line
			if( elem.first >= lineDoc )
				break;
		}

		return height;
	} ).second;
}


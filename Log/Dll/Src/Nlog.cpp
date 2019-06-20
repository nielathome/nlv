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
#include "StdAfx.h"

// Application includes
#include "Nline.h"
#include "Nlog.h"

// Boost includes
#include <boost/lexical_cast.hpp>

// C++ includes
#include <string>



/*-----------------------------------------------------------------------
 * NLifeTime
 -----------------------------------------------------------------------*/

void NLifeTime::Release( void )
{
	delete this;
}



/*-----------------------------------------------------------------------
 * NStateManager
 -----------------------------------------------------------------------*/

std::string NStateManager::GetState( void )
{
	std::string res;

	try
	{
		json store;

		for( const stateprovider_map_t::value_type & elem : m_StateProviders )
		{
			const std::string provider_guid{ elem.first };
			const stateprovider_ptr_t & provider{ elem.second };
			provider->GetState( store[ provider_guid ] );
		}

		res = store.dump();
	}
	catch( const std::exception & ex )
	{
		TraceError( e_StateCreate, "JSON exception: '%s'", ex.what() );
	}

	return res;
}


void NStateManager::PutState( const std::string & state_text )
{
	if( state_text.empty() )
		return;

	try
	{
		json store{ json::parse( state_text ) };

		for( auto elem : store.items() )
		{
			stateprovider_map_t::iterator iprovider{ m_StateProviders.find( elem.key() ) };
			if( iprovider != m_StateProviders.end() )
				iprovider->second->PutState( elem.value() );
		}
	}
	catch( const std::exception & ex )
	{
		TraceError( e_StateUse, "JSON exception: '%s'", ex.what() );
	}
}



/*-----------------------------------------------------------------------
 * NAnnotation
 -----------------------------------------------------------------------*/

static vint_t CountLines( const char * text )
{
	vint_t lines{ 0 };

	if( text )
	{
		while( *text != '\0' )
		{
			if( *(text++) == '\n' )
				++lines;
		}
		++lines;
	}

	return lines;
}


NAnnotation::NAnnotation( const char * text )
 : m_Text{ text }, m_NumLines{ CountLines( text ) }
{
}


void NAnnotation::GetState( json & store ) const
{
	store[ "text" ] = m_Text;
	store[ "style" ] = m_StyleNo;
	store[ "num_lines" ] = m_NumLines;
}


void NAnnotation::PutState( const json & store )
{
	m_Text = store.at( "text" ).get<std::string>();
	m_StyleNo = store.at( "style" ).get<vint_t>();
	m_NumLines = store.at( "num_lines" ).get<vint_t>();
}



/*-----------------------------------------------------------------------
 * NAnnotations
 -----------------------------------------------------------------------*/

NAnnotations::NAnnotations( void )
{
	RegisterStateProvider( "71EDFA0D-2008-4EC5-AE8B-AF515588AE2B",
		MakeStateProvider( this, &NAnnotations::GetState, &NAnnotations::PutState )
	);
}


void NAnnotations::GetState( json & store ) const
{
	int idx{ 0 };
	for( const annotation_map_t::value_type & elem : m_AnnotationMap )
	{
		const NAnnotation & annotation{ elem.second };
		json value;
		annotation.GetState( value );

		// add state to the store
		const std::string line_no{ boost::lexical_cast<std::string>(elem.first) };
		store[ line_no ] = value;
	}
}


void NAnnotations::PutState( const json & store )
{
	for( auto elem : store.items() )
	{
		const vint_t line_no{ boost::lexical_cast<vint_t>(elem.key()) };
		NAnnotation annotation;
		annotation.PutState( elem.value() );

		m_AnnotationMap[ line_no ] = annotation;
	}
}


// fetch a list of annotation sizes associated with the log file
annotationsizes_list_t NAnnotations::GetAnnotationSizes( void ) const
{
	annotationsizes_list_t res;
	res.reserve( m_AnnotationMap.size() );

	for( const annotation_map_t::value_type & elem : m_AnnotationMap )
		res.emplace_back( elem.first, elem.second.GetNumLines() );

	return res;
}


const NAnnotation * NAnnotations::GetAnnotation( vint_t log_line_no ) const
{
	const NAnnotation * ret{ nullptr };

	annotation_map_t::const_iterator iannotation{ m_AnnotationMap.find( log_line_no ) };
	if( iannotation != m_AnnotationMap.end() )
		ret = &iannotation->second;

	return ret;
}


void NAnnotations::SetAnnotationText( vint_t line, const char * text )
{
	// assume empty text means "delete"
	m_Tracker.RecordEvent();
	if( (text == nullptr) || (text[ 0 ] == '\0') )
	{
		annotation_map_t::const_iterator iannotation{ m_AnnotationMap.find( line ) };
		if( iannotation != m_AnnotationMap.end() )
			m_AnnotationMap.erase( iannotation );
	}
	else
		m_AnnotationMap[ line ] = NAnnotation{ text };
}


void NAnnotations::SetAnnotationStyle( vint_t line, vint_t style )
{
	annotation_map_t::iterator iannotation{ m_AnnotationMap.find( line ) };
	if( iannotation != m_AnnotationMap.end() )
		iannotation->second.SetStyle( style );
}


vint_t NAnnotations::GetNextAnnotation( nlineno_t current, bool forward )
{
	return NLine::GetNextLine( m_AnnotationMap, current, forward );
}



/*-----------------------------------------------------------------------
 * NAdornments
 -----------------------------------------------------------------------*/

NAdornments::NAdornments( logaccessor_ptr_t log_accessor )
	: m_LogAccessor{ log_accessor }
{
	RegisterStateProvider( "0EF8EE4F-4402-40F5-A9F7-5E48BC8876A6",
		MakeStateProvider( this, &NAdornments::GetState, &NAdornments::PutState )
	);
}


void NAdornments::GetState( json & store ) const
{
	for( vint_t line_no : m_UserMarkers )
		store.emplace_back( line_no );
}


void NAdornments::PutState( const json & store )
{
	for( const json & elem : store )
		m_UserMarkers.insert( elem.get<vint_t>() );
}


int NAdornments::LogMarkValue( vint_t log_line_no )
{
	NLineAdornmentsProvider provider{ this };
	LineAdornmentsAccessor adornments{ &provider, log_line_no };

	int res{ 0 }, bit{ 0x1 << (int) NConstants::e_StyleBaseMarker };

	GetLogAccessor()->VisitLine( log_line_no,
		[this, &res, &bit, &adornments] ( const LineAccessor & line )
		{
			// process auto markers first (i.e. lowest precedence is first item)
			for( const selector_ptr_t &selector : m_AutoMarkers )
			{
				if( selector && selector->GetImpl()->Hit( line, adornments ) )
					res |= bit;
				bit <<= 1;
			}
		}
	);

	// user marker is last - has highest precedence
	if( m_UserMarkers.find( log_line_no ) != m_UserMarkers.end() )
		res |= bit;

	// marker for the tracked line is managed from a different marker range
	if( m_LocalTrackerLine == log_line_no )
		res |= (0x1 << (int) NConstants::e_StyleBaseTracker);

	return res;
}


int NAdornments::ViewMarkValue( vint_t view_line_no, const SViewCellBuffer & cell_buffer )
{
	const int marker_base{ 0x1 << (int) NConstants::e_StyleBaseTracker };
	return cell_buffer.MarkValue( view_line_no, marker_base );
}


int NAdornments::MarkValue( vint_t view_line_no, const SViewCellBuffer & cell_buffer )
{
	// most markers come from the logfile
	const int log_markers{ LogMarkValue( cell_buffer.ViewLineToLogLine( view_line_no ) ) };

	// the global timecode markers come from the cell buffer, as knowledge of the neighbouring
	// lines is needed to perform the "nearest" time calculations
	const int global_markers{ ViewMarkValue( view_line_no, cell_buffer ) };

	return log_markers | global_markers;
}


bool NAdornments::HasUsermark( vint_t log_line_no ) const
{
	return m_UserMarkers.find( log_line_no ) != m_UserMarkers.end();
}


void NAdornments::ToggleUsermark( vint_t log_line_no )
{
	UserMarkers::iterator iline{ m_UserMarkers.find( log_line_no ) };
	if( iline == m_UserMarkers.end() )
		m_UserMarkers.insert( log_line_no );
	else
		m_UserMarkers.erase( iline );
}


vint_t NAdornments::GetNextUsermark( vint_t log_line_no, bool forward )
{
	return NLine::GetNextLine( m_UserMarkers, log_line_no, forward );
}



/*-----------------------------------------------------------------------
 * NHiliter
 -----------------------------------------------------------------------*/

void NHiliter::Hilite( const vint_t start, const char *first, const char *last, VControl *vcontrol )
{
	struct HiliteVisitor : Selector::Visitor
	{
		const vint_t m_Start;
		const char * m_First;
		unsigned m_Indicator;
		VControl * m_Vcontrol;

		HiliteVisitor( vint_t start, const char * first, unsigned indicator, VControl * vcontrol )
			: m_Start{ start }, m_First{ first }, m_Indicator{ indicator }, m_Vcontrol{ vcontrol } {}

		void Action( const char * found, size_t length ) override
		{
			const vint_t pos{ vint_cast( m_Start + (found - m_First) ) };
			const vint_t len{ vint_cast( length ) };
			m_Vcontrol->VIndicatorFillRange( m_Indicator, pos, len, 1 );
		}
	};

	if( m_Selector )
		m_Selector->GetImpl()->Visit( first, last, HiliteVisitor{ start, first, m_Indicator, vcontrol } );
}


void NHiliter::SetupMatchedLines( void )
{
	const bool buffer_changed{ m_CellBufferTracker.CompareTo( m_CellBuffer->GetTracker() ) };
	if( !m_SelectorChanged && !buffer_changed )
		return;

	m_SelectorChanged = false;

	if( !m_Selector )
		m_MatchedLines.clear();
	else
	{
		Selector * selector{ m_Selector->GetImpl() };
		m_MatchedLines = m_CellBuffer->Search( selector );
	}
}


nlineno_t NHiliter::Search( nlineno_t current, bool forward )
{
	SetupMatchedLines();
	return m_MatchedLines.empty() ? -1 : NLine::GetNextLine( m_MatchedLines, current, forward );
}


bool NHiliter::Hit( nlineno_t line_no )
{
	SetupMatchedLines();
	return NLine::Lookup( m_MatchedLines, nlineno_cast( m_MatchedLines.size() ), line_no, true ) >= 0;
}



/*-----------------------------------------------------------------------
 * NLogAccessor
 -----------------------------------------------------------------------*/

NLogAccessor::NLogAccessor( LogAccessorDescriptor & descriptor )
{
	SetImpl( LogAccessorFactory::Create( descriptor ) );
}



/*-----------------------------------------------------------------------
 * NFilterView
 -----------------------------------------------------------------------*/

NFilterView::NFilterView( logfile_ptr_t logfile )
	:
	m_Logfile{ logfile },
	m_Adornments{ logfile->GetAdornments() },
	m_AdornmentsProvider{ logfile->GetAdornments().get() },
	m_CellBuffer{ logfile->GetLogAccessor(), &m_AdornmentsProvider }
{
	Match descriptor{ Match::Type::e_Literal, std::string{}, false };
	std::unique_ptr<Selector> selector{ Selector::MakeSelector( descriptor, true ) };
	m_CellBuffer.Filter( selector.get(), true );
}


std::string NFilterView::GetNonFieldText( vint_t line_no )
{
	std::string res;

	m_CellBuffer.VisitLine( line_no, [&res] ( const LineAccessor & line ) {
		const char * first; const char * last;
		line.GetNonFieldText( &first, &last );
		res.assign( first, last );
	} );

	return res;
}


std::string NFilterView::GetFieldText( vint_t line_no, vint_t field_no )
{
	// as elsewhere, field 0 is an internal (hidden) field, so the public field
	// 0 is actually field 1

	std::string res;

	m_CellBuffer.VisitLine( line_no, [field_no, &res] ( const LineAccessor & line ) {
		const char * first; const char * last;
		line.GetFieldText( field_no + 1, &first, &last );
		res.assign( first, last );
	} );

	return res;
}


fieldvalue_t NFilterView::GetFieldValue( vint_t line_no, vint_t field_no )
{
	// as elsewhere, field 0 is an internal (hidden) field, so the public field
	// 0 is actually field 1

	fieldvalue_t res;

	m_CellBuffer.VisitLine( line_no, [field_no, &res] ( const LineAccessor & line ) {
		res = line.GetFieldValue( field_no + 1 );
	} );

	return res;
}


// line number translation between the view and the underlying logfile
vint_t NFilterView::ViewLineToLogLine( vint_t view_line_no ) const
{
	return m_CellBuffer.ViewLineToLogLine( view_line_no );
}


// return the view line at or after the supplied log line; otherwise -1
vint_t NFilterView::LogLineToViewLine( vint_t log_line_no ) const
{
	vint_t view_line{ m_CellBuffer.LogLineToViewLine( log_line_no ) };
	const vint_t new_log_line{ ViewLineToLogLine( view_line ) };

	if( new_log_line < log_line_no )
		view_line += 1;

	return (view_line >= GetNumLines()) ? -1 : view_line;
}


void NFilterView::SetNumHiliter( unsigned num_hiliter )
{
	m_Hiliters.clear();
	m_Hiliters.reserve( num_hiliter );
	for( unsigned i = 0; i < num_hiliter; ++i )
		m_Hiliters.emplace_back( hiliter_ptr_t{ new NHiliter{ i, &m_CellBuffer } } );
}


void NFilterView::ToggleBookmarks( vint_t view_fm_line, vint_t view_to_line )
{
	for( int line_no = view_fm_line; line_no <= view_to_line; ++line_no )
		m_Adornments->ToggleUsermark( m_CellBuffer.ViewLineToLogLine( line_no) );
}


// find the next visible view line for the source "get_next_log_line"
vint_t NFilterView::GetNextVisibleLine( vint_t view_line_no, bool forward, vint_t( NAdornments::*get_next_log_line)(vint_t, bool) )
{
	vint_t log_line_no{ m_CellBuffer.ViewLineToLogLine( view_line_no ) };
	while( true )
	{
		log_line_no = (m_Adornments.get()->*get_next_log_line)(log_line_no, forward);
		if( log_line_no < 0 )
			return log_line_no;

		view_line_no = m_CellBuffer.LogLineToViewLine( log_line_no, true );
		if( view_line_no >= 0 )
			return view_line_no;
	}
}


vint_t NFilterView::GetNextBookmark( vint_t view_line_no, bool forward )
{
	return GetNextVisibleLine( view_line_no, forward, &NAdornments::GetNextUsermark );
}


vint_t NFilterView::GetNextAnnotation( vint_t view_line_no, bool forward )
{
	return GetNextVisibleLine( view_line_no, forward, &NAdornments::GetNextAnnotation );
}


void NFilterView::SetLocalTrackerLine( vint_t line_no )
{
	m_Adornments->SetLocalTrackerLine( m_CellBuffer.ViewLineToLogLine( line_no ) );
}


vint_t NFilterView::GetLocalTrackerLine( void )
{
	return m_CellBuffer.LogLineToViewLine( m_Adornments->GetLocalTrackerLine() );
}


NTimecode * NFilterView::GetUtcTimecode( vint_t line_no )
{
	// as elsewhere, field 0 is an internal (hidden) field, so the public field
	// 0 is actually field 1

	NTimecode * res{ new NTimecode };

	m_CellBuffer.VisitLine( line_no, [&res] ( const LineAccessor & line ) {
		*res = line.GetUtcTimecode();
	} );

	return res;
}



/*-----------------------------------------------------------------------
 * NView
 -----------------------------------------------------------------------*/

NView::NView( logfile_ptr_t logfile )
	:
	NFilterView{ logfile },
	m_LineMarker{ new SLineMarkers{ logfile->GetAdornments(), m_CellBuffer } },
	m_LineLevel{ new SLineLevels },
	m_LineState{ new SLineState },
	m_LineMargin{ new SLineAnnotation{ logfile->GetAdornments(), m_CellBuffer } },
	m_LineAnnotation{ new SLineAnnotation{ logfile->GetAdornments(), m_CellBuffer } },
	m_ContractionState{ new SContractionState{ m_LineAnnotation, m_CellBuffer} }
{
}


void NView::Release( void )
{
	delete this;
}


SViewCellBuffer *__stdcall NView::GetCellBuffer()
{
	return & m_CellBuffer;
}


void __stdcall NView::ReleaseCellBuffer( VCellBuffer * )
{
}


VLineMarkers * __stdcall NView::GetLineMarkers( void )
{
	auto ret{ m_LineMarker.get() };
	intrusive_ptr_add_ref( ret );
	return ret;
}


VLineLevels * __stdcall NView::GetLineLevels( void )
{
	auto ret{ m_LineLevel.get() };
	intrusive_ptr_add_ref( ret );
	return ret;
}


VLineState * __stdcall NView::GetLineState( void )
{
	auto ret{ m_LineState.get() };
	intrusive_ptr_add_ref( ret );
	return ret;
}


VLineAnnotation * __stdcall NView::GetLineMargin( void )
{
	auto ret{ m_LineMargin.get() };
	intrusive_ptr_add_ref( ret );
	return ret;
}


VLineAnnotation * __stdcall NView::GetLineAnnotation( void )
{
	auto ret{ m_LineAnnotation.get() };
	intrusive_ptr_add_ref( ret );
	return ret;
}


VContractionState * __stdcall NView::GetContractionState( void )
{
	auto ret{ m_ContractionState.get() };
	intrusive_ptr_add_ref( ret );
	return ret;
}


void __stdcall NView::Notify_StartDrawLine( vint_t line_no )
{
	VControl * vcontrol{ GetControl() };
	const vint_t start{ m_CellBuffer.LineStart( line_no ) };
	const LineBuffer & line{ m_CellBuffer.GetLine( e_LineData::Text, line_no ) };

	// re-create indicators
	for( hiliter_ptr_t hiliter : m_Hiliters )
	{
		vcontrol->VIndicatorFillRange( hiliter->m_Indicator, 0, m_CellBuffer.Length(), 0 );
		hiliter->Hilite( start, line.First(), line.Last(), vcontrol );
	}
}


unsigned long long NView::GetContent( void )
{
	VContent *content{ this };
	return reinterpret_cast<unsigned long long>( content );
}


void NView::Filter( selector_ptr_t selector, bool add_irregular )
{
	NTextChanged handler{ m_CellBuffer, GetControl() };
	NFilterView::Filter( selector, add_irregular );
}


void NView::SetFieldMask( uint64_t field_mask )
{
	NTextChanged handler{ m_CellBuffer, GetControl() };
	NFilterView::SetFieldMask( field_mask );
}



/*-----------------------------------------------------------------------
 * GlobalTracker
 -----------------------------------------------------------------------*/

bool GlobalTracker::IsNearest( int line_no, int max_line_no, const NTimecodeAccessor * accessor ) const
{
	const NTimecode timecode{ accessor->GetUtcTimecode( line_no ) };
	const int64_t delta{ timecode - f_UtcTimecode };

	const bool tracker_at_or_before{ delta >= 0 };
	const bool tracker_at_or_after{ delta <= 0 };

	// first line
	if( line_no == 0 )
		return tracker_at_or_before;

	// last line
	if( line_no == max_line_no )
		return tracker_at_or_after;

	// tracker is at, or before, this line
	if( tracker_at_or_before )
	{
		const NTimecode prev_timecode{ accessor->GetUtcTimecode( line_no - 1 ) };
		const int64_t prev_delta{ prev_timecode - f_UtcTimecode };
		const bool tracker_at_or_before_prev{ prev_delta >= 0 };

		if( tracker_at_or_before_prev )
			return false;

		return delta < -prev_delta;
	}

	// tracker is after this line
	else
	{
		const NTimecode next_timecode{ accessor->GetUtcTimecode( line_no + 1 ) };
		const int64_t next_delta{ next_timecode - f_UtcTimecode };
		const bool tracker_at_or_after_next{ next_delta <= 0 };

		if( tracker_at_or_after_next )
			return false;

		return -delta < next_delta;
	}
}



/*-----------------------------------------------------------------------
 * GlobalTrackers
 -----------------------------------------------------------------------*/

std::vector<GlobalTracker> GlobalTrackers::s_GlobalTrackers{ 4 };


void GlobalTrackers::SetGlobalTracker( unsigned tracker_idx, const NTimecode & utc_timecode )
{
	s_GlobalTrackers[ tracker_idx ].SetUtcTimecode( utc_timecode );
}



/*-----------------------------------------------------------------------
 * LogfileTimecodeAccessor
 -----------------------------------------------------------------------*/

LogfileTimecodeAccessor::LogfileTimecodeAccessor( LogAccessor * accessor )
	: f_LogAccessor{ accessor }
{
}


NTimecode LogfileTimecodeAccessor::GetUtcTimecode( int line_no ) const
{
	return f_LogAccessor->GetUtcTimecode( line_no );
}



/*-----------------------------------------------------------------------
 * NLogfile
 -----------------------------------------------------------------------*/

NLogfile::NLogfile( logaccessor_ptr_t log_accessor )
	:
	m_LogAccessor{ log_accessor },
	m_Adornments{ new NAdornments{ log_accessor } }
{
}


Error NLogfile::Open( const std::wstring &file_path, ProgressMeter * progress, size_t skip_lines )
{
	return GetLogAccessor()->Open( file_path, progress, skip_lines );
}


view_ptr_t NLogfile::CreateView( void )
{
	return new NView{ logfile_ptr_t{ this } };
}


lineset_ptr_t NLogfile::CreateLineSet( void )
{
	return new NLineSet{ logfile_ptr_t{ this } };
}



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
#include <boost/python/object.hpp>

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


void NAnnotations::SetAnnotationText( vint_t log_line_no, const char * text )
{
	// assume empty text means "delete"
	m_Tracker.RecordEvent();
	if( (text == nullptr) || (text[ 0 ] == '\0') )
	{
		annotation_map_t::const_iterator iannotation{ m_AnnotationMap.find( log_line_no ) };
		if( iannotation != m_AnnotationMap.end() )
			m_AnnotationMap.erase( iannotation );
	}
	else
		m_AnnotationMap[ log_line_no ] = NAnnotation{ text };
}


void NAnnotations::SetAnnotationStyle( vint_t log_line_no, vint_t style )
{
	annotation_map_t::iterator iannotation{ m_AnnotationMap.find( log_line_no ) };
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

NAdornments::NAdornments( void )
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


int NAdornments::LogMarkValue( vint_t log_line_no, const LineAccessor & line )
{
	NLineAdornmentsProvider provider{ this };
	LineAdornmentsAccessor adornments{ &provider, log_line_no };

	int res{ 0 }, bit{ 0x1 << MarkerNumber::e_MarkerNumberStandardBase };

	// process auto markers first (i.e. lowest precedence is first item)
	for( const selector_ptr_t & selector : m_AutoMarkers )
	{
		if( selector && selector->Hit( line, adornments ) )
			res |= bit;
		bit <<= 1;
	}

	// user marker is last - has highest precedence
	if( m_UserMarkers.find( log_line_no ) != m_UserMarkers.end() )
		res |= bit;

	// marker for the tracked line is managed from a different marker range
	if( m_LocalTrackerLine == log_line_no )
		res |= (0x1 << MarkerNumber::e_MarkerNumberTrackerBase);

	return res;
}

bool NAdornments::SetAutoMarker( unsigned marker, boost::python::object match, logfile_ptr_t logfile )
{
	if( selector_ptr_t selector{ MakeSelector( match, false, logfile->GetSchema() ) } )
	{
		m_AutoMarkers[ marker ] = std::move(selector);
		return true;
	}
	else
		return false;
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
		m_Selector->Visit( first, last, HiliteVisitor{ start, first, m_Indicator, vcontrol } );
}


bool NHiliter::SetMatch( boost::python::object match )
{
	if( selector_ptr_t selector{ MakeSelector( match, false, m_Logfile->GetSchema() ) } )
	{
		m_SelectorChanged = true;
		m_Selector = std::move( selector );
		return true;
	}
	else
		return false;
}


void NHiliter::SetupMatchedLines( void )
{
	const bool buffer_changed{ m_ViewTracker.CompareTo( m_ViewAccessor->GetProperties()->GetTracker() ) };
	if( !m_SelectorChanged && !buffer_changed )
		return;

	m_SelectorChanged = false;

	if( !m_Selector )
		m_MatchedLines.clear();

	else
	{
		NLineAdornmentsProvider adornments_provider{ m_Logfile->GetAdornments() };
		m_MatchedLines = m_ViewAccessor->Search( m_Selector, &adornments_provider );
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
 * NViewCore
 -----------------------------------------------------------------------*/


NViewCore::NViewCore( logfile_ptr_t logfile, viewaccessor_ptr_t view_accessor )
	:
	m_Logfile{ logfile },
	m_ViewAccessor{ view_accessor }
{
	if( m_Logfile &&  m_ViewAccessor )
	{
		Match descriptor{ Match::Type::e_Literal, std::string{}, false };
		Filter( Selector::MakeSelector( descriptor, true, nullptr ), true );
	}
}


void NViewCore::Filter( selector_ptr_a selector, bool add_irregular )
{
	NLineAdornmentsProvider adornments_provider{ m_Logfile->GetAdornments() };
	m_ViewAccessor->Filter( selector, &adornments_provider, add_irregular );
}


bool NViewCore::Filter( boost::python::object match, bool add_irregular )
{
	if( selector_ptr_t selector{ MakeSelector( match, true, m_Logfile->GetSchema() ) } )
	{
		Filter( selector, add_irregular );
		return true;
	}
	else
		return false;
}



/*-----------------------------------------------------------------------
 * NViewFieldAccess
 -----------------------------------------------------------------------*/

fieldvalue_t NViewFieldAccess::GetFieldValue( vint_t line_no, vint_t field_no )
{
	fieldvalue_t res;

	m_ViewAccessor->VisitLine( line_no, [field_no, &res] ( const LineAccessor & line ) {
		res = line.GetFieldValue( field_no );
	} );

	return res;
}


std::string NViewFieldAccess::GetNonFieldText( vint_t line_no )
{
	std::string res;

	m_ViewAccessor->VisitLine( line_no, [&res] ( const LineAccessor & line ) {
		const char * first; const char * last;
		line.GetNonFieldText( &first, &last );
		res.assign( first, last );
	} );

	return res;
}


std::string NViewFieldAccess::GetFieldText( vint_t line_no, vint_t field_no )
{
	std::string res;

	m_ViewAccessor->VisitLine( line_no, [field_no, &res] ( const LineAccessor & line ) {
		const char * first; const char * last;
		line.GetFieldText( field_no, &first, &last );
		res.assign( first, last );
	} );

	return res;
}



/*-----------------------------------------------------------------------
 * NViewLineTranslation
 -----------------------------------------------------------------------*/

NViewLineTranslation::NViewLineTranslation( void )
	: m_ViewLineTranslation{ m_ViewAccessor->GetLineTranslation() }
{
	if( !m_ViewLineTranslation )
		throw std::runtime_error{ "ViewAccessor has no ViewLineTranslation" };
}


// line number translation between the view and the underlying logfile
vint_t NViewLineTranslation::ViewLineToLogLine( vint_t view_line_no ) const
{
	return m_ViewLineTranslation->ViewLineToLogLine( view_line_no );
}


// return the view line at or after the supplied log line; otherwise -1
vint_t NViewLineTranslation::LogLineToViewLine( vint_t log_line_no, bool exact ) const
{
	vint_t view_line{ m_ViewLineTranslation->LogLineToViewLine( log_line_no, exact ) };
	if( view_line < 0 )
		return view_line;

	const vint_t new_log_line{ ViewLineToLogLine( view_line ) };
	if( new_log_line < log_line_no )
		view_line += 1;

	return (view_line >= GetNumLines()) ? -1 : view_line;
}



/*-----------------------------------------------------------------------
 * NViewTimecode
 -----------------------------------------------------------------------*/


NViewTimecode::NViewTimecode( void )
	: m_ViewTimecode{ m_ViewAccessor->GetTimecode() }
{
	if( !m_ViewTimecode )
		throw std::runtime_error{ "ViewAccessor has no ViewTimecode" };
}


NTimecode * NViewTimecode::GetNearestUtcTimecode( vint_t line_no )
{
	return new NTimecode{ m_ViewTimecode->GetNearestUtcTimecode( line_no ) };
}



/*-----------------------------------------------------------------------
 * NViewHiliting
 -----------------------------------------------------------------------*/

void NViewHiliting::SetNumHiliter( unsigned num_hiliter )
{
	m_Hiliters.clear();
	m_Hiliters.reserve( num_hiliter );
	for( unsigned i = 0; i < num_hiliter; ++i )
		m_Hiliters.emplace_back( hiliter_ptr_t{ new NHiliter{ i, m_Logfile, m_ViewAccessor } } );
}



/*-----------------------------------------------------------------------
 * NLineSet
 -----------------------------------------------------------------------*/

NLineSet::NLineSet( logfile_ptr_t logfile, viewaccessor_ptr_t view_accessor )
	:
	NViewCore{ logfile, view_accessor }
{
}



/*-----------------------------------------------------------------------
 * NEventView
 -----------------------------------------------------------------------*/

NEventView::NEventView( logfile_ptr_t logfile, viewaccessor_ptr_t view_accessor )
	:
	NViewCore{ logfile, view_accessor }
{
}


bool NEventView::Filter( boost::python::object match )
{
	return NViewCore::Filter( match, true );
}


void NEventView::Sort( unsigned col_num, int direction )
{
	SortControl * sort_control{ m_ViewAccessor->GetSortControl() };
	if( sort_control )
		sort_control->SetSort( col_num, direction );
}


bool NEventView::IsContainer( vint_t line_no )
{
	HierarchyAccessor * hierarchy{ m_ViewAccessor->GetHierarchyAccessor() };
	return hierarchy ? hierarchy->IsContainer( line_no ) : false;
}


std::vector<int> NEventView::GetChildren( vint_t line_no, bool view_flat )
{
	HierarchyAccessor * hierarchy{ m_ViewAccessor->GetHierarchyAccessor() };
	return hierarchy ? hierarchy->GetChildren( line_no, view_flat ) : std::vector<int>{};
}


int NEventView::GetParent( vint_t line_no )
{
	HierarchyAccessor * hierarchy{ m_ViewAccessor->GetHierarchyAccessor() };
	return hierarchy ? hierarchy->GetParent( line_no ) : -1;
}


int NEventView::LookupEventId( int64_t event_id )
{
	HierarchyAccessor * hierarchy{ m_ViewAccessor->GetHierarchyAccessor() };
	return hierarchy ? hierarchy->LookupEventId( event_id ) : -1;
}



/*-----------------------------------------------------------------------
 * NLogView
 -----------------------------------------------------------------------*/

 // Note: field 0 is an internal (hidden) field, so the public field
 // 0 is actually field 1
NLogView::NLogView( logfile_ptr_t logfile, viewaccessor_ptr_t view_accessor )
	:
	NViewCore{ logfile, view_accessor },
	m_CellBuffer{ view_accessor },
	m_LineMarker{ new SLineMarkers{ logfile->GetAdornments(), view_accessor } },
	m_LineLevel{ new SLineLevels },
	m_LineState{ new SLineState },
	m_LineMargin{ new SLineMarginText{ view_accessor, logfile->GetSchema()->GetTimecodeBase().GetFieldId() } },
	m_LineAnnotation{ new SLineAnnotation{ logfile->GetAdornments(), view_accessor } },
	m_ContractionState{ new SContractionState{ m_LineAnnotation, view_accessor } },
	m_ViewMap{ view_accessor->GetMap() },
	m_ViewLineTranslation{ view_accessor->GetLineTranslation() }
{
	if( !m_ViewMap )
		throw std::runtime_error{ "ViewAccessor has no ViewMap" };
	if( !m_ViewLineTranslation )
		throw std::runtime_error{ "ViewAccessor has no ViewLineTranslation" };
}


void NLogView::Release( void )
{
	delete this;
}


SViewCellBuffer *__stdcall NLogView::GetCellBuffer()
{
	return & m_CellBuffer;
}


void __stdcall NLogView::ReleaseCellBuffer( VCellBuffer * )
{
}


VLineMarkers * __stdcall NLogView::GetLineMarkers( void )
{
	auto ret{ m_LineMarker.get() };
	intrusive_ptr_add_ref( ret );
	return ret;
}


VLineLevels * __stdcall NLogView::GetLineLevels( void )
{
	auto ret{ m_LineLevel.get() };
	intrusive_ptr_add_ref( ret );
	return ret;
}


VLineState * __stdcall NLogView::GetLineState( void )
{
	auto ret{ m_LineState.get() };
	intrusive_ptr_add_ref( ret );
	return ret;
}


VLineAnnotation * __stdcall NLogView::GetLineMargin( void )
{
	auto ret{ m_LineMargin.get() };
	intrusive_ptr_add_ref( ret );
	return ret;
}


VLineAnnotation * __stdcall NLogView::GetLineAnnotation( void )
{
	auto ret{ m_LineAnnotation.get() };
	intrusive_ptr_add_ref( ret );
	return ret;
}


VContractionState * __stdcall NLogView::GetContractionState( void )
{
	auto ret{ m_ContractionState.get() };
	intrusive_ptr_add_ref( ret );
	return ret;
}


void __stdcall NLogView::Notify_StartDrawLine( vint_t line_no )
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


unsigned long long NLogView::GetContent( void )
{
	VContent *content{ this };
	return reinterpret_cast<unsigned long long>( content );
}


bool NLogView::Filter( boost::python::object match )
{
	NTextChanged handler{ m_CellBuffer, GetControl() };
	return NViewCore::Filter( match, true );
}


void NLogView::SetFieldMask( uint64_t field_mask )
{
	NTextChanged handler{ m_CellBuffer, GetControl() };
	NViewHiliting::SetFieldMask( field_mask );
}


void NLogView::ToggleBookmarks( vint_t view_fm_line, vint_t view_to_line )
{
	for( int line_no = view_fm_line; line_no <= view_to_line; ++line_no )
		GetAdornments()->ToggleUsermark( m_ViewLineTranslation->ViewLineToLogLine( line_no ) );
}


adornments_ptr_t NLogView::GetAdornments( void )
{
	return m_Logfile->GetAdornments();
}


// find the next visible view line for the source "get_next_log_line"
vint_t NLogView::GetNextVisibleLine( vint_t view_line_no, bool forward, vint_t( NAdornments::*get_next_log_line )(vint_t, bool) )
{
	vint_t log_line_no{ m_ViewLineTranslation->ViewLineToLogLine( view_line_no ) };
	while( true )
	{
		log_line_no = (GetAdornments().get()->*get_next_log_line)(log_line_no, forward);
		if( log_line_no < 0 )
			return log_line_no;

		view_line_no = m_ViewLineTranslation->LogLineToViewLine( log_line_no, true );
		if( view_line_no >= 0 )
			return view_line_no;
	}
}


vint_t NLogView::GetNextBookmark( vint_t view_line_no, bool forward )
{
	return GetNextVisibleLine( view_line_no, forward, &NAdornments::GetNextUsermark );
}


vint_t NLogView::GetNextAnnotation( vint_t view_line_no, bool forward )
{
	return GetNextVisibleLine( view_line_no, forward, &NAdornments::GetNextAnnotation );
}


void NLogView::SetLocalTrackerLine( vint_t line_no )
{
	GetAdornments()->SetLocalTrackerLine( m_ViewLineTranslation->ViewLineToLogLine( line_no ) );
}


vint_t NLogView::GetLocalTrackerLine( void )
{
	return m_ViewLineTranslation->LogLineToViewLine( GetAdornments()->GetLocalTrackerLine() );
}


vint_t NLogView::GetGlobalTrackerLine( unsigned tracker_idx )
{
	const GlobalTracker & tracker{ GlobalTrackers::GetGlobalTracker(tracker_idx) };
	if( !tracker.IsInUse() )
		return -1;

	const NTimecode & target{ tracker.GetUtcTimecode() };
	const ViewMap * view_map{ m_ViewMap };

	vint_t low_idx{ 0 }, high_idx{ view_map->m_NumLinesOrOne - 1 };
	do
	{
		const vint_t sample_idx{ (high_idx + low_idx + 1) / 2 }; 	// Round high
		vint_t usable_idx{ sample_idx };

		while( !m_ViewTimecode->HasTimeCode(usable_idx) )
			usable_idx -= 1;
		
		if(usable_idx < 0 )
			break;
		
		if (usable_idx <= low_idx)
		{
			// back to where we started
			low_idx = sample_idx;
			continue;
		}

		const NTimecode value{ m_ViewTimecode->GetUtcTimecode(usable_idx) };
		if( target < value )
			high_idx = usable_idx - 1;
		else
			low_idx = usable_idx;
	} while( low_idx < high_idx );

	while (!m_ViewTimecode->HasTimeCode(low_idx))
		low_idx -= 1;

	if( tracker.IsNearest( low_idx, view_map->m_NumLinesOrOne, m_ViewTimecode ) )
		return low_idx;
	else
		return low_idx + 1;
}


void NLogView::SetHistoryLine( vint_t line_no )
{
	m_LineMarker->SetHistoryLine( line_no );
}


void NLogView::SetupMarginText( SLineMarginText::Type type, SLineMarginText::Precision prec )
{
	m_LineMargin->Setup( type, prec );
}



/*-----------------------------------------------------------------------
 * GlobalTracker
 -----------------------------------------------------------------------*/

bool GlobalTracker::IsNearest( int line_no, int max_line_no, const ViewTimecode * timecode_accessor ) const
{
	if( !timecode_accessor->HasTimeCode( line_no ) )
		return false;

	const NTimecode timecode{ timecode_accessor->GetUtcTimecode( line_no ) };
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
		const NTimecode prev_timecode{ timecode_accessor->GetNearestUtcTimecode( line_no - 1 ) };
		const int64_t prev_delta{ prev_timecode - f_UtcTimecode };
		const bool tracker_at_or_before_prev{ prev_delta >= 0 };

		if( tracker_at_or_before_prev )
			return false;

		return delta < -prev_delta;
	}

	// tracker is after this line
	else
	{
		const NTimecode next_timecode{ timecode_accessor->GetNearestUtcTimecode( line_no + 1 ) };
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
 * NLogfile
 -----------------------------------------------------------------------*/

NLogfile::NLogfile( logaccessor_ptr_t && log_accessor )
	:
	m_LogAccessor{ std::move(log_accessor) },
	m_Adornments{ new NAdornments }
{
}


Error NLogfile::Open( const std::wstring &file_path, ProgressMeter * progress )
{
	return GetLogAccessor()->Open( file_path, progress );
}


lineset_ptr_t NLogfile::CreateLineSet( boost::python::object match )
{
	try
	{
		lineset_ptr_t res{ new NLineSet{ logfile_ptr_t{ this }, GetLogAccessor()->CreateViewAccessor() } };

		if( !res->Filter( match, false ) )
			res.reset();

		return res;
	}
	catch( const std::exception & ex )
	{
		TraceError( e_CreateLineSet, "Exception: '%s'", ex.what() );
	}

	return lineset_ptr_t{};
}


eventview_ptr_t NLogfile::CreateEventView( void )
{
	try
	{
		return new NEventView{ logfile_ptr_t{ this }, GetLogAccessor()->CreateViewAccessor() };
	}
	catch( const std::exception & ex )
	{
		TraceError( e_CreateEventView, "Exception: '%s'", ex.what() );
	}

	return eventview_ptr_t{};
}


logview_ptr_t NLogfile::CreateLogView( void )
{
	try
	{
		return new NLogView{ logfile_ptr_t{ this }, GetLogAccessor()->CreateViewAccessor() };
	}
	catch( const std::exception & ex )
	{
		TraceError( e_CreateLogView, "Exception: '%s'", ex.what() );
	}

	return logview_ptr_t{};
}


bool  NLogfile::SetAutoMarker( unsigned marker, boost::python::object match )
{
	return m_Adornments->SetAutoMarker( marker, match, logfile_ptr_t{ this } );
}

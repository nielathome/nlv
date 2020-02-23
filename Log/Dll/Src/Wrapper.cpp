//
// Copyright (C) 2017-2020 Niel Clausen. All rights reserved.
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

// Boost includes
#include <boost/python.hpp>
using namespace boost::python;

// Application includes
#include "Nlog.h"

// C++ includes
#include <codecvt>



/*-------------------------------------------------------------------------
 * Tracing
 ------------------------------------------------------------------------*/

namespace
{
	// logger object to call-back into Python
	object g_Logger;


	// tracing can be sent to Python for distribution and storage
	void TraceToPython( Error error, const std::string & message )
	{
		const char * method{ "error" };
		if( error == e_TraceDebug )
			method = "debug";
		else if( error == e_TraceInfo )
			method = "info";

		g_Logger.attr( method )(message);
	}
}


/*-------------------------------------------------------------------------
 * Performance
 ------------------------------------------------------------------------*/

// performance timing integrated with Python G_PerfTimer
namespace
{
	// timer factory object to call-back into Python
	object g_PerfTimerFactory;

	struct FullPerfTimer : public PythonPerfTimerImpl
	{
		object m_PythonPerfTimer;

		FullPerfTimer( const char * description, size_t item_count ) {
			m_PythonPerfTimer = g_PerfTimerFactory( description, item_count );
		}

		void AddArgument( const char * arg ) override {
			m_PythonPerfTimer.attr( "AddArgument" )(arg);
		}

		void AddArgument( const wchar_t * arg ) override {
			using converter_t = std::wstring_convert<std::codecvt_utf8<wchar_t>>;
			std::string utf8{ converter_t{}.to_bytes( arg ) };
			m_PythonPerfTimer.attr( "AddArgument" )(utf8);
		}

		void Close( size_t item_count ) override {
			m_PythonPerfTimer.attr( "Close" )(item_count);
		}
	};

}

std::unique_ptr<PythonPerfTimerImpl> PythonPerfTimerImpl::Create( const char * description, size_t item_count )
{
	return std::make_unique<FullPerfTimer>( description, item_count );
};




/*-----------------------------------------------------------------------
 * ADAPTERS
 -----------------------------------------------------------------------*/

// LogAccessor factory
logaccessor_ptr_t MakeLogAccessor( object log_schema )
{
	LogAccessorDescriptor descriptor
	{
		extract<std::string>{ log_schema.attr( "AccessorName" ) },
		extract<std::string>{ log_schema.attr( "Guid" ) },
		extract<std::string>{ log_schema.attr( "RegexText" ) },
		extract<unsigned>{ log_schema.attr( "TextOffsetSize" ) }
	};

	stl_input_iterator<object> end;

	for( auto ifield_schema = stl_input_iterator<object>{ log_schema }; ifield_schema != end; ++ifield_schema )
	{
		bool available{ true };
		try
		{
			available = extract<bool>{ ifield_schema->attr( "Available" ) };
		}
		catch( error_already_set & )
		{
			PyErr_Clear();
		}

		unsigned data_col_offset{ 0 };
		try
		{
			data_col_offset = extract<unsigned>{ ifield_schema->attr( "DataColumnOffset" ) };
		}
		catch( error_already_set & )
		{
			PyErr_Clear();
		}

		descriptor.m_FieldDescriptors.push_back( FieldDescriptor
		{
			available,
			extract<std::string>{ ifield_schema->attr( "Name" ) },
			extract<std::string>{ ifield_schema->attr( "Type" ) },
			extract<std::string>{ ifield_schema->attr( "Separator" ) },
			extract<unsigned>{ ifield_schema->attr( "SeparatorCount" ) },
			extract<unsigned>{ ifield_schema->attr( "MinWidth" ) },
			data_col_offset
		} );
	}

	object formatter{ log_schema.attr( "GetFormatter" )() };
	for( auto iformat = stl_input_iterator<object>{ formatter }; iformat != end; ++iformat )
	{
		const std::string regex_text{ extract<std::string>{ iformat->attr( "RegexText" ) } };
		std::regex_constants::syntax_option_type flags{
			std::regex_constants::ECMAScript
			| std::regex_constants::optimize
		};

		std::vector<unsigned> style_nos;
		for( auto istyleno = stl_input_iterator<object>{ iformat->attr( "StyleNumbers" ) }; istyleno != end; ++istyleno )
			style_nos.push_back( extract<unsigned>{ *istyleno } );

		FormatDescriptor line_formatter{ std::regex{ regex_text, flags }, std::move( style_nos ) };
		descriptor.m_LineFormatters.push_back( std::move( line_formatter ) );
	}

	TraceDebug( "name:'%s' match_desc:'%s' guid:'%s'",
		descriptor.m_Name.c_str(),
		descriptor.m_RegexText.c_str(),
		descriptor.m_Guid.c_str()
	);

	logaccessor_ptr_t accessor{ LogAccessorFactory::Create( descriptor ) };
	const Error error{ accessor ? e_OK : e_BadAccessorName };
	if( !Ok( error ) )
		accessor.reset();

	return accessor;
}


// Selector factory
selector_ptr_t MakeSelector( object match, bool empty_selects_all, const LogSchemaAccessor * log_schema )
{
	Match descriptor{
		extract<Match::Type>{ match.attr( "GetSelectorId" )() },
		extract<std::string>{ match.attr( "MatchText" ) },
		extract<bool>{ match.attr( "MatchCase" ) }
	};

	selector_ptr_t selector{ Selector::MakeSelector( descriptor, empty_selects_all, log_schema ) };
	const Error error{ selector ? e_OK : TraceError( e_BadSelectorDefinition, "'%s'", descriptor.m_Text.c_str() ) };
	return selector;
}



/*-----------------------------------------------------------------------
 * MODULE
 -----------------------------------------------------------------------*/

// Python initialisation
void Setup( object logger, object perf_timer_factory )
{
	// performance timing
	g_PerfTimerFactory = perf_timer_factory;

	// startup message
	static OnEvent evt{ OnEvent::EventType::Startup,
		[] () {
			const char * build =
			#ifdef _DEBUG
				"debug";
			#else
				"release";
			#endif
			TraceDebug( "DLL running: build:'%s'", build );
	} };

	// run shutdown actions before tracing re-directed
	const bool startup{ logger.is_none() ? false : true };
	if( !startup )
		OnEvent::RunEvents( OnEvent::EventType::Shutdown );

	// re-direct trace output
	SetTraceFunc( startup ? TraceToPython : nullptr );
	g_Logger = logger;

	// run startup actions after tracing re-directed
	if( startup )
		OnEvent::RunEvents( OnEvent::EventType::Startup );
}


// Python access to logfile factory
logfile_ptr_t MakeLogfile( const std::string & nlog_path, object log_schema, object progress )
{
	using converter_t = std::wstring_convert<std::codecvt_utf8<wchar_t>>;
	std::wstring wnlog_path{ converter_t{}.from_bytes( nlog_path ) };

	struct PythonProgress : public ProgressMeter
	{
		// disable when running under the debugger, otherwise get strange crash in
		// wxProgressDialogTaskRunner::Entry sometime after the callback to Python ...
		const bool f_Enabled{ true };

		object & f_Progress;
		PythonProgress( object & progress )
			: f_Progress{ progress } {}

		void Pulse( const std::string & message ) override {
			if( f_Enabled && !f_Progress.is_none() )
				f_Progress( message );
		}

	} meter{ progress };

	TraceDebug( "path:'%S'", wnlog_path.c_str() );

	logfile_ptr_t logfile{ new NLogfile{ std::move( MakeLogAccessor( log_schema ) ) } };
	const Error error{ logfile->Open( wnlog_path, &meter ) };
	if( !Ok( error ) )
		logfile.reset();

	return logfile;
}


// Python access to the global tracker array
void SetGlobalTracker( unsigned tracker_idx, const NTimecode & timecode )
{
	GlobalTrackers::SetGlobalTracker( tracker_idx, timecode );
}


#ifdef VS2015U3
//
// Some versions of VS2015 fail to link Boost Python with errors like:
//   Wrapper.obj : error LNK2001 : unresolved external symbol "class NLogfile const volatile
//   * __cdecl boost::get_pointer<class NLogfile const volatile >(class NLogfile const
//   volatile *)" (? ? $get_pointer@$$CDVNLogfile@@@boost@@YAPEDVNLogfile@@PEDV1@@Z)
//
// For an explanation of the workaround below, see:
//  https://stackoverflow.com/questions/38261530/unresolved-external-symbols-since-visual-studio-2015-update-3-boost-python-link
//  https://github.com/TNG/boost-python-examples/issues/10
//
// The issue is apparently fixed in VS2017.
//

namespace boost
{
	template <> NLogfile const volatile * get_pointer( NLogfile const volatile *n ) { return n; }
	template <> NLogView const volatile * get_pointer( NLogView const volatile *n ) { return n; }
	template <> NEventView const volatile * get_pointer( NEventView const volatile *n ) { return n; }
	template <> NLineSet const volatile * get_pointer( NLineSet const volatile *n ) { return n; }
	template <> NHiliter const volatile * get_pointer( NHiliter const volatile *n ) { return n; }
}
#endif


// build the Python module interfaces
// References:
//  https://wiki.python.org/moin/boost.python/PointersAndSmartPointers
BOOST_PYTHON_MODULE( Nlog )
{
	class_<std::vector<int> >( "ivec" )
		.def( "__iter__", iterator<std::vector<int>>() )
		;

	// although boost::noncopyable is specified here, Boost still attempts
	// to make use of a copy constructor, so the kludged default constructors
	// are needed for the time being
	class_<PerfTimer>( "PerfTimer" )
		.def( "Overall", &PerfTimer::Overall )
		.def( "PerItem", &PerfTimer::PerItem )
		;

	class_<NHiliter, hiliter_ptr_t, boost::noncopyable>( "Hiliter", no_init )
		.def( "Search", &NHiliter::Search )
		.def( "Hit", &NHiliter::Hit )
		.def( "SetMatch", &NHiliter::SetMatch )
		;

	enum_<Match::Type>( "EnumSelector" )
		.value( "Literal", Match::e_Literal )
		.value( "RegularExpression", Match::e_RegularExpression )
		.value( "LogviewFilter", Match::e_LogviewFilter )
		.export_values()
		;

	enum_<MarkerNumber>( "EnumMarker" )
		.value( "StandardBase", MarkerNumber::e_MarkerNumberStandardBase )
		.value( "TrackerBase", MarkerNumber::e_MarkerNumberTrackerBase )
		.value( "History", MarkerNumber::e_MarkerNumberHistory )
		.export_values()
		;

	enum_<Style>( "EnumStyle" )
		.value( "AnnotationBase", Style::e_StyleAnnotationBase )
		.value( "Default", Style::e_StyleDefault )
		.value( "FieldBase", Style::e_StyleFieldBase )
		.value( "UserFormatBase", Style::e_StyleUserFormatBase )
		.export_values()
		;

	enum_<SLineMarginText::Type>( "EnumMarginType" )
		.value( "Empty", SLineMarginText::Type::e_None )
		.value( "LineNumber", SLineMarginText::Type::e_LineNumber )
		.value( "Offset", SLineMarginText::Type::e_Offset )
		.export_values()
		;

	enum_<SLineMarginText::Precision>( "EnumMarginPrecision" )
		.value( "MsecDotNsec", SLineMarginText::Precision::e_MsecDotNsec )
		.value( "Usec", SLineMarginText::Precision::e_Usec )
		.value( "Msec", SLineMarginText::Precision::e_Msec )
		.value( "Sec", SLineMarginText::Precision::e_Sec )
		.value( "MinSec", SLineMarginText::Precision::e_MinSec )
		.value( "HourMinSec", SLineMarginText::Precision::e_HourMinSec )
		.value( "DayHourMinSec", SLineMarginText::Precision::e_DayHourMinSec )
		.export_values()
		;

	class_<NTimecodeBase, boost::noncopyable>( "TimecodeBase", init<time_t, unsigned>() )
		.def( "GetUtcDatum", &NTimecodeBase::GetUtcDatum )
		.def( "GetFieldId", &NTimecodeBase::GetFieldId )
		;

	class_<NTimecode, boost::noncopyable>( "Timecode", init<time_t, int64_t>() )
		.def( "GetUtcDatum", &NTimecode::GetUtcDatum )
		.def( "GetOffsetNs", &NTimecode::GetOffsetNs )
		.def( "Normalise", &NTimecode::Normalise )
		.def( "Subtract", &NTimecode::Subtract )
		;

	class_<NViewCore>( "ViewCore", no_init )
		.def( "GetNumLines", &NViewCore::GetNumLines )
		;

	class_<NViewFieldAccess>( "ViewFieldAccess", no_init )
		.def( "GetNonFieldText", &NViewFieldAccess::GetNonFieldText ) \
		.def( "GetFieldText", &NViewFieldAccess::GetFieldText ) \
		.def( "GetFieldValueUnsigned", &NViewFieldAccess::GetFieldValueUnsigned ) \
		.def( "GetFieldValueSigned", &NViewFieldAccess::GetFieldValueSigned ) \
		.def( "GetFieldValueFloat", &NViewFieldAccess::GetFieldValueFloat ) \
		;

	class_<NViewLineTranslation>( "ViewLineTranslation", no_init )
		.def( "ViewLineToLogLine", &NViewLineTranslation::ViewLineToLogLine )
		.def( "LogLineToViewLine", &NViewLineTranslation::LogLineToViewLine )
		;

	class_<NViewHiliting>( "ViewHiliting", no_init )
		.def( "SetNumHiliter", &NViewHiliting::SetNumHiliter ) \
		.def( "GetHiliter", &NViewHiliting::GetHiliter ) \
		.def( "SetFieldMask", &NViewHiliting::SetFieldMask )
		;

	class_<NViewTimecode>( "ViewTimecode", no_init )
		.def( "GetNearestUtcTimecode", &NViewTimecode::GetNearestUtcTimecode, return_value_policy<manage_new_object>() ) \
		;

	class_<NLineSet, lineset_ptr_t, bases<NViewCore, NViewFieldAccess, NViewTimecode, NViewLineTranslation>>( "LineSet", no_init )
		;

	class_<NEventView, eventview_ptr_t, bases<NViewCore, NViewFieldAccess, NViewHiliting>>( "NEventView", no_init )
		.def( "Filter", &NEventView::Filter )
		.def( "Sort", &NEventView::Sort )
		.def( "IsContainer", &NEventView::IsContainer )
		.def( "GetChildren", &NEventView::GetChildren )
		.def( "GetParent", &NEventView::GetParent )
		.def( "LookupEventId", &NEventView::LookupEventId )
		;

	class_<NLogView, logview_ptr_t, bases<NViewFieldAccess, NViewTimecode, NViewHiliting>>( "LogView", no_init )
		.def( "Filter", &NLogView::Filter )
		.def( "GetContent", &NLogView::GetContent )
		.def( "ToggleBookmarks", &NLogView::ToggleBookmarks )
		.def( "GetNextBookmark", &NLogView::GetNextBookmark )
		.def( "GetNextAnnotation", &NLogView::GetNextAnnotation )
		.def( "SetLocalTrackerLine", &NLogView::SetLocalTrackerLine )
		.def( "GetLocalTrackerLine", &NLogView::GetLocalTrackerLine )
		.def( "GetGlobalTrackerLine", &NLogView::GetGlobalTrackerLine )
		.def( "SetupMarginText", &NLogView::SetupMarginText )
		.def( "SetHistoryLine", &NLogView::SetHistoryLine )
		;

	class_<NLogfile, logfile_ptr_t, boost::noncopyable>( "Logfile", no_init )
		.def( "GetState", &NLogfile::GetState )
		.def( "PutState", &NLogfile::PutState )
		.def( "CreateLineSet", &NLogfile::CreateLineSet )
		.def( "CreateLogView", &NLogfile::CreateLogView )
		.def( "CreateEventView", &NLogfile::CreateEventView )
		.def( "SetNumAutoMarker", &NLogfile::SetNumAutoMarker )
		.def( "SetAutoMarker", &NLogfile::SetAutoMarker )
		.def( "ClearAutoMarker", &NLogfile::ClearAutoMarker )
		.def( "SetTimezoneOffset", &NLogfile::SetTimezoneOffset )
		.def( "GetTimecodeBase", &NLogfile::GetTimecodeBase, return_value_policy<manage_new_object>() )
		;

	def( "Setup", Setup );
	def( "MakeLogfile", MakeLogfile );
	def( "SetGlobalTracker", SetGlobalTracker );
}

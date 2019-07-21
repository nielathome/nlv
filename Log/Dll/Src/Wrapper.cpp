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



/*-----------------------------------------------------------------------
 * MODULE
 -----------------------------------------------------------------------*/

// Python initialisation
void Setup( object logger )
{
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


// Python access to LogAccessor factory
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
		descriptor.m_FieldDescriptors.push_back( FieldDescriptor
		{
			extract<std::string>{ ifield_schema->attr( "Type" ) },
			extract<std::string>{ ifield_schema->attr( "Name" ) },
			extract<std::string>{ ifield_schema->attr( "Separator" ) },
			extract<unsigned>{ ifield_schema->attr( "SeparatorCount" ) },
			extract<unsigned>{ ifield_schema->attr( "MinWidth" ) }
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


// Python access to logfile factory
logfile_ptr_t MakeLogfile( const std::string & nlog_path, object log_schema, object progress )
{
	using converter_t = std::wstring_convert<std::codecvt_utf8_utf16<wchar_t>>;
	std::wstring wnlog_path{ converter_t{}.from_bytes( nlog_path ) };

	struct PythonProgress : public ProgressMeter
	{
		object & f_Progress;
		PythonProgress( object & progress )
			: f_Progress{ progress } {}

		void SetRange( size_t range ) override {
			if( !f_Progress.is_none() )
				f_Progress.attr( "SetRange" )( range );
		}

		virtual void SetProgress( size_t value ) override {
			if( !f_Progress.is_none() )
				f_Progress.attr( "SetProgress" )( value );
		}

	} meter{ progress };

	TraceDebug( "path:'%S'", wnlog_path.c_str() );

	logfile_ptr_t logfile{ new NLogfile{ std::move( MakeLogAccessor( log_schema ) ) } };
	const Error error{ logfile->Open( wnlog_path, &meter ) };
	if( !Ok( error ) )
		logfile.reset();

	return logfile;
}


// Python access to Selector factory
selector_ptr_t MakeSelector( object match, bool empty_selects_all, const NLogfile * logfile = nullptr )
{
	Match descriptor{
		extract<Match::Type>{ match.attr( "GetSelectorId" )() },
		extract<std::string>{ match.attr( "MatchText" ) },
		extract<bool>{ match.attr( "MatchCase" ) }
	};

	const LogSchemaAccessor * schema{ logfile ? logfile->GetSchema() : nullptr };

	selector_ptr_t selector{ new NSelector{ descriptor, empty_selects_all, schema } };
	const Error error{ selector->Ok() ? e_OK : TraceError( e_BadSelectorDefinition, "'%s'", descriptor.m_Text.c_str() ) };
	if( !Ok( error ) )
		selector.reset();

	return selector;
}
BOOST_PYTHON_FUNCTION_OVERLOADS( MakeSelectorOverloads, MakeSelector, 2, 3 )


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
	template <> NHiliter const volatile * get_pointer( NHiliter const volatile *n ) { return n; }
	template <> NSelector const volatile * get_pointer( NSelector const volatile *n ) { return n; }
	template <> NView const volatile * get_pointer( NView const volatile *n ) { return n; }
	template <> NLineSet const volatile * get_pointer( NLineSet const volatile *n ) { return n; }
	template <> NLogfile const volatile * get_pointer( NLogfile const volatile *n ) { return n; }
}
#endif


// build the Python module interfaces
// References:
//  https://wiki.python.org/moin/boost.python/PointersAndSmartPointers
BOOST_PYTHON_MODULE( Nlog )
{
	// although boost::noncopyable is specified here, Boost still attempts
	// to make use of a copy constructor, so the kludged default constructors
	// are needed for the time being
	class_<PerfTimer, boost::noncopyable>( "PerfTimer" )
		.def( "Overall", &PerfTimer::Overall )
		.def( "PerItem", &PerfTimer::PerItem )
		;

	class_<NHiliter, hiliter_ptr_t, boost::noncopyable>( "Hiliter" )
		.def( "Search", &NHiliter::Search )
		.def( "Hit", &NHiliter::Hit )
		.def( "SetSelector", &NHiliter::SetSelector )
		;

	enum_<Match::Type>( "EnumSelector" )
		.value( "Literal", Match::e_Literal )
		.value( "RegularExpression", Match::e_RegularExpression )
		.value( "LogviewFilter", Match::e_LogviewFilter )
		.export_values()
		;

	enum_<NConstants>( "EnumConstants" )
		.value( "StyleBaseMarker", NConstants::e_StyleBaseMarker )
		.value( "StyleBaseTracker", NConstants::e_StyleBaseTracker )
		.export_values()
		;

	class_<NTimecodeBase, boost::noncopyable>( "NTimecodeBase", init<time_t, unsigned>() )
		.def( "GetUtcDatum", &NTimecodeBase::GetUtcDatum )
		.def( "GetFieldId", &NTimecodeBase::GetFieldId )
		;

	class_<NTimecode, boost::noncopyable>( "NTimecode", init<time_t, int64_t>() )
		.def( "GetUtcDatum", &NTimecode::GetUtcDatum )
		.def( "GetOffsetNs", &NTimecode::GetOffsetNs )
		.def( "Normalise", &NTimecode::Normalise )
		.def( "Subtract", &NTimecode::Subtract )
		;

	class_<NSelector, selector_ptr_t, boost::noncopyable>( "Selector" )
		;

	// NLineSet and NView present similar interfaces to Python, but have
	// incompatible inheritance structure; so using a macro to extract the
	// commonality
	#define NFilterView_Members(CLS) \
		.def( "GetUtcTimecode", &CLS::GetUtcTimecode, return_value_policy<manage_new_object>() ) \
		.def( "GetNonFieldText", &CLS::GetNonFieldText ) \
		.def( "GetFieldText", &CLS::GetFieldText ) \
		.def( "GetFieldValueUnsigned", &CLS::GetFieldValueUnsigned ) \
		.def( "GetFieldValueSigned", &CLS::GetFieldValueSigned ) \
		.def( "GetFieldValueFloat", &CLS::GetFieldValueFloat ) \
		.def( "SetNumHiliter", &CLS::SetNumHiliter ) \
		.def( "GetHiliter", &CLS::GetHiliter ) \
		.def( "SetFieldMask", &CLS::SetFieldMask )

	class_<NLineSet, lineset_ptr_t, boost::noncopyable>( "LineSet" )
		NFilterView_Members( NLineSet )
		.def( "Filter", &NLineSet::Filter )
		.def( "GetNumLines", &NLineSet::GetNumLines )
		.def( "ViewLineToLogLine", &NLineSet::ViewLineToLogLine )
		.def( "LogLineToViewLine", &NLineSet::LogLineToViewLine )
		;

	class_<NView, view_ptr_t, boost::noncopyable>( "View" )
		NFilterView_Members( NView )
		.def( "Filter", &NView::Filter )
		.def( "GetContent", &NView::GetContent )
		.def( "ToggleBookmarks", &NView::ToggleBookmarks )
		.def( "GetNextBookmark", &NView::GetNextBookmark )
		.def( "GetNextAnnotation", &NView::GetNextAnnotation )
		.def( "SetLocalTrackerLine", &NView::SetLocalTrackerLine )
		.def( "GetLocalTrackerLine", &NView::GetLocalTrackerLine )
		.def( "GetGlobalTrackerLine", &NView::GetGlobalTrackerLine )
		;

	class_<NLogfile, logfile_ptr_t, boost::noncopyable>( "Logfile" )
		.def( "GetState", &NLogfile::GetState )
		.def( "PutState", &NLogfile::PutState )
		.def( "CreateView", &NLogfile::CreateView )
		.def( "CreateLineSet", &NLogfile::CreateLineSet )
		.def( "SetNumAutoMarker", &NLogfile::SetNumAutoMarker )
		.def( "SetAutoMarker", &NLogfile::SetAutoMarker )
		.def( "ClearAutoMarker", &NLogfile::ClearAutoMarker )
		.def( "SetTimezoneOffset", &NLogfile::SetTimezoneOffset )
		.def( "GetTimecodeBase", &NLogfile::GetTimecodeBase, return_value_policy<manage_new_object>() )
		;

	def( "Setup", Setup );
	def( "MakeLogfile", MakeLogfile );
	def( "MakeSelector", MakeSelector, MakeSelectorOverloads{} );
	def( "SetGlobalTracker", SetGlobalTracker );
}

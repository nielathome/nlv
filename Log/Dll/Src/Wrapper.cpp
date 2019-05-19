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
namespace python = boost::python;

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
	python::object g_Logger;


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
void Setup( python::object logger )
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


// Python access to logfile factory
logfile_ptr_t MakeLogfile( const std::string & nlog_path, NLogAccessor * log_accessor, python::object progress, size_t skip_lines = 0 )
{
	using converter_t = std::wstring_convert<std::codecvt_utf8_utf16<wchar_t>>;
	std::wstring wnlog_path{ converter_t{}.from_bytes( nlog_path ) };

	struct PythonProgress : public ProgressMeter
	{
		python::object & f_Progress;
		PythonProgress( python::object & progress )
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

	logfile_ptr_t logfile{ new NLogfile{ log_accessor } };
	const Error error{ logfile->Open( wnlog_path, &meter, skip_lines ) };
	if( !Ok( error ) )
		logfile.reset();

	return logfile;
}
BOOST_PYTHON_FUNCTION_OVERLOADS( MakeLogfileOverloads, MakeLogfile, 3, 4 )


// Python access to LogAccessor factory
logaccessor_ptr_t MakeLogAccessor( python::object log_schema, python::object formatter )
{
	using as_string = python::extract<std::string>;
	using as_char = python::extract<char>;
	using as_unsigned = python::extract<unsigned>;
	using as_size = python::extract<size_t>;

	const std::string accessor_name{ as_string{ log_schema.attr( "GetAccessorName" )() } };
	const std::string guid{ as_string{ log_schema.attr( "GetGuid" )() } };
	const std::string match_desc{ as_string{ log_schema.attr( "GetMatchDesc" )() } };
	const size_t num_fields{ as_size{ log_schema.attr( "GetNumFields" )() } };
	const unsigned text_offset_size{as_unsigned{ log_schema.attr( "GetTextOffsetSize" )() } };

	fielddescriptor_list_t field_descs; field_descs.reserve( num_fields + 2 );
	for( size_t i = 0; i < num_fields; ++i )
	{
		python::object field_schema{ log_schema.attr( "GetFieldSchema" )(i) };

		const std::string field_type{ as_string{ field_schema.attr( "Type" ) } };
		const std::string field_name{ as_string{ field_schema.attr( "Name" ) } };
		const std::string separator{ as_string{ field_schema.attr( "Separator" ) } };
		const unsigned separator_count{ as_unsigned{ field_schema.attr( "SeparatorCount" ) } };
		const unsigned min_width{ as_unsigned{ field_schema.attr( "MinWidth" ) } };

		// using emplace_back here results in compiler unable to find FieldDescriptor constructor ??
		field_descs.push_back( FieldDescriptor{ field_type, field_name, separator, separator_count, min_width } );
	}

	const size_t num_formatters{ as_size{ formatter.attr( "GetNumFormats" )() } };
	formatdescriptor_list_t formats;
	for( size_t i = 0; i < num_formatters; ++i )
	{
		const std::string regex_text{ as_string{ formatter.attr( "GetFormatRegex" )( i ) } };
		std::regex_constants::syntax_option_type flags{
			std::regex_constants::ECMAScript
			| std::regex_constants::optimize
		};

		FormatDescriptor line_formatter{ std::regex{ regex_text, flags} };

		const size_t num_styles{ as_size{ formatter.attr( "GetFormatNumStyles" )( i ) } };
		for( size_t j = 0; j < num_styles; ++j )
			line_formatter.m_Styles.push_back( as_unsigned{ formatter.attr( "GetFormatStyle" )( i, j ) } );

		formats.push_back( std::move( line_formatter ) );
	}

	TraceDebug( "name:'%s' match_desc:'%s' guid:'%s'", accessor_name.c_str(), match_desc.c_str(), guid.c_str() );

	logaccessor_ptr_t accessor{ new NLogAccessor{
		accessor_name,
		guid,
		text_offset_size,
		std::move( field_descs ),
		match_desc,
		std::move( formats )
	} };

	const Error error{ accessor->Ok() ? e_OK : e_BadAccessorName };
	if( !Ok( error ) )
		accessor.reset();

	return accessor;
}


// Python access to Selector factory
selector_ptr_t MakeSelector( python::object match, bool empty_selects_all, const NLogfile * logfile = nullptr )
{
	Match descriptor{
		python::extract<Match::Type>{ match.attr( "GetSelectorId" )() },
		python::extract<std::string>{ match.attr( "MatchText" ) },
		python::extract<bool>{ match.attr( "MatchCase" ) }
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
	template <> NLogAccessor const volatile * get_pointer( NLogAccessor const volatile *n ) { return n;  }
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
	using namespace python;

	// although boost::noncopyable is specified here, Boost still attempts
	// to make use of a copy constructor, so the kludged default constructors
	// are needed for the time being
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

	class_<NLogAccessor, logaccessor_ptr_t, boost::noncopyable>( "LogAccessor" )
		;

	// NLineSet and NView present similar interfaces to Pythin, but have
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
		.def( "Filter", &CLS::Filter ) \
		.def( "SetFieldMask", &CLS::SetFieldMask )

	class_<NLineSet, lineset_ptr_t, boost::noncopyable>( "LineSet" )
		NFilterView_Members( NLineSet )
		.def( "GetNumLines", &NLineSet::GetNumLines )
		.def( "ViewLineToLogLine", &NLineSet::ViewLineToLogLine )
		.def( "LogLineToViewLine", &NLineSet::LogLineToViewLine )
		;

	class_<NView, view_ptr_t, boost::noncopyable>( "View" )
		NFilterView_Members( NView )
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
	def( "MakeLogfile", MakeLogfile, MakeLogfileOverloads{} );
	def( "MakeLogAccessor", MakeLogAccessor );
	def( "MakeSelector", MakeSelector, MakeSelectorOverloads{} );
	def( "SetGlobalTracker", SetGlobalTracker );
}

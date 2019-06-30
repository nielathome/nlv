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
#pragma once

// Nlog includes
#include "Match.h"
#include "Nfilesystem.h"
#include "Nmisc.h"
#include "Ntime.h"
#include "Ntrace.h"

// C++ includes
#include <list>
#include <map>
#include <memory>
#include <regex>
#include <string>
#include <vector>



/*-----------------------------------------------------------------------
 * Types
 -----------------------------------------------------------------------*/

// Scintilla compatible line number / line size type
using nlineno_t = int;

template<typename T_VALUE>
nlineno_t nlineno_cast( T_VALUE value )
{
	return static_cast<nlineno_t>(value);
}



/*-----------------------------------------------------------------------
 * FieldValue
 -----------------------------------------------------------------------*/

// support three basic field types
enum class FieldValueType
{
	unsigned64,
	signed64,
	float64,
	invalid
};

// convert a type to the matching field-value-type
template<typename> struct TypeToFieldType {};

template<> struct TypeToFieldType<uint64_t> {
	static const FieldValueType type{ FieldValueType::unsigned64 };
};

template<> struct TypeToFieldType<int64_t> {
	static const FieldValueType type{ FieldValueType::signed64 };
};

template<> struct TypeToFieldType<double> {
	static const FieldValueType type{ FieldValueType::float64 };
};

// field value type
class FieldValue
{
private:
	FieldValueType m_Type{ FieldValueType::invalid };
	uint64_t m_Payload{ 0 };

public:
	FieldValue( void ) {}

	template<typename T_VALUE>
	FieldValue( T_VALUE value )
		:
		m_Type{ TypeToFieldType<T_VALUE>::type },
		m_Payload{ *reinterpret_cast<uint64_t *>(&value) }
	{
	}

	FieldValue & operator = ( const FieldValue & rhs ) {
		m_Type = rhs.m_Type;
		m_Payload = rhs.m_Payload;
		return *this;
	}

	template<typename T_RESULT>
	T_RESULT As( void ) const
	{
		if( TypeToFieldType<T_RESULT>::type != m_Type )
			throw std::runtime_error{ "Invalid FieldValue conversion" };

		return *reinterpret_cast<const T_RESULT *>(&m_Payload);
	}

	template<typename T_RESULT>
	T_RESULT Convert( void ) const
	{
		switch( m_Type )
		{
		case FieldValueType::unsigned64:
			return static_cast<T_RESULT>(m_Payload);

		case FieldValueType::signed64:
			return static_cast<T_RESULT>(*reinterpret_cast<const int64_t *>(&m_Payload));

		case FieldValueType::float64:
			return static_cast<T_RESULT>(*reinterpret_cast<const double *>(&m_Payload));

		default:
			throw std::runtime_error{ "Invalid convert" };
		}

		return T_RESULT{};
	}

	FieldValue Convert( FieldValueType type ) const
	{
		switch( type )
		{
		case FieldValueType::unsigned64:
			return FieldValue{ Convert<uint64_t>() };

		case FieldValueType::signed64:
			return FieldValue{ Convert<int64_t>() };

		case FieldValueType::float64:
			return FieldValue{ Convert<double>() };

		default:
			throw std::runtime_error{ "Invalid convert" };
		}
	}

	FieldValueType GetType( void ) const {
		return m_Type;
	}

	std::string AsString( void ) const;
};

using fieldvalue_t = FieldValue;



/*-----------------------------------------------------------------------
 * Style
 -----------------------------------------------------------------------*/

enum Style : char
{
	e_StyleDefault = 0,
	e_StyleField00 = 1,
	e_StyleField19 = 20
};



/*-----------------------------------------------------------------------
 * ProgressMeter
 -----------------------------------------------------------------------*/

// provide progress information back to the UI
struct ProgressMeter
{
	virtual void SetRange( size_t /* range */ ) {}
	virtual void SetProgress( size_t /* value */ ) {}
};



/*-----------------------------------------------------------------------
 * LineBuffer
 -----------------------------------------------------------------------*/

// small class to hold a copy of a line's text
class LineBuffer
{
private:
	static const unsigned c_TypicalLineLength{ 2048 };
	
	bool m_Reserved{ false };
	std::string m_Buffer;

	void Reserve( void )
	{
		if( !m_Reserved )
		{
			// improve chance that Append does not have to re-allocate string
			m_Buffer.reserve( c_TypicalLineLength );
			m_Reserved = true;
		}
	}

public:
	void Append( char ch, size_t cnt = 1 ) {
		Reserve();
		m_Buffer.append( cnt, ch );
	}

	void Append( const char * first, const char * last ) {
		Reserve();
		m_Buffer.append( first, last );
	}

	void Clear( void ) {
		m_Buffer.clear();
	}

	void Replace( char ch, size_t pos, size_t cnt ) {
		m_Buffer.replace( pos, cnt, cnt, ch );
	}

	// C style pointer access
	const char * First( void ) const {
		return m_Buffer.c_str();
	}

	const char * Last( void ) const {
		return First() + m_Buffer.size();
	}
};



/*-----------------------------------------------------------------------
 * LineAccessor
 -----------------------------------------------------------------------*/

// interface for accessing irregular log line data
struct LineAccessorIrregular
{
	virtual nlineno_t GetLength( void ) const = 0;
	virtual nlineno_t GetLineNo( void ) const = 0;
};


// interface for accessing regular log line data
struct LineAccessor : public LineAccessorIrregular
{
	virtual bool IsRegular( void ) const = 0;
	virtual const LineAccessorIrregular * NextIrregular( void ) const = 0;
	virtual void GetText( const char ** first, const char ** last ) const = 0;
	virtual void GetNonFieldText( const char ** first, const char ** last ) const = 0;
	virtual void GetFieldText( unsigned field_id, const char ** first, const char ** last ) const = 0;
	virtual fieldvalue_t GetFieldValue( unsigned field_id ) const = 0;
	virtual NTimecode GetUtcTimecode( void ) const = 0;
};



/*-----------------------------------------------------------------------
 * LineVisitor
 -----------------------------------------------------------------------*/

// interface to support visiting all lines in a set (e.g. a log file)
struct LineVisitor
{
	virtual ~LineVisitor( void ) {}

	// perform a task on a single log-file line; implemented by Visitor user
	struct Task
	{
		// can be called from multiple threads; note that the visit_line_no and the
		// log_line line number can be different - the visitor line numbers are mapped
		// by the VisitLineToLogLine member
		virtual void Action( const LineAccessor & line, nlineno_t visit_line_no ) = 0;

	};
	using task_ptr_t = std::shared_ptr<Task>;

	// Visitor interface (callback); implemented by Visitor user
	struct Visitor
	{
		// the total number of lines that will be processed
		virtual void SetNumLines( nlineno_t num_lines ) {}

		// create a new Task for processing a subset of lines
		virtual task_ptr_t MakeTask( nlineno_t num_lines ) = 0;

		// combine the computed results from the Task into this Visitor
		// guaranteed to be called in visitor line-number sequence
		virtual void Join( task_ptr_t task ) = 0;
	};

	// "visit" a single line; use as a generalised line accessor
	virtual void VisitLine( Task & task, nlineno_t visit_line_no ) const = 0;

	// apply callback to a single line; signature is void f(const LineAccessor & log_line)
	template<typename T_FUNC>
	void VisitLine( nlineno_t visit_line_no, T_FUNC & functor )
	{
		using functor_t = T_FUNC;

		struct LocalTask : public Task
		{
			functor_t & f_Functor;
			LocalTask( functor_t & functor )
				: f_Functor{ functor } {}

			void Action( const LineAccessor & line, nlineno_t visit_line_no ) override {
				f_Functor( line );
			}
		};

		LocalTask task{ functor };
		VisitLine( task, visit_line_no );
	}
};



/*-----------------------------------------------------------------------
 * LogSchemaAccessor
 -----------------------------------------------------------------------*/

// all access to information about a logfile is abstracted by this interface
struct LogSchemaAccessor
{
	virtual size_t GetNumFields( void ) const = 0;
	virtual std::string GetFieldName( unsigned field_id ) const = 0;
	virtual FieldValueType GetFieldType( unsigned field_id ) const = 0;
	virtual uint16_t GetFieldEnumCount( unsigned field_id ) const = 0;
	virtual const char * GetFieldEnumName( unsigned field_id, uint16_t enum_id ) const = 0;

	// misc logfile info; timecode field index and UTC datum for the log file
	virtual const NTimecodeBase & GetTimecodeBase( void ) const = 0;
};



/*-----------------------------------------------------------------------
 * FieldDescriptor
 -----------------------------------------------------------------------*/

// describe a field; analog of Python's G_FieldSchema
struct FieldDescriptor
{
	// field "type" (e.g. "enum16") - the key used by FieldFactory
	std::string f_Type;

	// arbitrary name - used LVF/LVA for selection/matching
	std::string f_Name;

	// field separator sequence
	std::string f_Separator;

	// count of separators; one solution for case where field contains f_Separator
	unsigned f_SeparatorCount;

	// field minimum width; another solution for case where field contains f_Separator
	unsigned f_MinWidth;
};

using fielddescriptor_list_t = std::vector<FieldDescriptor>;



/*-----------------------------------------------------------------------
 * FormatDescriptor
 -----------------------------------------------------------------------*/

 // describe a formatter; analog of Python's G_Formatter
struct FormatDescriptor
{
	std::regex m_Regex;
	std::vector<unsigned> m_Styles;
};

using formatdescriptor_list_t = std::list<FormatDescriptor>;



/*-----------------------------------------------------------------------
 * ViewProperties
 -----------------------------------------------------------------------*/

class ViewProperties
{
protected:
	ChangeTracker m_Tracker{ true };

public:
	const ChangeTracker & GetTracker( void ) const {
		return m_Tracker;
	}

	// set the field mask and re-calculate line lengths
	virtual void SetFieldMask( uint64_t field_mask ) = 0;
};



/*-----------------------------------------------------------------------
 * ViewMap
 -----------------------------------------------------------------------*/

struct ViewMap
{
	// line start locations in the view
	std::vector<nlineno_t> m_Lines;

	// key text metrics
	nlineno_t m_TextLen{ 0 };
	nlineno_t m_NumLinesOrOne{ 0 };

	// warning: an empty Scintilla document has a line count of 1
	// this flag disambiguates the two cases
	bool m_IsEmpty{ true };
};



/*-----------------------------------------------------------------------
 * ViewAccessor
 -----------------------------------------------------------------------*/

enum class e_LineData
{
	Text,
	Style,
	_Count
};


struct ViewAccessor : public LineVisitor
{
	// visit all lines in scope; use for searching/filtering
	virtual void VisitLines( Visitor & visitor, bool include_irregular ) const = 0;

	// basic line access (for SViewCellBuffer)
	virtual nlineno_t GetNumLines( void ) const = 0;
	virtual const LineBuffer & GetLine( e_LineData type, nlineno_t line_no ) const = 0;
	virtual nlineno_t LogLineToViewLine( nlineno_t log_line_no, bool exact = false ) const = 0;
	virtual nlineno_t ViewLineToLogLine( nlineno_t view_line_no ) const = 0;

	// view configuration; optional (can return null)
	virtual ViewProperties * GetProperties( void ) {
		return nullptr;
	}

	// view map; optional (can return null)
	virtual const ViewMap * GetMap( void ) {
		return nullptr;
	}
	
	// NIEL remove after re-factoring
	virtual nlineno_t GetLineLength( nlineno_t line_no ) const = 0;
	virtual NTimecode GetUtcTimecode( nlineno_t line_no ) const = 0;

	// update the view to contain solely logfile lines which are matched by
	// the given selector
	virtual void Filter( Selector * selector, LineAdornmentsProvider * adornments_provider, bool add_irregular ) = 0;
};

using viewaccessor_ptr_t = std::shared_ptr<ViewAccessor>;



/*-----------------------------------------------------------------------
 * LogAccessor
 -----------------------------------------------------------------------*/

struct LogAccessor : public LineVisitor
{
	// visit all lines in scope; use for searching/filtering
	virtual void VisitLines( Visitor & visitor, uint64_t field_mask, bool include_irregular ) const = 0;

	// core setup
	virtual Error Open( const std::filesystem::path & file_path, ProgressMeter *, size_t skip_lines ) = 0;
	virtual viewaccessor_ptr_t CreateViewAccessor( void ) = 0;

	// field schema access
	virtual const LogSchemaAccessor * GetSchema( void ) const = 0;

	// timezone control
	virtual void SetTimezoneOffset( int offset_sec ) = 0;
};



/*-----------------------------------------------------------------------
 * LogAccessorFactory
 -----------------------------------------------------------------------*/

struct LogAccessorDescriptor
{
	std::string m_Name;
	std::string m_Guid;
	std::string m_MatchDesc;
	unsigned m_TextOffsetsSize;
	fielddescriptor_list_t m_FieldDescriptors;
	formatdescriptor_list_t m_LineFormatters;
};


class LogAccessorFactory
{
public:
	static void RegisterLogAccessor( const std::string & name, LogAccessor * (*creator)(LogAccessorDescriptor &) );

	// factory for creating LogAccessor interfaces
	static LogAccessor * Create( LogAccessorDescriptor & descriptor );

protected:
	static std::map<std::string, LogAccessor * (*)(LogAccessorDescriptor &)> m_Makers;
};

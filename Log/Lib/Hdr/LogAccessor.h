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
#include "Field.h"
#include "Match.h"
#include "Nfilesystem.h"
#include "Nmisc.h"
#include "Ntime.h"
#include "Ntrace.h"

// C++ includes
#include <list>
#include <map>
#include <regex>



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


struct LineKey
{
	nlineno_t f_LineNo;
	uint64_t f_FieldMask;

	bool operator < ( const LineKey & rhs ) const {
		if( f_LineNo != rhs.f_LineNo )
			return f_LineNo < rhs.f_LineNo;
		else
			return f_FieldMask < rhs.f_FieldMask;
	}
};



/*-----------------------------------------------------------------------
 * Style
 -----------------------------------------------------------------------*/

enum Style : char
{
	e_StyleAnnotationBase = 40,
	e_StyleDefault = 50,
	e_StyleFieldBase = 51,
	e_StyleUserFormatBase = 80
};



/*-----------------------------------------------------------------------
 * ProgressMeter
 -----------------------------------------------------------------------*/

// provide progress information back to the UI
struct ProgressMeter
{
	virtual void Pulse( const std::string & /* message */ ) {}
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
	LineBuffer( void ) {}

	LineBuffer( const LineBuffer & rhs ) = default;

	LineBuffer( LineBuffer && rhs )
		: m_Reserved{ rhs.m_Reserved }, m_Buffer{ std::move( rhs.m_Buffer ) } {}

	void Append( char ch, size_t cnt = 1 ) {
		Reserve();
		m_Buffer.append( cnt, ch );
	}

	void Append( const char * first, const char * last ) {
		Reserve();
		m_Buffer.append( first, last );
	}

	bool Empty( void ) const {
		return m_Buffer.empty();
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

// interface for accessing log line data and metadata
struct LineAccessor
{
	virtual nlineno_t GetLineNo( void ) const = 0;
	virtual nlineno_t GetLength( void ) const = 0;
	virtual void GetText( const char ** first, const char ** last ) const = 0;
	virtual bool IsRegular( void ) const = 0;
	virtual nlineno_t NextIrregularLineLength( void ) const = 0;
	virtual void GetNonFieldText( const char ** first, const char ** last ) const = 0;
	virtual void GetFieldText( unsigned field_id, const char ** first, const char ** last ) const = 0;
	virtual fieldvalue_t GetFieldValue( unsigned field_id ) const = 0;
};



/*-----------------------------------------------------------------------
 * Task
 -----------------------------------------------------------------------*/

// perform a task on a single log-file line
struct Task
{
	// can be called from multiple threads
	virtual void Action( const LineAccessor & line ) = 0;

};

using task_ptr_t = std::shared_ptr<Task>;



/*-----------------------------------------------------------------------
 * LogSchemaAccessor
 -----------------------------------------------------------------------*/

// all access to information about a logfile is abstracted by this interface
struct LogSchemaAccessor
{
	virtual size_t GetNumFields( void ) const = 0;
	virtual const FieldDescriptor & GetFieldDescriptor( unsigned field_id ) const = 0;
	virtual FieldValueType GetFieldType( unsigned field_id ) const = 0;
	virtual uint16_t GetFieldEnumCount( unsigned field_id ) const = 0;
	virtual const char * GetFieldEnumName( unsigned field_id, uint16_t enum_id ) const = 0;

	// misc logfile info; timecode field index and UTC datum for the log file
	virtual const NTimecodeBase & GetTimecodeBase( void ) const = 0;
};



/*-----------------------------------------------------------------------
 * LogAccessor
 -----------------------------------------------------------------------*/

struct ViewAccessor;
using viewaccessor_ptr_t = std::shared_ptr<ViewAccessor>;

struct LogAccessor
{
	// core setup
	virtual Error Open( const std::filesystem::path & file_path, ProgressMeter * ) = 0;
	virtual viewaccessor_ptr_t CreateViewAccessor( void ) = 0;

	// field schema access
	virtual const LogSchemaAccessor * GetSchema( void ) const = 0;

	// timezone control
	virtual void SetTimezoneOffset( int offset_sec ) = 0;
};

using logaccessor_ptr_t = std::unique_ptr<LogAccessor>;



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
 * LogAccessorDescriptor
 -----------------------------------------------------------------------*/

struct LogAccessorDescriptor
{
	std::string m_Name;
	std::string m_Guid;
	std::string m_RegexText;
	unsigned m_TextOffsetsSize;
	fielddescriptor_list_t m_FieldDescriptors;
	formatdescriptor_list_t m_LineFormatters;
};



/*-----------------------------------------------------------------------
 * LogAccessorFactory
 -----------------------------------------------------------------------*/

class LogAccessorFactory
{
public:
	static void RegisterLogAccessor( const std::string & name, logaccessor_ptr_t (*creator)(LogAccessorDescriptor &) );

	// factory for creating LogAccessor interfaces
	static logaccessor_ptr_t Create( LogAccessorDescriptor & descriptor );

protected:
	static std::map<std::string, logaccessor_ptr_t (*)(LogAccessorDescriptor &)> m_Makers;
};



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

enum class e_LineData
{
	Text,
	Style,
	_Count
};

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

	virtual nlineno_t GetLineLength( nlineno_t line_no ) const = 0;
	virtual const LineBuffer & GetLine( e_LineData type, nlineno_t line_no ) const = 0;
};



/*-----------------------------------------------------------------------
 * ViewLineTranslation
 -----------------------------------------------------------------------*/

struct ViewLineTranslation
{
	virtual nlineno_t LogLineToViewLine( nlineno_t log_line_no, bool exact = false ) const = 0;
	virtual nlineno_t ViewLineToLogLine( nlineno_t view_line_no ) const = 0;
};



/*-----------------------------------------------------------------------
 * SortControl
 -----------------------------------------------------------------------*/

struct SortControl
{
	virtual void SetSort( unsigned col_num, int direction ) = 0;
};



/*-----------------------------------------------------------------------
 * HierarchyAccessor
 -----------------------------------------------------------------------*/

struct HierarchyAccessor
{
	virtual bool IsContainer( nlineno_t line_no ) = 0;
	virtual std::vector<int> GetChildren( nlineno_t line_no ) = 0;
	virtual int GetParent( nlineno_t line_no ) = 0;
};



/*-----------------------------------------------------------------------
 * ViewAccessor
 -----------------------------------------------------------------------*/

struct ViewAccessor
{
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

			void Action( const LineAccessor & line ) override {
				f_Functor( line );
			}
		};

		LocalTask task{ functor };
		VisitLine( task, visit_line_no );
	}

	// basic line access
	virtual nlineno_t GetNumLines( void ) const = 0;

	// update the view to contain solely logfile lines which are matched by
	// the given selector
	virtual void Filter( selector_ptr_a selector, LineAdornmentsProvider * adornments_provider, bool add_irregular ) = 0;

	// search the view
	virtual std::vector<nlineno_t> Search( selector_ptr_a selector, LineAdornmentsProvider * adornments_provider) = 0;

	// view configuration
	virtual ViewProperties * GetProperties( void ) = 0;

	// optional interfaces
	virtual const ViewMap * GetMap( void ) {
		return nullptr;
	}

	virtual const ViewLineTranslation * GetLineTranslation( void ) {
		return nullptr;
	}

	virtual SortControl * GetSortControl( void ) {
		return nullptr;
	}

	virtual HierarchyAccessor * GetHierarchyAccessor( void ) {
		return nullptr;
	}

	virtual const ViewTimecode * GetTimecode( void ) {
		return nullptr;
	}
};

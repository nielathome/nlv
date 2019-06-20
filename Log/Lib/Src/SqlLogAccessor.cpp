//
// Copyright (C) 2019 Niel Clausen. All rights reserved.
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
#include "Nmisc.h"
#include "LogAccessor.h"

// C includes
#include "Deps/sqlite3.h"

// force link this module
void force_link_sqlaccessor_module() {}



void afunc( void )
{
	sqlite3 * db_handle{ nullptr };

	const int ret{ sqlite3_open( "hello", &db_handle ) };
}



/*-----------------------------------------------------------------------
* SqlLogAccessor, declarations
-----------------------------------------------------------------------*/

// the default log accessor is based on file mapping; the log must be entirely static
class SqlLogAccessor : public LogAccessor, public LogSchemaAccessor
{
private:
	// fake timecode; we don't support line timecodes in SQL logfiles yet
	NTimecodeBase m_TimecodeBase;

	// field schema
	const fielddescriptor_list_t m_FieldDescriptors;

protected:
	// LineVisitor interface
	void VisitLine( Task & task, nlineno_t visit_line_no, uint64_t field_mask ) const override;
	void VisitLines( Visitor & visitor, uint64_t field_mask, bool include_irregular, nlineno_t num_lines ) const override;

	SqlLogAccessor( LogAccessorDescriptor & descriptor );

public:
	// LogAccessor interfaces

	Error Open( const std::filesystem::path & file_path, ProgressMeter * progress, size_t skip_lines ) override;
	nlineno_t GetNumLines( void ) const override;
	const LineBuffer & GetLine( e_LineData type, nlineno_t line_no, uint64_t field_mask ) const override;
	void CopyLine( e_LineData type, nlineno_t line_no, uint64_t field_mask, LineBuffer * buffer ) const override;

	bool IsLineRegular( nlineno_t line_no ) const override {
		return true;
	}

	nlineno_t GetLineLength( nlineno_t line_no, uint64_t field_mask ) const override {
		return 0;
	}

	fieldvalue_t GetFieldValue( nlineno_t line_no, unsigned field_id ) const override {
		return FieldValue{};
	}

	NTimecode GetUtcTimecode( nlineno_t line_no ) const override {
		return NTimecode{};
	}

	void SetTimezoneOffset( int offset_sec ) override {}

	const LogSchemaAccessor * GetSchema( void ) const override {
		return this;
	}

public:
	// LogSchemaAccessor interfaces

	size_t GetNumFields( void ) const override {
		return m_FieldDescriptors.size();
	}

	std::string GetFieldName( unsigned field_id ) const override {
		return m_FieldDescriptors[ field_id ].f_Name;
	}

	FieldValueType GetFieldType( unsigned field_id ) const override {
		return FieldValueType::unsigned64;
	}

	uint16_t GetFieldEnumCount( unsigned field_id ) const override {
		return 0;
	}

	const char * GetFieldEnumName( unsigned field_id, uint16_t enum_id ) const override {
		return nullptr;
	}

	const NTimecodeBase & GetTimecodeBase( void ) const override {
		return m_TimecodeBase;
	}

public:
	static LogAccessor * MakeSqlLogAccessor( LogAccessorDescriptor & descriptor )
	{
		return new SqlLogAccessor( descriptor );
	}

};

static OnEvent RegisterMapLogAccessor
{
	OnEvent::EventType::Startup,
	[]() {
		LogAccessorFactory::RegisterLogAccessor( "sql", SqlLogAccessor::MakeSqlLogAccessor );
	}
};



/*-----------------------------------------------------------------------
 * SqlLogAccessor, definitions
 -----------------------------------------------------------------------*/

SqlLogAccessor::SqlLogAccessor( LogAccessorDescriptor & descriptor )
{

}


Error SqlLogAccessor::Open( const std::filesystem::path & file_path, ProgressMeter * progress, size_t skip_lines )
{
	return Error::e_BadDay;
}


nlineno_t SqlLogAccessor::GetNumLines( void ) const
{
	return 0;
}


const LineBuffer & SqlLogAccessor::GetLine( e_LineData type, nlineno_t line_no, uint64_t field_mask ) const
{
	static LineBuffer b;
	return b;
}


void SqlLogAccessor::CopyLine( e_LineData type, nlineno_t line_no, uint64_t field_mask, LineBuffer * buffer ) const
{

}





void SqlLogAccessor::VisitLine( Task & task, nlineno_t visit_line_no, uint64_t field_mask ) const
{

}


void SqlLogAccessor::VisitLines( Visitor & visitor, uint64_t field_mask, bool include_irregular, nlineno_t num_lines ) const
{

}

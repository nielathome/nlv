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



/*-----------------------------------------------------------------------
 * SqlStatement
 -----------------------------------------------------------------------*/

class SqlStatement;
using statement_ptr_t = std::unique_ptr<SqlStatement>;

class SqlStatement
{
private:
	sqlite3_stmt * m_Handle{ nullptr };

protected:
	friend class SqlDb;
	Error Open( sqlite3 * db, const char * sql_text );

public:
	~SqlStatement( void );

	Error Step( void );
	int GetAsInt( unsigned field_id );
	Error Close( void );
};


SqlStatement::~SqlStatement( void )
{
	Close();
}


Error SqlStatement::Open( sqlite3 * db, const char * sql_text )
{
	const char * tail{ nullptr };
	Error res{ e_OK };
	const int sql_ret{ sqlite3_prepare_v2( db, sql_text, -1, &m_Handle, &tail ) };

	if( sql_ret != SQLITE_OK )
		res = TraceError( e_SqlStatementOpen, "sql_res=[%d/%s] sql_text=[%s]", sql_ret, sqlite3_errstr( sql_ret ), sql_text );
	else if( (tail != nullptr) && (*tail != '\0') )
		res = TraceError( e_SqlStatementOpen, "sql_res=[%d/%s] tail=[%s]", sql_ret, sqlite3_errstr( sql_ret ), tail );

	return res;
}


Error SqlStatement::Step( void )
{
	Error res{ e_OK };
	const int sql_ret{ sqlite3_step( m_Handle ) };

	if( sql_ret == SQLITE_ROW )
		res = e_SqlRow;

	else if( sql_ret == SQLITE_DONE )
		res = e_SqlDone;

	else
		res = TraceError( e_SqlStatementStep, "sql_res=[%d/%s]", sql_ret, sqlite3_errstr( sql_ret ) );

	return res;
}


int SqlStatement::GetAsInt( unsigned field_id )
{
	return sqlite3_column_int( m_Handle, field_id );
}


Error SqlStatement::Close( void )
{
	Error res{ e_OK };

	if( m_Handle != nullptr )
	{
		const int sql_ret{ sqlite3_finalize( m_Handle ) };
		m_Handle = nullptr;

		if( sql_ret != SQLITE_OK )
			res = TraceError( e_SqlStatementClose, "sql_res=[%d/%s]", sql_ret, sqlite3_errstr( sql_ret ) );
	}

	return res;
}



/*-----------------------------------------------------------------------
 * SqlDb
 -----------------------------------------------------------------------*/

class SqlDb
{
private:
	sqlite3 * m_Handle{ nullptr };

public:
	~SqlDb( void );

	Error Open( const std::filesystem::path & file_path );
	Error Close( void );

	Error MakeStatement( const char * sql_text, statement_ptr_t & statement );
};


SqlDb::~SqlDb( void )
{
	Close();
}


Error SqlDb::Open( const std::filesystem::path & file_path )
{
	Error res{ e_OK };
	const int sql_ret{ sqlite3_open16( file_path.c_str(), &m_Handle ) };

	if( sql_ret != SQLITE_OK )
		res = TraceError( e_SqlDbOpen, "sql_res=[%d/%s] sql_path=[%s]", sql_ret, sqlite3_errstr( sql_ret ), file_path.c_str() );

	return res;
}


Error SqlDb::Close( void )
{
	Error res{ e_OK };

	if( m_Handle != nullptr )
	{
		const int sql_ret{ sqlite3_close( m_Handle ) };
		m_Handle = nullptr;

		if( sql_ret != SQLITE_OK )
			res = TraceError( e_SqlDbClose, "sql_res=[%d/%s]", sql_ret, sqlite3_errstr( sql_ret ) );
	}

	return res;
}


Error SqlDb::MakeStatement( const char * sql_text, statement_ptr_t & statement )
{
	statement = std::make_unique<SqlStatement>();
	return statement->Open( m_Handle, sql_text );
}



/*-----------------------------------------------------------------------
 * SqlLogAccessor, declarations
 -----------------------------------------------------------------------*/

// the default log accessor is based on file mapping; the log must be entirely static
class SqlLogAccessor : public LogAccessor, public LogSchemaAccessor
{
private:
	// the SQLite database
	SqlDb m_DB;

	nlineno_t m_NumLines{ 0 };

	// fake timecode; we don't support line timecodes in SQL logfiles yet
	NTimecodeBase m_TimecodeBase;

	// field schema
	const fielddescriptor_list_t m_FieldDescriptors;

private:
	Error CalcNumLines( void );

protected:
	// LineVisitor interface
	void VisitLine( Task & task, nlineno_t visit_line_no, uint64_t field_mask ) const override;
	void VisitLines( Visitor & visitor, uint64_t field_mask, bool include_irregular, nlineno_t num_lines ) const override;

	SqlLogAccessor( LogAccessorDescriptor & descriptor );

public:
	// LogAccessor interfaces

	Error Open( const std::filesystem::path & file_path, ProgressMeter *, size_t ) override;
	const LineBuffer & GetLine( e_LineData type, nlineno_t line_no, uint64_t field_mask ) const override;
//	void CopyLine( e_LineData type, nlineno_t line_no, uint64_t field_mask, LineBuffer * buffer ) const override;

	nlineno_t GetNumLines( void ) const override {
		return m_NumLines;
	}

	//bool IsLineRegular( nlineno_t line_no ) const override {
	//	return true;
	//}

	nlineno_t GetLineLength( nlineno_t line_no, uint64_t field_mask ) const override {
		return 0;
	}

	////fieldvalue_t GetFieldValue( nlineno_t line_no, unsigned field_id ) const override {
	////	return FieldValue{};
	////}

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



	void CreateViewAccessor( void ) override {
		//		return nullptr;
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


Error SqlLogAccessor::Open( const std::filesystem::path & file_path, ProgressMeter *, size_t )
{
	Error res{ m_DB.Open( file_path ) };

	if( Ok( res ) )
		UpdateError( res, CalcNumLines() );

	return res;
}


Error SqlLogAccessor::CalcNumLines( void )
{
	statement_ptr_t statement;
	Error res{ m_DB.MakeStatement( "select count(*) from reschedule", statement ) };
	UpdateError( res, statement->Step() );
	if( Ok( res ) )
		m_NumLines = statement->GetAsInt( 0 );

	return res;
}

const LineBuffer & SqlLogAccessor::GetLine( e_LineData type, nlineno_t line_no, uint64_t field_mask ) const
{
	static LineBuffer b;
	return b;
}


//void SqlLogAccessor::CopyLine( e_LineData type, nlineno_t line_no, uint64_t field_mask, LineBuffer * buffer ) const
//{
//
//}





void SqlLogAccessor::VisitLine( Task & task, nlineno_t visit_line_no, uint64_t field_mask ) const
{

}


void SqlLogAccessor::VisitLines( Visitor & visitor, uint64_t field_mask, bool include_irregular, nlineno_t num_lines ) const
{

}

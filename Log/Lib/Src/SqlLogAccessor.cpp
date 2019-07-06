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
* SqlViewAccessor, declarations
-----------------------------------------------------------------------*/

class SqlLogAccessor;

class SqlViewAccessor : public ViewAccessor
{
private:
	// our substrate
	SqlLogAccessor * m_LogAccessor;

public:
	SqlViewAccessor( SqlLogAccessor * accessor )
		: m_LogAccessor{ accessor }
	{}

public:
	// LineVisitor interface

	void VisitLine( Task & task, nlineno_t visit_line_no ) const override {}
	void VisitLines( Visitor & visitor, bool include_irregular ) const override {}

public:
	// ViewAccessor interfaces

	nlineno_t GetNumLines( void ) const override {
		return 0;
	}

	void Filter( Selector * selector, LineAdornmentsProvider * adornments_provider, bool add_irregular ) override;

	// fetch nearest preceding view line number to the supplied log line
	nlineno_t LogLineToViewLine( nlineno_t log_line_no, bool exact = false ) const override {
		return log_line_no;
	}

	nlineno_t ViewLineToLogLine( nlineno_t view_line_no ) const override {
		return view_line_no;
	}
};



/*-----------------------------------------------------------------------
 * SqlLogAccessor, declarations
 -----------------------------------------------------------------------*/

class SqlLogAccessor : public LogAccessor, public LogSchemaAccessor
{
private:
	// the SQLite database
	SqlDb m_DB;

	nlineno_t m_NumLines{ 0 };

	// field schema
	const fielddescriptor_list_t m_FieldDescriptors;

private:
	Error CalcNumLines( void );

protected:
	// LineVisitor interface

	void VisitLines( Visitor & visitor, uint64_t field_mask, bool include_irregular ) const override;

	SqlLogAccessor( LogAccessorDescriptor & descriptor );

public:
	// LogAccessor interfaces

	Error Open( const std::filesystem::path & file_path, ProgressMeter *, size_t ) override;

	void SetTimezoneOffset( int offset_sec ) override {
		// unsupported
	}

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
	
	viewaccessor_ptr_t CreateViewAccessor( void ) override {
		return std::make_shared<SqlViewAccessor>( this );
	}



	const NTimecodeBase & GetTimecodeBase( void ) const override {
		static NTimecodeBase fake;
		return fake;
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






void SqlLogAccessor::VisitLines( Visitor & visitor, uint64_t field_mask, bool include_irregular ) const
{
	statement_ptr_t statement;
	//if( !Ok( m_DB.MakeStatement( "select * from projection", statement ) ) )
	//	return;

	//while( statement->Step() )
	//{
	//	create a line visiotr
	//}
}



/*-----------------------------------------------------------------------
 * SqlViewAccessor, definitions
 -----------------------------------------------------------------------*/


void SqlViewAccessor::Filter( Selector * selector, LineAdornmentsProvider * adornments_provider, bool add_irregular ) 
{
	// TODO
}

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
using statement_ptr_t = std::shared_ptr<SqlStatement>;

class SqlStatement
{
private:
	sqlite3_stmt * m_Handle{ nullptr };

protected:
	friend class SqlDb;
	Error Open( sqlite3 * db, const char * sql_text );

public:
	~SqlStatement( void );

	Error Bind( int idx, int64_t value );
	Error Step( void );
	int GetAsInt( unsigned field_id ) const;
	int64_t GetAsInt64( unsigned field_id ) const;
	void GetAsText( unsigned field_id, const char ** first, const char ** last ) const;
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


Error SqlStatement::Bind( int idx, int64_t value )
{
	Error res{ e_OK };
	const int sql_ret{ sqlite3_bind_int64( m_Handle, idx, value ) };

	if( sql_ret != SQLITE_OK )
		res = TraceError( e_SqlStatementBind, "sql_res=[%d/%s]", sql_ret, sqlite3_errstr( sql_ret ) );

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


int SqlStatement::GetAsInt( unsigned field_id ) const
{
	return sqlite3_column_int( m_Handle, field_id );
}


int64_t SqlStatement::GetAsInt64( unsigned field_id ) const
{
	return sqlite3_column_int64( m_Handle, field_id );
}


void SqlStatement::GetAsText( unsigned field_id, const char ** first, const char ** last ) const
{
	*first = reinterpret_cast<const char *>(sqlite3_column_text( m_Handle, field_id ));
	*last = *first + sqlite3_column_bytes( m_Handle, field_id );
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

	Error MakeStatement( const char * sql_text, statement_ptr_t & statement ) const;
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


Error SqlDb::MakeStatement( const char * sql_text, statement_ptr_t & statement ) const
{
	statement = std::make_shared<SqlStatement>();
	return statement->Open( m_Handle, sql_text );
}



/*-----------------------------------------------------------------------
* SqlViewAccessor, declarations
-----------------------------------------------------------------------*/

class SqlLogAccessor;

class SqlViewAccessor
	:
	public ViewProperties,
	public ViewAccessor
{
private:
	// our substrate
	SqlLogAccessor * m_LogAccessor;

	// list of fields (columns) to display/search
	uint64_t m_FieldViewMask{ 0 };

public:
	SqlViewAccessor( SqlLogAccessor * accessor )
		: m_LogAccessor{ accessor }
	{}

public:
	// ViewProperties interfaces

	void SetFieldMask( uint64_t field_mask ) override {
		// record the change
		m_Tracker.RecordEvent();
		m_FieldViewMask = field_mask;
	}

public:
	// ViewAccessor interfaces

	void VisitLine( Task & task, nlineno_t visit_line_no ) const override;
	void VisitLines( Visitor & visitor ) const override;
	nlineno_t GetNumLines( void ) const override;
	void Filter( Selector * selector, LineAdornmentsProvider * adornments_provider, bool add_irregular ) override;

	// fetch nearest preceding view line number to the supplied log line
	nlineno_t LogLineToViewLine( nlineno_t log_line_no, bool exact = false ) const override {
		return log_line_no;
	}

	nlineno_t ViewLineToLogLine( nlineno_t view_line_no ) const override {
		return view_line_no;
	}

	ViewProperties * GetProperties( void ) override {
		return this;
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

	void VisitLines( Visitor & visitor, uint64_t field_mask ) const override;

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

	Error MakeStatement( const char * sql_text, statement_ptr_t & statement ) const {
		return m_DB.MakeStatement( sql_text, statement );
	}

	nlineno_t GetNumLines( void ) const {
		return m_NumLines;
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
	Error res{ MakeStatement( "SELECT count(*) FROM projection", statement ) };

	if( Ok( res ) )
		UpdateError( res, statement->Step() );

	if( Ok( res ) )
		m_NumLines = statement->GetAsInt( 0 );

	return res;
}



/*-----------------------------------------------------------------------
 * SqlLineAccessor
 -----------------------------------------------------------------------*/

//template<typename T_ACCESSOR>
class SqlLineAccessor : public LineAccessor
{
public:
	using accessor_t = SqlLogAccessor;

protected:
//	const accessor_t & m_Accessor;
	statement_ptr_t m_Statement;
	nlineno_t m_LineNo{ 0 };

	// transient store for line information
	mutable LineBuffer m_LineBuffer;

public:
	SqlLineAccessor( /*const accessor_t & accessor,*/ statement_ptr_t statement )
		: /*m_Accessor{ accessor },*/ m_Statement{ statement } {}

	void IncLineNo( void ) {
		++m_LineNo;
	}

public:
	// LineAccessor interfaces

	nlineno_t GetLineNo( void ) const override {
		return m_LineNo;
	}

	nlineno_t GetLength( void ) const override {
		return 0;
	}

	void GetText( const char ** first, const char ** last ) const override {
		*first = *last = nullptr;
	}

	// irregular/continuation lines not supported
	bool IsRegular( void ) const override {
		return true;
	}
	nlineno_t NextIrregularLineLength( void ) const override {
		return -1;
	}

	void GetNonFieldText( const char ** first, const char ** last ) const override {
		static const char dummy{ '\0' };
		*first = *last = &dummy;
	}

	void GetFieldText( unsigned field_id, const char ** first, const char ** last ) const override {
		m_Statement->GetAsText( field_id - 1, first, last );
	}

	fieldvalue_t GetFieldValue( unsigned field_id ) const override {
		return m_Statement->GetAsInt64( field_id - 1 );
	}

	NTimecode GetUtcTimecode( void ) const override {
		return NTimecode{};
//		return m_Accessor.GetUtcTimecode( m_LineNo );
	}
};


/*-----------------------------------------------------------------------
 * LineVisitor
 -----------------------------------------------------------------------*/


void SqlLogAccessor::VisitLines( Visitor & visitor, uint64_t field_mask ) const
{
	statement_ptr_t statement;
	Error res{ MakeStatement( "SELECT * FROM projection", statement ) };
	if( !Ok( res ) )
		return;

	task_ptr_t task{ visitor.MakeTask( m_NumLines ) };
	SqlLineAccessor line{ statement };
	while( statement->Step() == Error::e_SqlRow )
	{
		task->Action( line );
		line.IncLineNo();
	}
}



/*-----------------------------------------------------------------------
 * SqlViewAccessor, definitions
 -----------------------------------------------------------------------*/

void SqlViewAccessor::VisitLine( Task & task, nlineno_t visit_line_no ) const
{
	statement_ptr_t statement;
	Error res{ m_LogAccessor->MakeStatement( "SELECT * FROM projection WHERE rowid = ?1", statement ) };

	if( Ok( res ) )
		UpdateError( res, statement->Bind( 1, visit_line_no + 1 ) );

	if( Ok( res ) )
		UpdateError( res, statement->Step() );

	if( Ok( res ) )
	{
		SqlLineAccessor line{ statement };
		task.Action( line );
	}
}


void SqlViewAccessor::VisitLines( Visitor & visitor ) const
{

}

nlineno_t SqlViewAccessor::GetNumLines( void ) const
{
	return m_LogAccessor->GetNumLines();
}

void SqlViewAccessor::Filter( Selector * selector, LineAdornmentsProvider * adornments_provider, bool add_irregular ) 
{
	// TODO
}

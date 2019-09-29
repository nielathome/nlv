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
#include "Cache.h"
#include "FieldAccessor.h"
#include "LogAccessor.h"
#include "Nmisc.h"

// C includes
#include "sqlite3.h"

// C++ includes
#include <sstream>

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
	Error Open( sqlite3 * db, const char * sql_text, bool suppress_error_trace, const char ** tail = nullptr );

public:
	~SqlStatement( void );

	Error Bind( int idx, int value );
	Error Step( void );
	Error Reset( void );
	Error Close( void );

	int GetAsInt( unsigned field_id ) const;
	int64_t GetAsInt64( unsigned field_id ) const;
	double GetAsReal( unsigned field_id ) const;
	void GetAsText( unsigned field_id, const char ** first, const char ** last ) const;

	template<FieldValueType TYPE>
	fieldvalue_t GetValue( unsigned field_id ) const {}

	template<>
	fieldvalue_t GetValue<FieldValueType::signed64>( unsigned field_id ) const
	{
		return GetAsInt64( field_id );
	}

	template<>
	fieldvalue_t GetValue<FieldValueType::float64>( unsigned field_id ) const
	{
		return GetAsReal( field_id );
	}
};


SqlStatement::~SqlStatement( void )
{
	Close();
}


Error SqlStatement::Open( sqlite3 * db, const char * sql_text, bool suppress_error_trace, const char ** tail )
{
	const char * local_tail{ nullptr };
	if( tail == nullptr )
		tail = &local_tail;

	Error res{ e_OK };
	const int sql_ret{ sqlite3_prepare_v2( db, sql_text, -1, &m_Handle, tail ) };

	// ignore create error
	if( sql_ret != SQLITE_OK )
	{
		if( suppress_error_trace )
			res = e_SqlStatementOpen;
		else
			res = TraceError( e_SqlStatementOpen, "sql_res=[%d/%s] sql_text=[%s]", sql_ret, sqlite3_errstr( sql_ret ), sql_text );
	}
	
	// don't ignore parse related errors
	if( (local_tail != nullptr) && (*local_tail != '\0') )
		res = TraceError( e_SqlStatementOpen, "sql_res=[%d/%s] tail=[%s]", sql_ret, sqlite3_errstr( sql_ret ), *tail );

	return res;
}


Error SqlStatement::Bind( int idx, int value )
{
	Error res{ e_OK };
	const int sql_ret{ sqlite3_bind_int( m_Handle, idx, value ) };

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


Error SqlStatement::Reset( void )
{
	Error res{ e_OK };
	const int sql_ret{ sqlite3_reset( m_Handle ) };

	if( sql_ret != SQLITE_OK )
		res = TraceError( e_SqlStatementReset, "sql_res=[%d/%s]", sql_ret, sqlite3_errstr( sql_ret ) );

	return res;
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


int SqlStatement::GetAsInt( unsigned field_id ) const
{
	return sqlite3_column_int( m_Handle, field_id );
}


int64_t SqlStatement::GetAsInt64( unsigned field_id ) const
{
	return sqlite3_column_int64( m_Handle, field_id );
}


double SqlStatement::GetAsReal( unsigned field_id ) const
{
	return sqlite3_column_double( m_Handle, field_id );
}


void SqlStatement::GetAsText( unsigned field_id, const char ** first, const char ** last ) const
{
	*first = reinterpret_cast<const char *>(sqlite3_column_text( m_Handle, field_id ));
	*last = *first + sqlite3_column_bytes( m_Handle, field_id );
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

	Error MakeStatement( const char * sql_text, bool step, bool suppress_error_trace, statement_ptr_t & statement ) const;
	Error ExecuteStatements( const char * sql_text ) const;
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


Error SqlDb::MakeStatement( const char * sql_text, bool step, bool suppress_error_trace, statement_ptr_t & statement ) const
{
	statement = std::make_shared<SqlStatement>();

	Error res{ statement->Open( m_Handle, sql_text, suppress_error_trace ) };

	if( step && Ok( res ) )
		UpdateError( res, statement->Step() );

	return res;
}

Error SqlDb::ExecuteStatements( const char * sql_text ) const
{
	Error res{ e_Success };
	const char * tail{ sql_text };
	while( tail && *tail != '\0' && Ok( res ) )
	{
		statement_ptr_t statement{ std::make_shared<SqlStatement>() };
		res = statement->Open( m_Handle, tail, false, &tail );
		if( Ok( res ) )
			UpdateError( res, statement->Step() );
	}

	return res;
}



/*-----------------------------------------------------------------------
 * SqlFieldAccessor
 -----------------------------------------------------------------------*/

// forwards
struct SqlFieldAccessor;
using sqlfieldaccessor_maker_t = FieldTraits<SqlFieldAccessor>::field_ptr_t (*) (const FieldDescriptor & field_desc, unsigned field_id);

struct SqlFieldAccessor : public FieldFactory<SqlFieldAccessor, sqlfieldaccessor_maker_t>
{
	SqlFieldAccessor( const FieldDescriptor &, unsigned field_id )
		: c_FieldId{ field_id } {}

	SqlFieldAccessor( FieldValueType type, unsigned field_id )
		: c_FieldType{ type }, c_FieldId{ field_id } {}

	// the field's class
	const FieldValueType c_FieldType{ FieldValueType::invalid };

	// effectively, the index of this field within the parent index
	const unsigned c_FieldId;

	// fetch the field's current (text) value
	void GetAsText( statement_ptr_t statement, const char ** first, const char ** last ) const {
		statement->GetAsText( c_FieldId, first, last );
	}

	// fetch the field's current (binary) value
	virtual fieldvalue_t GetValue( statement_ptr_t statement ) const {
		return 0ULL;
	}
};



/*-----------------------------------------------------------------------
 * SqlFieldAccessorScalar
 -----------------------------------------------------------------------*/

template<FieldValueType TYPE>
struct SqlFieldAccessorScalar : public SqlFieldAccessor
{
	SqlFieldAccessorScalar( const FieldDescriptor &, unsigned field_id )
		: SqlFieldAccessor{ TYPE, field_id } {}

	fieldvalue_t GetValue( statement_ptr_t statement ) const override {
		return statement->GetValue<TYPE>( c_FieldId );
	}
};

using SqlFieldAccessorUnsigned = SqlFieldAccessorScalar<FieldValueType::unsigned64>;
using SqlFieldAccessorInt = SqlFieldAccessorScalar<FieldValueType::signed64>;
using SqlFieldAccessorReal = SqlFieldAccessorScalar<FieldValueType::float64>;



/*-----------------------------------------------------------------------
 * SqlFieldAccessor Factory
 -----------------------------------------------------------------------*/

SqlFieldAccessor::factory_t::map_t SqlFieldAccessor::factory_t::m_Map
{
	{ c_Type_Bool, &MakeField<SqlFieldAccessorInt> },
	{ c_Type_Int, &MakeField<SqlFieldAccessorInt> },
	{ c_Type_Real, &MakeField<SqlFieldAccessorReal> },
	{ c_Type_Text, &MakeField<SqlFieldAccessor> }
};



/*-----------------------------------------------------------------------
 * SqlLineAccessorCore
 -----------------------------------------------------------------------*/

class SqlLineAccessorCore : public LineAccessor
{
protected:
	unsigned m_NumFields;
	uint64_t m_FieldViewMask{ 0 };
	nlineno_t m_LineNo{ 0 };

	// transient store for line information
	mutable LineBuffer m_LineBuffer;

public:
	SqlLineAccessorCore( unsigned num_fields = 0, uint64_t field_mask = 0 )
		: m_NumFields{ num_fields }, m_FieldViewMask{ field_mask } {}

	SqlLineAccessorCore( SqlLineAccessorCore && rhs )
		: m_NumFields{ rhs.m_NumFields }, m_FieldViewMask{ rhs.m_FieldViewMask } {}

public:
	// LineAccessor interfaces

	nlineno_t GetLineNo( void ) const override {
		return m_LineNo;
	}

	nlineno_t GetLength( void ) const override;
	void GetText( const char ** first, const char ** last ) const override;

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
};



/*-----------------------------------------------------------------------
 * SqlLogLineAccessor, declarations
 -----------------------------------------------------------------------*/

class SqlLogAccessor;

class SqlLogLineAccessor : public SqlLineAccessorCore
{
private:
	const SqlLogAccessor * m_LogAccessor{ nullptr };
	const NTimecodeBase m_TimecodeBase;
	statement_ptr_t m_Statement;

public:
	SqlLogLineAccessor( const SqlLogAccessor * log_accessor, uint64_t field_mask, statement_ptr_t statement );

	void IncLineNo( void ) {
		m_LineBuffer.Clear();
		++m_LineNo;
	}

public:
	// LineAccessor interfaces

	void GetFieldText( unsigned field_id, const char ** first, const char ** last ) const override;
	fieldvalue_t GetFieldValue( unsigned field_id ) const override;
};



/*-----------------------------------------------------------------------
 * SqlViewLineAccessor, declarations
 -----------------------------------------------------------------------*/

class SqlViewLineAccessor : public SqlLineAccessorCore
{
private:
	using capture_t = std::pair<std::string, fieldvalue_t>;
	std::vector<capture_t> m_Captures;

public:
	SqlViewLineAccessor( void ) {}

	SqlViewLineAccessor( const SqlLogAccessor * log_accessor, uint64_t field_mask, statement_ptr_t & statement );

	SqlViewLineAccessor( SqlViewLineAccessor && rhs )
		: m_Captures{ std::move( rhs.m_Captures ) }, SqlLineAccessorCore{ std::move( rhs ) } {}

public:
	// LineAccessor interfaces

	void GetFieldText( unsigned field_id, const char ** first, const char ** last ) const override {
		if( field_id < m_Captures.size() )
		{
			const std::string & text = m_Captures[ field_id ].first;
			*first = text.c_str();
			*last = *first + text.size();
		}
		else
			*first = *last = "";
	}

	fieldvalue_t GetFieldValue( unsigned field_id ) const override {
		if( field_id < m_Captures.size() )
			return m_Captures[ field_id ].second;
		else
			return 0LL;
	}
};



/*-----------------------------------------------------------------------
 * SqlLogAccessor, declarations
 -----------------------------------------------------------------------*/

class SqlLogAccessor
	:
	public LogAccessor,
	public LogSchemaAccessor,
	public FieldStore<SqlFieldAccessor>
{
private:
	// the SQLite database
	SqlDb m_DB;

	NTimecodeBase m_TimecodeBase;
	nlineno_t m_NumLines{ 0 };

	// field schema
	const fielddescriptor_list_t m_FieldDescriptors;

private:
	Error GetDatum( void );
	Error CalcNumLines( void );

public:
	// LogAccessor interfaces

	Error Open( const std::filesystem::path & file_path, ProgressMeter * ) override;

	void SetTimezoneOffset( int offset_sec ) override {
		// unsupported
	}

	const LogSchemaAccessor * GetSchema( void ) const override {
		return this;
	}

public:
	// LogSchemaAccessor interfaces

	viewaccessor_ptr_t CreateViewAccessor( void ) override;

	size_t GetNumFields( void ) const override {
		return m_FieldDescriptors.size();
	}

	const FieldDescriptor & GetFieldDescriptor( unsigned field_id ) const override {
		return m_FieldDescriptors[ field_id ];
	}

	FieldValueType GetFieldType( unsigned field_id ) const override {
		return m_UserFields[ field_id ]->c_FieldType;
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
	SqlLogAccessor( LogAccessorDescriptor & descriptor );

	static logaccessor_ptr_t MakeSqlLogAccessor( LogAccessorDescriptor & descriptor ) {
		return std::make_unique<SqlLogAccessor>( descriptor );
	}

public:
	Error MakeStatement( const char * sql_text, bool step, bool suppress_error_trace, statement_ptr_t & statement ) const {
		return m_DB.MakeStatement( sql_text, step, suppress_error_trace, statement );
	}

	Error ExecuteStatements( const char * sql_text ) const {
		return m_DB.ExecuteStatements( sql_text );
	}

	nlineno_t GetNumLines( void ) const {
		return m_NumLines;
	}

	void GetFieldText( statement_ptr_t statement, unsigned field_id, const char ** first, const char ** last ) const {
		m_UserFields[ field_id ]->GetAsText( statement, first, last );
	}

	fieldvalue_t GetFieldValue( statement_ptr_t statement, unsigned field_id ) const {
		return m_UserFields[ field_id ]->GetValue( statement );
	}

	template<typename T_FUNCTOR>
	void VisitLines( const char * projection, T_FUNCTOR func, uint64_t field_mask ) const;
};

static OnEvent RegisterMapLogAccessor
{
	OnEvent::EventType::Startup,
	[]() {
		LogAccessorFactory::RegisterLogAccessor( "sql", SqlLogAccessor::MakeSqlLogAccessor );
	}
};



/*-----------------------------------------------------------------------
 * SqlViewAccessor, declarations
 -----------------------------------------------------------------------*/

class SqlViewAccessor
	:
	public ViewProperties,
	public ViewAccessor,
	public SortControl
{
private:
	// our substrate
	SqlLogAccessor * m_LogAccessor;

	// list of fields (columns) to display/search
	uint64_t m_FieldViewMask{ 0 };

	nlineno_t m_NumLines{ 0 };

	// Line caching
	using LineCache = Cache<SqlViewLineAccessor, LineKey>;
	static CacheStatistics m_LineCacheStats;
	mutable LineCache m_LineCache{ m_LineCacheStats };

	// Sorting
	unsigned m_SortColumn{ 1 };
	int m_SortDirection{ 1 };

protected:
	std::vector<nlineno_t> MapViewLines( const char * projection, nlineno_t num_visit_lines, selector_ptr_a selector, LineAdornmentsProvider * adornments_provider );
	std::string MakeViewSql( bool with_limit = false ) const;
	SqlViewLineAccessor CaptureLine( Error status, statement_ptr_t & statement ) const;

	void RecordEvent( void ) {
		m_LineCache.Clear();
		m_Tracker.RecordEvent();
	}

public:
	SqlViewAccessor( SqlLogAccessor * accessor )
		:
		m_LogAccessor{ accessor },
		m_SortColumn{ accessor->GetTimecodeBase().GetFieldId() }
	{}

public:
	// ViewProperties interfaces

	void SetFieldMask( uint64_t field_mask ) override {
		// record the change
		RecordEvent();
		m_FieldViewMask = field_mask;
	}

public:
	// ViewAccessor interfaces

	nlineno_t GetNumLines( void ) const override {
		return m_NumLines;
	}

	void VisitLine( Task & task, nlineno_t visit_line_no ) const override;
	void Filter( selector_ptr_a selector, LineAdornmentsProvider * adornments_provider, bool ) override;
	std::vector<nlineno_t> Search( selector_ptr_a selector, LineAdornmentsProvider * adornments_provider ) override;

	ViewProperties * GetProperties( void ) override {
		return this;
	}

public:
	// SortControl interfaces

	void SetSort( unsigned col_num, int direction ) override {
		// record the change
		RecordEvent();

		m_SortColumn = col_num;
		m_SortDirection = direction;
		m_LineCache.Clear();
	}

	SortControl * GetSortControl( void ) override {
		return this;
	}
};



/*-----------------------------------------------------------------------
 * SqlLineAccessorCore, definitions
 -----------------------------------------------------------------------*/

nlineno_t SqlLineAccessorCore::GetLength( void ) const
{
	const char * first{ nullptr }; const char * last{ nullptr };
	GetText( &first, &last );
	return nlineno_cast( last - first + 1 );
}


void SqlLineAccessorCore::GetText( const char ** first, const char ** last ) const
{
	if( m_LineBuffer.Empty() )
	{
		uint64_t bit{ 0x1 };
		for( unsigned field_id = 0; field_id < m_NumFields; ++field_id, bit <<= 1 )
			if( m_FieldViewMask & bit )
			{
				const char * f{ nullptr }; const char * l{ nullptr };
				GetFieldText( field_id, &f, &l );
				m_LineBuffer.Append( f, l );
				m_LineBuffer.Append( '|' );
			}
	}

	*first = m_LineBuffer.First();
	*last = m_LineBuffer.Last();
}



/*-----------------------------------------------------------------------
 * SqlLogLineAccessor, definitions
 -----------------------------------------------------------------------*/

SqlLogLineAccessor::SqlLogLineAccessor( const SqlLogAccessor * log_accessor, uint64_t field_mask, statement_ptr_t statement )
	:
	SqlLineAccessorCore{ static_cast<unsigned>(log_accessor->GetNumFields()), field_mask },
	m_LogAccessor{ log_accessor },
	m_TimecodeBase{ log_accessor->GetTimecodeBase() },
	m_Statement{ statement }
{
}


void SqlLogLineAccessor::GetFieldText( unsigned field_id, const char ** first, const char ** last ) const
{
	m_LogAccessor->GetFieldText( m_Statement, field_id, first, last );
}


fieldvalue_t SqlLogLineAccessor::GetFieldValue( unsigned field_id ) const
{
	return m_LogAccessor->GetFieldValue( m_Statement, field_id );
}



/*-----------------------------------------------------------------------
 * SqlViewLineAccessor, definitions
 -----------------------------------------------------------------------*/

SqlViewLineAccessor::SqlViewLineAccessor( const SqlLogAccessor * log_accessor, uint64_t field_mask, statement_ptr_t & statement )
	: SqlLineAccessorCore{ static_cast<unsigned>(log_accessor->GetNumFields()), field_mask }
{
	m_Captures.reserve( m_NumFields );

	uint64_t mask{ 0x1 };
	for( unsigned field_id = 0; field_id < m_NumFields; ++field_id, mask <<= 1 )
	{
		std::string text;
		if( mask & field_mask )
		{
			const char * first{ nullptr }; const char * last{ nullptr };
			log_accessor->GetFieldText( statement, field_id, &first, &last );
			text.assign( first, last );
		}

		const fieldvalue_t value{ log_accessor->GetFieldValue( statement, field_id ) };

		m_Captures.push_back( std::move( std::make_pair( std::move( text ), value ) ) );
	}
}



/*-----------------------------------------------------------------------
 * SqlLogAccessor, definitions
 -----------------------------------------------------------------------*/

SqlLogAccessor::SqlLogAccessor( LogAccessorDescriptor & descriptor )
	: m_FieldDescriptors{ std::move( descriptor.m_FieldDescriptors ) }
{
	SetupUserFields( m_FieldDescriptors );
}


viewaccessor_ptr_t SqlLogAccessor::CreateViewAccessor( void )
{
	return std::make_shared<SqlViewAccessor>( this );
}


Error SqlLogAccessor::Open( const std::filesystem::path & file_path, ProgressMeter * )
{
	Error res{ m_DB.Open( file_path ) };

	if( Ok( res ) )
		UpdateError( res, GetDatum() );

	if( Ok( res ) )
		UpdateError( res, CalcNumLines() );

	return res;
}


Error SqlLogAccessor::GetDatum( void )
{
	statement_ptr_t statement;
	Error res{ MakeStatement( "SELECT * FROM projection_meta", true, true, statement ) };

	if( Ok( res ) )
	{
		const time_t utc_datum{ statement->GetAsInt64( 0 ) };
		const unsigned field_id{ static_cast<unsigned>(statement->GetAsInt( 1 )) };
		m_TimecodeBase = NTimecodeBase{ utc_datum, field_id };
	}

	// ignore datum errors - it is no required that a projection has any date/times
	return e_Success;
}


Error SqlLogAccessor::CalcNumLines( void )
{
	statement_ptr_t statement;
	Error res{ MakeStatement( "SELECT count(*) FROM projection", true, false, statement ) };

	if( Ok( res ) )
		m_NumLines = statement->GetAsInt( 0 );

	return res;
}


template<typename T_FUNCTOR>
void SqlLogAccessor::VisitLines( const char * projection, T_FUNCTOR func, uint64_t field_mask ) const
{
	statement_ptr_t statement;
	Error res{ MakeStatement( projection, false, false, statement ) };
	if( !Ok( res ) )
		return;

	SqlLogLineAccessor line{ this, field_mask, statement };
	while( statement->Step() == Error::e_SqlRow )
	{
		func( line );
		line.IncLineNo();
	}
}



/*-----------------------------------------------------------------------
 * SqlViewAccessor, definitions
 -----------------------------------------------------------------------*/

CacheStatistics SqlViewAccessor::m_LineCacheStats{ "SqlLineCache" };

std::string SqlViewAccessor::MakeViewSql( bool with_limit ) const
{
	std::ostringstream strm;

	// note SQL column numbers start counting at 1

	strm << R"__(
			SELECT
				*
			FROM
				filtered_projection
			ORDER BY )__" << m_SortColumn + 1 << " " << (m_SortDirection > 0 ? "ASC" : "DESC");

	if( with_limit )
		strm << R"__(
			LIMIT 16 OFFSET ?1
		)__";

	return strm.str();
}


SqlViewLineAccessor SqlViewAccessor::CaptureLine( Error status, statement_ptr_t & statement ) const
{
	if( Ok( status ) )
		return SqlViewLineAccessor{ m_LogAccessor, m_FieldViewMask, statement };
	else
		return SqlViewLineAccessor{};
}


void SqlViewAccessor::VisitLine( Task & task, nlineno_t visit_line_no ) const
{
	Error res;
	statement_ptr_t statement;

	const LineCache::find_t found{ m_LineCache.Fetch(
		{ visit_line_no, m_FieldViewMask },

		[this, &res, &statement] ( const LineKey & key ) -> SqlViewLineAccessor
		{
			res = m_LogAccessor->MakeStatement( MakeViewSql( true ).c_str(), false, false, statement );

			if( Ok( res ) )
				UpdateError( res, statement->Bind( 1, key.f_LineNo ) );

			if( Ok( res ) )
				UpdateError( res, statement->Step() );

			return CaptureLine( res, statement );
		}
	) };

	if( !found.first )
	{
		for( int i = 1; i < 16 && Ok( res ); ++i )
		{
			res = statement->Step();

			m_LineCache.Fetch(
				{ visit_line_no + i, m_FieldViewMask },
				[this, res, & statement] ( const LineKey & key ) -> SqlViewLineAccessor
				{
					return CaptureLine( res, statement );
				}
			);
		}
	}

	task.Action( *found.second );
}


std::vector<nlineno_t> SqlViewAccessor::MapViewLines( const char * projection, nlineno_t num_visit_lines, selector_ptr_a selector, LineAdornmentsProvider * adornments_provider )
{
	std::vector<nlineno_t> map;
	map.reserve( num_visit_lines );

	m_LogAccessor->VisitLines
	(
		projection,
		[&map, &selector, adornments_provider] ( const LineAccessor & line )
		{
			const nlineno_t log_line_no{ line.GetLineNo() };
			LineAdornmentsAccessor adornments{ adornments_provider, log_line_no };
			if( selector->Hit( line, adornments ) )
				map.push_back( log_line_no );
		},
		m_FieldViewMask
	);

	return map;
}


void SqlViewAccessor::Filter( selector_ptr_a selector, LineAdornmentsProvider * adornments_provider, bool )
{
	PythonPerfTimer map_timer{"Nlog::SqlViewAccessor::Filter::Map"};

	const nlineno_t num_log_lines{ m_LogAccessor->GetNumLines() };
	std::vector<nlineno_t> map{ MapViewLines(
		"SELECT * FROM projection",
		num_log_lines,
		selector,
		adornments_provider
	) };

	m_NumLines = nlineno_cast(map.size());
	map_timer.Close( m_NumLines );

	PythonPerfTimer sql_timer{ "Nlog::SqlViewAccessor::Filter::Sql" };;

	Error res{ m_LogAccessor->ExecuteStatements( "BEGIN TRANSACTION; DELETE FROM filter" ) };
	if( !Ok( res ) )
		return;

	statement_ptr_t statement;
	res = m_LogAccessor->MakeStatement( "INSERT INTO filter VALUES(?1)", false, false, statement );

	for( nlineno_t line_no : map )
	{
		if( Ok( res ) )
			UpdateError( res, statement->Bind( 1, line_no + 1 ) );

		if( Ok( res ) )
			UpdateError( res, statement->Step() );

		if( Ok( res ) )
			UpdateError( res, statement->Reset() );
	}

	m_LogAccessor->ExecuteStatements( Ok( res ) ? "COMMIT TRANSACTION" : "ROLLBACK TRANSACTION" );

	sql_timer.Close( map.size() );

	// record the change
	RecordEvent();
}


std::vector<nlineno_t> SqlViewAccessor::Search( selector_ptr_a selector, LineAdornmentsProvider * adornments_provider )
{
	PythonPerfTimer timer{ __FUNCTION__ };

	const nlineno_t num_view_lines{ GetNumLines() };
	std::vector<nlineno_t> map{ MapViewLines(
		MakeViewSql().c_str(),
		num_view_lines,
		selector,
		adornments_provider
	) };

	// write out performance data
	timer.Close( num_view_lines );

	return map;
}


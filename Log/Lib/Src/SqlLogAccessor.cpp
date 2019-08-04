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
#include "Deps/sqlite3.h"

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
	Error Open( sqlite3 * db, const char * sql_text, const char ** tail = nullptr );

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
};


SqlStatement::~SqlStatement( void )
{
	Close();
}


Error SqlStatement::Open( sqlite3 * db, const char * sql_text, const char ** tail )
{
	const char * local_tail{ nullptr };
	if( tail == nullptr )
		tail = &local_tail;

	Error res{ e_OK };
	const int sql_ret{ sqlite3_prepare_v2( db, sql_text, -1, &m_Handle, tail ) };

	if( sql_ret != SQLITE_OK )
		res = TraceError( e_SqlStatementOpen, "sql_res=[%d/%s] sql_text=[%s]", sql_ret, sqlite3_errstr( sql_ret ), sql_text );
	
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

	Error MakeStatement( const char * sql_text, bool step, statement_ptr_t & statement ) const;
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


Error SqlDb::MakeStatement( const char * sql_text, bool step, statement_ptr_t & statement ) const
{
	statement = std::make_shared<SqlStatement>();

	Error res{ statement->Open( m_Handle, sql_text ) };

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
		res = statement->Open( m_Handle, tail, &tail );
		if( Ok( res ) )
			UpdateError( res, statement->Step() );
	}

	return res;
}



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
protected:
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

	void GetFieldText( unsigned field_id, const char ** first, const char ** last ) const override {
		m_Statement->GetAsText( field_id, first, last );
	}

	fieldvalue_t GetFieldValue( unsigned field_id ) const override {
		return m_Statement->GetAsInt64( field_id );
	}
};



/*-----------------------------------------------------------------------
 * FieldAccessor
 -----------------------------------------------------------------------*/

 // forwards
class FieldAccessor;

using fieldaccessor_maker_t = FieldTraits<FieldAccessor>::field_ptr_t (*) (const FieldDescriptor & field_desc, unsigned field_id);

class FieldAccessor : public FieldFactory<FieldAccessor, fieldaccessor_maker_t>
{
protected:
	std::string m_Text;
	fieldvalue_t m_Value;

public:
	FieldAccessor( unsigned field_id )
		: c_FieldId { field_id } {}

	// effectively, the index of this field within the parent index
	const unsigned c_FieldId;

	virtual void Update( statement_ptr_t statement ) = 0;

	// fetch the field's current (text) value
	void GetAsText( const char ** first, const char ** last ) const {
		*first = m_Text.data();
		*last = *first + m_Text.size();
	}

	// fetch the field's current (binary) value
	fieldvalue_t GetValue( void ) const {
		return m_Value;
	}
};



/*-----------------------------------------------------------------------
 * FieldAccessorText
 -----------------------------------------------------------------------*/

class FieldAccessorText : public FieldAccessor
{
public:
	FieldAccessorText( const FieldDescriptor &, unsigned field_id )
		: FieldAccessor{ field_id } {}

	void Update( statement_ptr_t statement ) {
		const char * first{ nullptr }; const char * last{ nullptr };
		statement->GetAsText( c_FieldId, &first, &last );
		m_Text.assign( first, last );
	}
};



/*-----------------------------------------------------------------------
 * FieldAccessorInt
 -----------------------------------------------------------------------*/

class FieldAccessorInt : public FieldAccessorText
{
public:
	FieldAccessorInt( const FieldDescriptor & field_desc, unsigned field_id )
		: FieldAccessorText{ field_desc, field_id } {}

	void Update( statement_ptr_t statement ) {
		m_Value = statement->GetAsInt64( c_FieldId );
		FieldAccessorText::Update( statement );
	}
};



/*-----------------------------------------------------------------------
 * FieldAccessorReal
 -----------------------------------------------------------------------*/

class FieldAccessorReal : public FieldAccessorText
{
public:
	FieldAccessorReal( const FieldDescriptor & field_desc, unsigned field_id )
		: FieldAccessorText{ field_desc, field_id } {}

	void Update( statement_ptr_t statement ) {
		m_Value = statement->GetAsReal( c_FieldId );
		FieldAccessorText::Update( statement );
	}
};



/*-----------------------------------------------------------------------
 * FieldAccessor Factory
 -----------------------------------------------------------------------*/

FieldAccessor::factory_t::map_t FieldAccessor::factory_t::m_Map
{
	{ c_Type_Bool, &MakeField<FieldAccessorInt> },
	{ c_Type_Uint08, &MakeField<FieldAccessorInt> },
	{ c_Type_Uint16, &MakeField<FieldAccessorInt> },
	{ c_Type_Uint32, &MakeField<FieldAccessorInt> },
	{ c_Type_Uint64, &MakeField<FieldAccessorInt> },
	{ c_Type_Int08, &MakeField<FieldAccessorInt> },
	{ c_Type_Int16, &MakeField<FieldAccessorInt> },
	{ c_Type_Int32, &MakeField<FieldAccessorInt> },
	{ c_Type_Int64, &MakeField<FieldAccessorInt> },
	{ c_Type_Float32, &MakeField<FieldAccessorReal> },
	{ c_Type_Float64, &MakeField<FieldAccessorReal> },
	{ c_Type_Text, &MakeField<FieldAccessorText> }
};



/*-----------------------------------------------------------------------
 * SqlViewLineAccessor, declarations
 -----------------------------------------------------------------------*/

class SqlViewLineAccessor
	:
	public SqlLineAccessorCore,
	public FieldStore<FieldAccessor>
{
public:
	void Update( const fielddescriptor_list_t & field_descs, uint64_t field_mask, statement_ptr_t statement );

public:
	// LineAccessor interfaces

	void GetFieldText( unsigned field_id, const char ** first, const char ** last ) const override {
		m_Fields[field_id]->GetAsText( first, last );
	}

	fieldvalue_t GetFieldValue( unsigned field_id ) const override {
		return m_Fields[ field_id ]->GetValue();
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

// NIEL needed ?? e.g. for date filtering
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
	SqlLogAccessor( LogAccessorDescriptor & descriptor );

	const fielddescriptor_list_t & GetFieldDescriptors( void ) const {
		return m_FieldDescriptors;
	}

	static logaccessor_ptr_t MakeSqlLogAccessor( LogAccessorDescriptor & descriptor ) {
		return std::make_unique<SqlLogAccessor>( descriptor );
	}

public:
	Error MakeStatement( const char * sql_text, bool step, statement_ptr_t & statement ) const {
		return m_DB.MakeStatement( sql_text, step, statement );
	}

	Error ExecuteStatements( const char * sql_text ) const {
		return m_DB.ExecuteStatements( sql_text );
	}

	nlineno_t GetNumLines( void ) const {
		return m_NumLines;
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
	mutable LineCache m_LineCache{ 128, m_LineCacheStats };

	// Sorting
	unsigned m_SortColumn{ 1 };
	int m_SortDirection{ 1 };

protected:
	std::vector<nlineno_t> MapViewLines( const char * projection, nlineno_t num_visit_lines, selector_ptr_a selector, LineAdornmentsProvider * adornments_provider );
	std::string MakeViewSql( bool with_limit = false ) const;

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
	m_TimecodeBase{ log_accessor->GetTimecodeBase() },
	m_Statement{ statement }
{
}



/*-----------------------------------------------------------------------
 * SqlViewLineAccessor, definitions
 -----------------------------------------------------------------------*/

void SqlViewLineAccessor::Update( const fielddescriptor_list_t & field_descs, uint64_t field_mask, statement_ptr_t statement )
{
	SetupFields( field_descs,
		[] ( const FieldDescriptor & field_desc, unsigned field_id ) -> field_ptr_t {
			return field_t::CreateField( field_desc, field_id );
		}
	);

	m_LineBuffer.Clear();
	m_NumFields = static_cast<unsigned>(GetNumFields());
	m_FieldViewMask = field_mask;

	for( field_ptr_t field : m_Fields )
		field->Update( statement );
}



/*-----------------------------------------------------------------------
 * SqlLogAccessor, definitions
 -----------------------------------------------------------------------*/

SqlLogAccessor::SqlLogAccessor( LogAccessorDescriptor & descriptor )
	: m_FieldDescriptors{ std::move( descriptor.m_FieldDescriptors ) }
{
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
	Error res{ MakeStatement( "SELECT * FROM projection_meta", true, statement ) };

	if( Ok( res ) )
	{
		const time_t utc_datum{ statement->GetAsInt64( 0 ) };
		const unsigned field_id{ static_cast<unsigned>(statement->GetAsInt( 1 )) };
		m_TimecodeBase = NTimecodeBase{ utc_datum, field_id };
	}

	return res;
}


Error SqlLogAccessor::CalcNumLines( void )
{
	statement_ptr_t statement;
	Error res{ MakeStatement( "SELECT count(*) FROM projection", true, statement ) };

	if( Ok( res ) )
		m_NumLines = statement->GetAsInt( 0 );

	return res;
}


template<typename T_FUNCTOR>
void SqlLogAccessor::VisitLines( const char * projection, T_FUNCTOR func, uint64_t field_mask ) const
{
	statement_ptr_t statement;
	Error res{ MakeStatement( projection, false, statement ) };
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
				projection
				JOIN
					filter
				ON
					projection.rowid = filter.log_row_no
			ORDER BY )__" << m_SortColumn + 1 << " " << (m_SortDirection > 0 ? "ASC" : "DESC");

	if( with_limit )
		strm << R"__(
			LIMIT 16 OFFSET ?1
		)__";

	return strm.str();
}


void SqlViewAccessor::VisitLine( Task & task, nlineno_t visit_line_no ) const
{
	LineCache::find_t found{ m_LineCache.Find( { visit_line_no, m_FieldViewMask } ) };
	SqlViewLineAccessor * line{ found.second };

	if( !found.first )
	{
		statement_ptr_t statement;
		Error res{ m_LogAccessor->MakeStatement( MakeViewSql( true ).c_str(), false, statement ) };

		if( Ok( res ) )
			UpdateError( res, statement->Bind( 1, visit_line_no ) );

		for( int i = 0; i < 16 && Ok( res ); ++i )
		{
			res = statement->Step();

			SqlViewLineAccessor * update;
			if( i == 0 )
				update = line;
			else
			{
				LineCache::find_t f{ m_LineCache.Find( { visit_line_no + i, m_FieldViewMask } ) };
				update = f.first ? nullptr : f.second;
			}

			if( update && Ok( res ) )
				update->Update( m_LogAccessor->GetFieldDescriptors(), m_FieldViewMask, statement );

		}
	}

	task.Action( *line );
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
	PerfTimer filter_timer;

	const nlineno_t num_log_lines{ m_LogAccessor->GetNumLines() };
	std::vector<nlineno_t> map{ MapViewLines(
		"SELECT * FROM projection",
		num_log_lines,
		selector,
		adornments_provider
	) };

	m_NumLines = nlineno_cast(map.size());

	TraceDebug( "filter_time:%.2fs per_line:%.3fus", filter_timer.Overall(), filter_timer.PerItem( num_log_lines ) );

	PerfTimer sql_timer;

	Error res{ m_LogAccessor->ExecuteStatements( "BEGIN TRANSACTION; DELETE FROM filter" ) };
	if( !Ok( res ) )
		return;

	statement_ptr_t statement;
	res = m_LogAccessor->MakeStatement( "INSERT INTO filter VALUES(?1)", false, statement );

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

	TraceDebug( "sql_time:%.2fs per_line:%.3fus", sql_timer.Overall(), sql_timer.PerItem( map.size() ) );

	// record the change
	RecordEvent();
}


std::vector<nlineno_t> SqlViewAccessor::Search( selector_ptr_a selector, LineAdornmentsProvider * adornments_provider )
{
	PerfTimer timer;

	const nlineno_t num_view_lines{ GetNumLines() };
	std::vector<nlineno_t> map{ MapViewLines(
		MakeViewSql().c_str(),
		num_view_lines,
		selector,
		adornments_provider
	) };

	// write out performance data
	TraceDebug( "time:%.2fs per_line:%.3fus", timer.Overall(), timer.PerItem( num_view_lines ) );

	return map;
}


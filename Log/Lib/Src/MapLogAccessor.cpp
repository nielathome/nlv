//
// Copyright (C) 2017-2019 Niel Clausen. All rights reserved.
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
#include "MapLogIndexWriter.h"
#include "Nline.h"

// Intel TBB includes
#include <tbb/flow_graph.h>

// force link this module
void force_link_mapaccessor_module() {}


/*-----------------------------------------------------------------------
 * LineFormatter, declarations
 -----------------------------------------------------------------------*/

class LineFormatter
{
private:
	// descriptors
	const formatdescriptor_list_t m_FormatDescriptors;

public:
	LineFormatter( formatdescriptor_list_t && descriptors )
		: m_FormatDescriptors{ std::move( descriptors ) } {}

	void Apply( const LineBuffer & text, LineBuffer * fmt ) const;
};



/*-----------------------------------------------------------------------
 * LineFormatter, definitions
 -----------------------------------------------------------------------*/

void LineFormatter::Apply( const LineBuffer & text, LineBuffer * fmt ) const
{
	const char *last{ text.Last() };
	for( const FormatDescriptor & desc : m_FormatDescriptors )
	{
		std::cmatch match;
		size_t offset{ 0 };
		const char *at{ text.First() };

		while( std::regex_search( at + offset, last, match, desc.m_Regex ) )
		{
			const size_t num_matches{ match.size() };
			if( num_matches <= 1 )
				continue;

			const size_t num_formats{ std::min( desc.m_Styles.size(), num_matches - 1 ) };
			for( size_t i = 0; i < num_formats; ++i )
				fmt->Replace( desc.m_Styles[ i ], match.position( i + 1 ) + offset, match.length( i + 1 ) );

			offset = match[ 0 ].second - at;
		}
	}
}



/*-----------------------------------------------------------------------
 * MapLogAccessor, declarations
 -----------------------------------------------------------------------*/

struct Visitor;

// the default log accessor is based on file mapping; the log must be entirely static
class MapLogAccessor : public LogAccessor, public LogSchemaAccessor
{
private:
	// the logfile's text
	FileMap m_Log;
	const char * m_Text{ nullptr };

	// the index data
	const std::string m_TextOffsetsFieldType;
	std::unique_ptr<LogIndexAccessor> m_Index;

	// "timezone", as an offset in seconds
	int m_TzOffset;

	// field schema
	const std::string m_Guid;
	const fielddescriptor_list_t m_FieldDescriptors;
	const std::string m_MatchDesc;

	// Line/style caching
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

	using LineCache = Cache<LineBuffer, LineKey>;
	static CacheStatistics m_LineCacheStats[ static_cast<int>(e_LineData::_Count) ];
	mutable LineCache m_LineCache[ static_cast<int>(e_LineData::_Count) ]
	{
		{ 128, m_LineCacheStats[ 0 ] },
		{ 128, m_LineCacheStats[ 1 ] }
	};

	// line formatting
	LineFormatter m_LineFormatters;

protected:
	std::filesystem::path CalcIndexPath( const std::filesystem::path & file_path );
	MapLogAccessor( LogAccessorDescriptor & descriptor );

public:
	void VisitLines( Visitor & visitor, uint64_t field_mask ) const;

public:
	// MapViewAccessor intefaces

	const LineBuffer & GetLine( e_LineData type, nlineno_t line_no, uint64_t field_mask ) const;

	const LogSchemaAccessor * GetSchema( void ) const override {
		return this;
	}

public:
	// LogAccessor interfaces

	Error Open( const std::filesystem::path & file_path, ProgressMeter * progress, size_t skip_lines ) override;
	viewaccessor_ptr_t CreateViewAccessor( void ) override;

	void SetTimezoneOffset( int offset_sec ) override {
		m_TzOffset = offset_sec;
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
		return m_Index->GetFieldType( field_id );
	}

	uint16_t GetFieldEnumCount( unsigned field_id ) const override {
		return m_Index->GetFieldEnumCount( field_id );
	}

	const char * GetFieldEnumName( unsigned field_id, uint16_t enum_id ) const override {
		return m_Index->GetFieldEnumName( field_id, enum_id );
	}

	const NTimecodeBase & GetTimecodeBase( void ) const override {
		return m_Index->GetTimecodeBase();
	}

public:
	// MapLineAccessor interfaces

	void CopyLine( e_LineData type, nlineno_t line_no, uint64_t field_mask, LineBuffer * buffer ) const;

	nlineno_t GetNumLines( void ) const {
		return m_Index->GetNumLines();
	}

	bool IsLineRegular( nlineno_t line_no ) const {
		return m_Index->IsLineRegular( line_no );
	}

	nlineno_t GetLineLength( nlineno_t line_no, uint64_t field_mask = 0 ) const {
		return m_Index->GetLineLength( line_no, field_mask );
	}

	NTimecode GetUtcTimecode( nlineno_t line_no ) const {
		const NTimecodeBase & timecode_base{ GetTimecodeBase() };
		const int64_t offset{ GetFieldValue( line_no, timecode_base.GetFieldId() ).As<int64_t>() };

		// apply the timezone offset to the result
		return NTimecode{ timecode_base.GetUtcDatum() - m_TzOffset, offset };
	}

	void GetNonFieldText( nlineno_t line_no, const char ** first, const char ** last ) const
	{
		nlineno_t first_offset, last_offset;
		m_Index->GetNonFieldTextOffsets( line_no, &first_offset, &last_offset );

		*first = m_Text + first_offset;
		*last = m_Text + last_offset;
	}

	void GetFieldText( nlineno_t line_no, unsigned field_id, const char ** first, const char ** last ) const
	{
		nlineno_t first_offset, last_offset;
		m_Index->GetFieldTextOffsets( line_no, field_id, &first_offset, &last_offset );

		*first = m_Text + first_offset;
		*last = m_Text + last_offset;
	}

	fieldvalue_t GetFieldValue( nlineno_t line_no, unsigned field_id ) const {
		return m_Index->GetFieldValue( line_no, field_id );
	}

public:
	static LogAccessor * MakeMapLogAccessor( LogAccessorDescriptor & descriptor )
	{
		return new MapLogAccessor( descriptor );
	}
};


static OnEvent RegisterMapLogAccessor
{
	OnEvent::EventType::Startup,
	[]() {
		LogAccessorFactory::RegisterLogAccessor( "map", MapLogAccessor::MakeMapLogAccessor );
	}
};



/*-----------------------------------------------------------------------
 * MapViewAccessor, declarations
 -----------------------------------------------------------------------*/

class MapViewAccessor
	:
	public ViewProperties,
	public ViewMap,
	public ViewAccessor
{
private:
	// our substrate
	MapLogAccessor * m_LogAccessor;

	// map a view line number (index) to a logfile line number (value)
	std::vector<nlineno_t> m_LineMap;

	// list of fields (columns) to display/search
	uint64_t m_FieldViewMask{ 0 };

public:
	MapViewAccessor( MapLogAccessor * accessor )
		: m_LogAccessor{ accessor }
	{}

	void VisitLines( Visitor & visitor ) const;

public:
	// ViewProperties interfaces

	void SetFieldMask( uint64_t field_mask ) override;

public:
	// ViewMap interfaces

	nlineno_t GetLineLength( nlineno_t line_no ) const override {
		return m_LogAccessor->GetLineLength( ViewLineToLogLine( line_no ), m_FieldViewMask );
	}

	const LineBuffer & GetLine( e_LineData type, nlineno_t line_no ) const override {
		return m_LogAccessor->GetLine( type, ViewLineToLogLine( line_no ), m_FieldViewMask );
	}

	NTimecode GetUtcTimecode( nlineno_t line_no ) const override {
		return m_LogAccessor->GetUtcTimecode( ViewLineToLogLine( line_no ) );
	}

public:
	// ViewAccessor interface

	void VisitLine( Task & task, nlineno_t visit_line_no ) const override;
	void Filter( Selector * selector, LineAdornmentsProvider * adornments_provider, bool add_irregular ) override;
	std::vector<nlineno_t> Search( Selector * selector, LineAdornmentsProvider * adornments_provider ) override;

	nlineno_t GetNumLines( void ) const override {
		return m_IsEmpty ? 0 : m_NumLinesOrOne;
	}

	// fetch nearest preceding view line number to the supplied log line
	nlineno_t LogLineToViewLine( nlineno_t log_line_no, bool exact = false ) const override {
		return NLine::Lookup( m_LineMap, m_NumLinesOrOne, log_line_no, exact );
	}

	nlineno_t ViewLineToLogLine( nlineno_t view_line_no ) const override {
		return m_LineMap[view_line_no];
	}

	ViewProperties * GetProperties( void ) override {
		return this;
	}

	const ViewMap * GetMap( void ) override {
		return this;
	}

public:
	// MapLineAccessor interfaces

	bool IsLineRegular( nlineno_t line_no ) const {
		return m_LogAccessor->IsLineRegular( ViewLineToLogLine( line_no ) );
	}

	void CopyLine( e_LineData type, nlineno_t line_no, LineBuffer * buffer ) const {
		return m_LogAccessor->CopyLine( type, ViewLineToLogLine( line_no ), m_FieldViewMask, buffer );
	}

	void GetNonFieldText( nlineno_t line_no, const char ** first, const char ** last ) const {
		return m_LogAccessor->GetNonFieldText( ViewLineToLogLine( line_no ), first, last );
	}

	void GetFieldText( nlineno_t line_no, unsigned field_id, const char ** first, const char ** last ) const {
		return m_LogAccessor->GetFieldText( ViewLineToLogLine( line_no ), field_id, first, last );
	}

	fieldvalue_t GetFieldValue( nlineno_t line_no, unsigned field_id ) const {
		return m_LogAccessor->GetFieldValue( ViewLineToLogLine( line_no ), field_id );
	}
};



/*-----------------------------------------------------------------------
 * MapLogAccessor, definitions
 -----------------------------------------------------------------------*/

CacheStatistics MapLogAccessor::m_LineCacheStats[]
{
	{ "MapLogAccessor/Text" },
	{ "MapLogAccessor/Style" }
};


const std::string & ExpandFieldOffsetSize( unsigned text_offsets_size )
{
	return text_offsets_size == 16 ? c_Type_TextOffsets16 : c_Type_TextOffsets08;
}


fielddescriptor_list_t && ExpandFieldDescriptors( const std::string & text_offsets_field_type, fielddescriptor_list_t && field_descs )
{
	// expand the application defined field descriptor list with 2 "hidden" fields:
	// - the first field is always the line position
	// - and the last field is always the text offsets data
	field_descs.insert( field_descs.begin(), FieldDescriptor{ "uint64", "LineOffset" } );
	field_descs.push_back( FieldDescriptor{ text_offsets_field_type, "NoField" } );
	return std::move(field_descs);
}


MapLogAccessor::MapLogAccessor( LogAccessorDescriptor & descriptor )
	:
	m_Guid{ std::move( descriptor.m_Guid ) },
	m_TextOffsetsFieldType{ ExpandFieldOffsetSize( descriptor.m_TextOffsetsSize ) },
	m_FieldDescriptors{ ExpandFieldDescriptors( m_TextOffsetsFieldType, std::move( descriptor.m_FieldDescriptors ) ) },
	m_MatchDesc{ std::move( descriptor.m_MatchDesc ) },
	m_LineFormatters{ std::move( descriptor.m_LineFormatters ) }
{
}


std::filesystem::path MapLogAccessor::CalcIndexPath( const std::filesystem::path & file_path )
{
	using namespace std::filesystem;

	const path cache_subdir{ L".nlvc" };
	const path file_dir{ file_path.parent_path() };

	bool in_cache_dir{ false };
	for(const path & elem : file_dir )
		if( elem == cache_subdir )
		{
			in_cache_dir = true;
			break;
		}

	const path cache_dir{ in_cache_dir ? file_dir : file_dir / cache_subdir };
	if( !exists( cache_dir ) )
		create_directory( cache_dir );

	return (cache_dir / file_path.filename()).concat( L".idx" );
}


Error MapLogAccessor::Open( const std::filesystem::path & file_path, ProgressMeter * progress, size_t skip_lines )
{
	// map logfile
	const Error log_error{ m_Log.Map( file_path ) };
	if( !Ok( log_error ) )
		return log_error;
	m_Text = m_Log.GetData();

	// identify the index file's path
	std::filesystem::path index_path;
	try
	{
		index_path = CalcIndexPath( file_path );
	}
	catch( const std::filesystem::filesystem_error & ex )
	{
		return TraceError( e_FileSystem, "%s", ex.what() );
	}
	
	// try to map logfile index
	const FILETIME & log_modified_time{ m_Log.GetModifiedTime() };
	m_Index = MakeLogIndexAccessor( m_TextOffsetsFieldType, m_FieldDescriptors );
	Error idx_error{ m_Index->Load( index_path, log_modified_time, m_Guid ) };

	// if no index found, need to make one
	const bool no_index{ idx_error == e_FileNotFound };

	// some index errors are re-tryable
	const bool rebuild{
		(idx_error == e_CorruptIndex)
		|| (idx_error == e_UnsupportedIndexVersion)
		|| (idx_error == e_LogfileChanged)
		|| (idx_error == e_FieldSchemaChanged)
		|| (idx_error == e_WrongIndex)
	};

	if( no_index )
		TraceInfo( "No index file found, creating ..." );

	if( rebuild )
		TraceError( e_IndexUnusable, "Index is not usable, re-creating ..." );
	
	if( no_index || rebuild )
	{
		// write new index
		m_Index = MakeLogIndexAccessor( m_TextOffsetsFieldType, m_FieldDescriptors );
		LogIndexWriter indexer{ m_Log, m_FieldDescriptors, m_MatchDesc };
		idx_error = indexer.Write( index_path, log_modified_time, m_Guid, progress, skip_lines );

		// and attempt to load it
		if( Ok( idx_error ) )
			idx_error = m_Index->Load( index_path, log_modified_time, m_Guid );
	}

	return idx_error;
}


viewaccessor_ptr_t MapLogAccessor::CreateViewAccessor( void )
{
	return std::make_shared<MapViewAccessor>( this );
}


void MapLogAccessor::CopyLine( e_LineData type, nlineno_t line_no, uint64_t field_mask, LineBuffer * line_buffer ) const
{
	line_buffer->Clear();

	if( type == e_LineData::Text )
		m_Index->CopyLine( line_no, field_mask, m_Text, line_buffer );

	else
	{
		const LineBuffer & text{ GetLine( e_LineData::Text, line_no, field_mask ) };
		m_Index->CopyStyle( line_no, field_mask, line_buffer );
		m_LineFormatters.Apply( text, line_buffer );
	}
}


const LineBuffer & MapLogAccessor::GetLine( e_LineData type, nlineno_t line_no, uint64_t field_mask ) const
{
	LineCache & line_cache{ m_LineCache[ static_cast<int>(type) ] };
	std::pair<bool, LineBuffer*> found{ line_cache.Find( { line_no, field_mask } ) };

	LineBuffer * line{ found.second };
	if( !found.first )
		CopyLine( type, line_no, field_mask, line );

	return *line;
}



/*-----------------------------------------------------------------------
 * MapViewAccessor, definitions
 -----------------------------------------------------------------------*/

void MapViewAccessor::SetFieldMask( uint64_t field_mask )
{
	// record the change
	m_Tracker.RecordEvent();
	m_FieldViewMask = field_mask;

	if( !m_IsEmpty )
	{
		PerfTimer timer;

		// TODO: parallelise
		nlineno_t pos{ 0 };
		for( nlineno_t line_no = 0; line_no < m_NumLinesOrOne; ++line_no )
		{
			m_Lines[ line_no ] = pos;
			pos += GetLineLength( line_no );
		}

		m_TextLen = m_Lines[ m_NumLinesOrOne ] = pos;

		// write out performance data
		TraceDebug( "time:%.2fs per_line:%.3fus", timer.Overall(), timer.PerItem( m_NumLinesOrOne ) );
	}
}



/*-----------------------------------------------------------------------
 * MapLineAccessor
 -----------------------------------------------------------------------*/

template<typename T_ACCESSOR>
class MapLineAccessor : public LineAccessor
{
public:
	using accessor_t = T_ACCESSOR;

private:
	// continuation (next) line handling
	mutable nlineno_t m_IrregularLineNo{ -1 };

protected:
	const accessor_t & m_Accessor;
	nlineno_t m_LineNo{ -1 };

	// transient store for line information
	mutable LineBuffer m_LineBuffer;

public:
	MapLineAccessor( const accessor_t & accessor )
		:
		m_Accessor{ accessor }
	{}

	void SetLineNo( nlineno_t line_no ) {
		m_LineNo = line_no;
		m_IrregularLineNo = line_no + 1;
	}

public:
	// LineAccessor interfaces

	nlineno_t GetLineNo( void ) const override {
		return m_LineNo;
	}

	bool IsRegular( void ) const override {
		return m_Accessor.IsLineRegular( m_LineNo );
	}

	// switch this line accessor to the next continuation line
	nlineno_t NextIrregularLineLength( void ) const override {
		if( m_Accessor.IsLineRegular( m_IrregularLineNo ) )
			return -1;
		else
			return m_Accessor.GetLineLength( m_IrregularLineNo++ );
	}

	void GetNonFieldText( const char ** first, const char ** last ) const override {
		m_Accessor.GetNonFieldText( m_LineNo, first, last );
	}

	void GetFieldText( unsigned field_id, const char ** first, const char ** last ) const override {
		m_Accessor.GetFieldText( m_LineNo, field_id, first, last );
	}

	fieldvalue_t GetFieldValue( unsigned field_id ) const override {
		return m_Accessor.GetFieldValue( m_LineNo, field_id );
	}

	NTimecode GetUtcTimecode( void ) const override {
		return m_Accessor.GetUtcTimecode( m_LineNo );
	}
};



/*-----------------------------------------------------------------------
 * MapLogLineAccessor
 -----------------------------------------------------------------------*/

class MapLogLineAccessor : public MapLineAccessor<MapLogAccessor>
{
private:
	uint64_t m_FieldMask;

public:
	MapLogLineAccessor( const MapLineAccessor::accessor_t & accessor, uint64_t field_mask )
		: MapLineAccessor{ accessor }, m_FieldMask{ field_mask } {}

	nlineno_t GetLength( void ) const override {
		return m_Accessor.GetLineLength( m_LineNo, m_FieldMask );
	}

	void GetText( const char ** first, const char ** last ) const override {
		m_LineBuffer.Clear();

		m_Accessor.CopyLine( e_LineData::Text, m_LineNo, m_FieldMask, &m_LineBuffer );

		*first = m_LineBuffer.First();
		*last = m_LineBuffer.Last();
	}
};



/*-----------------------------------------------------------------------
 * MapViewLineAccessor
 -----------------------------------------------------------------------*/

class MapViewLineAccessor : public MapLineAccessor<MapViewAccessor>
{
public:
	MapViewLineAccessor( const MapLineAccessor::accessor_t & accessor )
		: MapLineAccessor{ accessor } {}


	nlineno_t GetLength( void ) const override {
		return m_Accessor.GetLineLength( m_LineNo );
	}

	void GetText( const char ** first, const char ** last ) const override {
		m_LineBuffer.Clear();

		m_Accessor.CopyLine( e_LineData::Text, m_LineNo, &m_LineBuffer );

		*first = m_LineBuffer.First();
		*last = m_LineBuffer.Last();
	}
};



/*-----------------------------------------------------------------------
 * VisitLines
 -----------------------------------------------------------------------*/

 // Visitor interface (callback); implemented by Visitor user
struct Visitor
{
	// the total number of lines that will be processed
	virtual void SetNumLines( nlineno_t num_lines ) {}

	// create a new Task for processing a subset of lines
	virtual task_ptr_t MakeTask( nlineno_t num_lines ) = 0;

	// combine the computed results from the Task into this Visitor
	// guaranteed to be called in visitor line-number order
	virtual void Join( task_ptr_t task ) = 0;
};


// the TBB task iterates the user task over a batch of lines - in a worker thread
template<typename T_LINEACCESSOR>
class TBBTask
{
public:
	// type for the user's task
	using lineaccessor_t = T_LINEACCESSOR;

	// sequence number for downstream serialisation of work
	const size_t m_Sequence{ 0 };

	TBBTask
	(
		const lineaccessor_t & line_accessor,
		task_ptr_t line_task,
		size_t sequence,
		nlineno_t begin_line,
		nlineno_t end_line,
		bool include_irregular
	)
		:
		m_LineAccessor{ line_accessor },
		m_Task{ line_task},
		m_Sequence{ sequence },
		m_BeginLine{ begin_line },
		m_EndLine{ end_line },
		m_SkipIrregular{ ! include_irregular }
	{}

	task_ptr_t GetUserTask( void ) const {
		return m_Task;
	}

	// run the user task
	void Action( void )
	{
		for( nlineno_t visit_line_no = m_BeginLine; visit_line_no < m_EndLine; ++visit_line_no )
		{
			m_LineAccessor.SetLineNo( visit_line_no );

			if( m_SkipIrregular && !m_LineAccessor.IsRegular() )
				continue;

			m_Task->Action( m_LineAccessor );
		}
	}

private:
	// copy of the logfile/line accessor
	lineaccessor_t m_LineAccessor;

	// line data over which the user task will be run
	const nlineno_t m_BeginLine{ 0 }, m_EndLine{ 0 };

	// the user task
	task_ptr_t m_Task;

	// should we process irregular ("continuation") lines?
	const bool m_SkipIrregular;
};

template<typename T_LINEACCESSOR>
using tbb_task_ptr_t = std::shared_ptr<TBBTask<T_LINEACCESSOR>>;


// the TBB source creates the TBB tasks to be executed by the worker threads
template<typename T_LINEACCESSOR>
struct TBBSource
{
	using lineaccessor_t = T_LINEACCESSOR;
	using tbb_task_ptr_t = ::tbb_task_ptr_t<lineaccessor_t>;

	// copy of the logfile/line accessor
	lineaccessor_t f_Accessor;

	// reference back to the user visitor
	Visitor & f_Visitor;

	// state variables
	nlineno_t f_BeginLine{ 0 };
	const nlineno_t f_EndLine;
	const nlineno_t f_LineIncr{ 10000 };
	size_t f_Sequence{ 0 };

	// should we process irregular ("continuation") lines?
	const bool f_IncludeIrregular;

	TBBSource
	(
		const lineaccessor_t & accessor,
		Visitor & visitor,
		nlineno_t num_lines,
		bool include_irregular
	)
		:
		f_Accessor{ accessor },
		f_Visitor{ visitor },
		f_EndLine{ num_lines },
		f_IncludeIrregular{ include_irregular }
	{}

	bool operator()( tbb_task_ptr_t & tbb_task )
	{
		// determine the line range
		if( f_BeginLine >= f_EndLine )
			return false;

		const bool is_last{ (f_BeginLine + f_LineIncr) >= f_EndLine };
		const nlineno_t end_line{ is_last ? f_EndLine : f_BeginLine + f_LineIncr };

		// initialise the task
		tbb_task = std::make_shared<typename tbb_task_ptr_t::element_type>
		(
			f_Accessor,
			f_Visitor.MakeTask(end_line - f_BeginLine),
			f_Sequence++,
			f_BeginLine,
			end_line,
			f_IncludeIrregular
		);

		// update ready for next call
		f_BeginLine = end_line;
		return true;
	}
};


// run the user visitor task over all lines
template<typename T_ACCESSOR, typename T_LINEACCESSOR>
void VisitLines( const T_ACCESSOR & accessor, T_LINEACCESSOR & line_accessor, Visitor & visitor, bool include_irregular )
{
	using accessor_t = T_ACCESSOR;
	using lineaccessor_t = T_LINEACCESSOR;
	using tbb_task_ptr_t = ::tbb_task_ptr_t<lineaccessor_t>;
	using tbb_source_t = TBBSource<lineaccessor_t>;

	tbb::flow::graph flow_graph;

	// the number of lines to process
	const nlineno_t line_count{ accessor.GetNumLines() };
	visitor.SetNumLines( line_count );

	// create batches of lines to process
	tbb::flow::source_node<tbb_task_ptr_t> source {
		flow_graph,
		tbb_source_t{ line_accessor, visitor, line_count, include_irregular },
		false
	};

	// process batches of lines; as an array of worker threads
	tbb::flow::function_node<tbb_task_ptr_t, tbb_task_ptr_t, tbb::flow::rejecting> work{
		flow_graph,
		tbb::flow::unlimited,
		[] ( const tbb_task_ptr_t & tbb_task ) -> tbb_task_ptr_t {
			tbb_task->Action();
			return tbb_task;
		} };

	// serialise line batches from the worker array
	tbb::flow::sequencer_node<tbb_task_ptr_t> reorder{
		flow_graph,
		[] ( const tbb_task_ptr_t & tbb_task ) -> size_t {
			return tbb_task->m_Sequence;
		} };

	// and combine user task results - in sequence
	tbb::flow::function_node<tbb_task_ptr_t> complete{
		flow_graph,
		1,	// completer is not thread safe, so only run one
		[&visitor] ( const tbb_task_ptr_t & tbb_task ) -> tbb::flow::continue_msg {
			visitor.Join( tbb_task->GetUserTask() );
			return tbb::flow::continue_msg{};
		} };

	tbb::flow::make_edge( source, work );
	tbb::flow::make_edge( work, reorder );
	tbb::flow::make_edge( reorder, complete );

	source.activate();
	flow_graph.wait_for_all();
}


void MapLogAccessor::VisitLines( Visitor & visitor, uint64_t field_mask ) const
{
	// don't include irregular lines in the visit
	MapLogLineAccessor line_accessor{ *this, field_mask };
	::VisitLines<MapLogAccessor, MapLogLineAccessor>( *this, line_accessor, visitor, false );
}


void MapViewAccessor::VisitLine( Task & task, nlineno_t visit_line_no ) const
{
	MapViewLineAccessor line_accessor{ *this };
	line_accessor.SetLineNo( visit_line_no );

	task.Action( line_accessor );
}


void MapViewAccessor::VisitLines( Visitor & visitor ) const
{
	// do include irregular lines in the visit
	MapViewLineAccessor line_accessor{ *this };
	::VisitLines<MapViewAccessor, MapViewLineAccessor>( *this, line_accessor, visitor, true );
}



/*-----------------------------------------------------------------------
 * MapViewAccessor - Filtering
 -----------------------------------------------------------------------*/

struct FilterData
{
	bool f_AddIrregular;
	Selector * f_Selector;
	LineAdornmentsProvider * f_LineAdornmentsProvider;
};


// filter a single log file line; must be thread safe
struct FilterTask : public Task
{
	// line data for the lines proccessed within this task
	std::vector<nlineno_t> f_Lines;
	std::vector<nlineno_t> f_Map;
	nlineno_t f_ViewPos{ 0 };
	const FilterData & f_FilterData;

	FilterTask( const FilterData & filter_data, nlineno_t num_lines )
		: f_FilterData{ filter_data }
	{
		f_Lines.reserve( num_lines );
		f_Map.reserve( num_lines );
	}

	void Action( const LineAccessor & line ) override
	{
		nlineno_t log_line_no{ line.GetLineNo() };
		LineAdornmentsAccessor adornments{ f_FilterData.f_LineAdornmentsProvider, log_line_no };
		if( !f_FilterData.f_Selector->Hit( line, adornments ) )
			return;

		// add the selected line
		f_Lines.push_back( f_ViewPos );
		f_Map.push_back( log_line_no++ );
		f_ViewPos += line.GetLength();

		// if requested, add in any irregular continuation lines
		// i.e. add the selected line and all of its continuations
		if( !f_FilterData.f_AddIrregular )
			return;

		nlineno_t irregular_line_length{ 0 };
		while( (irregular_line_length = line.NextIrregularLineLength()) >= 0 )
		{
			f_Lines.push_back( f_ViewPos );
			f_Map.push_back( log_line_no++ );
			f_ViewPos += irregular_line_length;
		};
	}
};


// filter all log file lines
struct FilterVisitor : public Visitor
{
	// line data for all lines
	std::vector<nlineno_t> f_Lines;
	std::vector<nlineno_t> f_Map;
	nlineno_t f_ViewPos{ 0 };
	const FilterData & f_FilterData;

	using task_ptr_t = task_ptr_t;

	FilterVisitor( const FilterData & filter_data )
		: f_FilterData{ filter_data } {}

	void SetNumLines( nlineno_t num_lines ) override
	{
		f_Lines.reserve( num_lines + 1 );
		f_Map.reserve( num_lines + 1 );
	}

	task_ptr_t MakeTask( nlineno_t num_lines ) override
	{
		return std::make_shared<FilterTask>( f_FilterData, num_lines );
	}

	void Join( task_ptr_t line_task ) override
	{
		FilterTask *filter_task{ dynamic_cast<FilterTask*>(line_task.get()) };

		for( nlineno_t line_pos : filter_task->f_Lines )
			f_Lines.push_back( f_ViewPos + line_pos );

		for( nlineno_t log_line_no : filter_task->f_Map )
			f_Map.push_back( log_line_no );

		f_ViewPos += filter_task->f_ViewPos;
	}

	void Finish( void )
	{
		// add a "one past end of file" entry; e.g. needed to find line lengths
		// which look at the next line in the document
		const bool empty{ f_Lines.empty() };
		nlineno_t last_log_lineno{ empty ? 0 : f_Map.back() + 1 };
		f_Lines.push_back( f_ViewPos );
		f_Map.push_back( last_log_lineno );
	}
};


void MapViewAccessor::Filter( Selector * selector, LineAdornmentsProvider * adornments_provider, bool add_irregular )
{
	PerfTimer timer;

	FilterData filter_data
	{
		add_irregular,
		selector,
		adornments_provider
	};

	FilterVisitor visitor{ filter_data };
	m_LogAccessor->VisitLines( visitor, m_FieldViewMask );
	visitor.Finish();

	m_TextLen = visitor.f_ViewPos;
	m_Lines = std::move( visitor.f_Lines );
	m_LineMap = std::move( visitor.f_Map );

	// an empty document in Scintilla requires a line count of one
	m_IsEmpty = m_LineMap.size() <= 1,

	// set to one for either empty, or a real line count of one ...
	// use m_IsEmpty to distinguish the two cases
	m_NumLinesOrOne = nlineno_cast( !m_IsEmpty ? m_LineMap.size() - 1 : 1 );

	// record the change
	m_Tracker.RecordEvent();

	// write out performance data
	TraceDebug( "time:%.2fs per_line:%.3fus", timer.Overall(), timer.PerItem( m_LogAccessor->GetNumLines() ) );
}



/*-----------------------------------------------------------------------
 * MapViewAccessor - Searching
 -----------------------------------------------------------------------*/

// the search implementation is adapted from the filter implementation
// search a single view line; must be thread safe
struct SearchTask : public Task
{
	// line data for the lines proccessed within this task
	std::vector<nlineno_t> f_Map;
	Selector * f_Selector;
	const LineAdornmentsProvider & f_Provider;

	SearchTask( const LineAdornmentsProvider & provider, Selector * selector, nlineno_t num_lines )
		: f_Selector{ selector }, f_Provider{ provider }
	{
		f_Map.reserve( num_lines );
	}

	void Action( const LineAccessor & line ) override
	{
		const nlineno_t view_line_no{ line.GetLineNo() };
		LineAdornmentsAccessor adornments{ & f_Provider, view_line_no };
		if( f_Selector->Hit( line, adornments ) )
			f_Map.push_back( view_line_no );
	}
};


// search all view lines
struct SearchVisitor : public Visitor
{
	// line data for all lines
	std::vector<nlineno_t> f_Map;
	Selector * f_Selector;
	const LineAdornmentsProvider & f_Provider;

	using task_ptr_t = task_ptr_t;

	SearchVisitor( const LineAdornmentsProvider & provider, Selector * selector )
		: f_Selector{ selector }, f_Provider{ provider }
	{
		const size_t guestimated_average_search_hits{ 2048 };
		f_Map.reserve( guestimated_average_search_hits );
	}

	task_ptr_t MakeTask( nlineno_t num_lines ) override
	{
		return std::make_shared<SearchTask>( f_Provider, f_Selector, num_lines );
	}

	void Join( task_ptr_t line_task ) override
	{
		SearchTask *filter_task{ dynamic_cast<SearchTask*>(line_task.get()) };

		for( nlineno_t log_line_no : filter_task->f_Map )
			f_Map.push_back( log_line_no );
	}
};


std::vector<nlineno_t> MapViewAccessor::Search( Selector * selector, LineAdornmentsProvider * adornments_provider )
{
	SearchVisitor visitor{ * adornments_provider, selector };

	PerfTimer timer;
	VisitLines( visitor );
	TraceDebug( "time:%.2fs per_line:%.3fus", timer.Overall(), timer.PerItem( GetNumLines() ) );

	return std::move( visitor.f_Map);
}

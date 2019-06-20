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

// Application includes
#include "MapLogIndexWriter.h"
#include "Nmisc.h"

// Intel TBB includes
#include <tbb/flow_graph.h>

// force link this module
void force_link_mapaccessor_module() {}



/*-----------------------------------------------------------------------
 * LineCache
 -----------------------------------------------------------------------*/

class LineCacheElement : public LineBuffer
{
protected:
	friend class LineCache;

	std::tuple<bool, unsigned> Hit( nlineno_t line_no, uint64_t field_mask ) const
	{
		if( (m_LineNo == line_no) && (m_FieldMask == field_mask) )
			return{ true, ++m_Count };
		else
			return{ false, m_Count };
	}

	void Reset( nlineno_t line_no, uint64_t field_mask )
	{
		m_LineNo = line_no;
		m_FieldMask = field_mask;
		m_Count = 1;
	}

private:
	nlineno_t m_LineNo{ -1 };
	uint64_t m_FieldMask{ 0 };
	mutable unsigned m_Count{ 0 };
};



/*-----------------------------------------------------------------------
 * LineCache
 -----------------------------------------------------------------------*/

class LineCache : public LineBuffer
{
public:
	LineCache( CacheStatistics & stats )
		: m_Stats{ stats } {}

	std::tuple<bool, LineBuffer*> Hit( nlineno_t line_no, uint64_t field_mask )
	{
		m_Stats.Lookup();

		unsigned lowest_count{ std::numeric_limits<unsigned>::max() };
		LineCacheElement * oldest{ nullptr };
		for( LineCacheElement & line : m_Lines )
		{
			bool hit; unsigned count;
			std::tie( hit, count ) = line.Hit( line_no, field_mask );
			if( hit )
				return{ true, &line };
			else if( count < lowest_count )
			{
				lowest_count = count;
				oldest = &line;
			}
		}

		m_Stats.Miss();
		oldest->Reset( line_no, field_mask );
		return{ false, oldest };
	}

private:
	CacheStatistics & m_Stats;

	static const size_t c_NumLine{ 4 };
	LineCacheElement m_Lines[ c_NumLine ];
};



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
	static CacheStatistics m_LineCacheStats[ static_cast<int>(e_LineData::_Count) ];
	mutable LineCache m_LineCache[ static_cast<int>(e_LineData::_Count) ]
	{
		{ m_LineCacheStats[ 0 ] },
		{ m_LineCacheStats[ 1 ] }
	};

	// line formatting
	LineFormatter m_LineFormatters;

protected:
	// LineVisitor interface
	void VisitLine( Task & task, nlineno_t visit_line_no, uint64_t field_mask ) const override;
	void VisitLines( Visitor & visitor, uint64_t field_mask, bool include_irregular, nlineno_t num_lines ) const override;

	std::filesystem::path CalcIndexPath( const std::filesystem::path & file_path );

	MapLogAccessor( LogAccessorDescriptor & descriptor );

public:
	// LogAccessor interfaces

	Error Open( const std::filesystem::path & file_path, ProgressMeter * progress, size_t skip_lines ) override;
	nlineno_t GetNumLines( void ) const override;
	const LineBuffer & GetLine( e_LineData type, nlineno_t line_no, uint64_t field_mask ) const override;
	void CopyLine( e_LineData type, nlineno_t line_no, uint64_t field_mask, LineBuffer * buffer ) const override;

	bool IsLineRegular( nlineno_t line_no ) const override {
		return m_Index->IsLineRegular( line_no );
	}

	nlineno_t GetLineLength( nlineno_t line_no, uint64_t field_mask ) const override {
		return m_Index->GetLineLength( line_no, field_mask );
	}

	fieldvalue_t GetFieldValue( nlineno_t line_no, unsigned field_id ) const override {
		return m_Index->GetFieldValue( line_no, field_id );
	}

	NTimecode GetUtcTimecode( nlineno_t line_no ) const override {
		const NTimecodeBase & timecode_base{ GetTimecodeBase() };
		const int64_t offset{ GetFieldValue( line_no, timecode_base.GetFieldId() ).As<int64_t>() };

		// apply the timezone offset to the result
		return NTimecode{ timecode_base.GetUtcDatum() - m_TzOffset, offset };
	}

	void SetTimezoneOffset( int offset_sec ) override {
		m_TzOffset = offset_sec;
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
	static LogAccessor * MakeMapLogAccessor( LogAccessorDescriptor & descriptor )
	{
		return new MapLogAccessor( descriptor );
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
};


static OnEvent RegisterMapLogAccessor
{
	OnEvent::EventType::Startup,
	[]() {
		LogAccessorFactory::RegisterLogAccessor( "map", MapLogAccessor::MakeMapLogAccessor );
	}
};



/*-----------------------------------------------------------------------
 * MapLogAccessor, definitions
 -----------------------------------------------------------------------*/

CacheStatistics MapLogAccessor::m_LineCacheStats[]
{
	{ "MapLogAccessor/Text" }, { "MapLogAccessor/Style" }
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


void MapLogAccessor::CopyLine( e_LineData type, nlineno_t line_no, uint64_t field_mask, LineBuffer * line_buffer ) const
{
	line_buffer->Clear();

	if( type == e_LineData::Text )
		m_Index->CopyLine( line_no, field_mask, m_Text, line_buffer );

	else
	{
		LineBuffer text;
		m_Index->CopyLine( line_no, field_mask, m_Text, &text );
		m_Index->CopyStyle( line_no, field_mask, line_buffer );
		m_LineFormatters.Apply( text, line_buffer );
	}
}


const LineBuffer & MapLogAccessor::GetLine( e_LineData type, nlineno_t line_no, uint64_t field_mask ) const
{
	LineCache & line_cache{ m_LineCache[ static_cast<int>(type) ] };

	bool hit; LineBuffer * line;
	std::tie(hit, line ) = line_cache.Hit( line_no, field_mask );

	if( !hit )
		CopyLine( type, line_no, field_mask, line );

	return *line;
}


nlineno_t MapLogAccessor::GetNumLines( void ) const
{
	return m_Index->GetNumLines();
}





/*-----------------------------------------------------------------------
 * MapLineAccessorIrregular
 -----------------------------------------------------------------------*/

class MapLineAccessorIrregular : public LineAccessorIrregular
{
private:
	const MapLogAccessor & m_LogAccessor;

	nlineno_t m_ContinuationLineCount{ -1 };
	nlineno_t m_ContinuationLine{ 0 };

	void Setup( void ) {
		nlineno_t line_no{ GetLineNo() };
		while( !m_LogAccessor.IsLineRegular( ++line_no ) )
			;

		m_ContinuationLineCount = line_no - GetLineNo() - 1;
		m_ContinuationLine = 0;
	}

public:
	MapLineAccessorIrregular( const MapLogAccessor & log_accessor )
		: m_LogAccessor{ log_accessor } {}

	void Reset( nlineno_t line_no ) {
		m_ContinuationLineCount = -1;
		SetLineNo( line_no );
	}

	MapLineAccessorIrregular * NextIrregular( void ) {
		if( m_ContinuationLineCount < 0 )
			Setup();

		if( m_ContinuationLine++ < m_ContinuationLineCount )
		{
			SetLineNo( GetLineNo() + 1 );
			return this;
		}
		return nullptr;
	}

	nlineno_t GetLength( void ) const override {
		return m_LogAccessor.GetLineLength( GetLineNo(), 0 );
	}
};



/*-----------------------------------------------------------------------
 * MapLineAccessor
 -----------------------------------------------------------------------*/

class MapLineAccessor : public LineAccessor
{
private:
	// transient store for line information
	mutable LineBuffer m_LineBuffer;

	const MapLogAccessor & m_LogAccessor;
	const uint64_t m_FieldMask;

private:
	// continuation line handling
	mutable MapLineAccessorIrregular m_Irregulars;

public:
	MapLineAccessor( const MapLogAccessor & log_accessor, uint64_t field_mask )
		:
		m_LogAccessor{ log_accessor },
		m_FieldMask{ field_mask },
		m_Irregulars{ log_accessor }
	{}

	MapLineAccessor( const MapLineAccessor & map_line_accessor )
		:
		m_LogAccessor{ map_line_accessor.m_LogAccessor },
		m_FieldMask{ map_line_accessor.m_FieldMask },
		m_Irregulars { map_line_accessor.m_LogAccessor }
	{}

	void SetLineNo( nlineno_t line_no ) {
		m_Irregulars.Reset( line_no );
		LineAccessor::SetLineNo( line_no );
	}

public:
	// LineAccessor interfaces

	bool IsRegular( void ) const override {
		return m_LogAccessor.IsLineRegular( GetLineNo() );
	}

	// switch this line accessor to the next continuation line
	const LineAccessorIrregular * NextIrregular( void ) const override {
		return m_Irregulars.NextIrregular();
	}

	nlineno_t GetLength( void ) const override {
		return m_LogAccessor.GetLineLength( GetLineNo(), m_FieldMask );
	}

	void GetText( const char ** first, const char ** last ) const override {
		m_LineBuffer.Clear();

		m_LogAccessor.CopyLine( e_LineData::Text, GetLineNo(), m_FieldMask, &m_LineBuffer );

		*first = m_LineBuffer.First();
		*last = m_LineBuffer.Last();
	}

	void GetNonFieldText( const char ** first, const char ** last ) const override {
		m_LogAccessor.GetNonFieldText( GetLineNo(), first, last );
	}

	void GetFieldText( unsigned field_id, const char ** first, const char ** last ) const override {
		m_LogAccessor.GetFieldText( GetLineNo(), field_id, first, last );
	}

	fieldvalue_t GetFieldValue( unsigned field_id ) const override {
		return m_LogAccessor.GetFieldValue( GetLineNo(), field_id );
	}

	NTimecode GetUtcTimecode( void ) const override {
		return m_LogAccessor.GetUtcTimecode( GetLineNo() );
	}
};



/*-----------------------------------------------------------------------
 * LineVisitor
 -----------------------------------------------------------------------*/

 // apply a task to a single line
void MapLogAccessor::VisitLine( Task & task, nlineno_t visit_line_no, uint64_t field_mask ) const
{
	const nlineno_t log_line_no{ task.VisitLineToLogLine( visit_line_no ) };

	MapLineAccessor accessor{ *this, field_mask };
	accessor.SetLineNo( log_line_no );

	task.Action( accessor, visit_line_no );
}


// the TBB task iterates the user task over a batch of lines - in a worker thread
class TBBTask
{
public:
	// type for the user's task
	using task_t = LineVisitor::task_t;

	// sequence number for downstream serialisation of work
	const size_t m_Sequence{ 0 };

	TBBTask
	(
		const MapLineAccessor & log_accessor,
		task_t line_task,
		size_t sequence,
		nlineno_t begin_line,
		nlineno_t end_line,
		bool include_irregular
	)
		:
		m_LogAccessor{ log_accessor },
		m_Task{ line_task},
		m_Sequence{ sequence },

		m_BeginLine{ begin_line }, m_EndLine{ end_line },
		m_SkipIrregular{ ! include_irregular }
	{}

	task_t GetUserTask( void ) const {
		return m_Task;
	}

	// run the user task
	void Action( void )
	{
		for( nlineno_t i = m_BeginLine; i < m_EndLine; ++i )
		{
			// map line numbers from the "arbitrary" line number space to real log lines
			const nlineno_t log_line_no{ m_Task->VisitLineToLogLine( i ) };
			m_LogAccessor.SetLineNo( log_line_no );

			if( m_SkipIrregular && !m_LogAccessor.IsRegular() )
				continue;
			m_Task->Action( m_LogAccessor, i );
		}
	}

private:
	// copy of the logfile/line accessor
	MapLineAccessor m_LogAccessor;

	// line data over which the user task will be run
	const nlineno_t m_BeginLine{ 0 }, m_EndLine{ 0 };

	// the user task
	task_t m_Task;

	// should we process irregular ("continuation") lines?
	const bool m_SkipIrregular;
};
using tbb_task_t = std::shared_ptr<TBBTask>;


// the TBB source creates the TBB tasks to be executed by the worker threads
struct TBBSource
{
	using Visitor = LineVisitor::Visitor;

	// copy of the logfile/line accessor
	MapLineAccessor f_Accessor;

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
		const MapLineAccessor & accessor,
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

	bool operator()( tbb_task_t & tbb_task )
	{
		// determine the line range
		if( f_BeginLine >= f_EndLine )
			return false;

		const bool is_last{ (f_BeginLine + f_LineIncr) >= f_EndLine };
		const nlineno_t end_line{ is_last ? f_EndLine : f_BeginLine + f_LineIncr };

		// initialise the task
		tbb_task = std::make_shared<TBBTask>
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
void MapLogAccessor::VisitLines( Visitor & visitor, uint64_t field_mask, bool include_irregular, nlineno_t num_lines ) const
{
	tbb::flow::graph flow_graph;

	MapLineAccessor accessor{ *this, field_mask };

	// the number of lines to process is either supplied by the caller
	// (as view lines) or is taken from the log file
	const nlineno_t line_count{ (num_lines < 0) ? GetNumLines() : num_lines };

	// create batches of lines to process
	tbb::flow::source_node<tbb_task_t> source {
		flow_graph,
		TBBSource{ accessor, visitor, line_count, include_irregular },
		false
	};

	// process batches of lines; as an array of worker threads
	tbb::flow::function_node<tbb_task_t, tbb_task_t, tbb::flow::rejecting> work{
		flow_graph,
		tbb::flow::unlimited,
		[] ( const tbb_task_t & tbb_task ) -> tbb_task_t {
			tbb_task->Action();
			return tbb_task;
		} };

	// serialise line batches from the worker array
	tbb::flow::sequencer_node<tbb_task_t> reorder{
		flow_graph,
		[] ( const tbb_task_t & tbb_task ) -> size_t {
			return tbb_task->m_Sequence;
		} };

	// and combine user task results - in sequence
	tbb::flow::function_node<tbb_task_t> complete{
		flow_graph,
		1,	// completer is not thread safe, so only run one
		[&visitor] ( const tbb_task_t & tbb_task ) -> tbb::flow::continue_msg {
			visitor.Join( tbb_task->GetUserTask() );
			return tbb::flow::continue_msg{};
		} };

	tbb::flow::make_edge( source, work );
	tbb::flow::make_edge( work, reorder );
	tbb::flow::make_edge( reorder, complete );

	source.activate();
	flow_graph.wait_for_all();
}

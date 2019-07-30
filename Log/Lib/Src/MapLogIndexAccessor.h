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
#include "FileMap.h"
#include "FieldAccessor.h"
#include "LogAccessor.h"

// C++ includes
#include <algorithm>
#include <map>
#include <memory>
#include <vector>



/*-----------------------------------------------------------------------
 * IndexFileHeader
 -----------------------------------------------------------------------*/

// file structures should be 8-byte sized and aligned

enum E_Header : uint32_t
{
	e_Magic = 0xf00dc0de,
	e_DataOffset = 1024,
	e_IndexVersion_1 = 1,
	e_IndexVersion_2 = 2

};

// header data held in an index file
struct IndexFileHeaderV1
{
	// file identification
	const uint32_t f_Magic{ E_Header::e_Magic };
	const uint16_t f_HeaderSize;
	const uint8_t f_FileVersion;
	uint8_t f_NumFields{ 0 };

	// null terminated GUID string identifying the field schema
	char f_SchemaGuid[ 40 ]{ 0 };

	// reference modified time for the indexed log file
	FILETIME f_LogfileModifiedTime{ 0 };

	// line location information
	uint64_t f_LineDataOffset{ E_Header::e_DataOffset };
	uint64_t f_NumLines{ 0 };

	// location of field information; equivalent to:
	//  FieldHeaderV1 f_FieldDataOffset[f_NumFields];
	uint64_t f_FieldDataOffset{ 0 };

	// location of string table
	uint64_t f_StringTableOffset{ 0 };

	// UTC of first log line; effectively the datum for all time offsets
	// time offsets are measured in nano-seconds from this datum
	int64_t f_UtcDatum{ 0 };

	IndexFileHeaderV1( uint16_t header_size = sizeof( IndexFileHeaderV1 ), uint8_t version = e_IndexVersion_1 )
		: f_HeaderSize{ header_size }, f_FileVersion{ version } {}
};


struct IndexFileHeaderV2 : public IndexFileHeaderV1
{
	int8_t f_TimecodeFieldId{ -1 };

	IndexFileHeaderV2( void )
		: IndexFileHeaderV1{ sizeof( IndexFileHeaderV2 ), e_IndexVersion_2 } {}
};


// current header version
using IndexFileHeader = IndexFileHeaderV2;



/*-----------------------------------------------------------------------
 * FieldHeader
 -----------------------------------------------------------------------*/

// common data for fields
struct FieldHeaderV1
{
	const uint16_t f_HeaderSize{ sizeof( FieldHeaderV1 ) };
	const uint16_t f_FieldVersion{ 0 };

	uint32_t f_Padding{ 0 };

	FieldHeaderV1( uint16_t header_size, uint16_t field_version )
		: f_HeaderSize{ header_size }, f_FieldVersion{ field_version } {}
};


struct FieldHeaderEnumV1 : public FieldHeaderV1
{
	// number of enumerated items
	const uint16_t f_Count{ 0 };

	// padding
	uint16_t f_Padding1{ 0 };
	uint32_t f_Padding2{ 0 };

	// followed by:

	// array of offsets into string table
	// uint64_t f_Names[f_Count];

	FieldHeaderEnumV1( uint16_t count )
		:
		FieldHeaderV1{
			static_cast<uint16_t>(sizeof( FieldHeaderEnumV1 ) + (count * sizeof( uint64_t ))),
			0
		},
		f_Count{ count }
	{}
};



/*-----------------------------------------------------------------------
 * FieldTextOffsetsCommon
 -----------------------------------------------------------------------*/

// common support for accessing the text offests field binary data
// T_OFFSET should be uint8_t or uint16_t; T_OFFSETPAIR must be a type twice
// as long as T_OFFSET
template<typename T_OFFSET, typename T_OFFSET_PAIR>
class FieldTextOffsetsCommon
{
public:
	using offset_t = T_OFFSET;
	static const size_t c_OffsetSize{ sizeof( offset_t ) };

protected:
	using offsetpair_t = T_OFFSET_PAIR;
	static const size_t c_OffsetPairSize{ sizeof( offsetpair_t ) };

	static_assert(c_OffsetPairSize == 2 * c_OffsetSize, "Mismatched offset sizes");

	// determine the size of the offsets field in bytes
	static size_t CalcOffsetFieldSize( size_t num_fields ) {
		// for lines containing fields, the offsets field is an array of offset_t;
		// otherwise where no fields are present, the offsets "array" consists of
		// the line number of the last line which did have fields, preceded by two
		// zero offset_t's
		return std::max( 2 * num_fields * c_OffsetSize, sizeof( int64_t ) + c_OffsetPairSize );
	}

	static bool IsRegular( const uint8_t * data ) {
		return *reinterpret_cast<const offsetpair_t*>( data ) != 0;
	}

	static int64_t & GetLastRegular( uint8_t * data ) {
		return * reinterpret_cast<int64_t*>( data + c_OffsetPairSize);
	}
	static int64_t GetLastRegular( const uint8_t * data ) {
		return *reinterpret_cast<const int64_t*>( data + c_OffsetPairSize);
	}
};



/*-----------------------------------------------------------------------
 * LogIndexAccessor
 -----------------------------------------------------------------------*/

// forwards
class FieldAccessor;

// provide access to a logfile's index
class LogIndexAccessor : public FieldStore<FieldAccessor>
{
private:
	// the index data
	FileMap m_Map;

	// amount of data stored for each line
	size_t m_LineDataSize{ 0 };

	// start of the line's data in the index
	const uint8_t * m_LineData{ nullptr };

	// the timecode field index and UTC datum from the file header
	NTimecodeBase m_TimecodeBase;

protected:
	// number of lines in the logfile
	nlineno_t m_NumLines{ 0 };

protected:
	Error LoadHeader( FILETIME modified_time, const std::string & guid );

	// fetch line's data for a given line
	const uint8_t * GetLineData( nlineno_t line_no ) const {
		return m_LineData + (line_no * m_LineDataSize);
	}

	// fetch offset to line's text in the text map
	nlineno_t GetLineOffset( nlineno_t line_no ) const {
		return nlineno_cast( GetFieldValue( line_no, 0 ).As<uint64_t>() );
	}

public:
	LogIndexAccessor( const fielddescriptor_list_t & field_descs );
	Error Load( const std::filesystem::path & file_path, FILETIME modified_time, const std::string & guid );

	virtual bool IsLineRegular( nlineno_t line_no ) const = 0;
	virtual nlineno_t GetLineLength( nlineno_t line_no, uint64_t field_mask ) const = 0;
	virtual void CopyLine( nlineno_t line_no, uint64_t field_mask, const char * log_text, LineBuffer * line_buffer ) const = 0;
	virtual void CopyStyle( nlineno_t line_no, uint64_t field_mask, LineBuffer * line_buffer ) const = 0;
	virtual void GetNonFieldTextOffsets( nlineno_t line_no, nlineno_t *first, nlineno_t * last ) const = 0;
	virtual void GetFieldTextOffsets( nlineno_t line_no, unsigned field_id, nlineno_t *first, nlineno_t * last ) const = 0;

	FieldValueType GetFieldType( unsigned field_id ) const;
	fieldvalue_t GetFieldValue( nlineno_t line_no, unsigned field_id ) const;

	nlineno_t GetNumLines( void ) const {
		return m_NumLines;
	}

	const NTimecodeBase & GetTimecodeBase( void ) const {
		return m_TimecodeBase;
	}

	uint16_t GetFieldEnumCount( unsigned field_id ) const;
	const char * GetFieldEnumName( unsigned field_id, uint16_t enum_id ) const;
};

std::unique_ptr<LogIndexAccessor> MakeLogIndexAccessor( const std::string & text_offsets_field_type, const fielddescriptor_list_t & field_descs );
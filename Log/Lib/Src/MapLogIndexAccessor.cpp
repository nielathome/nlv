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
#include "MapLogIndexAccessor.h"

// C++ includes
#include <chrono>



/*-----------------------------------------------------------------------
 * FieldEnumAccessor
 -----------------------------------------------------------------------*/

// interface for the "extra" data that can be supplied by an enumeration
// field

struct FieldEnumAccessor
{
	// number of enumeration values
	virtual uint16_t GetCount( void ) const = 0;

	// textual value
	virtual const char * GetText( uint16_t enum_id ) const = 0;
};



/*-----------------------------------------------------------------------
 * MapFieldAccessor
 -----------------------------------------------------------------------*/

using mapfieldaccessor_maker_t = FieldTraits<MapFieldAccessor>::field_ptr_t (*) (const FieldDescriptor & field_desc, unsigned field_id, size_t * offset);

class MapFieldAccessor : public FieldFactory<MapFieldAccessor, mapfieldaccessor_maker_t>
{
protected:
	const IndexFileHeader * m_FileHeader{ nullptr };
	unsigned m_FieldId{ 0 };

protected:
	// convert an index offset into a pointer to the mapped data
	template<typename T_TYPE>
	const T_TYPE * offset_as( size_t offset ) const {
		const uint8_t * datum{ reinterpret_cast<const uint8_t *>(m_FileHeader) };
		return reinterpret_cast<const T_TYPE *>(datum + offset);
	}

	// fetch a string from the string table; the string_id is an offset into the string table
	const char * GetString( size_t string_id ) const {
		return offset_as<char>( m_FileHeader->f_StringTableOffset + string_id );
	}

	// fetch a pointer to the field's data, suitably typed
	template<typename T_TYPE = uint8_t>
	const T_TYPE * GetFieldData( const uint8_t * line_data ) const {
		return reinterpret_cast<const T_TYPE *>(line_data + c_FieldOffset);
	}

public:
	// constructor
	MapFieldAccessor( FieldValueType type, size_t size, const FieldDescriptor & field_desc, unsigned, size_t * offset )
		:
		c_FieldType{ type },
		c_FieldSize{ size },
		c_FieldName{ field_desc.f_Name },
		c_FieldOffset{ *offset }
	{
		(*offset) += c_FieldSize;
	}

	// the field's class
	const FieldValueType c_FieldType;

	// the size of this field's data in the index
	const size_t c_FieldSize;

	// the field's name
	const std::string c_FieldName;

	// the offset of this field's data from the start of the line entry
	const size_t c_FieldOffset;

	// attach the accessor to a logfile
	virtual Error AttachIndex( unsigned field_id, const IndexFileHeader * header ) {
		m_FieldId = field_id;
		m_FileHeader = header;
		return e_OK;
	}

	// fetch the field's type
	FieldValueType GetType( void ) const {
		return c_FieldType;
	}

	// fetch the field's current (binary) value
	virtual fieldvalue_t GetValue( const uint8_t * line_data ) const {
		const uint64_t value{ 0 };
		return fieldvalue_t{ value };
	}

	// enumeration fields support a number of extra interfaces
	virtual const FieldEnumAccessor * GetEnumAccessor( void ) const {
		return nullptr;
	}
};



/*-----------------------------------------------------------------------
 * MapFieldAccessorNull
 -----------------------------------------------------------------------*/

// use where no data is associated with a field - e.g. a text only field
struct MapFieldAccessorNull : public MapFieldAccessor
{
	MapFieldAccessorNull( const FieldDescriptor & field_desc, unsigned field_id, size_t * offset )
		: MapFieldAccessor{ FieldValueType::invalid, 0, field_desc, field_id, offset } {}
};



/*-----------------------------------------------------------------------
 * MapFieldAccessorScalar
 -----------------------------------------------------------------------*/

template<typename T_MAPPED_VALUE, typename T_FIELD_VALUE>
struct MapFieldAccessorScalar : public MapFieldAccessor
{
	using mapped_t = T_MAPPED_VALUE;
	using fieldtype_t = T_FIELD_VALUE;

	MapFieldAccessorScalar( const FieldDescriptor & field_desc, unsigned field_id, size_t * offset )
		: MapFieldAccessor{ TypeToFieldType<fieldtype_t>::type, sizeof( mapped_t ), field_desc, field_id, offset } {}

	fieldvalue_t GetValue( const uint8_t * line_data ) const override {
		// not sure on performance consequences for unaligned pointers here
		const fieldtype_t field_value{ * GetFieldData<mapped_t>(line_data) };
		return fieldvalue_t{ field_value };
	}
};


template<typename T_UINT>
using MapFieldAccessorUint = MapFieldAccessorScalar<T_UINT, uint64_t>;

template<typename T_INT>
using MapFieldAccessorInt = MapFieldAccessorScalar<T_INT, int64_t>;

template<typename T_FLOAT>
using MapFieldAccessorFloat = MapFieldAccessorScalar<T_FLOAT, double>;

using MapFieldAccessorBool = MapFieldAccessorUint<uint8_t>;
using MapFieldAccessorDate = MapFieldAccessorInt<int64_t>;



/*-----------------------------------------------------------------------
 * MapFieldAccessorEnum
 -----------------------------------------------------------------------*/

template<typename T_UINT>
class MapFieldAccessorEnum : public MapFieldAccessorUint<T_UINT>, public FieldEnumAccessor
{
private:
	using base_t = MapFieldAccessorUint<T_UINT>;

	const FieldHeaderEnumV1 * m_FieldHeader{ nullptr };

public:
	MapFieldAccessorEnum( const FieldDescriptor & field_desc, unsigned field_id, size_t * offset )
		: base_t{ field_desc, field_id, offset } {}

	// attach the accessor to a logfile; initialise m_FieldHeader
	Error AttachIndex( unsigned field_id, const IndexFileHeader * header ) override {
		const Error res{ MapFieldAccessor::AttachIndex( field_id, header ) };

		if( Ok( res ) )
		{
			size_t offset{ m_FileHeader->f_FieldDataOffset };
			for( unsigned i = 0; i < m_FieldId; ++i )
				offset += offset_as<FieldHeaderEnumV1>( offset )->f_HeaderSize;
			m_FieldHeader = offset_as<FieldHeaderEnumV1>( offset );
		}

		return res;
	}

	// enumeration fields support a number of extra interfaces
	const FieldEnumAccessor * GetEnumAccessor( void ) const {
		return this;
	}

	uint16_t GetCount( void ) const override {
		return m_FieldHeader->f_Count;
	}

	const char * GetText( uint16_t enum_id ) const override {
		const size_t * enum_string_ids{ reinterpret_cast<const size_t *>(m_FieldHeader + 1) };
		return GetString( enum_string_ids[ enum_id ] );
	}
};



/*-----------------------------------------------------------------------
 * MapFieldAccessorTextOffsets
 -----------------------------------------------------------------------*/

template<typename T_OFFSET, typename T_OFFSET_PAIR>
class MapFieldAccessorTextOffsets
	:
	public MapFieldAccessor,
	public FieldTextOffsetsCommon<T_OFFSET, T_OFFSET_PAIR>
{
protected:
	const RawFieldData * GetRawFieldData( const uint8_t * line_data ) const {
		return GetFieldData<RawFieldData>( line_data );
	}

public:
	MapFieldAccessorTextOffsets( const FieldDescriptor & field_desc, unsigned field_id, size_t * offset )
		: MapFieldAccessor{ FieldValueType::invalid, CalcOffsetFieldSize( field_id - 1 ), field_desc, field_id, offset } {}

	// does the line have any fields
	bool IsRegular( const uint8_t * line_data ) const {
		return RawToIsRegular( GetRawFieldData( line_data ) );
	}

	int64_t LastRegularLine( const uint8_t * line_data ) const {
		return RawToLastRegular( GetRawFieldData( line_data ) );
	}

	void GetNonFieldTextOffset( const uint8_t * line_data, offset_t * first ) const {
		const RawFieldData * data{ GetRawFieldData( line_data ) };
		if( RawToIsRegular( data ) )
			*first = RawToNonFieldTextOffset( data );
		else
			*first = 0;
	}

	void GetFieldTextOffsets( const uint8_t * line_data, unsigned field_id, offset_t * first, offset_t * last ) const {
		const RawFieldData * data{ GetRawFieldData( line_data ) };
		if( RawToIsRegular( data ) )
		{
			const offset_t * field_data{ RawToFieldTextOffsets( data, field_id ) };
			*first = field_data[ 0 ];
			*last = field_data[ 1 ];
		}
		else
			*first = *last = 0;
	}

	template<typename T_FUNC>
	void VisitFieldOffsets( const uint8_t * line_data, uint64_t field_mask, size_t max_count, T_FUNC & func )
	{
		if( field_mask == 0 )
			return;

		const RawFieldData * data{ GetRawFieldData( line_data ) };
		if( !RawToIsRegular( data ) )
			return;

		// for each visible field
		uint64_t field_bit{ 0x1 };
		for( unsigned field_id = 0; field_id < max_count; ++field_id )
		{
			if( field_bit & field_mask )
			{
				const offset_t * field_data{ RawToFieldTextOffsets( data, field_id ) };
				func( field_id, field_data[ 0 ], field_data[ 1 ] );
			}
			field_bit = field_bit << 1;
		}
	}
};

using MapFieldAccessorTextOffsets08 = MapFieldAccessorTextOffsets<uint8_t, uint16_t>;
using MapFieldAccessorTextOffsets16 = MapFieldAccessorTextOffsets<uint16_t, uint32_t>;



/*-----------------------------------------------------------------------
 * MapFieldAccessor Factory
 -----------------------------------------------------------------------*/

MapFieldAccessor::factory_t::map_t MapFieldAccessor::factory_t::m_Map
{
	{ c_Type_DateTime_Unix, &MakeField<MapFieldAccessorDate, const FieldDescriptor &, unsigned, size_t *> },
	{ c_Type_DateTime_UsStd, &MakeField<MapFieldAccessorDate, const FieldDescriptor &, unsigned, size_t *> },
	{ c_Type_DateTime_TraceFmt_IntStd, &MakeField<MapFieldAccessorDate, const FieldDescriptor &, unsigned, size_t *> },
	{ c_Type_DateTime_TraceFmt_UsStd, &MakeField<MapFieldAccessorDate, const FieldDescriptor &, unsigned, size_t *> },
	{ c_Type_DateTime_TraceFmt_IntHires, &MakeField<MapFieldAccessorDate, const FieldDescriptor &, unsigned, size_t *> },
	{ c_Type_DateTime_TraceFmt_UsHires, &MakeField<MapFieldAccessorDate, const FieldDescriptor &, unsigned, size_t *> },
	{ c_Type_Bool, &MakeField<MapFieldAccessorBool, const FieldDescriptor &, unsigned, size_t *> },
	{ c_Type_Uint08, &MakeField<MapFieldAccessorUint<uint8_t>, const FieldDescriptor &, unsigned, size_t *> },
	{ c_Type_Uint16, &MakeField<MapFieldAccessorUint<uint16_t>, const FieldDescriptor &, unsigned, size_t *> },
	{ c_Type_Uint32, &MakeField<MapFieldAccessorUint<uint32_t>, const FieldDescriptor &, unsigned, size_t *> },
	{ c_Type_Uint64, &MakeField<MapFieldAccessorUint<uint64_t>, const FieldDescriptor &, unsigned, size_t *> },
	{ c_Type_Int08, &MakeField<MapFieldAccessorInt<int8_t>, const FieldDescriptor &, unsigned, size_t *> },
	{ c_Type_Int16, &MakeField<MapFieldAccessorInt<int16_t>, const FieldDescriptor &, unsigned, size_t *> },
	{ c_Type_Int32, &MakeField<MapFieldAccessorInt<int32_t>, const FieldDescriptor &, unsigned, size_t *> },
	{ c_Type_Int64, &MakeField<MapFieldAccessorInt<int64_t>, const FieldDescriptor &, unsigned, size_t *> },
	{ c_Type_Float32, &MakeField<MapFieldAccessorFloat<float>, const FieldDescriptor &, unsigned, size_t *> },
	{ c_Type_Float64, &MakeField<MapFieldAccessorFloat<double>, const FieldDescriptor &, unsigned, size_t *> },
	{ c_Type_Enum08, &MakeField<MapFieldAccessorEnum<uint8_t>, const FieldDescriptor &, unsigned, size_t *> },
	{ c_Type_Enum16, &MakeField<MapFieldAccessorEnum<uint16_t>, const FieldDescriptor &, unsigned, size_t *> },
	{ c_Type_Emitter, &MakeField<MapFieldAccessorNull, const FieldDescriptor &, unsigned, size_t *> },
	{ c_Type_Text, &MakeField<MapFieldAccessorNull, const FieldDescriptor &, unsigned, size_t *> },
	{ c_Type_TextOffsets08, &MakeField<MapFieldAccessorTextOffsets08, const FieldDescriptor &, unsigned, size_t *> },
	{ c_Type_TextOffsets16, &MakeField<MapFieldAccessorTextOffsets16, const FieldDescriptor &, unsigned, size_t *> }
};



/*-----------------------------------------------------------------------
 * LogIndexAccessor
 -----------------------------------------------------------------------*/

LogIndexAccessor::LogIndexAccessor( const fielddescriptor_list_t & field_descs, unsigned text_offsets_size )
{
	m_FieldLineOffset = CreateField( FieldDescriptor{ false, "", "uint64" }, &m_LineDataSize );
	AddInternalField( m_FieldLineOffset );

	SetupUserFields( field_descs, &m_LineDataSize );

	const std::string text_offsets_field_type{ text_offsets_size == sizeof(uint16_t) ? c_Type_TextOffsets16 : c_Type_TextOffsets08 };
	AddInternalField( CreateField( FieldDescriptor{ false, "", text_offsets_field_type }, &m_LineDataSize ) );
}


nlineno_t LogIndexAccessor::GetLineOffset( nlineno_t line_no ) const
{
	const fieldvalue_t value{ m_FieldLineOffset->GetValue( GetLineData( line_no ) ) };
	return nlineno_cast( value.As<uint64_t>() );
}


FieldValueType LogIndexAccessor::GetFieldType( unsigned field_id ) const
{
	return m_UserFields[ field_id ]->GetType();
}


fieldvalue_t LogIndexAccessor::GetFieldValue( nlineno_t line_no, unsigned field_id ) const
{
	return m_UserFields[ field_id ]->GetValue( GetLineData( line_no ) );
}


Error LogIndexAccessor::LoadHeader( FILETIME modified_time, const std::string & guid )
{
	const IndexFileHeader *hdr{ m_Map.GetData<IndexFileHeader >() };

	if( hdr->f_Magic != E_Header::e_Magic )
		return TraceError( e_CorruptIndex, "Index has bad file type" );

	if( hdr->f_FileVersion != E_Header::e_IndexVersion_2 )
		return TraceError( e_UnsupportedIndexVersion, "Version %d", hdr->f_FileVersion );

	if( CompareFileTime( &hdr->f_LogfileModifiedTime, &modified_time ) != 0 )
		return TraceError( e_LogfileChanged, "Log file has been modified" );

	if( std::string( hdr->f_SchemaGuid) != guid )
		return TraceError( e_FieldSchemaChanged, "Index is out of date" );

	if( hdr->f_NumFields != m_AllFields.size() )
		return TraceError( e_WrongIndex, "Index does not match given specification" );

	Error res{ e_OK };
	for(unsigned field_id = 0; field_id < m_AllFields.size(); ++field_id )
		UpdateError( res, m_AllFields[ field_id ]->AttachIndex( field_id, hdr ) );

	m_LineData = reinterpret_cast<const uint8_t*>( m_Map.GetData() + hdr->f_LineDataOffset );
	m_NumLines = nlineno_cast(hdr->f_NumLines);

	// for historic reasons, the stored timecode field id is actually the field
	// index, which is one more than the user-field id - hence subtract one here
	const unsigned field_id{ static_cast<unsigned>(hdr->f_TimecodeFieldId) - 1 };
	m_TimecodeBase = NTimecodeBase{ hdr->f_UtcDatum, field_id };

	return res;
}


Error LogIndexAccessor::Load( const std::filesystem::path & file_path, FILETIME modified_time, const std::string & guid )
{
	Error res{ m_Map.Map( file_path ) };
	if( Ok( res ) )
		res = LoadHeader( modified_time, guid);
	return res;
}


uint16_t LogIndexAccessor::GetFieldEnumCount( unsigned field_id ) const
{
	const FieldEnumAccessor * enum_accessor{ m_UserFields[ field_id ]->GetEnumAccessor() };
	return enum_accessor ? enum_accessor->GetCount() : 0;
}


const char * LogIndexAccessor::GetFieldEnumName( unsigned field_id, uint16_t enum_id ) const
{
	const FieldEnumAccessor * enum_accessor{ m_UserFields[ field_id ]->GetEnumAccessor() };
	return enum_accessor ? enum_accessor->GetText( enum_id ) : nullptr;
}



/*-----------------------------------------------------------------------
 * LogIndexAccessorFull
 -----------------------------------------------------------------------*/

template<typename T_FIELD_TEXTOFFSETS>
class LogIndexAccessorFull : public LogIndexAccessor
{
private:
	// the text offsets field has extra services; keep a typed pointer to it
	T_FIELD_TEXTOFFSETS * m_FieldTextOffsets;

	// offsets into the log text can be 8 or 16 bit quantities
	using offset_t = typename T_FIELD_TEXTOFFSETS::offset_t;

protected:
	bool IsLineRegular( nlineno_t line_no ) const override;
	nlineno_t GetLineLength( nlineno_t line_no, uint64_t field_mask ) const override;
	void CopyLine( nlineno_t line_no, uint64_t field_mask, const char * log_text, LineBuffer * line_buffer ) const override;
	void CopyStyle( nlineno_t line_no, uint64_t field_mask, LineBuffer * line_buffer ) const override;
	void GetNonFieldTextOffsets( nlineno_t line_no, nlineno_t * first, nlineno_t * last ) const override;
	void GetFieldTextOffsets( nlineno_t line_no, unsigned field_id, nlineno_t * first, nlineno_t * last ) const override;

public:
	LogIndexAccessorFull( const fielddescriptor_list_t & field_descs )
		: LogIndexAccessor{ field_descs, T_FIELD_TEXTOFFSETS::c_OffsetSize }
	{
		// the last field must be the TextOffsets
		m_FieldTextOffsets = dynamic_cast<T_FIELD_TEXTOFFSETS*>(m_AllFields.back().get());
	}
};


template<typename T_FIELD_TEXTOFFSETS>
bool LogIndexAccessorFull<T_FIELD_TEXTOFFSETS>::IsLineRegular( nlineno_t line_no ) const
{
	if( line_no < m_NumLines )
		return m_FieldTextOffsets->IsRegular( GetLineData( line_no ) );
	return true;
}


template<typename T_FIELD_TEXTOFFSETS>
nlineno_t LogIndexAccessorFull<T_FIELD_TEXTOFFSETS>::GetLineLength( nlineno_t line_no, uint64_t field_mask ) const
{
	nlineno_t length{ 0 };

	m_FieldTextOffsets->VisitFieldOffsets( GetLineData( line_no ), field_mask, GetNumUserFields(),
		[&length] ( unsigned, offset_t off_lo, offset_t off_hi ) {
			length += off_hi - off_lo + 1;
		}
	);

	nlineno_t first, last;
	GetNonFieldTextOffsets( line_no, &first, &last );
	length += last - first;

	return length;
}


template<typename T_FIELD_TEXTOFFSETS>
void LogIndexAccessorFull<T_FIELD_TEXTOFFSETS>::CopyLine( nlineno_t line_no, uint64_t field_mask, const char * log_text, LineBuffer * line_buffer ) const
{
	const char * line_text{ log_text + GetLineOffset( line_no ) };

	m_FieldTextOffsets->VisitFieldOffsets( GetLineData( line_no ), field_mask, GetNumUserFields(),
		[&line_buffer, line_text] ( unsigned, offset_t off_lo, offset_t off_hi ) {
			line_buffer->Append( line_text + off_lo, line_text + off_hi );
			line_buffer->Append( ' ' );
		}
	);

	nlineno_t first, last;
	GetNonFieldTextOffsets( line_no, &first, &last );
	line_buffer->Append( log_text + first, log_text + last );
}


template<typename T_FIELD_TEXTOFFSETS>
void LogIndexAccessorFull<T_FIELD_TEXTOFFSETS>::CopyStyle( nlineno_t line_no, uint64_t field_mask, LineBuffer * line_buffer ) const
{
	m_FieldTextOffsets->VisitFieldOffsets( GetLineData( line_no ), field_mask, GetNumUserFields(),
		[&line_buffer] ( unsigned field_id, offset_t off_lo, offset_t off_hi ) {
			line_buffer->Append( static_cast<char>(field_id), off_hi - off_lo + 1 );
		}
	);

	nlineno_t first, last;
	GetNonFieldTextOffsets( line_no, &first, &last );
	line_buffer->Append( e_StyleDefault, last - first );
}


template<typename T_FIELD_TEXTOFFSETS>
void LogIndexAccessorFull<T_FIELD_TEXTOFFSETS>::GetNonFieldTextOffsets( nlineno_t line_no, nlineno_t * first, nlineno_t * last ) const
{
	offset_t text_offset{ 0 };
	m_FieldTextOffsets->GetNonFieldTextOffset( GetLineData( line_no ), &text_offset );

	*first = GetLineOffset( line_no ) + text_offset;
	*last = GetLineOffset( line_no + 1 );
}


template<typename T_FIELD_TEXTOFFSETS>
void LogIndexAccessorFull<T_FIELD_TEXTOFFSETS>::GetFieldTextOffsets( nlineno_t line_no, unsigned field_id, nlineno_t * first, nlineno_t * last ) const
{
	offset_t first_offset{ 0 }, last_offset{ 0 };
	m_FieldTextOffsets->GetFieldTextOffsets( GetLineData( line_no ), field_id,
		&first_offset, &last_offset
	);

	const nlineno_t line_offset{ GetLineOffset( line_no ) };
	*first = line_offset + first_offset;
	*last = line_offset + last_offset;
}



/*-----------------------------------------------------------------------
 * MakeLogIndexAccessor
 -----------------------------------------------------------------------*/

std::unique_ptr<LogIndexAccessor> MakeLogIndexAccessor( const std::string & text_offsets_field_type, const fielddescriptor_list_t & field_descs )
{
	if( text_offsets_field_type == c_Type_TextOffsets16 )
		return std::make_unique<LogIndexAccessorFull<MapFieldAccessorTextOffsets16>>( field_descs );
	else
		return std::make_unique<LogIndexAccessorFull<MapFieldAccessorTextOffsets08>>( field_descs );
}
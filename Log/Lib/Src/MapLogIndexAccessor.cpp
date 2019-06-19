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
 * FieldAccessor
 -----------------------------------------------------------------------*/

using fieldaccessor_maker_t = FieldTraits<FieldAccessor>::field_ptr_t (*) (const FieldDescriptor & field_desc, unsigned field_id, size_t & offset);

class FieldAccessor : public FieldFactory<FieldAccessor, fieldaccessor_maker_t>
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
	FieldAccessor( FieldValueType type, size_t size, const FieldDescriptor & field_desc, unsigned field_id, size_t & offset )
		:
		c_FieldType{ type },
		c_FieldSize{ size },
		c_FieldName{ field_desc.f_Name },
		c_FieldId { field_id },
		c_FieldOffset{ offset }
	{
		offset += c_FieldSize;
	}

	// the field's class
	const FieldValueType c_FieldType;

	// the size of this field's data in the index
	const size_t c_FieldSize;

	// the field's name
	const std::string c_FieldName;

	// effectively, the index of this field within the parent index
	const unsigned c_FieldId;

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
 * FieldAccessorNull
 -----------------------------------------------------------------------*/

// use where no data is associated with a field - e.g. a text only field
struct FieldAccessorNull : public FieldAccessor
{
	FieldAccessorNull( const FieldDescriptor & field_desc, unsigned field_id, size_t & offset )
		: FieldAccessor{ FieldValueType::invalid, 0, field_desc, field_id, offset } {}
};



/*-----------------------------------------------------------------------
 * FieldAccessorScalar
 -----------------------------------------------------------------------*/

template<typename T_MAPPED_VALUE, typename T_FIELD_VALUE>
struct FieldAccessorScalar : public FieldAccessor
{
	using mapped_t = T_MAPPED_VALUE;
	using fieldtype_t = T_FIELD_VALUE;

	FieldAccessorScalar( const FieldDescriptor & field_desc, unsigned field_id, size_t & offset )
		: FieldAccessor{ TypeToFieldType<fieldtype_t>::type, sizeof( mapped_t ), field_desc, field_id, offset } {}

	fieldvalue_t GetValue( const uint8_t * line_data ) const override {
		// not sure on performance consequences for unaligned pointers here
		const fieldtype_t field_value{ * GetFieldData<mapped_t>(line_data) };
		return fieldvalue_t{ field_value };
	}
};


template<typename T_UINT>
using FieldAccessorUint = FieldAccessorScalar<T_UINT, uint64_t>;

template<typename T_INT>
using FieldAccessorInt = FieldAccessorScalar<T_INT, int64_t>;

template<typename T_FLOAT>
using FieldAccessorFloat = FieldAccessorScalar<T_FLOAT, double>;

using FieldAccessorBool = FieldAccessorUint<uint8_t>;
using FieldAccessorDate = FieldAccessorInt<int64_t>;



/*-----------------------------------------------------------------------
 * FieldAccessorEnum
 -----------------------------------------------------------------------*/

template<typename T_UINT>
class FieldAccessorEnum : public FieldAccessorUint<T_UINT>, public FieldEnumAccessor
{
private:
	using base_t = FieldAccessorUint<T_UINT>;

	const FieldHeaderEnumV1 * m_FieldHeader{ nullptr };

public:
	FieldAccessorEnum( const FieldDescriptor & field_desc, unsigned field_id, size_t & offset )
		: base_t{ field_desc, field_id, offset } {}

	// attach the accessor to a logfile; initialise m_FieldHeader
	Error AttachIndex( unsigned field_id, const IndexFileHeader * header ) override {
		const Error res{ FieldAccessor::AttachIndex( field_id, header ) };

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
 * FieldAccessorTextOffsets
 -----------------------------------------------------------------------*/

template<typename T_OFFSET, typename T_OFFSET_PAIR>
class FieldAccessorTextOffsets
	:
	public FieldAccessor,
	public FieldTextOffsetsCommon<T_OFFSET, T_OFFSET_PAIR>
{
protected:
	const offset_t * GetTextOffsetData( const uint8_t * line_data, unsigned field_id = 0 ) const {
		return GetFieldData<offset_t>(line_data) + (2 * field_id);
	}

public:
	FieldAccessorTextOffsets( const FieldDescriptor & field_desc, unsigned field_id, size_t & offset )
		: FieldAccessor{ FieldValueType::invalid, CalcOffsetFieldSize( field_id), field_desc, field_id, offset } {}

	// does the line have any fields
	bool IsRegular( const uint8_t * line_data ) const {
		return FieldTextOffsetsCommon::IsRegular( GetFieldData( line_data ) );
	}

	int64_t LastRegularLine( const uint8_t * line_data ) const {
		return GetLastRegular( GetFieldData( line_data ) );
	}

	void GetNonFieldTextOffset( const uint8_t * line_data, offset_t * first ) const {
		if( IsRegular( line_data ) )
			*first = GetTextOffsetData( line_data )[0];
		else
			*first = 0;
	}

	void GetFieldTextOffsets( const uint8_t * line_data, unsigned field_id, offset_t * first, offset_t * last ) const {
		if( IsRegular( line_data ) )
		{
			const offset_t * field_data{ GetTextOffsetData( line_data, field_id ) };
			*first = field_data[ 0 ];
			*last = field_data[ 1 ];
		}
		else
			*first = *last = 0;
	}

	template<typename T_FUNC>
	void VisitFieldOffsets( const uint8_t * line_data, uint64_t field_mask, size_t max_count, T_FUNC & func )
	{
		if( !IsRegular( line_data ) )
			return;

		// internally, the zero'th field is associated with the non-field text, so
		// bit 0 of the caller's mask is our bit 1
		field_mask = field_mask << 1;
		uint64_t field_bit{ 0x2 };

		// for each visible field
		for( unsigned field_id = 1; field_id < max_count; ++field_id )
		{
			if( field_bit & field_mask )
			{
				const offset_t * field_data{ GetTextOffsetData( line_data, field_id ) };
				func( field_id, field_data[ 0 ], field_data[ 1 ] );
			}
			field_bit = field_bit << 1;
		}
	}
};

using FieldAccessorTextOffsets08 = FieldAccessorTextOffsets<uint8_t, uint16_t>;
using FieldAccessorTextOffsets16 = FieldAccessorTextOffsets<uint16_t, uint32_t>;



/*-----------------------------------------------------------------------
 * FieldAccessor Factory
 -----------------------------------------------------------------------*/

FieldAccessor::factory_t::map_t FieldAccessor::factory_t::m_Map
{
	{ c_Type_DateTime_Unix, &MakeField<FieldAccessorDate, const FieldDescriptor &, unsigned, size_t &> },
	{ c_Type_DateTime_UsStd, &MakeField<FieldAccessorDate, const FieldDescriptor &, unsigned, size_t &> },
	{ c_Type_DateTime_TraceFmt_IntStd, &MakeField<FieldAccessorDate, const FieldDescriptor &, unsigned, size_t &> },
	{ c_Type_DateTime_TraceFmt_UsStd, &MakeField<FieldAccessorDate, const FieldDescriptor &, unsigned, size_t &> },
	{ c_Type_DateTime_TraceFmt_IntHires, &MakeField<FieldAccessorDate, const FieldDescriptor &, unsigned, size_t &> },
	{ c_Type_DateTime_TraceFmt_UsHires, &MakeField<FieldAccessorDate, const FieldDescriptor &, unsigned, size_t &> },
	{ c_Type_Bool, &MakeField<FieldAccessorBool, const FieldDescriptor &, unsigned, size_t &> },
	{ c_Type_Uint08, &MakeField<FieldAccessorUint<uint8_t>, const FieldDescriptor &, unsigned, size_t &> },
	{ c_Type_Uint16, &MakeField<FieldAccessorUint<uint16_t>, const FieldDescriptor &, unsigned, size_t &> },
	{ c_Type_Uint32, &MakeField<FieldAccessorUint<uint32_t>, const FieldDescriptor &, unsigned, size_t &> },
	{ c_Type_Uint64, &MakeField<FieldAccessorUint<uint64_t>, const FieldDescriptor &, unsigned, size_t &> },
	{ c_Type_Int08, &MakeField<FieldAccessorInt<int8_t>, const FieldDescriptor &, unsigned, size_t &> },
	{ c_Type_Int16, &MakeField<FieldAccessorInt<int16_t>, const FieldDescriptor &, unsigned, size_t &> },
	{ c_Type_Int32, &MakeField<FieldAccessorInt<int32_t>, const FieldDescriptor &, unsigned, size_t &> },
	{ c_Type_Int64, &MakeField<FieldAccessorInt<int64_t>, const FieldDescriptor &, unsigned, size_t &> },
	{ c_Type_Float32, &MakeField<FieldAccessorFloat<float>, const FieldDescriptor &, unsigned, size_t &> },
	{ c_Type_Float64, &MakeField<FieldAccessorFloat<double>, const FieldDescriptor &, unsigned, size_t &> },
	{ c_Type_Enum08, &MakeField<FieldAccessorEnum<uint8_t>, const FieldDescriptor &, unsigned, size_t &> },
	{ c_Type_Enum16, &MakeField<FieldAccessorEnum<uint16_t>, const FieldDescriptor &, unsigned, size_t &> },
	{ c_Type_Emitter, &MakeField<FieldAccessorNull, const FieldDescriptor &, unsigned, size_t &> },
	{ c_Type_Text, &MakeField<FieldAccessorNull, const FieldDescriptor &, unsigned, size_t &> },
	{ c_Type_TextOffsets08, &MakeField<FieldAccessorTextOffsets08, const FieldDescriptor &, unsigned, size_t &> },
	{ c_Type_TextOffsets16, &MakeField<FieldAccessorTextOffsets16, const FieldDescriptor &, unsigned, size_t &> }
};



/*-----------------------------------------------------------------------
 * LogIndexAccessor
 -----------------------------------------------------------------------*/

LogIndexAccessor::LogIndexAccessor( const fielddescriptor_list_t & field_descs )
{
	size_t field_offset{ 0 };

	SetupFields( field_descs, field_offset,
		[] ( const FieldDescriptor & field_desc, unsigned field_id, size_t & offset ) -> field_ptr_t {
			// the template arguments are needed to ensure offset is passed by reference
			return field_t::CreateField<unsigned, size_t &>( field_desc, field_id, offset );
		}
	);

	m_LineDataSize = field_offset;
}


FieldValueType LogIndexAccessor::GetFieldType( unsigned field_id ) const
{
	return m_Fields[ field_id ]->GetType();
}


fieldvalue_t LogIndexAccessor::GetFieldValue( nlineno_t line_no, unsigned field_id ) const
{
	return m_Fields[ field_id ]->GetValue( GetLineData( line_no ) );
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

	if( hdr->f_NumFields != m_Fields.size() )
		return TraceError( e_WrongIndex, "Index does not match given specification" );

	Error res{ e_OK };
	for(unsigned field_id = 0; field_id < m_Fields.size(); ++field_id )
		UpdateError( res, m_Fields[ field_id ]->AttachIndex( field_id, hdr ) );

	m_LineData = reinterpret_cast<const uint8_t*>( m_Map.GetData() + hdr->f_LineDataOffset );
	m_NumLines = nlineno_cast(hdr->f_NumLines);

	const unsigned field_id{ static_cast<unsigned>(hdr->f_TimecodeFieldId) };
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
	const FieldEnumAccessor * enum_accessor{ m_Fields[ field_id ]->GetEnumAccessor() };
	return enum_accessor ? enum_accessor->GetCount() : 0;
}


const char * LogIndexAccessor::GetFieldEnumName( unsigned field_id, uint16_t enum_id ) const
{
	const FieldEnumAccessor * enum_accessor{ m_Fields[ field_id ]->GetEnumAccessor() };
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
		: LogIndexAccessor{ field_descs }
	{
		// the last field must be the TextOffsets
		m_FieldTextOffsets = dynamic_cast<T_FIELD_TEXTOFFSETS*>(m_Fields.back().get());
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

	m_FieldTextOffsets->VisitFieldOffsets( GetLineData( line_no ), field_mask, GetNumFields() - 1,
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

	m_FieldTextOffsets->VisitFieldOffsets( GetLineData( line_no ), field_mask, GetNumFields() - 1,
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
	m_FieldTextOffsets->VisitFieldOffsets( GetLineData( line_no ), field_mask, GetNumFields() - 1,
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
		return std::make_unique<LogIndexAccessorFull<FieldAccessorTextOffsets16>>( field_descs );
	else
		return std::make_unique<LogIndexAccessorFull<FieldAccessorTextOffsets08>>( field_descs );
}
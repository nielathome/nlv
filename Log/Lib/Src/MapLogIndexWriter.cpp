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

// C++ includes
#include <fstream>
#include <map>
#include <set>
#include <sstream>



/*-----------------------------------------------------------------------
 * OStream
 -----------------------------------------------------------------------*/

// helper to simplify working with file streams
struct OStream : public std::ofstream
{
	template<typename T_VALUE>
	OStream & write_value( const T_VALUE &value ) {
		write( reinterpret_cast<const char*>(&value), sizeof( value ) );
		return *this;
	}
};



/*-----------------------------------------------------------------------
 * StringTable
 -----------------------------------------------------------------------*/

class StringTable
{
private:
	size_t m_nextStringId{ 0 };
	std::vector<std::string> m_Strings;

public:
	size_t AddString( const std::string & string ) {
		size_t cur_string_id{ m_nextStringId };
		m_nextStringId += string.size() + 1;
		m_Strings.push_back( string );
		return cur_string_id;
	}

	void WriteValue( OStream & os ) {
		for( const std::string & string : m_Strings )
			os.write( string.c_str(), string.size() + 1 );
	}
};



/*-----------------------------------------------------------------------
 * WriteContext
 -----------------------------------------------------------------------*/

struct WriteContext
{
	// limit the number of errors we're prepared to report
	const int64_t c_MaxReports{ 25 };
	std::atomic<int64_t> m_ReportCount{ c_MaxReports };

	bool Report( void ) {
		const int64_t count{ --m_ReportCount };
		if( count == 0 )
			TraceError( e_ReportLimit, "... limit reached, no more indexer errors will be reported" );

		return count > 0;
	}

	StringTable & f_StringTable;
	IndexFileHeader & f_Header;
	OStream & f_Stream;
	int64_t f_LineNo{ 0 };
	int64_t f_LastParsedLine{ -1 };

	WriteContext( StringTable & string_table, IndexFileHeader & header, OStream & stream )
		: f_StringTable{ string_table }, f_Header{ header }, f_Stream{ stream } {}
};


// custom integration with info/error tracing - to permit limiting number of messages
#define TraceInfoCxt( CXT, FMT, ... ) \
	( \
		(CXT).Report() ? \
			(TraceInfoN( __FUNCTION__, FMT, ##__VA_ARGS__ ), e_FieldInterpretation) \
			: e_FieldInterpretation \
	)


#define TraceErrorCxt( CXT, ERR, FMT, ... ) \
	( \
		(CXT).Report() ? \
			TraceErrorN( ERR, __FUNCTION__, FMT, ##__VA_ARGS__ ) \
			: (ERR) \
	)



/*-----------------------------------------------------------------------
 * FieldWriter
 -----------------------------------------------------------------------*/

using fieldwriter_maker_t = FieldTraits<FieldWriter>::field_ptr_t (*)(const FieldDescriptor &, unsigned);

class FieldWriter : public FieldFactory<FieldWriter, fieldwriter_maker_t>
{
public:
	FieldWriter( const FieldDescriptor & field_desc, unsigned field_id )
		:
		c_Separator{ field_desc.f_Separator },
		c_MinWidth{ field_desc.f_MinWidth },
		c_SeparatorCount{ field_desc.f_SeparatorCount },
		c_FieldId{ field_id }
	{}

	// identification pattern; used to find the field's raw text in a log line
	const std::string c_Separator;
	const unsigned c_SeparatorCount;
	const unsigned c_MinWidth;

	// fields index within the set of all fields
	const unsigned c_FieldId;

	// convert and save the field's binary value; return false if conversion fails
	virtual Error WriteValue( WriteContext & cxt, const char *begin, const char *end ) {
		return Write( cxt );
	}

	// save a null value; used when we can't fully interpret a log line
	virtual Error Write( WriteContext & cxt, uint64_t hint = 0 ) = 0;

	virtual Error WriteFieldHeader( WriteContext & cxt ) {
		FieldHeaderV1 header{ sizeof( FieldHeaderV1 ), 0 };
		cxt.f_Stream.write_value( header );
		return e_OK;
	}
};



/*-----------------------------------------------------------------------
 * FieldWriterNull
 -----------------------------------------------------------------------*/

 // use where no data is associated with a field - e.g. a text only field
class FieldWriterNull : public FieldWriter
{
public:
	FieldWriterNull( const FieldDescriptor & field_desc, unsigned field_id )
		: FieldWriter{ field_desc, field_id } {}

	Error WriteValue( WriteContext & cxt, const char * first, const char * last ) override
	{
		// nothing needed here
		return e_OK;
	}

	Error Write( WriteContext & cxt, uint64_t hint = 0 ) override
	{
		// nothing needed here
		return e_OK;
	}
};



/*-----------------------------------------------------------------------
 * FieldWriterScalar
 -----------------------------------------------------------------------*/

struct IntegerCompare
{
	template<typename T, typename U>
	static bool Equal( T t, U u ) {
		return t == u;
	}
};

// From "The art of computer programming by Knuth" via
// https ://stackoverflow.com/questions/17333/what-is-the-most-effective-way-for-float-and-double-comparison
struct FloatCompare
{
	static bool Equal( double t, double u ) {
		const double max{ std::max( std::fabs( t ), std::fabs( u ) ) };
		const double epsilon{ max * std::numeric_limits<float>::epsilon() };
		return std::fabs( t - u ) <= epsilon;
	}
};


struct FieldConvertBool
{
	using value_t = uint64_t;
	using compare_t = IntegerCompare;

	static void GetEnd( const char * match, const char *begin, char **next )
	{
		int offset{ 0 };
		while( *match != '\0' )
		{
			const char m{ *(match++) };
			const char ch{ *(begin++) };
			if( m != ch && m != ::toupper( ch ) )
			{
				offset = -1;
				break;
			}
		}

		*next = const_cast<char*>(begin + offset);
	}

	static value_t Convert( const char *begin, char **next )
	{
		const char ch{ *begin };
		if( ch == '0' || ch == '1')
		{
			*next = const_cast<char*>(++begin);
			return ch - '0';
		}
		else if( ch == 't' || ch == 'T' )
		{
			GetEnd( "rue", ++begin, next );
			return 1;
		}
		else if( ch == 'f' || ch == 'F' )
		{
			GetEnd( "alse", ++begin, next );
			return 0;
		}
		else
		{
			*next = const_cast<char*>(begin);
			return 0;
		}
	}
};

struct FieldConvertUnsigned
{
	using value_t = uint64_t;
	using compare_t = IntegerCompare;

	static value_t Convert( const char *begin, char **next ) {
		return strtoull( begin, next, 0 );
	}
};

struct FieldConvertSigned
{
	using value_t = int64_t;
	using compare_t = IntegerCompare;

	static value_t Convert( const char *begin, char **next ) {
		return strtoll( begin, next, 0 );
	}
};

struct FieldConvertFloat
{
	using value_t = double;
	using compare_t = FloatCompare;

	static value_t Convert( const char *begin, char **next ) {
		return strtod( begin, next );
	}
};

template<typename T_SCALAR, typename T_CONVERTER>
class FieldWriterScalar : public FieldWriter
{
public:
	using scalar_t = T_SCALAR;
	using converter_t = T_CONVERTER;

	FieldWriterScalar( const FieldDescriptor & field_desc, unsigned field_id )
		: FieldWriter{ field_desc, field_id } {}

	Error WriteValue( WriteContext & cxt, const char *begin, const char *end ) override
	{
		using value_t = typename converter_t::value_t;
		using compare_t = typename converter_t::compare_t;

		char *next{ nullptr };
		const value_t number{ converter_t::Convert( begin, &next ) };

		if( (begin == next) || (next != end) )
			return TraceInfoCxt( cxt, "line:%lld converting:'%s'", cxt.f_LineNo, std::string{ begin, end }.c_str() );

		const scalar_t value{ static_cast<scalar_t>(number) };
		if( ! compare_t::Equal( value, number ) )
			return TraceInfoCxt( cxt, "line:%lld out-of-range:'%s'", cxt.f_LineNo, std::string{ begin, end }.c_str() );

		cxt.f_Stream.write_value( value );
		return e_OK;
	}

	Error Write( WriteContext & cxt, uint64_t hint = 0 ) override {
		scalar_t value{ static_cast<scalar_t>(hint) };
		cxt.f_Stream.write_value( value );
		return e_OK;
	}
};

using FieldWriterBool = FieldWriterScalar<uint8_t, FieldConvertBool>;

template<typename T_UINT>
using FieldWriterUint = FieldWriterScalar<T_UINT, FieldConvertUnsigned>;

template<typename T_INT>
using FieldWriterInt = FieldWriterScalar<T_INT, FieldConvertSigned>;

template<typename T_FLOAT>
using FieldWriterFloat = FieldWriterScalar<T_FLOAT, FieldConvertFloat>;



/*-----------------------------------------------------------------------
 * FieldWriterEnum
 -----------------------------------------------------------------------*/

template<typename T_UINT>
class FieldWriterEnum : public FieldWriterUint<T_UINT>
{
private:
	using base_t = FieldWriterUint<T_UINT>;
	using uint_t = scalar_t;

	// individual items in the enumeration have an id and a textual value
	struct Item
	{
		const uint_t f_EnumId;
		const std::string f_Value;

		Item( uint_t enum_id, const std::string &value )
			: f_EnumId{ enum_id }, f_Value{ value } {}
	};

	// items are referenced from a set
	struct Compare
	{
		bool operator () ( const Item & lhs, const Item & rhs ) {
			return lhs.f_Value < rhs.f_Value;
		}
	};
	using item_set_t = std::set<Item, Compare>;
	item_set_t m_EnumValues;

	// items are also referenced from a vector (in id order)
	// the size of this vector does not exceed the addressing range of uint_t
	using item_vector_t = std::vector<typename item_set_t::iterator>;
	item_vector_t m_EnumIds;

protected:
	// add a potentially new enumeration item; return ID
	Error AddEnum( WriteContext & cxt, const std::string & enum_text, uint_t * enum_id ) {
		const size_t size{ m_EnumIds.size() };
		const bool full{ size >= std::numeric_limits<uint_t>::max() };
		const uint_t next_id{ full ? uint_t{ 0 } : static_cast<uint_t>(size) };

		// note - the m_EnumValues set can have more entries than the m_EnumIds vector
		const Item item{ next_id, enum_text };
		std::pair<item_set_t::iterator, bool> ins{ m_EnumValues.insert( item ) };

		Error res{ e_OK };
		if( ins.second )
		{
			// new
			*enum_id = next_id;
			if( full )
				res = TraceErrorCxt( cxt, e_EnumOverflow, "line:%lld enum_value:'%s'", cxt.f_LineNo, enum_text.c_str() );
			else
				m_EnumIds.push_back( ins.first );
		}
		else
			// existing
			*enum_id = ins.first->f_EnumId;
		return res;
	}

public:
	FieldWriterEnum( const FieldDescriptor & field_desc, unsigned field_id )
		: base_t{ field_desc, field_id }
	{
		// an enum_id of 0 is regarded as bad
		Item item( 0, "!INVALID!" );
		m_EnumIds.push_back( m_EnumValues.insert( item ).first );
	}
	
	Error WriteValue( WriteContext & cxt, const char *begin, const char *end ) override {
		const std::string enum_text{ begin, end };
		uint_t enum_id{ 0 };
		const Error res{ AddEnum( cxt, enum_text, &enum_id ) };
		if( Ok( res ) )
			cxt.f_Stream.write_value( enum_id );
		return res;
	}

	Error WriteFieldHeader( WriteContext & cxt ) override {
		const uint_t num_ids{ static_cast<uint_t>( m_EnumIds.size() ) };
		FieldHeaderEnumV1 header{ num_ids };
		cxt.f_Stream.write_value( header );

		for( size_t i = 0; i < num_ids; ++i )
			cxt.f_Stream.write_value( cxt.f_StringTable.AddString( m_EnumIds[ i ]->f_Value ) );

		return e_OK;
	}
};



/*-----------------------------------------------------------------------
 * FieldWriterDateTime
 -----------------------------------------------------------------------*/

// base class for highly customised date/time converters
class FieldWriterDateTime : public FieldWriterInt<int64_t>
{
private:
	using base_t = FieldWriterInt<int64_t>;

	const char *m_Current{ nullptr };
	bool m_Error{ false };

protected:
	FieldWriterDateTime( const FieldDescriptor & field_desc, unsigned field_id )
		: base_t{ field_desc, field_id } {}

	// the first date time field discovered will be treated as "the" data time field
	Error WriteFieldHeader( WriteContext & cxt ) override {
		if( cxt.f_Header.f_TimecodeFieldId < 0 )
			cxt.f_Header.f_TimecodeFieldId = c_FieldId;

		return base_t::WriteFieldHeader( cxt );
	}

protected:
	// services for derived classes

	const int c_GmtimeYearOffset{ 1900 };

	tm InitState( const char * first ) {
		m_Current = first;
		m_Error = false;

		tm tm;
		tm.tm_wday = 0;
		tm.tm_yday = 0;
		tm.tm_isdst = 0;
		return tm;
	}

	char GetChar( void ) {
		return *(m_Current++);
	}

	char PeekChar( void ) {
		return *m_Current;
	}

	// convert next (numeric) character to an integer
	uint8_t CharToNumber( void ) {
		const uint8_t result{ static_cast<uint8_t>(GetChar() - '0') };

		if( result > 9 )
			m_Error = true;

		return result;
	}

	// convert next (numeric or space) character to an integer
	uint8_t CharOrSpaceToNumber( void ) {
		const char ch{ GetChar() };
		if( ch == ' ' )
			return 0;

		const uint8_t result{ static_cast<uint8_t>(ch - '0') };
		if( result > 9 )
			m_Error = true;

		return result;
	}

	int AmPmToCharsToNumber( int hour ) {
		const bool pm{ GetChar() == 'P' };
		const bool am{ !pm };
		ExpectChar( 'M' );

		if( am && (hour == 12) )
			hour -= 12;
		else if( pm && (hour != 12) )
			hour += 12;

		return hour;
	}

	// convert next c_NumChar characters to an integer, allowing the first character
	// to be a space
	template<unsigned c_NumChar, typename T_RESULT = int>
	T_RESULT CountedCharsToNumber( void ) {
		static_assert(c_NumChar >= 2, "Character count too small");
		using int_t = T_RESULT;

		int_t res{ CharOrSpaceToNumber() };

		for( unsigned i = 0; i < (c_NumChar - 1); ++i )
			res = (10 * res) + CharToNumber();

		return res;
	}

	// convert terminated character sequence (one or two characters) to a number
	template<char c_Terminator, typename T_RESULT = int>
	T_RESULT TerminatedCharsToNumber( void ) {
		using int_t = T_RESULT;

		int_t res{ CharToNumber() };
		if( PeekChar() != c_Terminator)
			res = (10 * res) + CharToNumber();

		return res;
	}

	void ExpectChar( char exp ) {
		const char ch{ GetChar() };
		if( ch != exp )
			m_Error = true;
	}

	// convert the next 3 characters to a month number, assuming the characters
	// are a standard month abbreviation in English
	int GetMonthAbbr( void )
	{
		int month{ 0 };

		const char ch0{ GetChar() };
		const char ch1{ GetChar() };
		const char ch2{ GetChar() };

		switch( ch0 )
		{
		case 'J': case 'j':
			// Jan, Jun, Jul
			if( ch1 == 'a' )
				month = 1;
			else if( ch2 == 'n' )
				month = 6;
			else if( ch2 == 'l' )
				month = 7;
			break;

		case 'F': case 'f':
			month = 2;
			break;

		case 'M': case 'm':
			// Mar, May
			if( ch2 == 'r' )
				month = 3;
			else if( ch2 == 'y' )
				month = 5;
			break;

		case 'A': case 'a':
			// Apr, Aug
			if( ch2 == 'r' )
				month = 4;
			else if( ch2 == 'g' )
				month = 8;
			break;

		case 'S': case 's':
			month = 9;
			break;

		case 'O': case 'o':
			month = 10;
			break;

		case 'N': case 'n':
			month = 11;
			break;

		case 'D': case 'd':
			month = 12;
			break;
		}

		if( month < 1 )
			m_Error = true;
		return month;
	}

	Error WriteDateTime( WriteContext & cxt, const char * first, const char * last, tm & tm, uint32_t ns = 0 )
	{
		const time_t utc{ _mkgmtime( &tm ) };
		if( m_Error || (utc == -1) || (m_Current != last) )
			return TraceInfoCxt( cxt, "Date missing: line:%lld text:'%s'", cxt.f_LineNo, std::string{ first, last }.c_str() );

		// check and write out fractional second part
		if( ns >= NTimecode::c_NanoSecond )
			return TraceInfoCxt( cxt, "Date missing: line:%lld fraction:%u", cxt.f_LineNo, ns );

		if( cxt.f_Header.f_UtcDatum == 0 )
			cxt.f_Header.f_UtcDatum = utc;

		const NTimecode timecode{ utc, ns };
		const int64_t log_time{ timecode.CalcOffsetToDatum( cxt.f_Header.f_UtcDatum ) };
		cxt.f_Stream.write_value( log_time );
		return e_OK;
	}
};


class FieldWriterDateTimeUnix : public FieldWriterDateTime
{
private:
	//
	// examples:
	//  Mar 31 23:58:15
	//  Apr  1 00:00:05
	//
	Error WriteValue( WriteContext & cxt, const char * first, const char * last ) override
	{
		tm tm{ InitState( first ) };

		tm.tm_mon = GetMonthAbbr() - 1; ExpectChar( ' ' );
		tm.tm_mday = CountedCharsToNumber<2>(); ExpectChar( ' ' );
		tm.tm_hour = CountedCharsToNumber<2>(); ExpectChar( ':' );
		tm.tm_min = CountedCharsToNumber<2>(); ExpectChar( ':' );
		tm.tm_sec = CountedCharsToNumber<2>();
		tm.tm_year = 2017 - c_GmtimeYearOffset; // TODO !

		return WriteDateTime( cxt, first, last, tm );
	}

public:
	FieldWriterDateTimeUnix( const FieldDescriptor & field_desc, unsigned field_id )
		: FieldWriterDateTime{ field_desc, field_id } {}
};


class FieldWriterDateTimeUsStd : public FieldWriterDateTime
{
private:
	//
	// examples
	//  12/9/2016 11:42:03[.234] PM
	//
	// where:
	//  month, day of month and hour consist of 1 or 2 characters
	//  millisecond time value is optional; 3 digits where present
	//
	Error WriteValue( WriteContext & cxt, const char * first, const char * last ) override
	{
		tm tm{ InitState( first ) };

		constexpr char date_sep{ '/' };
		tm.tm_mon = TerminatedCharsToNumber<date_sep>() - 1; ExpectChar( date_sep );
		tm.tm_mday = TerminatedCharsToNumber<date_sep>(); ExpectChar( date_sep );
		tm.tm_year = CountedCharsToNumber<4>() - c_GmtimeYearOffset; ExpectChar( ' ' );

		constexpr char time_sep{ ':' };
		tm.tm_hour = TerminatedCharsToNumber<time_sep>(); ExpectChar( time_sep );
		tm.tm_min = CountedCharsToNumber<2>(); ExpectChar( time_sep );
		tm.tm_sec = CountedCharsToNumber<2>();

		constexpr char ns_sep{ '.' };
		uint32_t ns{ 0 };
		if( PeekChar() == ns_sep )
		{
			ExpectChar( ns_sep );

			const uint32_t ms{ CountedCharsToNumber<3, uint32_t>() };
			ns = (1000000 * ms);
		}
		ExpectChar( ' ' );

		tm.tm_hour = AmPmToCharsToNumber( tm.tm_hour );

		return WriteDateTime( cxt, first, last, tm, ns );
	}

public:
	FieldWriterDateTimeUsStd( const FieldDescriptor & field_desc, unsigned field_id )
		: FieldWriterDateTime{ field_desc, field_id } {}
};


template<bool c_International, bool c_Hires>
class FieldWriterDateTimeTraceFmt : public FieldWriterDateTime
{
private:
	//
	// examples (international):
	//  standard - "12/06/2017-18:03:17.839"
	//  hires - "12/06/2017-18:03:17.839.222100"
	//
	Error WriteValue( WriteContext & cxt, const char * first, const char * last ) override
	{
		tm tm{ InitState( first ) };

		(c_International ? tm.tm_mday : tm.tm_mon) = CountedCharsToNumber<2>(); ExpectChar( '/' );
		(c_International ? tm.tm_mon : tm.tm_mday) = CountedCharsToNumber<2>(); ExpectChar( '/' );
		tm.tm_year = CountedCharsToNumber<4>() - c_GmtimeYearOffset; ExpectChar( '-' );
		tm.tm_hour = CountedCharsToNumber<2>(); ExpectChar( ':' );
		tm.tm_min = CountedCharsToNumber<2>(); ExpectChar( ':' );
		tm.tm_sec = CountedCharsToNumber<2>(); ExpectChar( '.' );
		tm.tm_mon -= 1;

		const uint32_t ms{ CountedCharsToNumber<3, uint32_t>() };
		uint32_t us{ 0 };

		if( c_Hires )
		{
			ExpectChar( '.' );
			us = CountedCharsToNumber<6, uint32_t>();
		}
		const uint32_t ns{ (1000000 * ms) + us };

		return WriteDateTime( cxt, first, last, tm, ns );
	}

public:
	FieldWriterDateTimeTraceFmt( const FieldDescriptor & field_desc, unsigned field_id )
		: FieldWriterDateTime{ field_desc, field_id } {}
};

using FieldWriterDateTimeTraceFmtIntStd = FieldWriterDateTimeTraceFmt<true, false>;
using FieldWriterDateTimeTraceFmtIntHires = FieldWriterDateTimeTraceFmt<true, true>;
using FieldWriterDateTimeTraceFmtUsStd = FieldWriterDateTimeTraceFmt<false, false>;
using FieldWriterDateTimeTraceFmtUsHires = FieldWriterDateTimeTraceFmt<false, true>;



/*-----------------------------------------------------------------------
 * FieldWriterTextOffsetsBase
 -----------------------------------------------------------------------*/

class FieldWriterTextOffsetsBase : public FieldWriter
{
protected:
	FieldWriterTextOffsetsBase( const FieldDescriptor & field_desc, unsigned field_id )
		: FieldWriter{ field_desc, field_id } {}

public:
	virtual void Setup( size_t num_fields ) = 0;
	virtual void Clear( int64_t last_parsed_line ) = 0;
	virtual void SetFieldOffsets( WriteContext & cxt, size_t field_id, size_t lower, size_t upper ) = 0;
	virtual void SetNonFieldOffset( WriteContext & cxt, size_t offset ) = 0;
};



/*-----------------------------------------------------------------------
 * FieldWriterTextOffsets
 -----------------------------------------------------------------------*/

template<typename T_OFFSET, typename T_OFFSET_PAIR>
class FieldWriterTextOffsets
	:
	public FieldWriterTextOffsetsBase,
	public FieldTextOffsetsCommon<T_OFFSET, T_OFFSET_PAIR>
{
private:
	// buffer for line offsets
	std::vector<offset_t> m_RawFieldDataStore;
	RawFieldData * m_RawFieldData{ nullptr };

	// line match results for next write
	Error m_Res{ e_OK };

protected:
	offset_t MakeOffset( WriteContext & cxt, size_t offset )
	{
		offset_t res{ 0 };

		if( offset > std::numeric_limits<offset_t>::max() )
			UpdateError( m_Res, TraceErrorCxt( cxt, e_LineOffsetRange, "line:%lld offset:%llu offset_size:%llu", cxt.f_LineNo, offset, c_OffsetSize ) );
		else
			res = static_cast<offset_t>(offset);
		
		return res;
	}

public:
	FieldWriterTextOffsets( const FieldDescriptor & field_desc, unsigned field_id )
		: FieldWriterTextOffsetsBase{ field_desc, field_id } {}

	void Setup( size_t num_fields ) override {
		m_RawFieldDataStore.resize( CalcOffsetFieldSize( num_fields ) / sizeof( offset_t ) );
		m_RawFieldData = reinterpret_cast<RawFieldData*>(m_RawFieldDataStore.data());
	}

	void Clear( int64_t last_parsed_line ) override {
		std::fill( m_RawFieldDataStore.begin(), m_RawFieldDataStore.end(), 0 );
		m_RawFieldData->u_Irregular.s_LastRegular = last_parsed_line;
	}

	void SetNonFieldOffset( WriteContext & cxt, size_t offset ) override {
		m_RawFieldData->u_Regular.s_NonFieldTextOffset = MakeOffset( cxt, offset );
	}

	void SetFieldOffsets( WriteContext & cxt, size_t field_id, size_t lower, size_t upper ) override {
		const size_t idx{ 2 * field_id };
		offset_t * offsets{ m_RawFieldData->u_Regular.s_FieldTextOffsets };
		offsets[ idx + 0 ] = MakeOffset( cxt, lower );
		offsets[ idx + 1 ] = MakeOffset( cxt, upper );
	}

	Error Write( WriteContext & cxt, uint64_t = 0 ) override {
		cxt.f_Stream.write( reinterpret_cast<char*>(m_RawFieldData), m_RawFieldDataStore.size() * c_OffsetSize );
		const Error ret{ m_Res };
		m_Res = e_OK;
		return ret;
	}
};



/*-----------------------------------------------------------------------
 * FieldWriter Factory
 -----------------------------------------------------------------------*/

FieldWriter::factory_t::map_t FieldWriter::factory_t::m_Map
{
	{ c_Type_DateTime_Unix, &MakeField<FieldWriterDateTimeUnix, const FieldDescriptor &, unsigned> },
	{ c_Type_DateTime_UsStd, &MakeField<FieldWriterDateTimeUsStd, const FieldDescriptor &, unsigned> },
	{ c_Type_DateTime_TraceFmt_IntStd, &MakeField<FieldWriterDateTimeTraceFmtIntStd, const FieldDescriptor &, unsigned> },
	{ c_Type_DateTime_TraceFmt_UsStd, &MakeField<FieldWriterDateTimeTraceFmtUsStd, const FieldDescriptor &, unsigned> },
	{ c_Type_DateTime_TraceFmt_IntHires, &MakeField<FieldWriterDateTimeTraceFmtIntHires, const FieldDescriptor &, unsigned> },
	{ c_Type_DateTime_TraceFmt_UsHires, &MakeField<FieldWriterDateTimeTraceFmtUsHires, const FieldDescriptor &, unsigned> },
	{ c_Type_Bool, &MakeField<FieldWriterBool, const FieldDescriptor &, unsigned> },
	{ c_Type_Uint08, &MakeField<FieldWriterUint<uint8_t>, const FieldDescriptor &, unsigned> },
	{ c_Type_Uint16, &MakeField<FieldWriterUint<uint16_t>, const FieldDescriptor &, unsigned> },
	{ c_Type_Uint32, &MakeField<FieldWriterUint<uint32_t>, const FieldDescriptor &, unsigned> },
	{ c_Type_Uint64, &MakeField<FieldWriterUint<uint64_t>, const FieldDescriptor &, unsigned> },
	{ c_Type_Int08, &MakeField<FieldWriterInt<int8_t>, const FieldDescriptor &, unsigned> },
	{ c_Type_Int16, &MakeField<FieldWriterInt<int16_t>, const FieldDescriptor &, unsigned> },
	{ c_Type_Int32, &MakeField<FieldWriterInt<int32_t>, const FieldDescriptor &, unsigned> },
	{ c_Type_Int64, &MakeField<FieldWriterInt<int64_t>, const FieldDescriptor &, unsigned> },
	{ c_Type_Float32, &MakeField<FieldWriterFloat<float>, const FieldDescriptor &, unsigned> },
	{ c_Type_Float64, &MakeField<FieldWriterFloat<double>, const FieldDescriptor &, unsigned> },
	{ c_Type_Enum08, &MakeField<FieldWriterEnum<uint8_t>, const FieldDescriptor &, unsigned> },
	{ c_Type_Enum16, &MakeField<FieldWriterEnum<uint16_t>, const FieldDescriptor &, unsigned> },
	{ c_Type_Emitter, &MakeField<FieldWriterNull, const FieldDescriptor &, unsigned> },
	{ c_Type_Text, &MakeField<FieldWriterNull, const FieldDescriptor &, unsigned> },
	{ c_Type_TextOffsets08, &MakeField<FieldWriterTextOffsets<uint8_t, uint16_t>, const FieldDescriptor &, unsigned> },
	{ c_Type_TextOffsets16, &MakeField<FieldWriterTextOffsets<uint16_t, uint32_t>, const FieldDescriptor &, unsigned> }
};



/*-----------------------------------------------------------------------
 * LogIndexWriter
 -----------------------------------------------------------------------*/

using field_location_t = std::tuple<bool, const char *, const char *>;

LogIndexWriter::LogIndexWriter( const FileMap & fmap, const fielddescriptor_list_t & field_descs, const std::string & text_offsets_field_type, const std::string & match_desc )
	: m_Log{ fmap }, m_UseRegex{ !match_desc.empty() }
{
	if( m_UseRegex )
	{
		std::regex_constants::syntax_option_type flags{
			std::regex_constants::ECMAScript
			| std::regex_constants::optimize
		};
		m_Regex = std::regex{ match_desc, flags };
	}

	AddInternalField( CreateField( FieldDescriptor{ false, "", "uint64" } ) );
	SetupUserFields( field_descs );
	AddInternalField( CreateField( FieldDescriptor{ false, "", text_offsets_field_type } ) );
	m_FieldTextOffsets = dynamic_cast<FieldWriterTextOffsetsBase*>(m_AllFields.back().get());
}


template<typename T_FIELDGET>
Error LogIndexWriter::WriteLine( WriteContext & cxt, size_t offset, const char *begin, const char *end, T_FIELDGET & field_get )
{
	// local error function
	auto report_error = [&cxt, begin, end] ( const char * msg ) {
		std::string text{ begin, end };

		size_t ichar;
		while( (ichar = text.find_first_of( "\n\r" )) != std::string::npos )
			text.erase( ichar );

		if( !text.empty() )
			(void) TraceInfoCxt( cxt, "%s: line:%lld converting:'%s'", msg, cxt.f_LineNo, text.c_str() );
	};

	// first field is the line's absolute location
	Error res{ e_OK };
	UpdateError( res, m_AllFields[ 0 ]->Write( cxt, offset ) );

	// output user visible fields
	bool line_ok{ true };
	const size_t num_user_field{ m_UserFields.size() };
	for( size_t i = 0; i < num_user_field; ++i )
	{
		field_location_t field;
		if( line_ok )
		{
			field = field_get.At( i );
			line_ok = std::get<0>(field);

			if( !line_ok )
				report_error( "Field missing" );
		}

		if( line_ok )
		{
			const char * field_begin{ std::get<1>( field ) }, *field_end{ std::get<2>( field ) };
			m_FieldTextOffsets->SetFieldOffsets( cxt, i, field_begin - begin, field_end - begin );
			const Error write_err{ m_UserFields[ i ]->WriteValue( cxt, field_begin, field_end ) };
			line_ok = Ok( write_err );

			// only record errors that leave the index file corrupt/unusable
			if( write_err != e_FieldInterpretation )
				UpdateError( res, write_err );
		}

		if( !line_ok )
			UpdateError( res, m_UserFields[ i ]->Write( cxt ) );
	}

	// last field is always the text_offsets field
	if( line_ok )
	{
		m_FieldTextOffsets->SetNonFieldOffset( cxt, field_get.Remainder() - begin );
		cxt.f_LastParsedLine = cxt.f_LineNo;
	}
	else
		m_FieldTextOffsets->Clear( cxt.f_LastParsedLine );

	UpdateError( res, m_FieldTextOffsets->Write( cxt ) );

	// report any match issues now; suppress where line has zero length -
	// as that is a valid call
	const bool unreported_error{ !Ok( res ) && line_ok };
	if( unreported_error && (begin != end) )
		report_error( "Unable to index line" );

	return res;
}


// identify the fields in a line using the field separator information
Error LogIndexWriter::WriteLineSeparated( WriteContext & cxt, size_t offset, const char *begin, const char *end )
{
	struct FieldGet
	{
		const field_array_t & f_Fields;
		const char * f_FieldBegin, *f_LineEnd;

		FieldGet( field_array_t & fields, const char * line_begin, const char * line_end )
			: f_Fields{ fields }, f_FieldBegin{ line_begin }, f_LineEnd{ line_end } {}

		field_location_t Fail( void ) {
			return field_location_t{ false, nullptr, nullptr };
		}

		field_location_t At( size_t field_id ) {
			const FieldWriter & info{ * f_Fields[ field_id ] };
			const std::string & separator{ info.c_Separator };
			const unsigned separator_count{ info.c_SeparatorCount };
			const unsigned min_width{ info.c_MinWidth };

			// step over the defined minimum width
			const char *field_end{ f_FieldBegin + min_width };
			if( field_end >= f_LineEnd )
				return Fail();

			// locate the separator in the remainder of the line
			for( unsigned i = 0; i < separator_count; ++i )
			{
				if( i != 0 )
					field_end += separator.size();

				field_end = std::search( field_end, f_LineEnd, separator.begin(), separator.end() );
				if( field_end == f_LineEnd )
					return Fail();
			}

			if( (field_end + separator.size()) >= f_LineEnd )
				return Fail();

			field_location_t field{ true, f_FieldBegin, field_end };
			f_FieldBegin = field_end + separator.size();

			return field;
		}

		const char * Remainder( void ) const {
			return f_FieldBegin;
		}
	};

	FieldGet field_get{ m_UserFields, begin, end };
	return WriteLine( cxt, offset, begin, end, field_get );
}


// identify the fields in a line using a regular expression
Error LogIndexWriter::WriteLineRegex( WriteContext & cxt, size_t offset, const char *begin, const char *end )
{
	struct FieldGet
	{
		std::cmatch f_MatchResults;
		bool f_Matched{ true };

		FieldGet( std::regex *re, const char * line_begin, const char * line_end, size_t num_field )
		{
			const bool searched{ std::regex_search( line_begin, line_end, f_MatchResults, *re ) };
			f_Matched = searched && f_MatchResults.ready() && (f_MatchResults.size() == num_field);
		}

		field_location_t At( size_t field_id ) const {
			if( f_Matched )
			{
				const auto & match{ f_MatchResults[ field_id ] };
				return field_location_t{ true, match.first, match.second };
			}
			else
				return field_location_t{ false, nullptr, nullptr };
		}

		const char * Remainder( void ) const {
			if( f_Matched )
				return f_MatchResults[ 0 ].second;
			else
				return nullptr;
		}
	};

	const size_t num_field{ m_UserFields.size() };
	FieldGet field_get{ &m_Regex, begin, end, num_field };
	return WriteLine( cxt, offset, begin, end, field_get );
}


Error LogIndexWriter::WriteLines( WriteContext & cxt, nlineno_t * pnum_lines, ProgressMeter * progress )
{
	const nlineno_t num_char{ nlineno_cast( m_Log.GetSize() ) };
	const nlineno_t num_char_minus_one{ num_char - 1 };

	// progress notifications
	struct NotifyProgress
	{
		const nlineno_t c_ProgressSize{ 1024 * 1024 };
		nlineno_t f_NextProgress{ c_ProgressSize };
		ProgressMeter * f_Progress;

		NotifyProgress( ProgressMeter * progress, nlineno_t range )
			: f_Progress{ progress } {}

		void Pulse( nlineno_t value )
		{
			if( value > f_NextProgress )
			{
				std::ostringstream strm;
				strm << "Creating index: " << (value / c_ProgressSize);
				f_Progress->Pulse( strm.str() );
				f_NextProgress += c_ProgressSize;
			}
		}

	} notifier{ progress, num_char };

	// discover and write out line index data
	const char *text{ m_Log.GetData() };
	nlineno_t start{ 0 };
	Error res{ e_OK };
	m_FieldTextOffsets->Setup( GetNumUserFields() );

	// silently strip any UTF-8 BOM
	if( (num_char >= 3) && (text[ 0 ] == char(0xEF)) && (text[ 1 ] == char(0xBB)) && (text[ 2 ] == char(0xBF)) )
		start += 3;

	// split raw text into a sequence of lines; cope with the mess of pre OSX Mac ("\r"),
	// DOS ("\r\n") and Unix ("\n") line endings
	nlineno_t num_lines{ 0 };
	for( nlineno_t i = start; i < num_char; ++i )
	{
		const char ch{ text[ i ] };

		if(
			(ch == '\n')
			|| (
				(ch == '\r')
				&& (i < num_char_minus_one)
				&& (text[ i + 1 ] != '\n')
				)
			)
		{
			cxt.f_LineNo += 1;
			const nlineno_t end{ i + 1 };

			num_lines += 1;
			UpdateError( res, WriteLine( cxt, start, text + start, text + end ) );

			start = end;

			notifier.Pulse( i );
		}
	}

	// last line handling, with/without trailing newline and ensuring an index entry
	// exists for "the line after the last line" (an "end" marker, needed by Scintilla);
	// the first WriteLine here either writes out the last line (where that line has no
	// line ending), otherwise, the end marker; WriteLine is called again for the
	// case of the last line having no line ending to ensure the end marker is written
	UpdateError( res, WriteLine( cxt, start, text + start, text + num_char ) );
	if( start != num_char )
	{
		UpdateError( res, WriteLine( cxt, start, text + num_char, text + num_char ) );
		num_lines += 1;
	}

	*pnum_lines = num_lines;
	return res;
}


Error LogIndexWriter::Write( const std::filesystem::path & index_path, FILETIME modified_time, const std::string & guid, ProgressMeter * progress )
{
	// detect and ignore empty logfiles
	PythonPerfTimer timer{ __FUNCTION__ };

	if( m_Log.GetSize() == 0 )
		return TraceError( e_Empty, "'%S'", index_path.c_str() );

	// create index file
	OStream stream;
	stream.open( index_path, std::ios_base::binary | std::ios_base::trunc );
	if( !stream.is_open() )
		return TraceError( e_OpenFileStream, "'%S'", index_path.c_str() );

	// placeholder for header
	stream.seekp( E_Header::e_DataOffset, std::ios_base::beg );

	// write out line data
	Error res{ e_OK };
	StringTable string_table;
	IndexFileHeaderV2 header;
	WriteContext cxt{ string_table, header, stream };
	nlineno_t num_lines{ 0 };
	UpdateError( res, WriteLines( cxt, &num_lines, progress ) );

	// align up to 8-byte boundary
	const size_t pos_line_end{ stream.tellp() };
	const size_t pos_field_data{ (pos_line_end & 0x7) ?
		(pos_line_end & ~0x7) + 8
		: pos_line_end
	};
	stream.seekp( pos_field_data, std::ios_base::beg );

	// write out field header data
	for( auto & field : m_AllFields )
		UpdateError( res, field->WriteFieldHeader( cxt ) );

	// write out string table
	const size_t pos_strtbl{ stream.tellp() };
	string_table.WriteValue( stream );

	// rewind and write out file header
	strcpy_s( header.f_SchemaGuid, guid.c_str() );
	header.f_LogfileModifiedTime = modified_time;
	header.f_NumFields = static_cast<uint8_t>(m_AllFields.size());
	header.f_NumLines = num_lines;
	header.f_FieldDataOffset = pos_field_data;
	header.f_StringTableOffset = pos_strtbl;

	stream.seekp( 0, std::ios_base::beg );
	stream.write_value( header );

	// flush all data out to disk
	stream.close();
	if( !stream.good() )
		return TraceError( e_Stream, "unable to create index: '%S'", index_path.c_str() );

	// write out performance data
	timer.AddArgument( index_path.c_str() );
	timer.Close( num_lines );
	
	return res;
}

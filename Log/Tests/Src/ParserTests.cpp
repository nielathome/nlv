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
#include "gtest/gtest.h"

#include "LogAccessor.h"
#include "Match.h"
#include "Ntrace.h"
#include "Parser.h"

// C++ includes
#include <vector>
#include <memory>

// keep tests in a private namespace
namespace {



/*-----------------------------------------------------------------------
 * U_CaptureTraceMessages
 -----------------------------------------------------------------------*/

using message_list_t = std::vector<std::string>;

struct U_CaptureTraceMessages
{
	// the trace system is global, so trace capture denies running UTs in parallel
	static message_list_t s_TraceMessages;

	// trace function; append all trace output to the global list
	static void TraceToMemory( Error, const std::string & message ) {
		s_TraceMessages.push_back( message );
	}

	U_CaptureTraceMessages( void ) {
		s_TraceMessages.clear();
		SetTraceFunc( &U_CaptureTraceMessages::TraceToMemory );
	}

	~U_CaptureTraceMessages( void ) {
		SetTraceFunc();
		EXPECT_EQ( message_list_t{}, s_TraceMessages );
	}

	void Expect( const message_list_t & expect_list );
};


message_list_t U_CaptureTraceMessages::s_TraceMessages;


void U_CaptureTraceMessages::Expect( const message_list_t & expect_list )
{
	const std::string missing{ "!no-message-available!" };
	std::ostringstream strm;

	const message_list_t & actual_list{ s_TraceMessages };
	const size_t limit{ std::max( expect_list.size(), actual_list.size() ) };
	unsigned ok_count{ 0 };
	for( size_t i = 0; i < limit; ++i )
	{
		const std::string & expect{ i < expect_list.size() ? expect_list[ i ] : missing };
		const std::string & actual{ i < actual_list.size() ? actual_list[ i ] : missing };

		strm << "Expect: " << expect << "\nActual: " << actual << "\n";

		const bool contains{ std::search( actual.begin(), actual.end(), expect.begin(), expect.end() ) != actual.end() };
		if( contains )
			ok_count += 1;
	}

	const bool got_messages_ok{ ok_count == expect_list.size() };
	EXPECT_TRUE( got_messages_ok ) << "Message lists:\n" << strm.str();
	s_TraceMessages.clear();
}



/*-----------------------------------------------------------------------
 * U_LineAccessor
 -----------------------------------------------------------------------*/

const time_t c_RefUtcDateTime{ 1516550557 }; // Sun, 21 Jan 2018 16:02:37 GMT
const time_t c_RefUtcDatum{ 1514817582 };    // Mon, 1  Jan 2018 14:39:42 GMT+00:00

// mock line accessor
struct U_LineAccessor : public LineAccessor, public LineAdornmentsProvider
{
	nlineno_t m_LineNo{ 0 };

	// non-field log line text
	const std::string & m_LogText;
	const std::string & m_AnnotationText;

	std::vector<fieldvalue_t> m_FieldValues;
	std::vector<std::string> m_TextValues;

	U_LineAccessor( const std::string & log_text, const std::string & annotation_text )
		: m_LogText{ log_text }, m_AnnotationText{ annotation_text }
	{
		/* 0 */ m_FieldValues.push_back( (uint64_t) 42 );
				m_TextValues.push_back( "42" );
		/* 1 */ m_FieldValues.push_back( (uint64_t) 100 );
				m_TextValues.push_back( "100" );
		/* 2 */ m_FieldValues.push_back( (uint64_t) 200 );
		/* 3 */ m_FieldValues.push_back( (uint64_t) 3 );
		/* 4 */ m_FieldValues.push_back( NTimecode{ c_RefUtcDateTime, 0 }.CalcOffsetToDatum( c_RefUtcDatum ) );
		/* 5 */ m_FieldValues.push_back( NTimecode{ c_RefUtcDateTime, 5000'000 }.CalcOffsetToDatum( c_RefUtcDatum ) );
		/* 6 */ m_FieldValues.push_back( (int64_t) 50 );
		/* 7 */ m_FieldValues.push_back( (int64_t) -50 );
		/* 8 */ m_FieldValues.push_back( (double) 96.7 );
	}

	nlineno_t GetLineNo( void ) const override {
		return m_LineNo;
	}

	nlineno_t GetLength( void ) const override {
		return nlineno_cast( m_LogText.size() );
	}

	bool IsRegular( void ) const override {
		return false;
	}

	nlineno_t NextIrregularLineLength( void ) const override {
		return -1;
	}

	static void StrToChrPtr( const std::string & str, const char ** first, const char ** last ) {
		*first = &(*str.begin());
		*last = *first + str.size();
	}

	void GetText( const char ** first, const char ** last ) const override {
		StrToChrPtr( m_LogText, first, last );
	}

	void GetNonFieldText( const char ** first, const char ** last ) const override {
		StrToChrPtr( m_LogText, first, last );
	}

	void GetFieldText( unsigned field_id, const char ** first, const char ** last ) const override {
		StrToChrPtr( m_TextValues[field_id], first, last );
	}

	fieldvalue_t GetFieldValue( unsigned field_id ) const override {
		return m_FieldValues[ field_id ];
	}

	bool IsBookMarked( nlineno_t ) const override {
		return false;
	}

	bool IsAnnotated( nlineno_t ) const override {
		return !m_AnnotationText.empty();
	}

	void GetAnnotationText( nlineno_t, const char ** first, const char ** last ) const override {
		*first = m_AnnotationText.c_str();
		*last = *first + m_AnnotationText.size();
	}
};



/*-----------------------------------------------------------------------
 * U_LogSchemaAccessor
 -----------------------------------------------------------------------*/

// simulate a few "well-known" fields
struct U_LogSchemaAccessor : public LogSchemaAccessor
{
	struct U_Field
	{
		FieldDescriptor m_FieldDescriptor;
		FieldValueType m_Type;
		std::vector<std::string> m_EnumValues;

		U_Field( const char * name, FieldValueType type )
			: m_FieldDescriptor{ true, name }, m_Type{ type } {}
	};
	std::vector<U_Field> m_Fields;

	U_LogSchemaAccessor( void ) {
		/* 0 */ m_Fields.emplace_back( U_Field{ "fieldA", FieldValueType::unsigned64 } );
		/* 1 */ m_Fields.emplace_back( U_Field{ "fieldB", FieldValueType::unsigned64 } );
		/* 2 */ m_Fields.emplace_back( U_Field{ "_field02", FieldValueType::unsigned64 } );
		/* 3 */ m_Fields.emplace_back( U_Field{ "fieldC", FieldValueType::unsigned64 } );
				m_Fields.back().m_EnumValues.emplace_back( "__INVALID__" );
				m_Fields.back().m_EnumValues.emplace_back( "e_Zero" );
				m_Fields.back().m_EnumValues.emplace_back( "e_One" );
				m_Fields.back().m_EnumValues.emplace_back( "e_Two" );
		/* 4 */ m_Fields.emplace_back( U_Field{ "dt", FieldValueType::signed64 } );
		/* 5 */ m_Fields.emplace_back( U_Field{ "d2", FieldValueType::signed64 } );
		/* 6 */ m_Fields.emplace_back( U_Field{ "spos", FieldValueType::signed64 } );
		/* 7 */ m_Fields.emplace_back( U_Field{ "sneg", FieldValueType::signed64 } );
		/* 8 */ m_Fields.emplace_back( U_Field{ "real", FieldValueType::float64 } );
	}

	size_t GetNumFields( void ) const override {
		return m_Fields.size();
	}

	const FieldDescriptor & GetFieldDescriptor( unsigned field_id ) const override {
		return m_Fields[ field_id ].m_FieldDescriptor;
	}

	FieldValueType GetFieldType( unsigned field_id ) const override {
		return m_Fields[ field_id ].m_Type;
	}

	uint16_t GetFieldEnumCount( unsigned field_id ) const override {
		return static_cast<uint16_t>(m_Fields[ field_id ].m_EnumValues.size());
	}

	const char * GetFieldEnumName( unsigned field_id, uint16_t enum_id ) const {
		return m_Fields[ field_id ].m_EnumValues[ enum_id ].c_str();
	}

	NTimecodeBase m_TimecodeBase{ c_RefUtcDatum };
	const NTimecodeBase & GetTimecodeBase( void ) const override {
		return m_TimecodeBase;
	}
};



/*-----------------------------------------------------------------------
 * U_Selector
 -----------------------------------------------------------------------*/

struct U_Selector
{
	using selector_ptr_t = std::shared_ptr<Selector>;
	selector_ptr_t m_Selector;

	U_Selector( const U_LogSchemaAccessor & schema, Match::Type type, const char * definition, bool match_case = true, bool succeeds = true )
		: m_Selector{ Selector::MakeSelector( Match{ type, definition, match_case }, true, &schema ) }
	{
		if( succeeds )
			EXPECT_NE( nullptr, m_Selector );
		else
			EXPECT_EQ( nullptr, m_Selector );
	}


	bool Hit( const std::string & text, const std::string & annotation_text = std::string{} )
	{
		U_LineAccessor line{ text, annotation_text };
		LineAdornmentsAccessor adornments( &line, 0 );
		return m_Selector ? m_Selector->Hit( line, adornments ) : false;
	}
};


struct U_SelectorLFV : public U_Selector
{
	U_SelectorLFV( const U_LogSchemaAccessor & schema, const char * definition, bool succeeds = true )
		: U_Selector{ schema, Match::e_LogviewFilter, definition, true, succeeds } {}
};



/*-----------------------------------------------------------------------
 * TestCommon
 -----------------------------------------------------------------------*/

struct TestCommon : public ::testing::Test
{
	U_CaptureTraceMessages m_Messages;
	U_LogSchemaAccessor m_LogSchema;
};



/*-----------------------------------------------------------------------
 * TestCommon_en_GB
 -----------------------------------------------------------------------*/

struct TestCommon_en_GB : public TestCommon
{
	void SetUp( void ) override {
		std::locale::global( std::locale( "en-GB" ) );
	}
};



/*-----------------------------------------------------------------------
 * UT Selector
 -----------------------------------------------------------------------*/

struct SelectTrue
	: public TestCommon {};

TEST_F( SelectTrue, EmptyDescriptor )
{
	U_Selector selector{ m_LogSchema, Match::e_Literal, "" };
	EXPECT_TRUE( selector.Hit( "" ) );
	EXPECT_TRUE( selector.Hit( "any text here" ) );
}


/*-----------------------------------------------------------------------
 * UT UserAdornmentsClause
 -----------------------------------------------------------------------*/

struct UserAdornmentsClause
	: public TestCommon {};

TEST_F( UserAdornmentsClause, Bookmarked )
{
	U_SelectorLFV bookmarked{ m_LogSchema,  R"__(bookmarked)__" };
	EXPECT_FALSE( bookmarked.Hit( "" ) );
}


TEST_F( UserAdornmentsClause, Annotated )
{
	{
		U_SelectorLFV annotated{ m_LogSchema,  R"__(annotated)__" };
		EXPECT_FALSE( annotated.Hit( "" ) );
	}

	{
		U_SelectorLFV annotated{ m_LogSchema,  R"__(annotated)__" };
		EXPECT_TRUE( annotated.Hit( "", "some annotation text" ) );
	}

	{
		U_SelectorLFV annotated{ m_LogSchema,  R"__(annotation ~= "some")__" };
		EXPECT_TRUE( annotated.Hit( "", "some annotation text" ) );
	}

	{
		U_SelectorLFV annotated{ m_LogSchema,  R"__(annotation ~= "none")__" };
		EXPECT_FALSE( annotated.Hit( "", "some annotation text" ) );
	}
}


/*-----------------------------------------------------------------------
 * UT TextMatchClauseBad
 -----------------------------------------------------------------------*/

// common error strings
#define e_SelectorCreate "nlog(e_SelectorCreate){Selector::MakeSelector} "
#define e_Parser_Expectation "nlog(e_Parser){ErrorHandlerContext::ExpectationPoint} Unable to parse "
#define e_ParseUnexpectedText "nlog(e_ParseUnexpectedText){ErrorHandlerContext::UnexpectedText} Unable to parse: "

#define c_Fail_LFV e_SelectorCreate "Unable to parse LVF definition"
#define c_Fail_Trailing e_SelectorCreate "Unable to parse trailing text"
#define c_Fail_SemanticAnalysis e_SelectorCreate "Semantic error"


struct TextMatchClauseMisc
	: public TestCommon {};

TEST_F( TextMatchClauseMisc, Annotation )
{
	U_SelectorLFV selector{ m_LogSchema, R"__(annotation ~= "literal")__" };

	// annotation's not implemented yet ...
	EXPECT_FALSE( selector.Hit( "includes word literal somewhere" ) );
}


struct TextMatchClauseBad
	: public TestCommon {};

TEST_F( TextMatchClauseBad, MisMatchedPlainQuoteChar )
{
	U_SelectorLFV selector{ m_LogSchema, R"__(log ~= /literal")__", false };

	m_Messages.Expect( message_list_t{
		e_Parser_Expectation "<plain-string>: at: line:{1} col:{8} text:{/literal\"...} expected: <literal-char>{/}",
		e_Parser_Expectation "<text-match-clause>: at: line:{1} col:{1} text:{log ~=...} expected: <text-value>",
		e_Parser_Expectation "<primary-expr>: at: line:{1} col:{1} text:{log ~=...} expected: <text-value> ",
		c_Fail_LFV
	} );
}


TEST_F( TextMatchClauseBad, MisMatchedRawQuoteChar )
{
	U_SelectorLFV selector{ m_LogSchema, R"__(log ~= r/(literal)")__", false };

	m_Messages.Expect( message_list_t{
		e_Parser_Expectation "<raw-string>: at: line:{1} col:{8} text:{r/(literal)...} expected: <literal-char>{/}",
		e_Parser_Expectation "<text-match-clause>: at: line:{1} col:{1} text:{log ~=...} expected: <text-value>",
		e_Parser_Expectation "<primary-expr>: at: line:{1} col:{1} text:{log ~=...} expected: <text-value> ",
		c_Fail_LFV
	} );
}


TEST_F( TextMatchClauseBad, MisMatchedRawDelimiter )
{
	U_SelectorLFV selector{ m_LogSchema, R"__(log ~= r/letters(literal)lett/)__", false };

	m_Messages.Expect( message_list_t{
		e_Parser_Expectation "<raw-string>: at: line:{1} col:{8} text:{r/letters(litera...} expected: <literal-string>{)letters}",
		e_Parser_Expectation "<text-match-clause>: at: line:{1} col:{1} text:{log ~=...} expected: <text-value>",
		e_Parser_Expectation "<primary-expr>: at: line:{1} col:{1} text:{log ~=...} expected: <text-value> ",
		c_Fail_LFV
	} );
}


TEST_F( TextMatchClauseBad, InvalidPlainQualifer )
{
	U_SelectorLFV selector{ m_LogSchema, R"__(log ~= "literal"I)__", false };

	m_Messages.Expect( message_list_t{
		e_ParseUnexpectedText "at: line:{1} col:{17} text:{I...}",
		c_Fail_Trailing
	} );
}


TEST_F( TextMatchClauseBad, InvalidRawQualifier )
{
	U_SelectorLFV selector{ m_LogSchema, R"__(log ~= r/aa(literal)aa/k)__", false };

	m_Messages.Expect( message_list_t{
		e_ParseUnexpectedText "at: line:{1} col:{24} text:{k...}",
		c_Fail_Trailing
	} );
}


TEST_F( TextMatchClauseBad, MissingPlainStringText )
{
	U_SelectorLFV selector{ m_LogSchema, R"__(  log ~= //)__", false };

	m_Messages.Expect( message_list_t{
		e_Parser_Expectation "<plain-string>: at: line:{1} col:{10} text:{/...} expected: <difference><char><literal-char>{/}",
		e_Parser_Expectation "<text-match-clause>: at: line:{1} col:{3} text:{log ~=...} expected: <text-value>",
		e_Parser_Expectation "<primary-expr>: at: line:{1} col:{3} text:{log ~=...} expected: <text-value> ",
		c_Fail_LFV
	} );
}


TEST_F( TextMatchClauseBad, MissingRawStringText )
{
	U_SelectorLFV selector{ m_LogSchema, R"__(  log ~= r/letters()letters/)__", false };

	m_Messages.Expect( message_list_t{
		e_Parser_Expectation "<raw-string>: at: line:{1} col:{10} text:{r/letters(...} expected: <difference><char><literal-string>{)letters}",
		e_Parser_Expectation "<text-match-clause>: at: line:{1} col:{3} text:{log ~=...} expected: <text-value>",
		e_Parser_Expectation "<primary-expr>: at: line:{1} col:{3} text:{log ~=...} expected: <text-value> ",
		c_Fail_LFV
	} );
}


TEST_F( TextMatchClauseBad, BadFieldName )
{
	U_SelectorLFV selector{ m_LogSchema, R"__(  unknown_field ~= "something")__", false };

	m_Messages.Expect( message_list_t{
		"nlog(e_FieldName){A_FieldName::GetFieldId} Unrecognised field name:{unknown_field}",
		c_Fail_SemanticAnalysis
	} );
}



/*-----------------------------------------------------------------------
 * UT TextMatchClauseHit
 -----------------------------------------------------------------------*/

struct TextMatchClauseHit
	: public TestCommon, public ::testing::WithParamInterface<const char*> {};

TEST_P( TextMatchClauseHit, Match )
{
	U_SelectorLFV selector{ m_LogSchema, GetParam() };

	EXPECT_FALSE( selector.Hit( "any text here" ) );
	EXPECT_TRUE( selector.Hit( "includes word literal somewhere" ) );
}

INSTANTIATE_TEST_CASE_P(
	I, TextMatchClauseHit,
	::testing::Values(
		// `plain_string` (literal)
		/* 00 */ R"__(log ~= "literal")__",
		/* 01 */ R"__(log ~= "liTeral"i)__",

		// `plain_string` (regular expression)
		/* 02 */ R"__(log ~= /li.*al/)__",

		// `raw_string` (literal)
		/* 03 */ R"__(log ~= r"(literal)")__",
		/* 04 */ R"__(log ~= r""(literal)"")__",
		/* 05 */ R"__(log ~= r"@(literal)@")__",

		// `raw_string` (regular expression)
		/* 06 */ R"__(log ~= r/(li.*al)/)__",
		/* 07 */ R"__(log ~= r/letters(li.*al)letters/)__",
		/* 08 */ R"__(log ~= r/letters(LI.*al)letters/i)__"
) );



/*-----------------------------------------------------------------------
 * UT FieldTextMatchClauseHit
 -----------------------------------------------------------------------*/

struct FieldTextMatchClauseHit
	: public TestCommon, public ::testing::WithParamInterface<const char*> {};

TEST_P( FieldTextMatchClauseHit, Match )
{
	U_SelectorLFV selector{ m_LogSchema, GetParam() };

	EXPECT_TRUE( selector.Hit( "any text here" ) );
}

INSTANTIATE_TEST_CASE_P(
	I, FieldTextMatchClauseHit,
	::testing::Values(
		// field text matches
		/* 01 */ R"__(fieldA ~= "42")__",
		/* 02 */ R"__(fieldA ~= r"@(2)@")__",
		/* 03 */ R"__(fieldB ~= /1../)__",
		/* 04 */ R"__(fieldB ~= r/##(1.)##/)__"
) );



/*-----------------------------------------------------------------------
 * UT FieldMatchClauseBad
 -----------------------------------------------------------------------*/

struct FieldMatchClauseBad
	: public TestCommon {};

TEST_F( FieldMatchClauseBad, MissingLowerBound )
{
	U_SelectorLFV selector{ m_LogSchema, R"__(fieldA in [ .. 10])__", false };

	m_Messages.Expect( message_list_t{
		e_Parser_Expectation "<field-match-clause>: at: line:{1} col:{1} text:{fieldA in [...} expected: <list><field-range-item><literal-char>{,}",
		e_Parser_Expectation "<primary-expr>: at: line:{1} col:{1} text:{fieldA in [...} expected: <list><field-range-item><literal-char>{,} ",
		c_Fail_LFV
	} );
}


TEST_F( FieldMatchClauseBad, MissingDotDot )
{
	U_SelectorLFV selector{ m_LogSchema, R"__(fieldA in [10 . 21 ])__", false };

	m_Messages.Expect( message_list_t{
		e_Parser_Expectation "<field-match-clause>: at: line:{1} col:{1} text:{fieldA in [10 ...} expected: <literal-char>{]}",
		e_Parser_Expectation "<primary-expr>: at: line:{1} col:{1} text:{fieldA in [10 ...} expected: <literal-char>{]} ",
		c_Fail_LFV
	} );
}


TEST_F( FieldMatchClauseBad, MissingUpperBound )
{
	U_SelectorLFV selector{ m_LogSchema, R"__(fieldA in [10 .. ])__", false };

	m_Messages.Expect( message_list_t{
		e_Parser_Expectation "<field-range-upper>: at: line:{1} col:{14} text:{ .....} expected: <field-value>",
		e_Parser_Expectation "<field-match-clause>: at: line:{1} col:{1} text:{fieldA in [10 ...} expected: <literal-char>{]}",
		e_Parser_Expectation "<primary-expr>: at: line:{1} col:{1} text:{fieldA in [10 ...} expected: <literal-char>{]} ",
		c_Fail_LFV
	} );
}


TEST_F( FieldMatchClauseBad, MissingRange )
{
	U_SelectorLFV selector{ m_LogSchema, R"__(fieldA in [10, ])__", false };

	m_Messages.Expect( message_list_t{
		e_Parser_Expectation "<field-match-clause>: at: line:{1} col:{1} text:{fieldA in [10...} expected: <literal-char>{]} ",
		e_Parser_Expectation "<primary-expr>: at: line:{1} col:{1} text:{fieldA in [10...} expected: <literal-char>{]}",
		c_Fail_LFV
	} );
}


TEST_F( FieldMatchClauseBad, NoRange )
{
	U_SelectorLFV selector{ m_LogSchema, R"__(fieldA in [ ])__", false };

	m_Messages.Expect( message_list_t{
		e_Parser_Expectation "<field-match-clause>: at: line:{1} col:{1} text:{fieldA in [...} expected: <list><field-range-item><literal-char>{,}",
		e_Parser_Expectation "<primary-expr>: at: line:{1} col:{1} text:{fieldA in [...} expected: <list><field-range-item><literal-char>{,} ",
		c_Fail_LFV
	} );
}


TEST_F( FieldMatchClauseBad, MisorderedBounds )
{
	U_SelectorLFV selector{ m_LogSchema, R"__(fieldA in [20..10])__", false };

	m_Messages.Expect( message_list_t{
		"nlog(e_MultipleEnum){A_FieldRangeItem::Analyse} Field range lower_bound:{20} not lower than upper_bound:{10}",
		c_Fail_SemanticAnalysis
	} );
}


TEST_F( FieldMatchClauseBad, WrongEnumName )
{
	U_SelectorLFV selector{ m_LogSchema, R"__(fieldC in ["e_Junk"])__", false };

	m_Messages.Expect( message_list_t{
		"nlog(e_EnumName){A_FieldValue::FieldValueVisitor::operator ()} Unrecognised enumeration value:{e_Junk}",
		c_Fail_SemanticAnalysis
	} );
}


TEST_F( FieldMatchClauseBad, EnumRangeBadLower )
{
	U_SelectorLFV selector{ m_LogSchema, R"__(fieldC in [/e_*/ .. "e_Two"])__", false };

	m_Messages.Expect( message_list_t{
		"nlog(e_MultipleEnum){A_FieldRangeItem::Analyse} Field range lower_bound matched more than one enumeration value",
		c_Fail_SemanticAnalysis
	} );
}


TEST_F( FieldMatchClauseBad, EnumRangeBadUpper )
{
	U_SelectorLFV selector{ m_LogSchema, R"__(fieldC in ["e_Two" .. /e_*/])__", false };

	m_Messages.Expect( message_list_t{
		"nlog(e_MultipleEnum){A_FieldValue::Analyse} Name:{e_*} matched multiple enumeration values",
		c_Fail_SemanticAnalysis
	} );
}



/*-----------------------------------------------------------------------
 * UT FieldMatchClauseMiss
 -----------------------------------------------------------------------*/

struct FieldMatchClauseMiss
	: public TestCommon, public ::testing::WithParamInterface<const char*> {};

TEST_P( FieldMatchClauseMiss, Match )
{
	U_SelectorLFV selector{ m_LogSchema, GetParam() };
	EXPECT_FALSE( selector.Hit( "" ) );
}

// fieldA == 42 (0x2A), fieldB == 100 (0x64)
INSTANTIATE_TEST_CASE_P(
	I, FieldMatchClauseMiss,
	::testing::Values(
		/* 00 */ R"__(fieldB in [101])__",
		/* 01 */ R"__(fieldB in [90..110, ^100])__",
		/* 02 */ R"__(fieldB in [50..150,^90..110])__",
		/* 03 */ R"__(fieldC in [/e_*/, ^"e_Two"])__",
		/* 04 */ R"__(fieldC in ["e_Zero", "e_One"])__",
		/* 05 */ R"__(fieldC in ["e_Junk"i])__"
) );



/*-----------------------------------------------------------------------
 * UT FieldMatchClauseHit
 -----------------------------------------------------------------------*/

struct FieldMatchClauseHit
	: public TestCommon, public ::testing::WithParamInterface<const char*> {};

TEST_P( FieldMatchClauseHit, Match )
{
	U_SelectorLFV selector{ m_LogSchema, GetParam() };
	EXPECT_TRUE( selector.Hit( "" ) );
}

INSTANTIATE_TEST_CASE_P(
	I, FieldMatchClauseHit,
	::testing::Values(
		/* 00 */ R"__(fieldB in [100])__",
		/* 01 */ R"__(     b in [100])__",
		/* 02 */ R"__(fieldB in [50, 60, 70, 100])__",
		/* 03 */ R"__(fieldB in [90..110])__",
		/* 04 */ R"__(fieldB in [1, 3, 5, 20..30, 40..50, 90..110])__",
		/* 05 */ R"__(fieldB in [^20..30, ^40..50, 90..110])__",
		/* 06 */ R"__(fieldC in ["e_Zero" .. "e_Two"])__",
		/* 07 */ R"__(fieldC in ["One", "Two"])__",
		/* 08 */ R"__(fieldC in [^"One"])__",	// no `included_range` part
		/* 09 */ R"__(fieldC in [^"Junk"i])__",
		/* 10 */ R"__(fieldC in [/e_*/])__",
		/* 11 */ R"__(sneg in [-55 .. -45])__",
		/* 12 */ R"__(real in [96 .. 97])__",
		/* 13 */ R"__(real in [96.5 .. 96.8])__"
) );



/*-----------------------------------------------------------------------
 * UT FieldCompareClauseBad
 -----------------------------------------------------------------------*/

struct FieldCompareClauseBad
	: public TestCommon {};

TEST_F( FieldCompareClauseBad, WrongFieldName )
{
	U_SelectorLFV selector{ m_LogSchema, R"__(identifier = 100)__", false };

	m_Messages.Expect( message_list_t{
		"nlog(e_FieldName){A_FieldName::GetFieldId} Unrecognised field name:{identifier}",
		c_Fail_SemanticAnalysis
	} );
}


TEST_F( FieldCompareClauseBad, MultipleFieldName )
{
	U_SelectorLFV selector{ m_LogSchema, R"__(field = 100)__", false };

	m_Messages.Expect( message_list_t{
		"nlog(e_MultipleField){A_FieldName::GetFieldId} Name:{field} matched multiple field names",
		c_Fail_SemanticAnalysis
	} );
}


TEST_F( FieldCompareClauseBad, BadHexNumber )
{
	U_SelectorLFV selector{ m_LogSchema, R"__(identifier = 0x ab)__", false };

	m_Messages.Expect( message_list_t{
		e_Parser_Expectation "<hex-number>: at: line:{1} col:{14} text:{0x...} expected: <unsigned-integer>",
		e_Parser_Expectation "<field-compare-clause>: at: line:{1} col:{1} text:{identifier = 0x...} expected: <unsigned-integer>",
		e_Parser_Expectation "<primary-expr>: at: line:{1} col:{1} text:{identifier = 0x...} expected: <unsigned-integer> ",
		c_Fail_LFV
	} );
}


TEST_F( FieldCompareClauseBad, BadRealNumber )
{
	U_SelectorLFV selector{ m_LogSchema, R"__(identifier = 1.)__", false };
	m_Messages.Expect( message_list_t{
		"nlog(e_ParseUnexpectedText){ErrorHandlerContext::UnexpectedText} Unable to parse: at: line:{1} col:{15} text:{....} ",
		c_Fail_Trailing
	} );
}


TEST_F( FieldCompareClauseBad, MultipleEnumsFound )
{
	U_SelectorLFV selector{ m_LogSchema, R"__(fieldC = "e_")__", false };

	m_Messages.Expect( message_list_t{
		"nlog(e_MultipleEnum){A_FieldValue::Analyse} Name:{e_} matched multiple enumeration values",
		c_Fail_SemanticAnalysis
	} );
}



/*-----------------------------------------------------------------------
 * UT FieldCompareClauseMiss
 -----------------------------------------------------------------------*/

struct FieldCompareClauseMiss
	: public TestCommon, public ::testing::WithParamInterface<const char*> {};

TEST_P( FieldCompareClauseMiss, Match )
{
	U_SelectorLFV selector{ m_LogSchema, GetParam() };
	EXPECT_FALSE( selector.Hit( "" ) );
}

// fieldA == 42 (0x2A), fieldB == 100 (0x64)
INSTANTIATE_TEST_CASE_P(
	I, FieldCompareClauseMiss,
	::testing::Values(
		/* 00 */ R"__(fieldA < 42)__",
		/* 01 */ R"__(fieldA <= 41)__",
		/* 02 */ R"__(fieldA > 42)__",
		/* 03 */ R"__(fieldA >= 43)__",
		/* 04 */ R"__(fieldA >= -1)__",	// fieldA unsigned, so -1 is uint max
		/* 05 */ R"__(fieldC = "e_One")__",
		/* 06 */ R"__(fieldC = "e_Junk"i)__",
		/* 07 */ R"__(real < 43)__"
) );



/*-----------------------------------------------------------------------
 * UT FieldCompareClauseHit
 -----------------------------------------------------------------------*/

struct FieldCompareClauseHit
	: public TestCommon, public ::testing::WithParamInterface<const char*> {};

TEST_P( FieldCompareClauseHit, Match )
{
	U_SelectorLFV selector{ m_LogSchema, GetParam() };
	EXPECT_TRUE( selector.Hit( "" ) );
}

INSTANTIATE_TEST_CASE_P(
	I, FieldCompareClauseHit,
	::testing::Values(
		/* 00 */ R"__(fieldA < 43)__",
		/* 01 */ R"__(    da < 43)__",
		/* 02 */ R"__(fieldA > 41)__",
		/* 03 */ R"__(fieldA = 42)__",
		/* 04 */ R"__(fieldA <= 42)__",
		/* 05 */ R"__(fieldA >= 42)__",
		/* 06 */ R"__(fieldA=42)__",
		/* 07 */ R"__(fieldA=0x2a)__",
		/* 08 */ R"__(fieldA=0x2A)__",
		/* 09 */ R"__(fieldC = "e_Two")__",
		/* 10 */ R"__(fieldC = /e_.Wo/i)__",
		/* 11 */ R"__(_field02= 200)__",
		/* 12 */ R"__(sneg <= -50)__",
		/* 13 */ R"__(spos = 50)__",
		/* 14 */ R"__(spos = +50)__",
		/* 15 */ R"__(spos > -1)__",
		/* 16 */ R"__(real > 95.3)__",
		/* 17 */ R"__(real < 100.77)__",
		/* 18 */ R"__(real > 95)__",
		/* 19 */ R"__(real < 100)__",
		/* 20 */ R"__(real > -1)__",
		/* 21 */ R"__(real > -1.1)__"
) );



/*-----------------------------------------------------------------------
 * UT DateTimeBad_en_GB
 -----------------------------------------------------------------------*/

//
// UTC - 1516550557
//  Sun, 21 Jan 2018 16:02:37 GMT
//
struct DateTimeBad_en_GB
	: public TestCommon_en_GB {};


TEST_F( DateTimeBad_en_GB, MissingMonth )
{
	U_SelectorLFV selector{ m_LogSchema, R"__(dt = 21/)__", false };

	m_Messages.Expect( message_list_t{
		e_Parser_Expectation "<date-part>: at: line:{1} col:{8} text:{/...} expected: <unsigned-integer> ",
		e_Parser_Expectation "<date>: at: line:{1} col:{6} text:{21/...} expected: <unsigned-integer> ",
		e_Parser_Expectation "<field-compare-clause>: at: line:{1} col:{1} text:{dt = 21/...} expected: <unsigned-integer> ",
		e_Parser_Expectation "<primary-expr>: at: line:{1} col:{1} text:{dt = 21/...} expected: <unsigned-integer> ",
		c_Fail_LFV
	} );
}


TEST_F( DateTimeBad_en_GB, MissingMonthYear )
{
	U_SelectorLFV selector{ m_LogSchema, R"__(dt = 21 16:02:37)__", false };

	m_Messages.Expect( message_list_t{
		e_ParseUnexpectedText "at: line:{1} col:{9} text:{16:02:37...}",
		c_Fail_Trailing
	} );
}


TEST_F( DateTimeBad_en_GB, MissingYear )
{
	U_SelectorLFV selector{ m_LogSchema, R"__(dt = 21/1/)__", false };

	m_Messages.Expect( message_list_t{
		e_Parser_Expectation "<date-part>: at: line:{1} col:{10} text:{/...} expected: <unsigned-integer> ",
		e_Parser_Expectation "<date>: at: line:{1} col:{6} text:{21/1/...} expected: <unsigned-integer> ",
		e_Parser_Expectation "<field-compare-clause>: at: line:{1} col:{1} text:{dt = 21/1/...} expected: <unsigned-integer> ",
		e_Parser_Expectation "<primary-expr>: at: line:{1} col:{1} text:{dt = 21/1/...} expected: <unsigned-integer> ",
		c_Fail_LFV
	} );
}


TEST_F( DateTimeBad_en_GB, InvalidSecondsSeparator )
{
	U_SelectorLFV selector{ m_LogSchema, R"__(dt = 21/1/2018 16:02 :37)__", false };

	m_Messages.Expect( message_list_t{
		e_Parser_Expectation "<std-time>: at: line:{1} col:{16} text:{16:02...} expected: <literal-char>{:} ",
		e_Parser_Expectation "<field-compare-clause>: at: line:{1} col:{1} text:{dt = 21/1/2018 1...} expected: <literal-char>{:} ",
		e_Parser_Expectation "<primary-expr>: at: line:{1} col:{1} text:{dt = 21/1/2018 1...} expected: <literal-char>{:} ",
		c_Fail_LFV
	} );
}


TEST_F( DateTimeBad_en_GB, MissingSeconds )
{
	U_SelectorLFV selector{ m_LogSchema, R"__(fieldA = 15:2:)__", false };

	m_Messages.Expect( message_list_t{
		e_Parser_Expectation "<std-time>: at: line:{1} col:{10} text:{15:2:...} expected: <unsigned-integer> ",
		e_Parser_Expectation "<field-compare-clause>: at: line:{1} col:{1} text:{fieldA = 15:2:...} expected: <unsigned-integer> ",
		e_Parser_Expectation "<primary-expr>: at: line:{1} col:{1} text:{fieldA = 15:2:...} expected: <unsigned-integer> ",
		c_Fail_LFV
	} );
}


TEST_F( DateTimeBad_en_GB, OutOfRangeSeconds )
{
	U_SelectorLFV selector{ m_LogSchema, R"__(fieldA = 15:2:100)__", false };

	m_Messages.Expect( message_list_t{
		"nlog(e_BadSeconds){A_StdTime::GetValue} Seconds value out of range:{100}",
		c_Fail_SemanticAnalysis
	} );
}


TEST_F( DateTimeBad_en_GB, OutOfRangeMinutes )
{
	U_SelectorLFV selector{ m_LogSchema, R"__(fieldA = 15:101:2)__", false };

	m_Messages.Expect( message_list_t{
		"nlog(e_BadMinutes){A_StdTime::GetValue} Minutes value out of range:{101}",
		c_Fail_SemanticAnalysis
	} );
}


TEST_F( DateTimeBad_en_GB, OutOfRangeHours )
{
	U_SelectorLFV selector{ m_LogSchema, R"__(fieldA = 102:2:2)__", false };

	m_Messages.Expect( message_list_t{
		"nlog(e_BadHours){A_StdTime::GetValue} Hours value out of range:{102}",
		c_Fail_SemanticAnalysis
	} );
}

TEST_F( DateTimeBad_en_GB, OutOfRangeDay )
{
	U_SelectorLFV selector{ m_LogSchema, R"__(fieldA = 30/2/2019)__", false };

	m_Messages.Expect( message_list_t{
		"nlog(e_BadDay){A_Date::UpdateTm} Day value out of range:{30} for month:{2}",
		c_Fail_SemanticAnalysis
	} );
}


TEST_F( DateTimeBad_en_GB, OutOfRangeMonth )
{
	U_SelectorLFV selector{ m_LogSchema, R"__(fieldA = 5/13/2019)__", false };

	m_Messages.Expect( message_list_t{
		"nlog(e_BadMonth){A_Date::UpdateTm} Month value out of range:{13}",
		c_Fail_SemanticAnalysis
	} );
}


TEST_F( DateTimeBad_en_GB, BadNumber )
{
	// don't accept negative numbers
	U_SelectorLFV selector{ m_LogSchema, R"__(dt = 21/1/2018 16:02:-37)__", false };

	m_Messages.Expect( message_list_t{
		e_Parser_Expectation "<std-time>: at: line:{1} col:{16} text:{16:02:...} expected: <unsigned-integer> ",
		e_Parser_Expectation "<field-compare-clause>: at: line:{1} col:{1} text:{dt = 21/1/2018 1...} expected: <unsigned-integer> ",
		e_Parser_Expectation "<primary-expr>: at: line:{1} col:{1} text:{dt = 21/1/2018 1...} expected: <unsigned-integer> ",
		c_Fail_LFV
	} );
}


TEST_F( DateTimeBad_en_GB, OversizedFraction )
{
	U_SelectorLFV selector{ m_LogSchema, R"__(d2 = 16:02:37.005000000564)__", false };

	m_Messages.Expect( message_list_t{
		"nlog(e_OversizedTimeFraction){A_Time::GetTimeFrac} Oversized fraction:{005000000564} ",
		c_Fail_SemanticAnalysis
	} );
}


TEST_F( DateTimeBad_en_GB, InvalidFraction )
{
	U_SelectorLFV selector{ m_LogSchema, R"__(d2 = 16:02:37.005fg6)__", false };

	m_Messages.Expect( message_list_t{
		e_ParseUnexpectedText "at: line:{1} col:{18} text:{fg6...} ",
		c_Fail_Trailing
	} );
}


TEST_F( DateTimeBad_en_GB, MissingFractionValue )
{
	U_SelectorLFV selector{ m_LogSchema, R"__(d2 = 16:02:37.)__", false };

	m_Messages.Expect( message_list_t{
		e_Parser_Expectation "<frac-time>: at: line:{1} col:{14} text:{....} expected: <char-set>",
		e_Parser_Expectation "<field-compare-clause>: at: line:{1} col:{1} text:{d2 = 16:02:37....} expected: <char-set> ",
		e_Parser_Expectation "<primary-expr>: at: line:{1} col:{1} text:{d2 = 16:02:37....} expected: <char-set> ",
		c_Fail_LFV
	} );
}



/*-----------------------------------------------------------------------
* UT DateTimeMiss_en_GB
-----------------------------------------------------------------------*/

struct DateTimeMiss_en_GB
	: public TestCommon_en_GB, public ::testing::WithParamInterface<const char*> {};

TEST_P( DateTimeMiss_en_GB, Match )
{
	U_SelectorLFV selector{ m_LogSchema, GetParam() };
	EXPECT_FALSE( selector.Hit( "" ) );
}

INSTANTIATE_TEST_CASE_P(
	I, DateTimeMiss_en_GB,
	::testing::Values(
		/* 00 */ R"__(dt >= 22/1 16:02:37)__",
		/* 01 */ R"__(dt < 16:02:38)__",		// referenced to datum, so 1/Jan
		/* 02 */ R"__(dt < 16:02:38.747)__",
		/* 03 */ R"__(dt < 22/1/15 16:02:37)__"	// pre-datum
) );



/*-----------------------------------------------------------------------
 * UT DateTimeHit_en_GB
 -----------------------------------------------------------------------*/

struct DateTimeHit_en_GB
	: public TestCommon_en_GB, public ::testing::WithParamInterface<const char*> {};

TEST_P( DateTimeHit_en_GB, Match )
{
	U_SelectorLFV selector{ m_LogSchema, GetParam() };
	EXPECT_TRUE( selector.Hit( "" ) );
}

INSTANTIATE_TEST_CASE_P(
	I, DateTimeHit_en_GB,
	::testing::Values(
		/* 00 */ R"__(dt = 21/1/2018 16:02:37)__",
		/* 01 */ R"__(dt = 21/1/2018  16:02:37)__",		// space separated
		/* 02 */ R"__(dt = 21/1/2018	16:02:37)__",	// tab separated
		/* 03 */ R"__(dt = 21/1/18 16:02:37)__",
		/* 04 */ R"__(dt = 21/1 16:02:37)__",
		/* 05 */ R"__(dt > 16:02:38)__",			// referenced to datum, so 1/Jan
		/* 06 */ R"__(dt > 16:02:38.419)__",
		/* 07 */ R"__(dt > 22/1/15 16:02:37)__",	// pre-datum
		/* 08 */ R"__(dt > 21/1/2018)__",
		/* 09 */ R"__(dt < 22/1/2018)__",
		/* 10 */ R"__(dt in [21/1/2018 .. 22/1/2018])__",
		/* 11 */ R"__(dt < 22/1 16:02:37)__",
		/* 12 */ R"__(d2 = 21/1 16:02:37.005)__",
		/* 13 */ R"__(d2 = 21/1 16:02:37.0050)__",
		/* 14 */ R"__(d2 = 21/1 16:02:37.005000000)__",
		/* 15 */ R"__(d2 > 21/1/2018 16:02:37.004999999)__",
		/* 16 */ R"__(d2 < 21/1 16:02:37.005000001)__",
		/* 17 */ R"__(d2 in [21/1 16:02:37 .. 21/1 16:02:37.1])__"
) );



/*-----------------------------------------------------------------------
 * UT DateTimeHit_en_US
 -----------------------------------------------------------------------*/

//In U.S.locale, the default date order is : month, day, year
struct DateTimeHit_en_US
	: public TestCommon, public ::testing::WithParamInterface<const char*> {};

TEST_P( DateTimeHit_en_US, Match )
{
	std::locale::global( std::locale( "en-US" ) );
	U_SelectorLFV selector{ m_LogSchema, GetParam() };
	EXPECT_TRUE( selector.Hit( "" ) );
}

INSTANTIATE_TEST_CASE_P(
	I, DateTimeHit_en_US,
	::testing::Values(
		/* 00 */ R"__(dt = 1/21/2018 16:02:37)__",
		/* 01 */ R"__(dt = 1/21/18 16:02:37)__",
		/* 02 */ R"__(dt = 1/21 16:02:37)__"
) );



/*-----------------------------------------------------------------------
 * UT DateTimeHit_ja_JP
 -----------------------------------------------------------------------*/

//In Japanese locale, the default date order is : year, month, day
struct DateTimeHit_ja_JP
	: public TestCommon, public ::testing::WithParamInterface<const char*> {};

TEST_P( DateTimeHit_ja_JP, Match )
{
	std::locale::global( std::locale( "ja-JP" ) );
	U_SelectorLFV selector{ m_LogSchema, GetParam() };
	EXPECT_TRUE( selector.Hit( "" ) );
}

INSTANTIATE_TEST_CASE_P(
	I, DateTimeHit_ja_JP,
	::testing::Values(
		/* 00 */ R"__(dt = 2018/1/21 16:02:37)__",
		/* 01 */ R"__(dt = 18/1/21 16:02:37)__",
		/* 02 */ R"__(dt = 1/21 16:02:37)__"
) );



/*-----------------------------------------------------------------------
 * UT LogicalOrExpr
 -----------------------------------------------------------------------*/

struct LogicalOrExprBad
	: public TestCommon {};

TEST_F( LogicalOrExprBad, MissingBracket )
{
	U_SelectorLFV selector{ m_LogSchema, R"__(fieldA = 1 and (fieldB =2)__", false };

	m_Messages.Expect( message_list_t{
		e_Parser_Expectation "<primary-expr>: at: line:{1} col:{16} text:{(fieldB =2...} expected: <literal-char>{)} ",
		e_ParseUnexpectedText "at: line:{1} col:{12} text:{and (fieldB =2...} ",
		c_Fail_Trailing
	} );
}


struct LogicalOrExprMiss
	: public TestCommon, public ::testing::WithParamInterface<const char*> {};

TEST_P( LogicalOrExprMiss, Match )
{
	U_SelectorLFV selector{ m_LogSchema, GetParam() };
	EXPECT_FALSE( selector.Hit( "" ) );
}

INSTANTIATE_TEST_CASE_P(
	I, LogicalOrExprMiss,
	::testing::Values(
		/* 00 */ R"__(fieldA = 42 and fieldB = 101)__",
		/* 01 */ R"__(fieldA = 43 or fieldB = 101)__",
		/* 02 */ R"__(not fieldA = 42)__"
) );


struct LogicalOrExprHit
	: public TestCommon, public ::testing::WithParamInterface<const char*> {};

TEST_P( LogicalOrExprHit, Match )
{
	U_SelectorLFV selector{ m_LogSchema, GetParam() };
	EXPECT_TRUE( selector.Hit( "" ) );
}

INSTANTIATE_TEST_CASE_P(
	I, LogicalOrExprHit,
	::testing::Values(
		/* 00 */ R"__(fieldA = 42 and fieldB = 100)__",
		/* 01 */ R"__(fieldA = 42 &&  fieldB = 100)__",
		/* 02 */ R"__(fieldA = 43 or fieldB = 100)__",
		/* 03 */ R"__(fieldA = 43 || fieldB = 100)__",
		/* 04 */ R"__(not (fieldA = 43))__",
		/* 05 */ R"__(  ! (fieldA = 43))__",
		/* 06 */ R"__( not (fieldA = 42 and fieldB = 101) )__"
) );

}

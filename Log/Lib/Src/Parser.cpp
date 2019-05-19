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

// Nlog includes
#include "LogAccessor.h"

// Application includes
#include "Parser.h"
#include "Ntrace.h"

// Boost includes
#include <boost/fusion/tuple.hpp>
#include <boost/lexical_cast.hpp>
#include <boost/spirit/include/qi.hpp>
#include <boost/spirit/include/phoenix_core.hpp>
#include <boost/spirit/include/phoenix_operator.hpp>
#include <boost/spirit/include/phoenix_fusion.hpp>

// C++ includes
#include <memory>


//
// abbreviations:
//
// A_ attribute struct
// a_ attribute datamember
// P_ parser or grammar struct/class
// r_ rule, parser or grammar data member
//



/*-----------------------------------------------------------------------
 * FieldOp
 -----------------------------------------------------------------------*/

 // determine the comparison type
enum class E_FieldCompareOp
{
	Eq,
	Lt,
	LtEq,
	Gt,
	GtEq,
	Ne
};


// perform a field operation
struct FieldOpBase
{
	virtual bool Compare( const fieldvalue_t & lhs, const fieldvalue_t & rhs ) const = 0;
};


template<typename T_VALUE>
struct FieldOp : public FieldOpBase
{
	const E_FieldCompareOp m_Op;

	FieldOp( E_FieldCompareOp op )
		: m_Op{ op } {}

	bool Compare( const fieldvalue_t & lhs, const fieldvalue_t & rhs ) const override
	{
		switch( m_Op )
		{
		case E_FieldCompareOp::Eq:
			return lhs.As<T_VALUE>() == rhs.As<T_VALUE>();

		case E_FieldCompareOp::Lt:
			return lhs.As<T_VALUE>() < rhs.As<T_VALUE>();

		case E_FieldCompareOp::LtEq:
			return lhs.As<T_VALUE>() <= rhs.As<T_VALUE>();

		case E_FieldCompareOp::Gt:
			return lhs.As<T_VALUE>() > rhs.As<T_VALUE>();

		case E_FieldCompareOp::GtEq:
			return lhs.As<T_VALUE>() >= rhs.As<T_VALUE>();

		case E_FieldCompareOp::Ne:
			return lhs.As<T_VALUE>() != rhs.As<T_VALUE>();
		}

		return false;
	}
};


using fieldop_ptr_t = std::shared_ptr<FieldOpBase>;


fieldop_ptr_t MakeFieldOperation( E_FieldCompareOp op, FieldValueType type )
{
	switch( type )
	{
	case FieldValueType::unsigned64:
		return std::make_shared<FieldOp<uint64_t>>( op );

	case FieldValueType::signed64:
		return std::make_shared<FieldOp<int64_t>>( op );

	case FieldValueType::float64:
		return std::make_shared<FieldOp<double>>( op );
	}

	return fieldop_ptr_t{};
}



/*-----------------------------------------------------------------------
 * Namespaces
 -----------------------------------------------------------------------*/

namespace spirit = boost::spirit;
namespace qi = spirit::qi;
namespace ascii = spirit::ascii;
namespace phoenix = boost::phoenix;



/*-----------------------------------------------------------------------
 * Types
 -----------------------------------------------------------------------*/

// forward declarations
struct A_LogicalOrExpr;

// parser iterator for reading source text
using str_iterator = std::string::const_iterator;

// skip parser
using P_Skip = ascii::space_type;

// common rule and grammar types
template<typename ...T_ARGS>
using P_Rule = qi::rule<str_iterator, P_Skip, T_ARGS...>;

template<typename ...T_ARGS>
using P_RuleNoSkip = qi::rule<str_iterator, T_ARGS...>;

template<typename ...T_ARGS>
using P_Grammar = qi::grammar<str_iterator, P_Skip, T_ARGS...>;

template<typename ...T_ARGS>
using P_GrammarNoSkip = qi::grammar<str_iterator, T_ARGS...>;

// catch-all error class for semantic/analysis issue
struct SemanticError : public std::domain_error
{
	SemanticError( void )
		: std::domain_error{ "Semantic error, see error log for details" } {}
};

// helper to trace and throw a semantic error
#define ThrowSemanticError( ERR, FMT, ... ) \
	do { \
		TraceError( ERR, FMT, ##__VA_ARGS__ ); \
		throw SemanticError{}; \
	} while( false )



/*-----------------------------------------------------------------------
 * SetRuleExpectationPointErrorHandler
 -----------------------------------------------------------------------*/

//
// it seems harder than it should be to attach error handling to a rule:
// the relevent functions are not documented, so are derived from source
// code review - which may be a long term maintenence hazard
//

// helper class to fetch and display reporting data about an error and where it occurred
class ErrorHandlerContext
{
private:
	// start of the text being parsed
	const str_iterator m_LVFStart;

	// convert a spirit::info into plain text
	static spirit::utf8_string CollectSpiritInfo( const spirit::info & info )
	{
		// visitor for receiving spirit::info data values; based on boost::spirit::simple_printer
		// builds up a description of what it was that the parser was expecting
		struct SpiritInfoCollector
		{
			spirit::utf8_string & f_Result;

			SpiritInfoCollector( spirit::utf8_string & result )
				: f_Result( result ) {}

			void element( spirit::utf8_string const & tag, spirit::utf8_string const & value, int /*depth*/ ) const
			{
				if( !tag.empty() )
					f_Result += spirit::utf8_string{ '<' } + tag + '>';

				if( !value.empty() )
					f_Result += spirit::utf8_string{ '{' } + value + '}';
			}
		};

		spirit::utf8_string result;
		SpiritInfoCollector collector{ result };
		spirit::basic_info_walker<SpiritInfoCollector> walker{ collector, info.tag, 0 };

		boost::apply_visitor( walker, info.value );
	
		return result;
	}

	// fetch limited amount of text from an iterator location
	static std::string CollectTextAt( str_iterator istart, const str_iterator & iend )
	{
		using count_t = str_iterator::difference_type;
		const count_t max_len{ 16 };
		const count_t given_len{ iend - istart };
		const count_t len{ std::min( max_len, given_len ) };
		const std::string terminate_at{ "\n\r" };

		std::string result;
		for( off_t i = 0; i < len; ++i )
		{
			const char ch{ *(istart++) };
			if( terminate_at.find( ch ) == std::string::npos )
				result.push_back( ch );
			else
				break;
		}

		result += std::string( "..." );
		return result;
	}

	// fetch a description (line & column numbers) for where the error occurred
	std::string DescribeErrorLocation( const str_iterator & istart ) const
	{
		// simple line counter outside of the parser
		str_iterator istr{ m_LVFStart };
		unsigned line{ 1 };
		unsigned column{ 1 };

		for( ; istr < istart; ++istr )
			if( *istr == '\n' )
			{
				line += 1;
				column = 1;
			}
			else
				column += 1;

		return std::string{ "line:{" } + boost::lexical_cast<std::string>(line)
			+ "} col:{" + boost::lexical_cast<std::string>(column) + '}';
	}

public:
	ErrorHandlerContext( str_iterator lvf_start )
		: m_LVFStart{ lvf_start } {}

	// trace out error information
	void ExpectationPoint( const std::string & rule_name, const spirit::info & info, const str_iterator & istart, const str_iterator & iend ) const
	{
		const spirit::utf8_string info_text{ CollectSpiritInfo( info ) };
		const std::string location_desc{ DescribeErrorLocation( istart ) };
		const std::string location_text{ CollectTextAt( istart, iend ) };

		TraceError( e_Parser, "Unable to parse <%s>: at: %s text:{%s} expected: %s",
			rule_name.c_str(),
			location_desc.c_str(),
			location_text.c_str(),
			info_text.c_str()
		);
	}

	void UnexpectedText( const str_iterator & istart, const str_iterator & iend ) const
	{
		const std::string location_desc{ DescribeErrorLocation( istart ) };
		const std::string location_text{ CollectTextAt( istart, iend ) };

		TraceError( e_ParseUnexpectedText, "Unable to parse: at: %s text:{%s}",
			location_desc.c_str(),
			location_text.c_str()
		);
	}
};


// handler, called when expectation point error occurs
template<typename T_RULE, bool V_REPORT>
struct ExpectationPointErrorHandler
{
	using rule_t = T_RULE;
	using context_t = typename rule_t::context_type;
	using result_t = qi::error_handler_result;

	// name of the rule to which the error handler is attached
	std::string f_RuleName;

	// error detail helper
	const ErrorHandlerContext & f_ErrorContext;

	ExpectationPointErrorHandler( const rule_t rule, const ErrorHandlerContext & error_context )
		: f_RuleName{ rule.name() }, f_ErrorContext{ error_context } {}

	using params_t = boost::fusion::vector<
		// [0] first - points to the position in the input sequence before the rule is matched
		str_iterator &,

		// [1] last -  points to the last position in the input sequence
		const str_iterator &,

		// [2] at - points to the position in the input sequence following the last character that was consumed by the rule
		const str_iterator &,

		// [3] info
		const spirit::info & 
	>;

	// callback called when an error occurs
	void operator () ( const params_t & args, const context_t & cxt, const result_t & result ) const
	{
		// not all expectation points add value to the error report for the user
		if( !V_REPORT )
			return;

		// fetch the spirit::info from the args vector
		const spirit::info & info{ boost::fusion::at_c<3>( args ) };

		// fetch location of the fault
		const str_iterator & at{ boost::fusion::at_c<0>( args ) };
		const str_iterator & last{ boost::fusion::at_c<2>( args ) };

		// trace it all out
		f_ErrorContext.ExpectationPoint( f_RuleName, info, at, last );
	}
};


//
// Respond to an expectation point failure in a rule (i.e. a ">" parser
// operator fails). Set "report" to silent where reporting the error adds no
// value to the user report. Set "result" to fail where it is clear that
// the error can be ignored; otherwise set to rethrow - in particular, where
// a parent rule contains alternatives do not set to fail, as the parser
// 'eats' the fail and continues with the next alternative, which is very
// confusing to the user
//
constexpr bool Report{ true };
constexpr bool Silent{ false };
template<bool V_REPORT, qi::error_handler_result V_RESULT, typename T_RULE>
void SetRuleExpectationPointErrorHandler( T_RULE & rule, const ErrorHandlerContext & error_context )
{
	// create and associate an error handler with the rule
	qi::on_error<V_RESULT>( rule, ExpectationPointErrorHandler<T_RULE, V_REPORT>{ rule, error_context } );
}



/*-----------------------------------------------------------------------
 * AnalyseContext
 -----------------------------------------------------------------------*/

// context for initialisation operations; mainly, semantic analysis
struct AnalyseContext
{
	// field schema access
	const LogSchemaAccessor & f_LogSchema;
	unsigned f_FieldId{ 0 };

	// cached copy of the logfile's UTC datum
	const time_t f_UtcDatum;
	tm f_Datum;

	AnalyseContext( const LogSchemaAccessor & log_schema )
		: f_LogSchema{ log_schema }, f_UtcDatum{ log_schema.GetTimecodeBase().GetUtcDatum() }
	{
		// identify the reference (datum) date
		gmtime_s( &f_Datum, &f_UtcDatum );
	}

	FieldValueType GetFieldType( void ) const {
		return f_LogSchema.GetFieldType( f_FieldId );
	}
};



/*-----------------------------------------------------------------------
 * FilterContext
 -----------------------------------------------------------------------*/

// context for filter operations
struct FilterContext
{
	// the line to match/filter
	const LineAccessor & f_Line;
	const LineAdornmentsAccessor & f_Adornments;

	FilterContext( const LineAccessor & line, const LineAdornmentsAccessor & adornments )
		: f_Line{ line }, f_Adornments{ adornments } {}
};



/*-----------------------------------------------------------------------
 * AnalyseVisitor / FilterVisitor
 -----------------------------------------------------------------------*/

// visitors are needed to pass Setup/Control down to alternate child expressions
// (which Spirit.Qi captures as a boost::variant)

// initialise parsed object, and confirm semantic validity of the term
struct AnalyseVistor : public boost::static_visitor<void>
{
	const AnalyseContext & f_Context;
	AnalyseVistor( const AnalyseContext & context )
		: f_Context{ context } {}

	template<typename T>
	void operator() ( T & child ) const {
		child.Analyse( f_Context );
	}
};


// determine whether the supplied context is matched
struct FilterVisitor : public boost::static_visitor<bool>
{
	const FilterContext & f_Context;
	FilterVisitor( const FilterContext & context )
		: f_Context{ context } {}

	template<typename T>
	bool operator() ( const T & child ) const {
		return child.Filter( f_Context );
	}
};



/*-----------------------------------------------------------------------
 * A_FieldName
 -----------------------------------------------------------------------*/

// determine the target "object" for a field match
enum class E_FieldIdentifier : int
{
	// negative values are for non-field matches
	Annotation = -2,
	Log = -1

	// positive values field IDs are for standard fields
};


// parsed `field_name`
struct A_FieldName : public std::string
{
	template<typename T_RESULT>
	T_RESULT GetFieldId( const LogSchemaAccessor & log_schema ) const;

	static std::string & ToUpper( std::string & str ) {
		std::transform( str.begin(), str.end(), str.begin(),
			[] ( char ch ) -> char {
				return static_cast<char>(std::toupper( ch ));
			}
		);
		return str;
	}
};


template<typename T_RESULT>
T_RESULT A_FieldName::GetFieldId( const LogSchemaAccessor & log_schema ) const
{
	// case-insensitive matching in here
	const std::string & field_name{ *this };
	std::string match{ field_name };
	ToUpper( match );

	// look for field names matching field_name
	unsigned field_id{ 0 }, count{ 0 };
	const size_t num_fields{ log_schema.GetNumFields() };
	for( unsigned i = 0; i < num_fields; ++i )
	{
		const std::string name{ ToUpper( log_schema.GetFieldName( i ) ) };
		if( std::search( name.begin(), name.end(), match.begin(), match.end() ) != name.end() )
		{
			field_id = i;
			count += 1;
		}
	}

	if( count == 0 )
		ThrowSemanticError( e_FieldName, "Unrecognised field name:{%s}", field_name.c_str() );

	else if( count != 1 )
		ThrowSemanticError( e_MultipleField, "Name:{%s} matched multiple field names", field_name.c_str() );

	return static_cast<T_RESULT>( field_id );
}



/*-----------------------------------------------------------------------
 * A_TextValue
 -----------------------------------------------------------------------*/

// parsed `text_value` and fusion adapter (convert parsed attribute tuple into structure)
struct A_TextValue
{
	// map type characters to names
	enum E_Type : char
	{
		e_Literal = '"',
		e_RegularExpression = '/'
	};

	// map qualifier character to a name
	enum E_Qualifier : char
	{
		e_CaseInsensitive = 'i'
	};

	// the match type (literal or regular expression) (`quote` in the grammar)
	E_Type a_Quote{ e_Literal };

	// the text to use during matching
	std::string a_StringText;

	// the case sensitivity `qualifier`
	boost::optional<E_Qualifier> a_Qualifier;

	// the selector to implement the match; important: can't use unique_ptr
	// here as it is incompatible with boost::variant, giving very mysterious
	// compiler failures
	using selector_ptr_t = std::shared_ptr<Selector>;
	selector_ptr_t f_Selector;
	bool m_CaseInsensitive{ false };

	// initialise parsed object, and confirm semantic validity of the term
	void Analyse( const AnalyseContext & context );

	// determine whether the given context is matched
	bool Filter( const LineAccessor & line, const LineAdornmentsAccessor & adornments, E_FieldIdentifier field_id ) const;
};
BOOST_FUSION_ADAPT_STRUCT
(
	A_TextValue,
	a_Quote,
	a_StringText,
	a_Qualifier
)


// build a Selector according to the text_value's description
void A_TextValue::Analyse( const AnalyseContext & context )
{
	Match::Type type{ Match::e_Literal };
	switch( a_Quote )
	{
	case e_Literal:
		type = Match::e_Literal;
		break;

	case e_RegularExpression:
		type = Match::e_RegularExpression;
		break;
	}

	m_CaseInsensitive = a_Qualifier ? (* a_Qualifier == e_CaseInsensitive) : false;
	const Match descriptor{ type, a_StringText, !m_CaseInsensitive };
	f_Selector = selector_ptr_t{ Selector::MakeSelector( descriptor, false ) };
}


bool A_TextValue::Filter( const LineAccessor & line, const LineAdornmentsAccessor & adornments, E_FieldIdentifier field_id ) const
{
	const char * first{ nullptr }; const char * last{ nullptr };

	if( field_id == E_FieldIdentifier::Log )
		line.GetNonFieldText( &first, &last );

	else if( field_id == E_FieldIdentifier::Annotation)
		adornments.GetAnnotationText( &first, &last );
		
	else
	{
		const unsigned fid{ static_cast<unsigned>(field_id) };
		line.GetFieldText( fid, &first, &last );
	}

	if( first != nullptr && last != nullptr )
		return f_Selector->Hit( first, last );
	else
		return false;
}



/*-----------------------------------------------------------------------
 * A_TextMatchClause
 -----------------------------------------------------------------------*/

// parsed `text_match_clause`
struct A_TextMatchClause
{
	// attributes
	using identifier_t = boost::variant<
		E_FieldIdentifier,
		A_FieldName
	>;
	identifier_t a_TextIdentifier;
	A_TextValue a_TextValue;

	// deduced field ID from a_TextIdentifier
	E_FieldIdentifier f_FieldId;

	void Analyse( const AnalyseContext & context );
	bool Filter( const FilterContext & context ) const;
};
BOOST_FUSION_ADAPT_STRUCT
(
	A_TextMatchClause,
	a_TextIdentifier,
	a_TextValue
)


void A_TextMatchClause::Analyse( const AnalyseContext & context )
{
	// variant visitor to convert a_TextIdentifier to a field_id
	struct TextIdentifierVisitor : public boost::static_visitor<E_FieldIdentifier>
	{
		const AnalyseContext & f_Context;
		TextIdentifierVisitor( const AnalyseContext & context )
			: f_Context{ context } {}

		result_type operator() ( E_FieldIdentifier value ) const {
			return value;
		}

		result_type operator() ( const A_FieldName & value ) const {
			return value.GetFieldId<result_type>( f_Context.f_LogSchema );
		}
	};

	f_FieldId = boost::apply_visitor( TextIdentifierVisitor{ context }, a_TextIdentifier );

	a_TextValue.Analyse( context );
}


bool A_TextMatchClause::Filter( const FilterContext & context ) const
{
	return a_TextValue.Filter( context.f_Line, context.f_Adornments, f_FieldId );
}



/*-----------------------------------------------------------------------
 * A_Adornment
 -----------------------------------------------------------------------*/

enum class E_Adornment
{
	Annotation,
	Bookmark
};

struct A_Adornment
{
	E_Adornment a_Adornment;

	A_Adornment( E_Adornment  adornment = E_Adornment::Annotation )
		: a_Adornment{ adornment } {}

	void Analyse( const AnalyseContext & context ) {}

	bool Filter( const FilterContext & context ) const {
		switch( a_Adornment )
		{
		case E_Adornment::Annotation:
			return context.f_Adornments.IsAnnotated();

		case E_Adornment::Bookmark:
			return context.f_Adornments.IsBookMarked();
		}
		return false;
	}
};



/*-----------------------------------------------------------------------
 * A_Date
 -----------------------------------------------------------------------*/

//
// a date can be sumarised as:
//
//   part_1 sep part_2  [ sep part_3 ]
//
// where partn is interpreted as day, month or year per the current locale
//

// parsed `date`
struct A_Date
{
	int a_First;
	int a_Second;
	boost::optional<int> a_Third;

	static void UpdateTm( tm * tm, int day, int month, int year = 0 )
	{
		if( month < 1 || month > 12 )
			ThrowSemanticError( e_BadMonth, "Month value out of range:{%u} locale:{%s}", month, std::locale{}.name().c_str() );

		// ignores leap years
		static const int s_days[ 12 ]{ 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31 };
		if( day < 1 || day > s_days[month - 1] )
			ThrowSemanticError( e_BadDay, "Day value out of range:{%u} for month:{%u}", day, month );

		tm->tm_mday = day;
		tm->tm_mon = month - 1;

		if( year != 0 )
		{
			if( year < 70 )
				year += 2000;

			tm->tm_year = year - 1900;
		}
	}

	void GetValue2( tm * tm, std::time_base::dateorder order ) const
	{
		switch( order )
		{
		case std::time_base::dmy:
		case std::time_base::ydm:
			UpdateTm( tm, a_First, a_Second ); break;

		case std::time_base::mdy:
		case std::time_base::ymd:
			UpdateTm( tm, a_Second, a_First ); break;
		}
	}

	void GetValue3( tm * tm, std::time_base::dateorder order ) const
	{
		switch( order )
		{
		case std::time_base::dmy:
			UpdateTm( tm, a_First, a_Second, *a_Third ); break;

		case std::time_base::mdy:
			UpdateTm( tm, a_Second, a_First, *a_Third ); break;

		case std::time_base::ymd:
			UpdateTm( tm, *a_Third, a_Second, a_First ); break;

		case std::time_base::ydm:
			UpdateTm( tm, a_Second, *a_Third, a_First ); break;
		}
	}

	void GetValue( tm * tm ) const
	{
		std::locale locale;
		const std::time_base::dateorder order{
			std::use_facet<std::time_get<char>>( locale ).date_order()
		};

		if( order == std::time_base::no_order )
			ThrowSemanticError( e_Locale, "Unable to determine day/month/year order from locale:{%s}", locale.name().c_str() );

		if( a_Third )
			GetValue3( tm, order );
		else
			GetValue2( tm, order );
	}
};
BOOST_FUSION_ADAPT_STRUCT
(
	A_Date,
	a_First,
	a_Second,
	a_Third
)



/*-----------------------------------------------------------------------
 * A_Time
 -----------------------------------------------------------------------*/

// parsed `time`
struct A_StdTime
{
	unsigned a_Hours, a_Minutes, a_Seconds;

	void GetValue( tm * tm ) const {
		if( a_Hours >= 24 )
			ThrowSemanticError( e_BadHours, "Hours value out of range:{%u}", a_Hours );

		if( a_Minutes >= 60 )
			ThrowSemanticError( e_BadMinutes, "Minutes value out of range:{%u}", a_Minutes );

		if( a_Seconds >= 60 )
			ThrowSemanticError( e_BadSeconds, "Seconds value out of range:{%u}", a_Seconds );

		tm->tm_hour = a_Hours;
		tm->tm_min = a_Minutes;
		tm->tm_sec = a_Seconds;
	}
};
BOOST_FUSION_ADAPT_STRUCT
(
	A_StdTime,
	a_Hours,
	a_Minutes,
	a_Seconds
)


using A_FracTime = boost::optional<std::string>;
struct A_Time
{
	A_StdTime a_StdTime;
	A_FracTime a_NanoSeconds;

	uint32_t GetTimeFrac( void ) const {
		if( !a_NanoSeconds )
			return 0;

		// only accept 9 characters in the number
		const std::string & number{ *a_NanoSeconds };
		if( number.empty() || (number.size() > 9) )
			ThrowSemanticError( e_OversizedTimeFraction, "Oversized fraction:{%s}", number.c_str() );

		// convert the supplied value to nano-seconds
		uint32_t ns{ 0 };
		try
		{
			uint32_t scale{ 1 };
			size_t exponent{ 9 - number.size() };
			for( size_t i = 0; i < exponent; ++i )
				scale *= 10;

			const uint32_t raw_number{ boost::lexical_cast<uint32_t>(number) };
			ns = raw_number * scale;
		}
		catch( boost::bad_lexical_cast )
		{
			ThrowSemanticError( e_BadTimeFraction, "Invalid fraction:{%s}", number.c_str() );
		}
		return ns;
	}

	void GetValue( tm * tm, uint32_t * ns ) const {
		a_StdTime.GetValue( tm );
		*ns = GetTimeFrac();
	}


};
BOOST_FUSION_ADAPT_STRUCT
(
	A_Time,
	a_StdTime,
	a_NanoSeconds
)



/*-----------------------------------------------------------------------
 * A_DateTime
 -----------------------------------------------------------------------*/

// parsed `datetime`
using optional_date_t = boost::optional<A_Date>;
using optional_time_t = boost::optional<A_Time>;
struct A_DateTime : public boost::fusion::tuple<optional_date_t, optional_time_t>
{
	fieldvalue_t GetValue( const AnalyseContext & context ) const {

		// setup default time structure
		tm tm; tm.tm_wday = tm.tm_yday = tm.tm_isdst = 0;
		tm.tm_mday = context.f_Datum.tm_mday;
		tm.tm_mon = context.f_Datum.tm_mon;
		tm.tm_year = context.f_Datum.tm_year;
		tm.tm_sec = tm.tm_min = tm.tm_hour = 0;

		const optional_date_t & opt_date{ boost::fusion::at_c<0>( *this ) };
		if( opt_date )
			opt_date->GetValue( &tm );

		uint32_t ns{ 0 };
		const optional_time_t & opt_time{ boost::fusion::at_c<1>( *this ) };
		if( opt_time )
			opt_time->GetValue( &tm, &ns );

		const NTimecode timecode{ _mkgmtime( &tm ), ns };
		return timecode.CalcOffsetToDatum( context.f_UtcDatum );
	}
};



/*-----------------------------------------------------------------------
 * A_FieldValue
 -----------------------------------------------------------------------*/

// field value types
using fieldrange_t = std::pair<fieldvalue_t, fieldvalue_t>;
using fieldvalue_list_t = std::vector<fieldvalue_t>;
using fieldrange_list_t = std::vector<fieldrange_t>;


// parsed `field_value`
struct A_FieldValue
{
	// attribute
	using clause_t = boost::variant<
		fieldvalue_t,
		A_DateTime,
		A_TextValue
	>;
	clause_t a_FieldValue;

	// variant visitor to convert a_FieldValue into numeric form
	struct FieldValueVisitor : public boost::static_visitor<fieldvalue_list_t>
	{
		const AnalyseContext & f_Context;
		FieldValueVisitor( const AnalyseContext & context )
			: f_Context{ context } {}

		// numeric match
		result_type operator() ( const fieldvalue_t & value ) const {
			return fieldvalue_list_t{ value.Convert( f_Context.GetFieldType() ) };
		}

		// date/time match
		result_type operator() ( const A_DateTime & value ) const {
			return fieldvalue_list_t{ value.GetValue( f_Context ) };
		}

		// enumeration value match
		result_type operator() ( A_TextValue & value ) const {
			fieldvalue_list_t result;
			value.Analyse( f_Context );

			// find all enumeration values which match the `text_value`
			const LogSchemaAccessor & log_schema{ f_Context.f_LogSchema };
			const unsigned field_id{ f_Context.f_FieldId };
			const uint16_t enum_count{ log_schema.GetFieldEnumCount( field_id ) };

			// note - an enum_id of 0 is invalid; adjust the range accordingly
			bool found{ false };
			for( uint16_t enum_id = 1; enum_id < enum_count; ++enum_id )
			{
				const char * name_first{ log_schema.GetFieldEnumName( field_id, enum_id ) };
				const char * name_last{ name_first + strlen( name_first ) };
				if( value.f_Selector->Hit( name_first, name_last ) )
				{
					const uint64_t full_enum_id{ enum_id };
					result.emplace_back( full_enum_id );
					found = true;
				}
			}

			// its an error if no enumeration values were matched; re-purpose
			// the text value qualifier "case insensitive" to mean "ignore" - where
			// specified, invalid enum values are accepted
			const bool allow_invalid_enum{ value.m_CaseInsensitive };
			if( !found )
			{
				if( allow_invalid_enum )
					result.emplace_back( uint64_t{ 0 } );
				else
					ThrowSemanticError( e_EnumName, "Unrecognised enumeration value:{%s}", value.a_StringText.c_str() );
			}

			return result;
		}
	};

	// fetch the field's numeric value(s)
	fieldvalue_list_t AnalyseArray( const AnalyseContext & context ) {
		return boost::apply_visitor( FieldValueVisitor{ context }, a_FieldValue );
	}

	// fetch the field's single numeric value
	fieldvalue_t Analyse( const AnalyseContext & context ) {
		fieldvalue_list_t values{ AnalyseArray( context ) };
		if( values.size() != 1 )
		{
			ThrowSemanticError( e_MultipleEnum, "Name:{%s} matched multiple enumeration values",
				boost::get<A_TextValue>( a_FieldValue ).a_StringText.c_str()
			);
		}

		return values.front();
	}
};
BOOST_FUSION_ADAPT_STRUCT
(
	A_FieldValue,
	a_FieldValue
)


struct A_FieldUpperValue
{
	A_FieldValue a_FieldValue;

	fieldvalue_t Analyse( const AnalyseContext & context ) {
		return a_FieldValue.Analyse( context );
	}
};
BOOST_FUSION_ADAPT_STRUCT
(
	A_FieldUpperValue,
	a_FieldValue
)



/*-----------------------------------------------------------------------
 * A_FieldRangeItem
 -----------------------------------------------------------------------*/

// parsed `field_range_item`
struct A_FieldRangeItem
{
	// attributes
	boost::optional<char> a_Exclusion;
	A_FieldValue a_LowerBound;
	boost::optional<A_FieldUpperValue> a_UpperBound;

	void Analyse( const AnalyseContext & context, fieldvalue_list_t & inc_values, fieldrange_list_t & inc_ranges, fieldvalue_list_t & exc_values, fieldrange_list_t & exc_ranges );
};
BOOST_FUSION_ADAPT_STRUCT
(
	A_FieldRangeItem,
	a_Exclusion,
	a_LowerBound,
	a_UpperBound
)


// add the range item as a numeric test to one of our parent's test lists
void A_FieldRangeItem::Analyse( const AnalyseContext & context, fieldvalue_list_t & inc_values, fieldrange_list_t & inc_ranges, fieldvalue_list_t & exc_values, fieldrange_list_t & exc_ranges )
{
	// permit the lower bound to have multiple values - can occur where an enumeration
	// is described via a regular expression
	const bool exclusion{ a_Exclusion };
	const fieldvalue_list_t lower_bounds{ a_LowerBound.AnalyseArray( context ) };
	const bool is_enum_list{ lower_bounds.size() > 1 };
	const fieldvalue_t & lower_bound{ lower_bounds.front() };
	const bool is_range{ a_UpperBound };
	const fieldvalue_t upper_bound{ is_range ? a_UpperBound->Analyse( context ) : fieldvalue_t{} };

	if( is_range && is_enum_list )
		ThrowSemanticError( e_MultipleEnum, "Field range lower_bound matched more than one enumeration value" );

	fieldop_ptr_t gte{ MakeFieldOperation( E_FieldCompareOp::GtEq, context.GetFieldType() ) };
	if( is_range && gte->Compare( lower_bound, upper_bound ) )
	{
		ThrowSemanticError( e_MultipleEnum, "Field range lower_bound:{%s} not lower than upper_bound:{%s}",
			lower_bound.AsString().c_str(), upper_bound.AsString().c_str()
		);
	}

	if( is_enum_list )
		std::copy( lower_bounds.begin(), lower_bounds.end(), std::back_inserter( exclusion ? exc_values : inc_values ) );

	else
	{
		if( is_range )
			(exclusion ? exc_ranges : inc_ranges).push_back( fieldrange_t{ lower_bound, upper_bound } );
		else
			(exclusion ? exc_values : inc_values).push_back( lower_bound );
	}
}



/*-----------------------------------------------------------------------
 * A_FieldMatchClause
 -----------------------------------------------------------------------*/

// parsed `field_match_clause`
struct A_FieldMatchClause
{
	// attributes
	A_FieldName a_FieldName;
	std::vector<A_FieldRangeItem> a_FieldRange;

	// field_id corresponding to a_FieldName
	unsigned f_FieldId{ 0 };

	// separated "inclusive" and "exclusive" value and range tests
	fieldvalue_list_t f_IncValues, f_ExcValues;
	fieldrange_list_t f_IncRanges, f_ExcRanges;
	bool f_ImplicitIncludeMatch{ false };

	// comparison operations
	fieldop_ptr_t m_OpEq;
	fieldop_ptr_t m_OpLtEq;

	void Analyse( const AnalyseContext & context );
	bool Filter( const FilterContext & context ) const;
};
BOOST_FUSION_ADAPT_STRUCT
(
	A_FieldMatchClause,
	a_FieldName,
	a_FieldRange
)


void A_FieldMatchClause::Analyse( const AnalyseContext & context )
{
	f_FieldId = a_FieldName.GetFieldId<unsigned>( context.f_LogSchema );

	AnalyseContext cxt{ context };
	cxt.f_FieldId = f_FieldId;

	for( A_FieldRangeItem & item : a_FieldRange )
		item.Analyse( cxt, f_IncValues, f_IncRanges, f_ExcValues, f_ExcRanges );

	// special case - at least one `excluded_range`, but no `included_range` parts
	const size_t num_excludes{ f_ExcValues.size() + f_ExcRanges.size() };
	const size_t num_includes{ f_IncValues.size() + f_IncRanges.size() };
	f_ImplicitIncludeMatch = (num_excludes != 0) && (num_includes == 0);

	const FieldValueType type{ cxt.GetFieldType() };
	m_OpEq = MakeFieldOperation( E_FieldCompareOp::Eq, type );
	m_OpLtEq = MakeFieldOperation( E_FieldCompareOp::LtEq, type );
}


bool A_FieldMatchClause::Filter( const FilterContext & context ) const
{
	// the range is matched when any inclusive sub-range is matched
	// AND all exclusive sub-ranges fail to match (== no exclusive sub-ranges match)
	const fieldvalue_t value{ context.f_Line.GetFieldValue( f_FieldId ) };

	// process excludes first
	for( const fieldvalue_t & v : f_ExcValues )
		if( m_OpEq->Compare( value, v ) )
			return false;

	for( const fieldrange_t & r : f_ExcRanges )
		if( m_OpLtEq->Compare( r.first, value ) && m_OpLtEq->Compare( value, r.second ) )
			return false;

	// special case - at least one `excluded_range`, but no `included_range` parts
	if( f_ImplicitIncludeMatch )
		return true;

	// then the includes
	for( const fieldvalue_t & v : f_IncValues )
		if( m_OpEq->Compare( value, v ) )
			return true;

	for( const fieldrange_t & r : f_IncRanges )
		if( m_OpLtEq->Compare( r.first, value ) && m_OpLtEq->Compare( value, r.second ) )
			return true;

	// no includes, so no match
	return false;
}



/*-----------------------------------------------------------------------
 * A_FieldCompareClause
 -----------------------------------------------------------------------*/

// parsed `field_compare_clause`
struct A_FieldCompareClause
{
	// attributes
	A_FieldName a_FieldName;
	E_FieldCompareOp a_FieldCompareOp{ E_FieldCompareOp::Eq };
	A_FieldValue a_FieldValue;

	// field_id corresponding to a_FieldName
	unsigned f_FieldId{ 0 };

	// numeric field value decoded from a_FieldValue
	fieldvalue_t f_FieldValue;

	// comparison function
	fieldop_ptr_t f_FieldOp;

	void Analyse( const AnalyseContext & context );
	bool Filter( const FilterContext & context ) const;
};
BOOST_FUSION_ADAPT_STRUCT
(
	A_FieldCompareClause,
	a_FieldName,
	a_FieldCompareOp,
	a_FieldValue
)


void A_FieldCompareClause::Analyse( const AnalyseContext & context )
{
	f_FieldId = a_FieldName.GetFieldId<unsigned>( context.f_LogSchema );

	AnalyseContext cxt{ context };
	cxt.f_FieldId = f_FieldId;
	f_FieldValue = a_FieldValue.Analyse( cxt );
	f_FieldOp = MakeFieldOperation( a_FieldCompareOp, cxt.GetFieldType() );
}


bool A_FieldCompareClause::Filter( const FilterContext & context ) const
{
	const fieldvalue_t line_value{ context.f_Line.GetFieldValue( f_FieldId ) };
	return f_FieldOp->Compare( line_value, f_FieldValue );
}



/*-----------------------------------------------------------------------
 * A_MatchClause
 -----------------------------------------------------------------------*/

// parsed `match_clause`
struct A_MatchClause
{
	// attributes
	using clause_t = boost::variant<
		A_Adornment,
		A_TextMatchClause,
		A_FieldMatchClause,
		A_FieldCompareClause
	>;
	clause_t a_MatchClause;

	void Analyse( const AnalyseContext & context ) {
		boost::apply_visitor( AnalyseVistor{ context }, a_MatchClause );
	}

	bool Filter( const FilterContext & context ) const {
		return boost::apply_visitor( FilterVisitor{ context }, a_MatchClause );
	}
};
BOOST_FUSION_ADAPT_STRUCT
(
	A_MatchClause,
	a_MatchClause
)



/*-----------------------------------------------------------------------
 * A_PrimaryExpr
 -----------------------------------------------------------------------*/

// parsed `primary_expr`
struct A_PrimaryExpr
{
	// attribute
	using primaryexpr_t = boost::variant<
		A_MatchClause,
		boost::recursive_wrapper<A_LogicalOrExpr>
	>;
	primaryexpr_t a_PrimaryExpr;

	void Analyse( const AnalyseContext & context );
	bool Filter( const FilterContext & context ) const;
};
BOOST_FUSION_ADAPT_STRUCT(
	A_PrimaryExpr,
	a_PrimaryExpr
)



/*-----------------------------------------------------------------------
 * A_LogicalNotOp
 -----------------------------------------------------------------------*/

 // known unary operators
enum class E_UnaryOp
{
	None,
	Not
};


// parsed `logical_not_expr`
struct A_LogicalNotExpr
{
	// attributes
	boost::optional<E_UnaryOp> a_LogicalNotOp;
	A_PrimaryExpr a_PrimaryExpr;

	void Analyse( const AnalyseContext & context );
	bool Filter( const FilterContext & context ) const;
};
BOOST_FUSION_ADAPT_STRUCT(
	A_LogicalNotExpr,
	a_LogicalNotOp,
	a_PrimaryExpr
)


void A_LogicalNotExpr::Analyse( const AnalyseContext & context )
{
	return a_PrimaryExpr.Analyse( context );
}


bool A_LogicalNotExpr::Filter( const FilterContext & context ) const
{
	bool filter{ a_PrimaryExpr.Filter( context ) };

	switch( a_LogicalNotOp.value_or( E_UnaryOp::None ) )
	{
	case E_UnaryOp::Not:
		filter = !filter;
	}

	return filter;
}



/*-----------------------------------------------------------------------
 * A_LogicalAndExpr
 -----------------------------------------------------------------------*/

 // parsed `logical_and_expr`; note the use of a data member and BOOST_FUSION_ADAPT_STRUCT
// fails with compile errors about absense of A_LogicalAndExpr::value_type, so use
// inheritance instead
struct A_LogicalAndExpr : public std::vector<A_LogicalNotExpr>
{
	void Analyse( const AnalyseContext & context );
	bool Filter( const FilterContext & context ) const;
};


void A_LogicalAndExpr::Analyse( const AnalyseContext & context )
{
	for( A_LogicalNotExpr & expr : *this )
		expr.Analyse( context );
}


bool A_LogicalAndExpr::Filter( const FilterContext & context ) const
{
	bool filter{ true };

	for( const A_LogicalNotExpr & expr : *this )
	{
		filter = expr.Filter( context ) && filter;
		if( !filter )
			break;
	}

	return filter;
}



/*-----------------------------------------------------------------------
 * A_LogicalOrExpr
 -----------------------------------------------------------------------*/

 // parsed `logical_or_expr`
struct A_LogicalOrExpr : public std::vector<A_LogicalAndExpr>
{
	void Analyse( const AnalyseContext & context );
	bool Filter( const FilterContext & context ) const;
};


void A_LogicalOrExpr::Analyse( const AnalyseContext & context )
{
	for( A_LogicalAndExpr & expr : *this )
		expr.Analyse( context );
}


bool A_LogicalOrExpr::Filter( const FilterContext & context ) const
{
	bool match{ false };

	for( const A_LogicalAndExpr & expr : *this )
	{
		match = expr.Filter( context ) || match;
		if( match )
			break;
	}

	return match;
}


void A_PrimaryExpr::Analyse( const AnalyseContext & context )
{
	return boost::apply_visitor( AnalyseVistor{ context }, a_PrimaryExpr );
}


bool A_PrimaryExpr::Filter( const FilterContext & context ) const
{
	return boost::apply_visitor( FilterVisitor{ context }, a_PrimaryExpr );
}



/*-----------------------------------------------------------------------
 * P_FieldNameGrammar
 -----------------------------------------------------------------------*/

// grammar to parse an identifier
struct P_FieldNameGrammar : P_GrammarNoSkip<A_FieldName(void)>
{
	// parse rule
	P_RuleNoSkip<A_FieldName(void)> r_FieldName{ std::string{ "field-name" } };

	P_FieldNameGrammar( void )
		: P_FieldNameGrammar::base_type{ r_FieldName }
	{
		const char * first{ "_a-zA-Z" };
		const char * other{ "_a-zA-Z0-9" };

		r_FieldName %=
		(
			ascii::char_( first )
			> * ascii::char_( other )
		);
	}
};



/*-----------------------------------------------------------------------
 * P_TextValueGrammar
 -----------------------------------------------------------------------*/

// grammar to parse a `text_value`
struct P_TextValueGrammar : P_Grammar<A_TextValue(void)>
{
	// parse rules
	P_RuleNoSkip<A_TextValue(void), qi::locals<char>> r_PlainString{ std::string{ "plain-string" } };
	P_RuleNoSkip<A_TextValue(void), qi::locals<char, std::string>> r_RawString{ std::string{ "raw-string" } };
	P_RuleNoSkip<std::string(void)> r_RawDelimiter{ std::string{ "raw-delimiter" } };
	P_Rule<A_TextValue(void)> r_TextValue{ std::string{ "text-value" } };

	P_TextValueGrammar( const ErrorHandlerContext & error_context )
		: P_TextValueGrammar::base_type{ r_TextValue }
	{
		using namespace qi::labels;

		const char quote_chars[]{ A_TextValue::e_Literal, A_TextValue::e_RegularExpression, '\0' };
		const char qualifier_char{ 'i' };

		r_PlainString %=
		(
			// capture the opening `quote` character to the local attribute
			ascii::char_( quote_chars )
				[ _a = _1 ]

			// the `string_text` cannot include the `quote` character
			> + ( ascii::char_ - ascii::char_( _a ) )

			// and the closing `quote` must be the same as the opening one
			> qi::lit( _a )

			// any case-sensitivity qualifier
			> - ascii::char_( qualifier_char )
		);
		SetRuleExpectationPointErrorHandler<Report, qi::rethrow>( r_PlainString, error_context );

		r_RawDelimiter %=
			* ( ascii::char_ - ascii::char_( '(' ) );

		r_RawString %=
		(
			qi::lit( 'r' )

			// capture the opening `quote` character to local attribute
			> ascii::char_( quote_chars )
				[ _a = _1 ]

			// capture any user supplied `delimiter` to a local attribute
			// prefix the delimiter with the required ")" character so that _b
			// is the entire string to be matched at the string's "tail"
			// the omit[] prevents the delimiter being added to the A_TextValue
			// attribute
			> qi::omit
			[
				r_RawDelimiter
					[ _b = std::string{ ')' } + _1 ]
			]

			> qi::lit( '(' )

			// the `string_text` is *anything* except the raw string's "tail"
			> + ( ascii::char_ - qi::lit( _b ) )

			> qi::lit( _b )

			// and the closing `quote` must be the same as the opening one
			> qi::lit( _a )

			// any case-senitivity qualifier
			> - ascii::char_( qualifier_char )
		);
		SetRuleExpectationPointErrorHandler<Report, qi::rethrow>( r_RawString, error_context );

		r_TextValue %=
		(
			r_PlainString
			| r_RawString
		);
		SetRuleExpectationPointErrorHandler<Silent, qi::fail>( r_TextValue, error_context );
	}
};



/*-----------------------------------------------------------------------
 * P_TextMatchClauseGrammar
 -----------------------------------------------------------------------*/

// grammar to parse a `text_match_clause`
struct P_TextMatchClauseGrammar : P_Grammar<A_TextMatchClause(void)>
{
	// symbol table
	struct P_TextIdentifierSymbol : qi::symbols<char, E_FieldIdentifier>
	{
		P_TextIdentifierSymbol( void )
		{
			add( "log", E_FieldIdentifier::Log );
			add( "anno", E_FieldIdentifier::Annotation );
			add( "annotation", E_FieldIdentifier::Annotation );
		}
	} r_TextIdentifierSymbol;

	// parse rule
	P_Rule<A_TextMatchClause(void)> r_TextMatchClause{ std::string{ "text-match-clause" } };

	// sub-grammars
	P_FieldNameGrammar r_FieldName;
	P_TextValueGrammar r_TextValue;

	P_TextMatchClauseGrammar( const ErrorHandlerContext & error_context )
		:
		P_TextMatchClauseGrammar::base_type{ r_TextMatchClause },
		r_TextValue{ error_context }
	{
		r_TextMatchClause %=
		(
			// identify the match clause's target - i.e. log text or annotation text
			( r_TextIdentifierSymbol | r_FieldName )

			// fixed operator value
			>> qi::lit( "~=" )

			// the text to match with
			> r_TextValue
		);
		SetRuleExpectationPointErrorHandler<Report, qi::rethrow>( r_TextMatchClause, error_context );
	}
};



/*-----------------------------------------------------------------------
 * P_DateTimeGrammar
 -----------------------------------------------------------------------*/

// grammar to parse a `datetime`
struct P_DateTimeGrammar : P_Grammar<A_DateTime( void )>
{
	// parse rules; had to split time into several rules in order to
	// get the attribute handling to work (simplistic approaches looses
	// the optional date/time parts)
	P_RuleNoSkip<int(void)> r_DatePart{ std::string{ "date-part" } };
	P_RuleNoSkip<A_Date(void)> r_Date{ std::string{ "date" } };
	P_RuleNoSkip<A_StdTime(void)> r_StdTime{ std::string{ "std-time" } };
	P_RuleNoSkip<A_FracTime(void)> r_FracTime{ std::string{ "frac-time" } };
	P_RuleNoSkip<A_Time(void)> r_Time{ std::string{ "time" } };
	P_Rule<A_DateTime(void)> r_DateTime{ std::string{ "datetime" } };

	P_DateTimeGrammar( const ErrorHandlerContext & error_context )
		:
		P_DateTimeGrammar::base_type{ r_DateTime }
	{
		using namespace qi::labels;

		// for compatibility with struct tm fields; parse unsigned numbers into
		// a signed integer
		qi::uint_parser<int, 10> uint_parser;

		// parse the fractional seconds as a string, as we need to know how
		// many numerals are present, as well as the overall numeric value
		const char * numbers{ "0-9" };

		r_DatePart %=
			qi::lit( '/' ) > uint_parser
			;
		SetRuleExpectationPointErrorHandler<Report, qi::rethrow>( r_DatePart, error_context );

		r_Date %=
			uint_parser
			>> r_DatePart
			>> - r_DatePart
		;
		SetRuleExpectationPointErrorHandler<Report, qi::rethrow>( r_Date, error_context );

		r_StdTime %=
			uint_parser
			>> qi::lit( ':' ) > uint_parser
			> qi::lit( ':' ) > uint_parser
		;
		SetRuleExpectationPointErrorHandler<Report, qi::rethrow>( r_StdTime, error_context );

		r_FracTime %=
			qi::lit( '.' ) > +ascii::char_( numbers )
		;
		SetRuleExpectationPointErrorHandler<Report, qi::rethrow>( r_FracTime, error_context );

		r_Time %=
			r_StdTime
			>> - r_FracTime
		;
		SetRuleExpectationPointErrorHandler<Silent, qi::rethrow>( r_Time, error_context );

		r_DateTime =
			r_Date || r_Time;
		SetRuleExpectationPointErrorHandler<Silent, qi::rethrow>( r_DateTime, error_context );
	}
};



/*-----------------------------------------------------------------------
 * P_FieldValueGrammar
 -----------------------------------------------------------------------*/

// real number parser policies
template <typename T_VALUE>
struct real_policies : qi::real_policies<T_VALUE>
{
	// insist on a period - numbers without periods should be parsed as integers
	static const bool expect_dot = true;

	// disallow trailing period - disambiguates "10..12", which is a range expression
	static const bool allow_trailing_dot = false;
};


// grammar to parse a `field_value`
struct P_FieldValueGrammar : P_Grammar<A_FieldValue(void)>
{
	// parse rules
	P_RuleNoSkip<fieldvalue_t(void)> r_HexNumber{ std::string{ "hex-number" } };
	P_RuleNoSkip<fieldvalue_t(void)> r_RealNumber{ std::string{ "real-number" } };
	P_RuleNoSkip<fieldvalue_t(void)> r_DecNumber{ std::string{ "dec-number" } };
	P_Rule<A_FieldValue(void)> r_FieldValue{ std::string{ "field-value" } };

	// sub-grammars
	P_TextValueGrammar r_TextValue;
	P_DateTimeGrammar r_DateTime;

	P_FieldValueGrammar( const ErrorHandlerContext & error_context )
		:
		P_FieldValueGrammar::base_type{ r_FieldValue },
		r_TextValue{ error_context },
		r_DateTime{ error_context }
	{
		r_HexNumber %=
		(
			qi::lit( "0x" )
			> qi::uint_parser<uint64_t, 16>{}
		);
		SetRuleExpectationPointErrorHandler<Report, qi::rethrow>( r_HexNumber, error_context );

		r_RealNumber %=
			qi::real_parser<double, real_policies<double>>{};

		r_DecNumber %=
			qi::int_parser<int64_t>{};

		r_FieldValue %=
			r_DateTime
			| r_HexNumber
			| r_RealNumber
			| r_DecNumber
			| r_TextValue;
		SetRuleExpectationPointErrorHandler<Silent, qi::rethrow>( r_FieldValue, error_context );
	}
};



/*-----------------------------------------------------------------------
 * P_FieldMatchClauseGrammar
 -----------------------------------------------------------------------*/

// grammar to parse a `field_match_clause`
struct P_FieldMatchClauseGrammar : P_Grammar<A_FieldMatchClause(void)>
{
	// parse rules
	P_Rule<A_FieldUpperValue(void)> r_FieldRangeUpper{ std::string{ "field-range-upper" } };
	P_Rule<A_FieldRangeItem(void)> r_FieldRangeItem{ std::string{ "field-range-item" } };
	P_Rule<A_FieldMatchClause(void)> r_FieldMatchClause{ std::string{ "field-match-clause" } };

	// sub-grammars
	P_FieldNameGrammar r_FieldName;
	P_FieldValueGrammar r_FieldValue;

	P_FieldMatchClauseGrammar( const ErrorHandlerContext & error_context )
		:
		P_FieldMatchClauseGrammar::base_type{ r_FieldMatchClause },
		r_FieldValue{ error_context }
	{
		// the r_FieldRangeUpper rule and encapsulating A_FieldUpperValue type
		// are both needed to make this work; switching the rule attribute type to 
		// A_FieldValue causes impenetrable compile failures (which makes no sense)
		r_FieldRangeUpper %=
		(
			qi::lit( ".." )
			> r_FieldValue
		);
		SetRuleExpectationPointErrorHandler<Report, qi::fail>( r_FieldRangeUpper, error_context );

		r_FieldRangeItem %=
		(
			// optional exclusion character
			- ascii::char_( '^' )

			// lower bound
			>> r_FieldValue

			// optional upper bound
			>> - r_FieldRangeUpper
		);

		r_FieldMatchClause %=
		(
			r_FieldName

			>> qi::lit( "in" )

			> qi::lit( '[' )

			> r_FieldRangeItem % ascii::char_( ',' )

			> qi::lit( ']' )
		);
		SetRuleExpectationPointErrorHandler<Report, qi::rethrow>( r_FieldMatchClause, error_context );
	}
};



/*-----------------------------------------------------------------------
 * P_FieldCompareClauseGrammar
 -----------------------------------------------------------------------*/

// grammar to parse a `field_compare_clause`
struct P_FieldCompareClauseGrammar : P_Grammar<A_FieldCompareClause(void)>
{
	// symbol table
	struct P_FieldCompareOpSymbol : qi::symbols<char, E_FieldCompareOp>
	{
		P_FieldCompareOpSymbol( void )
		{
			add( "=", E_FieldCompareOp::Eq );
			add( "==", E_FieldCompareOp::Eq );
			add( "<", E_FieldCompareOp::Lt );
			add( "<=", E_FieldCompareOp::LtEq );
			add( ">", E_FieldCompareOp::Gt );
			add( ">=", E_FieldCompareOp::GtEq );
			add( "!=", E_FieldCompareOp::Ne );
		}
	} r_FieldCompareOp;

	// parse rules
	P_Rule<A_FieldCompareClause(void)> r_FieldCompareClause{ std::string{ "field-compare-clause" } };

	// sub-grammars
	P_FieldNameGrammar r_FieldName;
	P_FieldValueGrammar r_FieldValue;

	P_FieldCompareClauseGrammar( const ErrorHandlerContext & error_context )
		:
		P_FieldCompareClauseGrammar::base_type{ r_FieldCompareClause },
		r_FieldValue{ error_context }
	{
		using namespace qi::labels;

		// using the auto-generated attribute assignments (i.e. %=) here results
		// in the comparison operator being appended to the identifier - unclear
		// why, but resorting to manual attribute assignments to force order
		r_FieldCompareClause =
		(
			r_FieldName
				[ phoenix::at_c<0>( _val ) = _1 ]

			>> r_FieldCompareOp
				[ phoenix::at_c<1>( _val ) = _1 ]

			> r_FieldValue
				[ phoenix::at_c<2>( _val ) = _1 ]
		);
		SetRuleExpectationPointErrorHandler<Report, qi::rethrow>( r_FieldCompareClause, error_context );
	}
};



/*-----------------------------------------------------------------------
 * P_MatchClauseGrammar
 -----------------------------------------------------------------------*/

// grammar to parse a `match_clause`
struct P_MatchClauseGrammar : P_Grammar<A_MatchClause(void)>
{
	// parse rules
	P_Rule<A_MatchClause(void)> r_MatchClause{ std::string{ "match-clause" } };

	// symbol table
	struct P_AdornmentSymbol : qi::symbols<char, A_Adornment>
	{
		P_AdornmentSymbol( void )
		{
			add( "annotated", E_Adornment::Annotation );
			add( "bookmarked", E_Adornment::Bookmark );
		}
	} r_AdornmentSymbol;

	// sub-grammars
	P_TextMatchClauseGrammar r_TextMatchClause;
	P_FieldMatchClauseGrammar r_FieldMatchClause;
	P_FieldCompareClauseGrammar r_FieldCompareClause;

	P_MatchClauseGrammar( const ErrorHandlerContext & error_context )
		:
		P_MatchClauseGrammar::base_type{ r_MatchClause },
		r_TextMatchClause{ error_context },
		r_FieldMatchClause{ error_context },
		r_FieldCompareClause{ error_context }
	{
		r_MatchClause %=
		(
			r_AdornmentSymbol
			| r_TextMatchClause
			| r_FieldMatchClause
			| r_FieldCompareClause
		);
		SetRuleExpectationPointErrorHandler<Silent, qi::rethrow>( r_MatchClause, error_context );
	}
};



/*-----------------------------------------------------------------------
 * P_LogicalOrExprGrammar
 -----------------------------------------------------------------------*/

// grammar to parse a `logical_or_expr`
struct P_LogicalOrExprGrammar : P_Grammar<A_LogicalOrExpr(void)>
{
	// symbol tables
	struct P_LogicalNotOpSymbol : qi::symbols<char, E_UnaryOp>
	{
		P_LogicalNotOpSymbol( void )
		{
			add( "!", E_UnaryOp::Not );
			add( "not", E_UnaryOp::Not );
		}
	} r_LogicalNotOp;

	struct P_LogicalAndOpSymbol : qi::symbols<char>
	{
		P_LogicalAndOpSymbol( void )
		{
			add( "&&" );
			add( "and" );
		}
	} r_LogicalAndOp;

	struct P_LogicalOrOpSymbol : qi::symbols<char>
	{
		P_LogicalOrOpSymbol( void )
		{
			add( "||" );
			add( "or" );
		}
	} r_LogicalOrOp;

	// parse rules
	P_Rule<A_PrimaryExpr(void)> r_PrimaryExpr{ std::string{ "primary-expr" } };
	P_Rule<A_LogicalNotExpr(void)> r_LogicalNotExpr{ std::string{ "logical-not-expr" } };
	P_Rule<A_LogicalAndExpr(void)> r_LogicalAndExpr{ std::string{ "logical-and-expr" } };
	P_Rule<A_LogicalOrExpr(void)> r_LogicalOrExpr{ std::string{ "logical-or-expr" } };

	// sub-grammars
	P_MatchClauseGrammar r_MatchClause;

	P_LogicalOrExprGrammar( const ErrorHandlerContext & error_context )
		:
		P_LogicalOrExprGrammar::base_type{ r_LogicalOrExpr },
		r_MatchClause{ error_context }
	{
		r_PrimaryExpr %=
			r_MatchClause
			| (qi::lit( '(' ) > r_LogicalOrExpr > qi::lit( ')' ))
		;
		SetRuleExpectationPointErrorHandler<Report, qi::fail>( r_PrimaryExpr, error_context );

		r_LogicalNotExpr %=
			- r_LogicalNotOp
			>> r_PrimaryExpr
		;

		r_LogicalAndExpr %=
			r_LogicalNotExpr % r_LogicalAndOp
		;

		r_LogicalOrExpr %=
			r_LogicalAndExpr % r_LogicalOrOp
		;
	}
};



/*-----------------------------------------------------------------------
 * LVF
 -----------------------------------------------------------------------*/

 // filter language implementation; provides parsing and matching support
class LVF
{
private:
	A_LogicalOrExpr m_SyntaxTree;

public:
	LVF( const std::string & definition, const LogSchemaAccessor & log_schema );
	bool Filter( const LineAccessor & line, const LineAdornmentsAccessor & adornments ) const;
};


// parse the query definition into an expression tree
LVF::LVF( const std::string & definition, const LogSchemaAccessor & log_schema )
{
	ErrorHandlerContext error_context{ definition.begin() };
	P_LogicalOrExprGrammar grammar{ error_context };

	str_iterator begin{ definition.begin() }, end{ definition.end() };
	const bool ret{ qi::phrase_parse( begin, end, grammar, ascii::space, m_SyntaxTree ) };

	if( !ret )
		throw std::runtime_error{ "Unable to parse LVF definition" };

	if( begin != end )
	{
		error_context.UnexpectedText( begin, end );
		throw std::runtime_error{ "Unable to parse trailing text" };
	}

	AnalyseContext context{ log_schema };
	m_SyntaxTree.Analyse( context );
}


// determine whether the supplied text is matched by the query
bool LVF::Filter( const LineAccessor & line, const LineAdornmentsAccessor & adornments ) const
{
	FilterContext context{ line, adornments };
	return m_SyntaxTree.Filter( context );
}



/*-----------------------------------------------------------------------
 * SelectorLogviewFilter
 -----------------------------------------------------------------------*/

SelectorLogviewFilter::SelectorLogviewFilter( const Match & match, const LogSchemaAccessor & log_schema )
	:
	Selector{ match },
	m_Parser{ std::make_unique<LVF>(match.m_Text, log_schema ) }
{
}


bool SelectorLogviewFilter::Hit( const LineAccessor & line, const LineAdornmentsAccessor & adornments ) const
{
	return m_Parser->Filter( line, adornments );
}

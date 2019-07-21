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

// C++ includes
#include <cctype>

// Nlog includes
#include "LogAccessor.h"

// Application includes
#include "Match.h"
#include "Parser.h"



/*-----------------------------------------------------------------------
 * Selector
 -----------------------------------------------------------------------*/

bool Selector::Hit( const char *, const char * ) const
{
	throw std::logic_error{ "Nlog: Selector line hit invalid in this context" };
	return false;
}


bool Selector::Hit( const LineAccessor & line ) const
{
	const char * first{ nullptr }; const char * last{ nullptr };
	line.GetText( &first, &last );
	return Hit( first, last );
}


bool Selector::Hit( const LineAccessor & line, const LineAdornmentsAccessor & ) const
{
	const char * first{ nullptr }; const char * last{ nullptr };
	line.GetText( &first, &last );
	return Hit( first, last );
}



/*-----------------------------------------------------------------------
 * MatchLiteral
 -----------------------------------------------------------------------*/

 // support for identifying line parts which match a literal textual description
class MatchLiteral : public Selector
{
private:
	static bool CompareCharCase( char lhs, char rhs ) {
		return lhs == rhs;
	}

	static bool CompareCharNoCase( char lhs, char rhs ) {
		return std::toupper( lhs ) == std::toupper( rhs );
	}

	// call visitor for each line part matched by the literal expression
	template<typename T_PRED>
	void Visit( const char *first, const char *last, Visitor & visitor, T_PRED p )
	{
		const std::string & m_Literal{ m_Match.m_Text };
		const size_t lit_size{ m_Literal.size() };
		const char * at{ first }, * found{ nullptr };
		while( (found = std::search( at, last, m_Literal.begin(), m_Literal.end(), p )) != last )
		{
			visitor.Action( found, lit_size );
			at = found + lit_size;
		}
	}

public:
	MatchLiteral( const Match & match )
		: Selector{ match } {}

	bool Hit( const char *first, const char *last ) const override;
	void Visit( const char *first, const char *last, Visitor & visitor ) override;
};



bool MatchLiteral::Hit( const char *first, const char *last ) const
{
	const std::string & m_Literal{ m_Match.m_Text };
	bool res = false;

	if( m_Match.m_Case )
		res = std::search( first, last, m_Literal.begin(), m_Literal.end() ) != last;

	else
		res = std::search( first, last, m_Literal.begin(), m_Literal.end(), CompareCharNoCase ) != last;

	return res;
}


void MatchLiteral::Visit( const char *first, const char *last, Visitor & visitor )
{
	if( m_Match.m_Case )
		Visit( first, last, visitor, CompareCharCase );

	else
		Visit( first, last, visitor, CompareCharNoCase );
}



/*-----------------------------------------------------------------------
 * MatchRegularExpression
 -----------------------------------------------------------------------*/

 // support for identifying line parts which match a regular expression
class MatchRegularExpression : public Selector
{
private:
	std::regex m_Regex;

public:
	MatchRegularExpression( const Match & match );
	bool Hit( const char *first, const char *last ) const override;
	void Visit( const char *first, const char *last, Visitor & visitor ) override;
};


MatchRegularExpression::MatchRegularExpression( const Match & match )
	: Selector{ match }
{
	std::regex_constants::syntax_option_type flags{
		std::regex_constants::ECMAScript
		| std::regex_constants::optimize
	};

	if( !m_Match.m_Case )
		flags |= std::regex_constants::icase;

	m_Regex = std::regex{ m_Match.m_Text, flags };
}


bool MatchRegularExpression::Hit( const char *first, const char *last ) const
{
	std::cmatch match;
	return std::regex_search( first, last, match, m_Regex );
}


// call visitor for each line part matched by the regular expression
void MatchRegularExpression::Visit( const char *first, const char *last, Visitor & visitor )
{
	std::cmatch match;
	const char *at{ first };

	while( std::regex_search( at, last, match, m_Regex ) )
	{
		const char *found{ match[ 0 ].first };
		at = match[ 0 ].second;
		visitor.Action( found, at - found );
	}
}



/*-----------------------------------------------------------------------
 * SelectUnconditional
 -----------------------------------------------------------------------*/

// unconditional selection
class SelectUnconditional : public Selector
{
private:
	const bool m_Value;

public:
	SelectUnconditional( const Match & match, bool value )
		: Selector{ match }, m_Value{ value } {}

	bool Hit( const char * /* first */, const char * /* last */ ) const override {
		return m_Value;
	}

	bool Hit( const LineAccessor & /* line */, const LineAdornmentsAccessor & /* adornments */ ) const override {
		return m_Value;
	}
};



/*-----------------------------------------------------------------------
 * Selector
 -----------------------------------------------------------------------*/

selector_ptr_t Selector::MakeSelector( const Match & match, bool empty_selects_all, const LogSchemaAccessor * schema )
{
	try {
		if( match.m_Text.empty() )
			return std::make_unique<SelectUnconditional>( match, empty_selects_all );

		switch( match.m_Type )
		{
		case Match::e_Literal:
			return std::make_unique<MatchLiteral>( match );

		case Match::e_RegularExpression:
			return std::make_unique<MatchRegularExpression>( match );

		case Match::e_LogviewFilter:
			if( schema == nullptr )
				throw std::exception( "Nlog: Logfile schema missing" );
			return std::make_unique<SelectorLogviewFilter>( match, *schema );
		}
	}
	catch( const std::exception & ex )
	{
		TraceError( e_SelectorCreate, "%s", ex.what() );
	}

	return nullptr;
}

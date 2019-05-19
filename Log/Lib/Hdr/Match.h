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

// C++ includes
#include <string>



/*-----------------------------------------------------------------------
 * LineAdornmentsProvider
 -----------------------------------------------------------------------*/

struct LineAdornmentsProvider
{
	virtual bool IsBookMarked( int line_no ) const = 0;
	virtual bool IsAnnotated( int line_no ) const = 0;
	virtual void GetAnnotationText( int line_no, const char ** first, const char ** last ) const = 0;
};



/*-----------------------------------------------------------------------
 * LineAdornmentsAccessor
 -----------------------------------------------------------------------*/

class LineAdornmentsAccessor
{
private:
	const LineAdornmentsProvider * m_AdornmentsProvider{ nullptr };
	int m_LogLineNo{ 0 };

public:
	LineAdornmentsAccessor( const LineAdornmentsProvider * provider, int log_line_no )
		: m_AdornmentsProvider{ provider }, m_LogLineNo{ log_line_no } {}

	bool IsBookMarked( void ) const {
		return m_AdornmentsProvider->IsBookMarked( m_LogLineNo );
	}

	bool IsAnnotated( void ) const {
		return m_AdornmentsProvider->IsAnnotated( m_LogLineNo );
	}

	void GetAnnotationText( const char ** first, const char ** last ) const  {
		m_AdornmentsProvider->GetAnnotationText( m_LogLineNo, first, last );
	}
};



/*-----------------------------------------------------------------------
 * Match
 -----------------------------------------------------------------------*/

struct Match
{
	// types of selector exposed to Python
	enum Type
	{
		e_Literal,
		e_RegularExpression,
		e_LogviewFilter,
	} m_Type;

	std::string m_Text;
	bool m_Case;

	Match( Type type, const std::string & text, bool cs )
		: m_Type{ type }, m_Text{ text }, m_Case{ cs } {}

	Match( const Match & match )
		: m_Type{ match.m_Type }, m_Text{ match.m_Text }, m_Case{ match.m_Case } {}
};



/*-----------------------------------------------------------------------
 * Selector
 -----------------------------------------------------------------------*/

// forwards
struct LineAccessor;
struct LogSchemaAccessor;

// general interface for identifying lines which match a criterion
struct Selector
{
	const Match m_Match;

	Selector( const Match & match )
		: m_Match{ match } {}

	virtual ~Selector( void ) {}

	virtual bool Hit( const char * first, const char * last ) const;
	virtual bool Hit( const LineAccessor & line ) const;
	virtual bool Hit( const LineAccessor & line, const LineAdornmentsAccessor & adornments ) const;

	struct Visitor
	{
		virtual void Action( const char * found, size_t length ) = 0;
	};
	virtual void Visit( const char *first, const char *last, Visitor & visitor )
	{
		return;
	}

	// factory
	static Selector * MakeSelector( const Match & match, bool empty_selects_all, const LogSchemaAccessor * schema = nullptr );
};

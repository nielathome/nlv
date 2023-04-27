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
#include <memory>



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
	bool m_HasDataPartition;
	int m_DataPartition;

	Match( Type type, const std::string & text, bool cs, bool has_data_partition = false, int data_partition = 0 )
		:
		m_Type{ type },
		m_Text{ text },
		m_Case{ cs },
		m_HasDataPartition{ has_data_partition },
		m_DataPartition{ data_partition }
	{}

	Match( const Match & match )
		:
		m_Type{ match.m_Type },
		m_Text{ match.m_Text },
		m_Case{ match.m_Case },
		m_HasDataPartition{ match.m_HasDataPartition },
		m_DataPartition{ match.m_DataPartition }
	{}
};



/*-----------------------------------------------------------------------
 * Selector
 -----------------------------------------------------------------------*/

// forwards
struct Selector;
struct LineAccessor;
struct LogSchemaAccessor;
using selector_ptr_t = std::unique_ptr<Selector>;
using selector_ptr_a = const selector_ptr_t &;

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

	const std::pair<bool, int> GetDataPartition( void ) const {
		return std::make_pair( m_Match.m_HasDataPartition, m_Match.m_DataPartition );
	}

	struct Visitor
	{
		virtual void Action( const char * found, size_t length ) = 0;
	};
	virtual void Visit( const char *first, const char *last, Visitor & visitor )
	{
		return;
	}

	// factory
	static selector_ptr_t MakeSelector( const Match & match, bool empty_selects_all, const LogSchemaAccessor * schema = nullptr );
};

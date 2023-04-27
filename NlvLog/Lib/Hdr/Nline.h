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

#include <map>
#include <set>
#include <vector>



/*-----------------------------------------------------------------------
 * NLine
 -----------------------------------------------------------------------*/

namespace NLine
{
	//
	// helper to find lines in maps and sets
	//

	// GetKeyValue container accessors; takes a single argument (of type
	// T_CONTAINER::const_iterator) and should return the line number (vint_t)
	// at that position in the container
	template
	<
		typename T_CONTAINER,
		std::enable_if_t<std::is_same<T_CONTAINER, std::set<typename T_CONTAINER::key_type>>::value, int> = 0
	>
	typename T_CONTAINER::key_type GetKeyValue( const typename T_CONTAINER::const_iterator & it )
	{
		return *it;
	}

	template
	<
		typename T_CONTAINER,
		std::enable_if_t<std::is_same<T_CONTAINER, std::map<typename T_CONTAINER::key_type, typename T_CONTAINER::mapped_type>>::value, int> = 0
	>
	typename T_CONTAINER::key_type GetKeyValue( const typename T_CONTAINER::const_iterator & it )
	{
		return it->first;
	}

	// given a map or set of line numbers find the line which follows (or precedes)
	// the supplied line_no
	template<typename T_CONTAINER, typename T_KEY = typename T_CONTAINER::key_type>
	static T_KEY GetNextLine( const T_CONTAINER & container, T_KEY line_no, bool forward )
	{
		using container_t = T_CONTAINER;
		using key_t = T_KEY;
		using const_iterator = typename container_t::const_iterator;
		const_iterator ibegin{ container.begin() };
		const_iterator iend{ container.end() };

		const_iterator iline{ container.find( line_no ) };
		if( iline != iend )
		{
			// the current line is in the container; move iterator "forwards"
			if( forward )
			{
				++iline;
				return (iline == iend) ? -1 : GetKeyValue<container_t>( iline );
			}
			else
				return (iline == ibegin) ? -1 : GetKeyValue<container_t>( --iline );
		}
		else
		{
			// line_no wasn't in the container, so do linear search to find it
			key_t ret{ -1 };
			for( iline = ibegin; iline != iend; ++iline )
			{
				ret = GetKeyValue<container_t>( iline );
				if( ret >= line_no )
				{
					if( forward )
						return ret;
					else
						return (iline == ibegin) ? -1 : GetKeyValue<container_t>( --iline );
				}
			}
			return forward ? -1 : ret;
		}
	}


	//
	// helpers to find lines in vectors
	//

	//
	// For a vector which maps an index A to a value V, find the lowest value of
	// A which maps a given target value V. Effectively a reverse lookup - requires
	// the vector to be sorted, as this is a binary search. Specify "exact" true
	// to return a negative index if "target" is not present in "map".
	//
	template<typename T_VALUE>
	T_VALUE Lookup
	(
		const std::vector<T_VALUE> & map,
		T_VALUE map_size,
		T_VALUE target,
		bool exact = false
	)
	{
		using value_t = T_VALUE;
		if( map_size == 0 )
			return -1;

		value_t low_idx{ 0 }, high_idx{ map_size - 1 };
		do
		{
			const value_t idx{ (high_idx + low_idx + 1) / 2 }; 	// Round high
			const value_t value{ map[ idx ] };
			if( target < value )
				high_idx = idx - 1;
			else
				low_idx = idx;
		} while( low_idx < high_idx );

		return (exact && (map[ low_idx ] != target)) ? -1 : low_idx;
	}

	// re-use Lookup to search a map for a line
	template<typename T_VALUE>
	T_VALUE GetNextLine( const std::vector<T_VALUE> & map, T_VALUE current, bool forward )
	{
		using value_t = T_VALUE;

		value_t idx{ Lookup( map, nlineno_cast( map.size() ), current ) };
		const value_t found{ map[ idx ] };

		if( found == current )
			idx += (forward ? 1 : -1);

		else if( forward )
		{
			if( found < current )
				idx += 1;
		}

		else
		{
			if( found > current )
				return -1;
		}

		if( idx >= map.size() )
			return -1;

		return map[ idx ];
	}
};

//
// Copyright (C) 2019 Niel Clausen. All rights reserved.
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
#include <map>
#include <memory>

// Application includes
#include "Nmisc.h"

// BOOST includes
#include <boost/intrusive/list.hpp>



/*-----------------------------------------------------------------------
 * Cache
 -----------------------------------------------------------------------*/

namespace ci = boost::intrusive;

// the cache size should be large enough for a screen's worth of lines
constexpr size_t c_DefaultCacheSize{ 128 };

// T_ITEM should have a move constructor; T_KEY must be comparable
template<typename T_ITEM, typename T_KEY>
class Cache
{
public: 
	using item_t = T_ITEM;
	using key_t = T_KEY;

private:
	// cache behaviour/performance measure
	CacheStatistics & m_Stats;

	// maximum size the cache will grow to
	const size_t m_Limit;

	// the link list pointers maintained by the intrusive MRU list
	using hook_t = ci::list_member_hook
	<
		ci::link_mode<ci::auto_unlink>
	>;

	// cache entries; entries are held in two structures, a std::map
	// for lookup by key, and a MRU "ordered" list for age/size
	// management
	struct CacheEntry
	{
		// a copy of the entry key; allows lookups in the std::map
		// starting from an entry
		const key_t m_Key;

		// the user "cached" data
		item_t m_UserItem;

		// intrusive list pointers
		hook_t m_Hook;

		CacheEntry( const key_t & key, item_t && item )
			: m_Key{ key }, m_UserItem{ std::move( item ) } {}

		void unlink( void ) {
			return m_Hook.unlink();
		}
	};

	// an intrusive list of cache entry structures
	using entry_t = CacheEntry;
	using list_t = ci::list
	<
		entry_t,
		ci::member_hook<entry_t, hook_t, &entry_t::m_Hook>,
		ci::constant_time_size<false>
	>;
	list_t m_MruList;

	// an index of cache entries
	using entry_ptr_t = std::unique_ptr<entry_t>;
	using map_t = std::map<key_t, entry_ptr_t>;
	map_t m_Map;

protected:
	// make the entry the "most recently used"
	void MakeMRU( entry_t & entry )
	{
		entry.unlink();
		m_MruList.push_back( entry );
	}

	// erase "least recently used" entries until the cache
	// size constraint is met
	void EraseLRU( void )
	{
		while( m_Map.size() >= m_Limit )
			m_Map.erase( m_MruList.front().m_Key );
	}

	// create and index a new cache entry
	entry_t & CreateEntry( const key_t & key, item_t && item )
	{
		entry_ptr_t pentry{ std::make_unique<entry_t>( key, std::move( item ) ) };
		entry_t & entry{ *pentry };
		m_MruList.push_back( *pentry );

		map_t::value_type value{ key, std::move( pentry ) };
		m_Map.insert( std::move( value ) );

		return entry;
	}

public:
	Cache( CacheStatistics & stats, size_t limit = c_DefaultCacheSize )
		: m_Stats{ stats }, m_Limit{ limit } {}

	using find_t = std::pair<bool, item_t*>;

	template<typename T_INITIALISER>
	find_t Fetch( const key_t & key, T_INITIALISER initialiser )
	{
		m_Stats.Lookup();

		map_t::iterator ientry{ m_Map.find( key ) };

		if( ientry != m_Map.end() )
		{
			entry_t & entry{ *(ientry->second) };
			MakeMRU( entry );
			return std::make_pair( true, & entry.m_UserItem );
		}
		else
		{
			m_Stats.Miss();
			EraseLRU();
			return std::make_pair( false, & CreateEntry( key, initialiser( key ) ).m_UserItem );
		}
	}

	void Clear( void )
	{
		m_Map.clear();
	}
};

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
#include <chrono>
#include <functional>
#include <list>



/*-----------------------------------------------------------------------
 * Initialisation / Shutdown
 -----------------------------------------------------------------------*/

// instances of OnEvent must be declared statically

class OnEvent
{
public:
	using function_t = std::function<void( void )>;

	enum class EventType
	{
		Startup,
		Shutdown,
		_NumTypes
	};

private:
	// stored lists (of all) event callbacks; must be simple list,
    // as the linker does not guarantee the initialisation order of
    // static variables, whereas zero'd values will be set beforehand
	static constexpr size_t c_NumEvents{ static_cast<size_t>(EventType::_NumTypes) };
	static OnEvent * m_EventHandlers[ c_NumEvents ];
    OnEvent * m_Next{ nullptr };

	static OnEvent * & GetEventList( EventType type ) {
		return m_EventHandlers[ static_cast<size_t>(type) ];
	};

	// callback for *this* event
	function_t m_Function;

public:
	static void RunEvents( EventType type );
	OnEvent( EventType type, function_t func );
};



/*-----------------------------------------------------------------------
 * ChangeTracker
 -----------------------------------------------------------------------*/

// simple way to recall and check for the validity of an item
class ChangeTracker
{
private:
	mutable size_t m_Count{ 0 };

public:
	ChangeTracker( bool initialise = false )
		: m_Count{ initialise ? 1U : 0U } {}

	void RecordEvent( void ) {
		m_Count += 1;
	}

	// return true where the states are different
	bool CompareTo( const ChangeTracker & source ) const {
		if( source.m_Count == 0 )
			throw std::domain_error{ "Nlog: Uninitialised ChangeCounter" };

		if( m_Count != source.m_Count )
		{
			m_Count = source.m_Count;
			return true;
		}
		else
			return false;
	}
};



/*-----------------------------------------------------------------------
 * CacheStatistics
 -----------------------------------------------------------------------*/

 // instances of this class should be static
class CacheStatistics
{
public:
	CacheStatistics( const char * name )
		: m_Name{ name }
	{
		m_Next = m_First;
		m_First = this;
	}

	static void ReportAll( void );

	void Lookup( void ) {
		m_Lookups += 1;
	}

	void Miss( void ) {
		m_Misses += 1;
	}

private:
	void Report( void );

	uint64_t m_Lookups{ 0 }, m_Misses{ 0 };
	const char * m_Name;
	CacheStatistics * m_Next;

private:
	static CacheStatistics * m_First;
};



/*-----------------------------------------------------------------------
 * Performance Timer
 -----------------------------------------------------------------------*/

class PerfTimer
{
private:
	const std::chrono::system_clock::time_point m_Start;
	std::chrono::duration<double> m_DurationAll_S;

	bool m_Closed{ false };
	void Close( void );

public:
	PerfTimer( void );
	double Overall( void );
	double PerItem( size_t item_count = 0 );
};


struct PythonPerfTimerImpl
{
	static std::unique_ptr<PythonPerfTimerImpl> Create( const char * description, size_t item_count );
	virtual void AddArgument( const char * arg ) = 0;
	virtual void AddArgument( const wchar_t * arg ) = 0;
	virtual void Close( size_t item_count ) = 0;
};


class PythonPerfTimer
{
private:
	std::unique_ptr<PythonPerfTimerImpl> m_Impl;

public:
	PythonPerfTimer( const char * description, size_t item_count = 0 )
		: m_Impl{ PythonPerfTimerImpl::Create( description, item_count ) } {}

	~PythonPerfTimer( void ) {
		Close();
	}

	void AddArgument( const char * arg ) {
		m_Impl->AddArgument( arg );
	}

	void AddArgument( const wchar_t * arg ) {
		m_Impl->AddArgument( arg );
	}

	void Close( size_t item_count = 0 ) {
		m_Impl->Close( item_count );
	}
};

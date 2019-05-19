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
#include "LogAccessor.h"
#include "Nmisc.h"
#include "Ntrace.h"



/*-----------------------------------------------------------------------
 * Initialisation / Shutdown
 -----------------------------------------------------------------------*/

// initialisation and shutdown handlers are run when Python calls Setup()

// event handlers
OnEvent::EventList OnEvent::m_EventHandlers[ c_NumEvents ];


void OnEvent::RunEvents( EventType type )
{
	for( OnEvent * handler : GetEventList( type ) )
		(handler->m_Function)();
}


OnEvent::OnEvent( EventType type, function_t func )
	: m_Function{ func }
{
	GetEventList( type ).push_back( this );
}



/*-----------------------------------------------------------------------
 * CacheStatistics
 -----------------------------------------------------------------------*/

CacheStatistics * CacheStatistics::m_First{ nullptr };


static OnEvent s_CacheStatisticsReport{ OnEvent::EventType::Shutdown,
	[&] () {
		CacheStatistics::ReportAll();
	} };


void CacheStatistics::Report( void )
{
	if( m_Lookups != 0 )
	{
		const double ratio{ (100.0 * m_Misses) / m_Lookups };
		TraceDebug( "%s: lookups:%llu misses:%llu ratio:%.2f%%", m_Name, m_Lookups, m_Misses, ratio );
	}
	else
		TraceDebug( "%s: lookups:0", m_Name );
}


void CacheStatistics::ReportAll( void )
{
	for( CacheStatistics * stats = m_First; stats != nullptr; stats = stats->m_Next )
		stats->Report();
}


/*-----------------------------------------------------------------------
 * FieldValue
 -----------------------------------------------------------------------*/

std::string FieldValue::AsString( void ) const
{
	const size_t bufsz{ 128 };
	char buf[ bufsz ];
	int len{ -1 };

	switch( m_Type )
	{
	case FieldValueType::unsigned64:
		len = sprintf_s( buf, "%I64u", As<uint64_t>() );
		break;

	case FieldValueType::signed64:
		len = sprintf_s( buf, "%I64d", As<int64_t>() );
		break;

	case FieldValueType::float64:
		len = sprintf_s( buf, "%.7g", As<double>() );
		break;

	}

	if( len >= 0 )
		return std::string{ buf };
	else
		return std::string{ "<unknown>" };
}

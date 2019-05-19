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
#include "Ntrace.h"

// C includes
#include <stdarg.h>
#include <stdio.h>
#include <time.h>



/*-------------------------------------------------------------------------
 * Tracing
 ------------------------------------------------------------------------*/

namespace
{
	const unsigned MSGSIZE{ 4096 };

	const std::string GetOsError( Error error )
	{
		// fetch any system error value first
		const DWORD err_code{ GetLastError() };
		std::string res;

		// convert the last system error into a string
		if( !IsOsError( error ) )
			/* skip, not an error message */;

		else if( err_code == ERROR_SUCCESS )
			res.assign( "SYSTEM{code:0x00000000}" );

		else
		{
			LPVOID lpMsgBuf{ nullptr };
			const DWORD nchar{ FormatMessage( FORMAT_MESSAGE_ALLOCATE_BUFFER | FORMAT_MESSAGE_FROM_SYSTEM, NULL, err_code, MAKELANGID( LANG_NEUTRAL, SUBLANG_DEFAULT ), (LPTSTR) &lpMsgBuf, 0, NULL ) };
			const bool have_sysmsg{ (nchar != 0) && (lpMsgBuf != nullptr) };

			LPTSTR sysmsg{ L"None" };
			if( have_sysmsg )
			{
				sysmsg = (LPTSTR) lpMsgBuf;

				wchar_t * end{ nullptr };
				if( (end = wcspbrk( sysmsg, L".\r\n" )) != 0 )
					*end = '\0';
			}

			char sbuf[ MSGSIZE ];
			if( sprintf_s( sbuf, "SYSTEM{code:0x%08x: diagnosis:'%S'}", err_code, sysmsg ) >= 0 )
				res.assign( sbuf );

			if( lpMsgBuf != nullptr )
				LocalFree( lpMsgBuf );

			// clear system message value to avoid repeats,
			SetLastError( ERROR_SUCCESS );
		}

		return res;
	}


	// by default, tracing is sent to a file in the current directory
	void TraceToFile( Error, const std::string & message )
	{
		// create timestamp
		const time_t tt{ time( nullptr ) };
		struct tm tm; localtime_s( &tm, &tt );
		char ts[ 128 ]; strftime( ts, sizeof( ts ), "%d-%b-%Y %H:%M:%S", &tm );

		FILE *tf; const errno_t err{ fopen_s( &tf, "nlogtrace.txt", "a" ) };
		if( !err )
		{
			fprintf( tf, "%s: %s\n", ts, message.c_str() );
			fclose( tf );
		}
	}


	tracefunc_t g_TraceFunc{ TraceToFile };
}


// simple trace handler
void _TraceMessage( Error error, const char * stream, const char * func, const char * fmt, ... )
{
	// process errors first
	const std::string os_error{ GetOsError( error ) };

	char sbuf[ MSGSIZE ];
	std::string prefix;
	if( sprintf_s( sbuf, "%s{%s}", stream, func ) >= 0 )
		prefix.assign( sbuf );

	std::string text{ "A trace error has occured, message has been lost" };
	va_list ap;
	va_start( ap, fmt );
	if( vsprintf_s( sbuf, fmt, ap ) >= 0 )
		text.assign( sbuf );
	va_end( ap );

	std::string message;
	message += prefix + ' ' + text + ' ';
	if( !os_error.empty() )
		message += os_error;

	(*g_TraceFunc)( error, message );
}


// set the trace output function; if func is nullptr, revert to default outputter
void SetTraceFunc( tracefunc_t func )
{
	g_TraceFunc = (func != nullptr) ? func : TraceToFile;
}

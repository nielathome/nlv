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
 * Error
 -----------------------------------------------------------------------*/

// simple error return system; an error code should only be used in one place
enum Error : unsigned
{
	e_Success = 0x00000,
	e_OK,
	e_TraceInfo,
	e_TraceDebug,
	e_SqlRow,
	e_SqlDone,

	e_Error = 0x10000,
	e_Unknown,
	e_FileNotFound,
	e_Empty,
	e_LogfileChanged,
	e_FieldSchemaChanged,
	e_CorruptIndex,
	e_UnsupportedIndexVersion,
	e_IndexUnusable,
	e_BadAccessorName,
	e_WrongIndex,
	e_SelectorCreate,
	e_BadSelectorDefinition,
	e_FieldInterpretation,
	e_BadSeconds,
	e_BadMinutes,
	e_BadHours,
	e_BadDay,
	e_BadMonth,
	e_BadTimeFraction,
	e_OversizedTimeFraction,
	e_EnumOverflow,
	e_LineOffsetRange,
	e_StateCreate,
	e_StateUse,
	e_Parser,
	e_FieldName,
	e_MultipleField,
	e_EnumName,
	e_MultipleEnum,
	e_ParseUnexpectedText,
	e_ReportLimit,
	e_Locale,
	e_CreateLineSet,
	e_CreateEventView,
	e_CreateLogView,

	e_OsError = 0x20000,
	e_OpenFileStream,
	e_Stream,
	e_UnmapView,
	e_CloseMapHandle,
	e_CloseFileHandle,
	e_CreateMapping,
	e_CreateView,
	e_GetModifiedTime,
	e_OpenFileHandle,
	e_CreateFileHandle,
	e_FileSize,
	e_FileSystem,

	e_SqlDbOpen,
	e_SqlDbClose,
	e_SqlStatementOpen,
	e_SqlStatementBind,
	e_SqlStatementReset,
	e_SqlStatementClose,
	e_SqlStatementStep
};


inline bool Ok( Error value )
{
	return value < e_Error;
}


inline bool IsOsError( Error value )
{
	return (value & e_OsError) != 0;
}


inline void UpdateError( Error & value, Error error )
{
	if( Ok( value ) )
		value = error;
}


template<typename T_FUNC>
void ExecuteIfOk( T_FUNC func, Error & value )
{
	if( Ok( value ) )
		value = func();
}



/*-----------------------------------------------------------------------
 * Tracing
 -----------------------------------------------------------------------*/

// allow the tracing function to be altered
using tracefunc_t = void (*) (Error error, const std::string & message);
void SetTraceFunc( tracefunc_t func = nullptr );

void _TraceMessage( Error error, const char * stream, const char * func, const char * fmt, ... );

// informational message aimed at NLog developers
#define TraceDebug( FMT, ... ) \
	_TraceMessage( e_TraceDebug, "nlog", __FUNCTION__, FMT, ##__VA_ARGS__ )

// informational messages aimed at NLog users
#define TraceInfoN( NAME, FMT, ... ) \
	_TraceMessage( e_TraceInfo, "nlog", NAME, FMT, ##__VA_ARGS__ )

#define TraceInfo( FMT, ... ) \
	TraceInfoN( __FUNCTION__, FMT, ##__VA_ARGS__ )

// error messages for NLog users
#define TraceErrorN( ERR, NAME, FMT, ... ) \
	(_TraceMessage( ERR, "nlog(" #ERR ")", NAME, FMT, ##__VA_ARGS__ ), (ERR))

#define TraceError( ERR, FMT, ... ) \
	TraceErrorN( ERR, __FUNCTION__, FMT, ##__VA_ARGS__ )

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
#include "FileMap.h"



/*-----------------------------------------------------------------------
 * FileMap
 -----------------------------------------------------------------------*/

FileMap::~FileMap( void )
{
	UnMap();
}


Error FileMap::UnMap( void )
{
	// remove file view from memory map
	Error error = e_OK;
	if( m_Data != nullptr )
	{
		if( !UnmapViewOfFile( m_Data ) )
			UpdateError( error, TraceError( e_UnmapView, "'%S'", m_Path.c_str() ) );
	}
	m_Data = nullptr;
	m_Size = 0;

	// close mapping and file handles
	if( m_MappingHandle != NULL )
	{
		if( !CloseHandle( m_MappingHandle ) )
			UpdateError( error, TraceError( e_CloseMapHandle, "'%S'", m_Path.c_str() ) );
	}
	m_MappingHandle = NULL;

	if( m_FileHandle != INVALID_HANDLE_VALUE )
	{
		if( !CloseHandle( m_FileHandle ) )
			UpdateError( error, TraceError( e_CloseFileHandle, "'%S'", m_Path.c_str() ) );
	}
	m_FileHandle = INVALID_HANDLE_VALUE;

	return error;
}


Error FileMap::Map( bool read_write, std::uintmax_t map_size )
{
	// create the file mapping object
	LARGE_INTEGER msize; msize.QuadPart = map_size;
	const DWORD flProtect{ (DWORD) (read_write ? PAGE_READWRITE : PAGE_READONLY) };
	m_MappingHandle = CreateFileMapping( m_FileHandle, nullptr, flProtect, msize.HighPart, msize.LowPart, 0 );
	if( m_MappingHandle == NULL )
		return TraceError( e_CreateMapping, "'%S'", m_Path.c_str() );

	// map the whole file
	const DWORD dwDesiredAccess{ (DWORD) (read_write ? FILE_MAP_ALL_ACCESS : FILE_MAP_READ) };
	m_Data = MapViewOfFile( m_MappingHandle, dwDesiredAccess, 0, 0, 0 );
	if( m_Data == 0 )
		return TraceError( e_CreateView, "'%S'", m_Path.c_str() );

	// make a note of the file's last modified time
	if( !GetFileTime( m_FileHandle, nullptr, nullptr, &m_ModifiedTime ) )
		return TraceError( e_GetModifiedTime, "'%S'", m_Path.c_str() );

	// write out results
	return e_OK;
}


Error FileMap::Map( const std::filesystem::path & file_path, bool read_write, std::uintmax_t size )
{
	TraceDebug( "path:'%S' read_write:%d size:%llu", file_path.c_str(), (int) read_write, size );
	m_Path = file_path;

	// remove any old/partial mapping
	Error unmap_error{ UnMap() };
	if( !Ok( unmap_error ) )
		return unmap_error;

	// attempt to open an existing file
	const bool read_only{ !read_write };
	const DWORD dwDesiredAccess{ read_write ? GENERIC_READ | GENERIC_WRITE : GENERIC_READ };
	const DWORD dwShareMode{ FILE_SHARE_READ };
	m_FileHandle = CreateFile( file_path.c_str(), dwDesiredAccess, dwShareMode, nullptr, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, 0 );

	std::uintmax_t map_size;
	if( m_FileHandle == INVALID_HANDLE_VALUE )
	{
		// separate file not found errors from other errors opening the file
		const bool file_not_found{ GetLastError() == ERROR_FILE_NOT_FOUND };
		if( !file_not_found )
			return TraceError( e_OpenFileHandle, "'%S'", m_Path.c_str() );
		else if( read_only || (size == 0) )
			return e_FileNotFound;

		// no existing file (and read_write with size), so create new one
		m_FileHandle = CreateFile( file_path.c_str(), GENERIC_READ | GENERIC_WRITE, dwShareMode, nullptr, CREATE_NEW, FILE_ATTRIBUTE_NORMAL, 0 );
		if( m_FileHandle == INVALID_HANDLE_VALUE )
			// unable to create a new file, so give up
			return TraceError( e_CreateFileHandle, "'%S'", m_Path.c_str() );

		// record that the file was created successfully
		map_size = size;
	}
	else
	{
		// determine file's size
		std::error_code ec;
		map_size = std::filesystem::file_size( file_path, ec );
		if( ec )
			return TraceError( e_FileSize, "'%S'", m_Path.c_str() );
	}

	// write out results
	m_Size = map_size;
	return Map( read_write, map_size );
}

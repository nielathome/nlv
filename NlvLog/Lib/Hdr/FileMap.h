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

// Application includes
#include "Nfilesystem.h"
#include "Ntrace.h"



/*-----------------------------------------------------------------------
 * FileMap
 -----------------------------------------------------------------------*/

class FileMap
{
private:
	// copy of path
	std::filesystem::path m_Path;

	// file mapping handles
	HANDLE m_FileHandle{ INVALID_HANDLE_VALUE }, m_MappingHandle{ NULL };

	// file's last modified time in OS format; we don't use std::filesystem::file_time_type
	// as the (std::experimental) implementation applies an undocumented offset
	// to the time value - making it an unreliable API where the value is stored
	// long term in the index file (e.g. would the non-experimental implementation
	// do the same?)
	// std::filesystem::file_time_type m_ModifiedTime;
	FILETIME m_ModifiedTime{ 0, 0 };

	// mapped data
	void * m_Data{ nullptr };
	std::uintmax_t m_Size{ 0 };

protected:
	Error Map( bool read_write, std::uintmax_t map_size );
	Error UnMap( void );

public:
	~FileMap( void );

	// file must already exist to be mapped read-only
	// file may exist to map read-write; if not, it is created with size
	Error Map( const std::filesystem::path & file_path, bool read_write = false, std::uintmax_t size = 0 );

	// accessors
	template<typename T_DATA = char>
	const T_DATA * GetData( void ) const {
		return reinterpret_cast<const T_DATA *>( m_Data );
	}

	std::uintmax_t GetSize( void ) const {
		return m_Size;
	}

	const FILETIME & GetModifiedTime( void ) const {
		return m_ModifiedTime;
	}
};

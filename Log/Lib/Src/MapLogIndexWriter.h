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

// Nlog includes
#include "MapLogIndexAccessor.h"

// C++ includes
#include <atomic>
#include <regex>



/*-----------------------------------------------------------------------
 * LogIndexWriter
 -----------------------------------------------------------------------*/

 // forwards
class FieldWriter;
class FieldWriterTextOffsetsBase;
struct WriteContext;

// create a mapped index for a logfile, suitable for later access via LogIndexAccessor
class LogIndexWriter : public LogIndexBase<FieldWriter>
{
private:
	// logfile
	const FileMap & m_Log;

	// line matcher
	const bool m_UseRegex;
	std::regex m_Regex;

	// the text offsets field has extra services; keep a typed pointer to it
	FieldWriterTextOffsetsBase * m_FieldTextOffsets{ nullptr };

	template<typename T_FIELDGET>
	Error WriteLine( WriteContext & cxt, size_t offset, const char *begin, const char *end, T_FIELDGET & field_get );
	Error WriteLineRegex( WriteContext & cxt, size_t offset, const char *begin, const char *end );
	Error WriteLineSeparated( WriteContext & cxt, size_t offset, const char *begin, const char *end );

	Error WriteLine( WriteContext & cxt, size_t offset, const char *begin, const char *end ) {
		if( m_UseRegex )
			return WriteLineRegex( cxt, offset, begin, end );
		else
			return WriteLineSeparated( cxt, offset, begin, end );
	}

protected:
	Error WriteLines( WriteContext & cxt, nlineno_t * num_lines, ProgressMeter * progress, size_t skip_lines );

public:
	LogIndexWriter( const FileMap & fmap, const fielddescriptor_list_t & field_descs, const std::string & match_desc );
	Error Write( const std::filesystem::path & index_path, FILETIME modified_time, const std::string & guid, ProgressMeter * progress, size_t skip_lines );
};

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
#include <stdexcept>

// Boost includes
#include <boost/intrusive_ptr.hpp>

// Common Scintilla types
#include <scintilla/src/VContent.h>

// Application includes
#include "Nmisc.h"



/*-----------------------------------------------------------------------
 * Forwards
 -----------------------------------------------------------------------*/

class NAnnotations; using annotations_ptr_t = boost::intrusive_ptr<NAnnotations>;
class NAdornments; using adornments_ptr_t = boost::intrusive_ptr<NAdornments>;
class NLogfile; using logfile_ptr_t = boost::intrusive_ptr<NLogfile>;
class NView; using view_ptr_t = boost::intrusive_ptr<NView>;
class NLineSet;  using lineset_ptr_t = boost::intrusive_ptr<NLineSet>;



/*-----------------------------------------------------------------------
 * Support
 -----------------------------------------------------------------------*/

inline void UnsupportedVoid( const char *fname, bool silent = false )
{
	std::string what{ "Nlog: Unsupported function: " };
	what += fname;
	if( !silent )
		throw std::domain_error{ what };
}


template <typename T_RETURN>
T_RETURN Unsupported( const char *fname )
{
	UnsupportedVoid( fname );
	return T_RETURN();
}

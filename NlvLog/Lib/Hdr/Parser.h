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
#include <memory>

// Application includes
#include "Match.h"



/*-----------------------------------------------------------------------
 * SelectorLogviewFilter
 -----------------------------------------------------------------------*/

class LVF;
class SelectorLogviewFilter : public Selector
{
private:
	using parser_ptr_t = std::unique_ptr<LVF>;
	parser_ptr_t m_Parser;

public:
	SelectorLogviewFilter( const Match & match, const LogSchemaAccessor & schema );
	bool Hit( const LineAccessor & line, const LineAdornmentsAccessor & adornments ) const override;
};


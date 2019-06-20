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
#include "Logaccessor.h"

void force_link_dependencies()
{
	extern void force_link_mapaccessor_module();
	force_link_mapaccessor_module();

	extern void force_link_sqlaccessor_module();
	force_link_sqlaccessor_module();
}



/*-----------------------------------------------------------------------
 * LogAccessorFactory
 -----------------------------------------------------------------------*/

std::map<std::string, LogAccessor * (*)(LogAccessorDescriptor &)> LogAccessorFactory::m_Makers;


void LogAccessorFactory::RegisterLogAccessor( const std::string & name, LogAccessor * (*creator)(LogAccessorDescriptor &) )
{
	m_Makers[ name ] = creator;
}


LogAccessor * LogAccessorFactory::Create( LogAccessorDescriptor & descriptor )
{
	return m_Makers[ descriptor.m_Name ]( descriptor );
}

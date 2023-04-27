//
// Copyright (C) 2019 Niel Clausen. All rights reserved.
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
#include "Field.h"

// C++ includes
#include <map>
#include <memory>



/*-----------------------------------------------------------------------
 * FieldTraits
 -----------------------------------------------------------------------*/

// simple traits to generate uniform types related to Field
template<typename T_FIELD>
struct FieldTraits
{
	using field_ptr_t = std::shared_ptr<T_FIELD>;
};



/*-----------------------------------------------------------------------
 * FieldFactory
 -----------------------------------------------------------------------*/

// effectively, the recognised field types; when extending, update the documentation
// at group.rst as well
const std::string c_Type_DateTime_Unix{ "datetime_unix" };
const std::string c_Type_DateTime_UsStd{ "datetime_us_std" };
const std::string c_Type_DateTime_TraceFmt_IntStd{ "datetime_tracefmt_int_std" };
const std::string c_Type_DateTime_TraceFmt_UsStd{ "datetime_tracefmt_us_std" };
const std::string c_Type_DateTime_TraceFmt_IntHires{ "datetime_tracefmt_int_hires" };
const std::string c_Type_DateTime_TraceFmt_UsHires{ "datetime_tracefmt_us_hires" };
const std::string c_Type_DateTime_WebUTC{ "datetime_web_utc" };
const std::string c_Type_Time_TraceFmt_NoDate{ "datetime_tracefmt_no_date" };
const std::string c_Type_Bool{ "bool" };
const std::string c_Type_Uint08{ "uint08" };
const std::string c_Type_Uint16{ "uint16" };
const std::string c_Type_Uint32{ "uint32" };
const std::string c_Type_Uint64{ "uint64" };
const std::string c_Type_Int08{ "int08" };
const std::string c_Type_Int16{ "int16" };
const std::string c_Type_Int32{ "int32" };
const std::string c_Type_Int64{ "int64" };
const std::string c_Type_Float32{ "float32" };
const std::string c_Type_Float64{ "float64" };
const std::string c_Type_Enum08{ "enum08" };
const std::string c_Type_Enum16{ "enum16" };
const std::string c_Type_Emitter{ "emitter" };
const std::string c_Type_Text{ "text" };
const std::string c_Type_TextOffsets08{ "text_offsets08" };
const std::string c_Type_TextOffsets16{ "text_offsets16" };

const std::string c_Type_Int{ "int" };
const std::string c_Type_Real{ "real" };


// field base class and factory
template <typename T_FIELD, typename T_MAKER>
class FieldFactory
{
public:
	using field_t = T_FIELD;
	using maker_t = T_MAKER;
	using factory_t = FieldFactory;
	using field_ptr_t = typename FieldTraits<field_t>::field_ptr_t;

	// field factories; create a field given its type
	template<typename ...T_ARGS>
	static field_ptr_t CreateField( const FieldDescriptor & field_desc, T_ARGS ...args ) {
		maker_t maker{ *GetFieldCreator( field_desc.f_Type ) };
		return (*maker)(field_desc, args...);
	}

private:
	// the map of field creators
	using map_t = std::map<std::string, maker_t>;
	static map_t m_Map;

	// lookup field type in the map of creator functions
	static maker_t GetFieldCreator( const std::string & type ) {
		map_t::iterator imaker{ m_Map.find( type ) };
		if( imaker == m_Map.end() )
			throw std::domain_error{ "Nlog: Unknown field type: " + type};

		return imaker->second;
	}
};


// helper to create a new field
template<typename T_FIELD, typename ...T_ARGS>
typename T_FIELD::field_ptr_t MakeField( T_ARGS ...args )
{
	return std::make_shared<T_FIELD>( args... );
}



/*-----------------------------------------------------------------------
 * FieldStore
 -----------------------------------------------------------------------*/

template<typename T_FIELD>
class FieldStore
{
protected:
	using field_t = T_FIELD;
	using field_ptr_t = typename FieldTraits<field_t>::field_ptr_t;
	using field_array_t = std::vector<field_ptr_t>;

	// the fields
	field_array_t m_UserFields;
	field_array_t m_AllFields;


	// CreateField(const FieldDescriptor &, unsigned, offset *), or
	// CreateField( const FieldDescriptor &, unsigned )
	template<typename ...T_ARGS>
	field_ptr_t CreateField( const FieldDescriptor & field_desc, T_ARGS ...args )
	{
		const unsigned field_id{ static_cast<unsigned>(m_AllFields.size()) };
		return field_t::CreateField( field_desc, field_id, args... );
	}
	
	void AddUserField( field_ptr_t field ) {
		m_AllFields.push_back( field );
		m_UserFields.push_back( field );
	}

	void AddInternalField( field_ptr_t field ) {
		m_AllFields.push_back( field );
	}

	// iterate over a list of field descriptors
	template<typename ...T_ARGS>
	void SetupUserFields( const fielddescriptor_list_t & field_descs, T_ARGS ...args )
	{
		for( const FieldDescriptor & field_desc : field_descs )
			AddUserField( CreateField( field_desc, args... ) );
	}

public:
	unsigned GetNumUserFields( void ) const {
		return static_cast<unsigned>(m_UserFields.size());
	}
};

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

// C++ includes
#include <string>
#include <vector>



/*-----------------------------------------------------------------------
 * FieldValue
 -----------------------------------------------------------------------*/

// support three basic field types
enum class FieldValueType
{
	unsigned64,
	signed64,
	float64,
	invalid
};

// convert a type to the matching field-value-type
template<typename> struct TypeToFieldType {};

template<> struct TypeToFieldType<uint64_t> {
	static const FieldValueType type{ FieldValueType::unsigned64 };
};

template<> struct TypeToFieldType<int64_t> {
	static const FieldValueType type{ FieldValueType::signed64 };
};

template<> struct TypeToFieldType<double> {
	static const FieldValueType type{ FieldValueType::float64 };
};

// field value type
class FieldValue
{
private:
	FieldValueType m_Type{ FieldValueType::invalid };
	uint64_t m_Payload{ 0 };

public:
	FieldValue( void ) {}

	template<typename T_VALUE>
	FieldValue( T_VALUE value )
		:
		m_Type{ TypeToFieldType<T_VALUE>::type },
		m_Payload{ *reinterpret_cast<uint64_t *>(&value) }
	{
	}

	FieldValue & operator = ( const FieldValue & rhs ) {
		m_Type = rhs.m_Type;
		m_Payload = rhs.m_Payload;
		return *this;
	}

	template<typename T_RESULT>
	T_RESULT As( void ) const
	{
		if( TypeToFieldType<T_RESULT>::type != m_Type )
			throw std::runtime_error{ "Invalid FieldValue conversion" };

		return *reinterpret_cast<const T_RESULT *>(&m_Payload);
	}

	template<typename T_RESULT>
	T_RESULT Convert( void ) const
	{
		switch( m_Type )
		{
		case FieldValueType::unsigned64:
			return static_cast<T_RESULT>(m_Payload);

		case FieldValueType::signed64:
			return static_cast<T_RESULT>(*reinterpret_cast<const int64_t *>(&m_Payload));

		case FieldValueType::float64:
			return static_cast<T_RESULT>(*reinterpret_cast<const double *>(&m_Payload));

		default:
			throw std::runtime_error{ "Invalid convert" };
		}

		return T_RESULT{};
	}

	FieldValue Convert( FieldValueType type ) const
	{
		switch( type )
		{
		case FieldValueType::unsigned64:
			return FieldValue{ Convert<uint64_t>() };

		case FieldValueType::signed64:
			return FieldValue{ Convert<int64_t>() };

		case FieldValueType::float64:
			return FieldValue{ Convert<double>() };

		default:
			throw std::runtime_error{ "Invalid convert" };
		}
	}

	FieldValueType GetType( void ) const {
		return m_Type;
	}

	std::string AsString( void ) const;
};

using fieldvalue_t = FieldValue;



/*-----------------------------------------------------------------------
 * FieldDescriptor
 -----------------------------------------------------------------------*/

// describe a field; analog of Python's G_FieldSchema
struct FieldDescriptor
{
	// is the field available to the end-user (else, it is hidden from them)
	bool f_Available;

	// arbitrary name - used LVF/LVA for selection/matching
	std::string f_Name;

	// field "type" (e.g. "enum16") - the key used by FieldFactory
	std::string f_Type;

	// field separator sequence
	std::string f_Separator;

	// count of separators; one solution for case where field contains f_Separator
	unsigned f_SeparatorCount;

	// field minimum width; another solution for case where field contains f_Separator
	unsigned f_MinWidth;

	// offset to another field which holds the actual data to be used for sorting/filtering
	unsigned f_DataColumnOffset;
};

using fielddescriptor_list_t = std::vector<FieldDescriptor>;




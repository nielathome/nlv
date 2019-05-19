//
// Copyright (C) 2018 Niel Clausen. All rights reserved.
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
#include "gtest/gtest.h"

#include "LogAccessor.h"

// keep tests in a private namespace
namespace {


struct FieldValueTest : public ::testing::Test
{
};


TEST_F( FieldValueTest, ConstructUnsigned )
{
	const uint64_t value{ 42 };
	FieldValue field{ value };

	EXPECT_EQ( FieldValueType::unsigned64, field.GetType() );
	EXPECT_EQ( 42, field.As<uint64_t>() );
}


TEST_F( FieldValueTest, ConstructSigned )
{
	const int64_t value{ -42 };
	FieldValue field{ value };

	EXPECT_EQ( FieldValueType::signed64, field.GetType() );
}


TEST_F( FieldValueTest, AsUnsigned )
{
	{
		const uint64_t value{ 42 };
		FieldValue field{ value };
		EXPECT_EQ( 42, field.As<uint64_t>() );
	}

	{
		const int64_t value{ -42 };
		FieldValue field{ value };
		EXPECT_THROW( field.As<uint64_t>(), std::runtime_error );
	}

	{
		const double value{ 42.1 };
		FieldValue field{ value };
		EXPECT_THROW( field.As<uint64_t>(), std::runtime_error );
	}
}


TEST_F( FieldValueTest, AsSigned )
{
	{
		const uint64_t value{ 42 };
		FieldValue field{ value };
		EXPECT_THROW( field.As<int64_t>(), std::runtime_error );
	}

	{
		const int64_t value{ -42 };
		FieldValue field{ value };
		EXPECT_EQ( -42, field.As<int64_t>() );
	}

	{
		const double value{ 42.1 };
		FieldValue field{ value };
		EXPECT_THROW( field.As<int64_t>(), std::runtime_error );
	}
}


TEST_F( FieldValueTest, AsDouble )
{
	{
		const uint64_t value{ 42 };
		FieldValue field{ value };
		EXPECT_THROW( field.As<double>(), std::runtime_error );
	}

	{
		const int64_t value{ -42 };
		FieldValue field{ value };
		EXPECT_THROW( field.As<double>(), std::runtime_error );
	}

	{
		const double value{ 42.1 };
		FieldValue field{ value };
		EXPECT_DOUBLE_EQ( 42.1, field.As<double>() );
	}
}


TEST_F( FieldValueTest, ConvertUnsigned )
{
	{
		const uint64_t value{ 42 };
		FieldValue field{ value };
		EXPECT_EQ( 42, field.Convert<uint64_t>() );
	}

	{
		const int64_t value{ -42 };
		FieldValue field{ value };
		EXPECT_EQ( 0xFFFF'FFFF'FFFF'FFD6, field.Convert<uint64_t>() );
	}

	{
		const double value{ 42.1 };
		FieldValue field{ value };
		EXPECT_EQ( 42, field.Convert<uint64_t>() );
	}
}


TEST_F( FieldValueTest, ConvertSigned )
{
	{
		const uint64_t value{ 42 };
		FieldValue field{ value };
		EXPECT_EQ( 42, field.Convert<int64_t>() );
	}

	{
		const int64_t value{ -42 };
		FieldValue field{ value };
		EXPECT_EQ( -42, field.Convert<int64_t>() );
	}

	{
		const double value{ 42.1 };
		FieldValue field{ value };
		EXPECT_EQ( 42, field.Convert<int64_t>() );
	}
}


TEST_F( FieldValueTest, ConvertDouble )
{
	{
		const uint64_t value{ 42 };
		FieldValue field{ value };
		EXPECT_DOUBLE_EQ( 42.0, field.Convert<double>() );
	}

	{
		const int64_t value{ -42 };
		FieldValue field{ value };
		EXPECT_DOUBLE_EQ( -42.0, field.Convert<double>() );
	}

	{
		const double value{ 42.1 };
		FieldValue field{ value };
		EXPECT_DOUBLE_EQ( 42.1, field.Convert<double>() );
	}
}

}
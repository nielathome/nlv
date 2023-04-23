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

#include "Ntime.h"

// keep tests in a private namespace
namespace {



/*-----------------------------------------------------------------------
 * Diff
 -----------------------------------------------------------------------*/

struct TimecodeTest : public ::testing::Test
{
};


TEST_F( TimecodeTest, Equal )
{
	NTimecode a{ 1, 1000 };
	NTimecode b{ 1, 1000 };

	EXPECT_EQ( 0U, a - b );
}


TEST_F( TimecodeTest, CommonDatum )
{
	NTimecode a{ 1, 1000 };
	NTimecode b{ 1, 500 };

	EXPECT_EQ( 500, a - b );
	EXPECT_EQ( -500, b - a );

	EXPECT_TRUE( b < a );
}


TEST_F( TimecodeTest, MixedDatumA )
{
	NTimecode a{ 1, 1000 };
	NTimecode b{ 2, 500 };

	EXPECT_EQ( 999'999'500, a.Diff( b ) );
	EXPECT_EQ( -999'999'500, a - b );
	EXPECT_EQ( 999'999'500, b - a );

	EXPECT_EQ( -999'999'500, a.Subtract( b ) );
	EXPECT_EQ( 999'999'500, b.Subtract( a ) );

	EXPECT_TRUE( a < b );
}


TEST_F( TimecodeTest, MixedDatumB )
{
	NTimecode a{ 1, 500 };
	NTimecode b{ 2, 1000 };

	EXPECT_EQ( 1'000'000'500, a.Diff( b ) );
	EXPECT_EQ( -1'000'000'500, a - b );
	EXPECT_EQ( 1'000'000'500, b - a );

	EXPECT_EQ( -1'000'000'500, a.Subtract( b ) );
	EXPECT_EQ( 1'000'000'500, b.Subtract( a ) );

	EXPECT_TRUE( a < b );
}

}
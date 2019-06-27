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
#pragma once

// C++ includes
#include <vector>



/*-----------------------------------------------------------------------
 * NTimecode
 -----------------------------------------------------------------------*/

// the base information needed to fetch a usable timecode from a logfile is
// the log file (per line) field which stores the timecode offset, and the log file's
// UTC datum (from which the offset is measured)
class NTimecodeBase
{
private:
	time_t m_UtcDatum{ 0 };
	unsigned m_FieldId{ 0 };

public:
	NTimecodeBase( time_t utc_datum = 0, unsigned field_id = 0 )
		: m_UtcDatum{ utc_datum }, m_FieldId{ field_id } {}

	time_t GetUtcDatum( void ) const {
		return m_UtcDatum;
	}

	unsigned GetFieldId( void ) const {
		return m_FieldId;
	}
};


 // times in a logfile are stored as billionths of a second (ns) from the
 // UTC time of the first log line (the log file's "UTC datum"); approx
 // time span of 292 years
class NTimecode
{
private:
	time_t m_UtcDatum;
	int64_t m_OffsetNs;

public:
	static const int64_t c_NanoSecond{ 1'000'000'000 };

	NTimecode( time_t utc_datum = 0, int64_t ns = 0 )
		: m_UtcDatum{ utc_datum }, m_OffsetNs{ ns } {}

	// determine the ns offset with respect to the alternate datum
	int64_t CalcOffsetToDatum( time_t utc_datum ) const
	{
		// limit offfset to >= 0; i.e. we choose to not represent
		// the case where our timecode is in te past (i.e. earlier than
		// the alternate datum)
		const int64_t offset{ (c_NanoSecond * (m_UtcDatum - utc_datum)) + m_OffsetNs };
		return (offset >= 0) ? offset : 0;
	}

	// note, returns numeric difference, not a whole timecode
	int64_t operator - ( const NTimecode & rhs ) const {
		return (c_NanoSecond * (m_UtcDatum - rhs.m_UtcDatum)) + (m_OffsetNs - rhs.m_OffsetNs);
	}

	bool operator < ( const NTimecode & rhs ) const {
		return (*this - rhs) < 0;
	}

	int64_t Diff( const NTimecode & rhs ) const {
		int64_t res{ *this - rhs };
		if( res < 0 )
			res = 0 - res;
		return res;
	}

public:
	time_t GetUtcDatum( void ) const {
		return m_UtcDatum;
	}

	int64_t GetOffsetNs( void ) const {
		return m_OffsetNs;
	}

	// ensure the nanosecond offset is less than 1 second
	void Normalise( void ) {
		const int64_t whole_offset{ m_OffsetNs / c_NanoSecond };
		const int64_t frac_offset{ m_OffsetNs - (whole_offset * c_NanoSecond) };
		m_UtcDatum += whole_offset;
		m_OffsetNs = frac_offset;
	}

	int64_t Subtract( const NTimecode & rhs ) const {
		return *this - rhs;
	}
};



/*-----------------------------------------------------------------------
 * GlobalTracker
 -----------------------------------------------------------------------*/

class GlobalTracker
{
private:
	bool f_InUse{ false };
	NTimecode f_UtcTimecode;

public:
	struct NTimecodeAccessor
	{
		virtual NTimecode GetUtcTimecode( int line_no ) const = 0;
	};
	bool IsNearest( int line_no, int max_line_no, const NTimecodeAccessor & accessor ) const;

	void SetUtcTimecode( const NTimecode & timecode ) {
		f_InUse = true;
		f_UtcTimecode = timecode;
	}

	bool IsInUse( void ) const {
		return f_InUse;
	}

	const NTimecode & GetUtcTimecode( void ) const {
		return f_UtcTimecode;
	}
};



/*-----------------------------------------------------------------------
 * GlobalTrackers
 -----------------------------------------------------------------------*/

class GlobalTrackers
{
private:
	// global tracker support
	static std::vector<GlobalTracker> s_GlobalTrackers;

public:
	static const GlobalTracker & GetGlobalTracker( unsigned idx ) {
		return s_GlobalTrackers[ idx ];
	}

	static const std::vector<GlobalTracker> & GetTrackers( void ) {
		return s_GlobalTrackers;
	}

	static void SetGlobalTracker( unsigned tracker_idx, const NTimecode & utc_timecode );
};



/*-----------------------------------------------------------------------
 * ViewTimecodeAccessor
 -----------------------------------------------------------------------*/

struct ViewAccessor;
class ViewTimecodeAccessor : public GlobalTracker::NTimecodeAccessor
{
private:
	const ViewAccessor & f_ViewAccessor;

public:
	ViewTimecodeAccessor( const ViewAccessor & accessor );
	NTimecode GetUtcTimecode( int line_no ) const override;
};




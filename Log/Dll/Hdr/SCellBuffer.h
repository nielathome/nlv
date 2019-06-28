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
#include <string>
#include <vector>

// Application includes
#include "LogAccessor.h"
#include "Ntypes.h"

// Scintilla includes
#include <scintilla/src/CellBuffer.h>



/*-----------------------------------------------------------------------
 * SViewCellBuffer
 -----------------------------------------------------------------------*/

// forwards
struct Selector;

// Scintilla CellBuffer replacement, representing a view onto an underlying logfile
class SViewCellBuffer : public VCellBuffer
{
private:
	ChangeTracker m_Tracker{ true };

	// the lifetimes of the objects pointed-to here must be managed by this
	// objects owner
	viewaccessor_ptr_t m_ViewAccessor;
	LineAdornmentsProvider * m_LineAdornmentsProvider{ nullptr };

protected:
	// the view converts logical positions/lines (as presented to the CellBuffer user)
	// to actual positions/lines in an underlying logfile

	// line start locations in the view
	std::vector<vint_t> m_Lines;

	// local copies of key metrics
	vint_t m_TextLen{ 0 };
	vint_t m_NumLinesOrOne{ 0 };

	// warning: an empty Scintilla document has a line count of 1
	// this flag disambiguates the two cases
	bool m_IsEmpty{ true };

	// list of fields to display
	uint64_t m_FieldViewMask{ 0 };

	// determine the number of characters in a view line
	vint_t GetLineLength( vint_t view_line_no ) const {
		return m_ViewAccessor->GetLineLength( view_line_no, m_FieldViewMask );
	}

	// convert a view position into a view line number and an offset within that line
	void PositionToInfo( vint_t pos, vint_t *view_line_no, vint_t *offset ) const {
		// identify the view's line number
		*view_line_no = PositionToViewLine( pos );

		// determine the offset within the view's line
		*offset = pos - m_Lines[ *view_line_no ];
	}

	// return true if out-of-range
	bool BadRange( vint_t position, vint_t lengthRetrieve = 0 ) const {
		// Note: avoid operator < with vint_t, in case the type is unsigned and
		// the variable has zero value
		return (lengthRetrieve < 0)
			|| (position < 0)
			|| ((position + lengthRetrieve) > m_TextLen);
	}

	vint_t PositionToViewLine( vint_t pos ) const;
	char CharAt( e_LineData type, vint_t position ) const;
	void GetRange( e_LineData type, char * buffer, vint_t position, vint_t lengthRetrieve ) const;

public:
	// non-Scintilla interfaces

	SViewCellBuffer( void ) {}
	SViewCellBuffer( viewaccessor_ptr_t accessor, LineAdornmentsProvider * provider )
		: m_ViewAccessor{ accessor }, m_LineAdornmentsProvider{ provider } {}

	LineAdornmentsProvider * GetLineAdornmentsProvider( void ) const {
		return m_LineAdornmentsProvider;
	}

	const ChangeTracker & GetTracker( void ) const {
		return m_Tracker;
	}

	vint_t GetGlobalTrackerLine( unsigned idx ) const;

	vint_t LogLineToViewLine( vint_t log_line_no, bool exact = false ) const {
		return m_ViewAccessor->LogLineToViewLine( log_line_no, exact );
	}

	vint_t ViewLineToLogLine( vint_t view_line_no ) const {
		return m_ViewAccessor->ViewLineToLogLine( view_line_no );
	}

	const LineBuffer & GetLine( e_LineData type, vint_t view_line_no ) const {
		return m_ViewAccessor->GetLine( type, view_line_no, m_FieldViewMask );
	}

	bool IsEmpty( void ) const {
		return m_IsEmpty;
	}

	// NIEL remove
	vint_t GetNumLines( void ) const {
		return IsEmpty() ? 0 : m_NumLinesOrOne;
	}

	// update the view to contain solely logfile lines which are matched by
	// the given selector
	void Filter( Selector * selector, bool add_irregular );

	// set the field mask and re-calculate line lengths
	void SetFieldMask( uint64_t field_mask );

	std::vector<nlineno_t> Search( Selector * selector ) const;
	int MarkValue( vint_t line_no, int marker_base ) const;

	// apply callback to a single line; signature is void f(const LineAccessor & log_line)
// NIEL should not be needed - move callers to the accessor
	template<typename T_FUNC>
	void VisitLine( nlineno_t visit_line_no, T_FUNC & functor )
	{
		m_ViewAccessor->VisitLine( visit_line_no, functor );
	}

public:
	// Scintilla interfaces

	char CharAt( vint_t position ) const override;
	void GetCharRange( char * buffer, vint_t position, vint_t lengthRetrieve ) const override;
	char StyleAt( vint_t position ) const override;
	void GetStyleRange( unsigned char * buffer, vint_t position, vint_t lengthRetrieve ) const override;

	const char *BufferPointer( void ) override {
		return Unsupported<char*>( __FUNCTION__ );
	}
	const char *RangePointer( vint_t /* position */, vint_t /* rangeLength */ ) override {
		return Unsupported<char*>( __FUNCTION__ );
	}

	vint_t GapPosition() const override {
		return 0;
	}

	vint_t Length( void ) const override;

	void Allocate( vint_t /*newSize*/ ) override {
		UnsupportedVoid( __FUNCTION__ );
	}

	vint_t GetLineEndTypes() const override {
		return Unsupported<vint_t>( __FUNCTION__ );
	}
	void SetLineEndTypes( int /* utf8LineEnds */ ) override {
		UnsupportedVoid( __FUNCTION__ );
	}
	bool ContainsLineEnd( const char * /* s */, int /* length */ ) const override {
		return Unsupported<bool>( __FUNCTION__ );
	}

	void SetPerLine( PerLine * /*pl*/ ) override {
		// allow, but ignore
	}

	vint_t Lines( void ) const override;
	vint_t LineStart( vint_t line ) const override;
	vint_t LineFromPosition( vint_t pos ) const  override;


	void InsertLine( vint_t /*line*/, vint_t /*position*/, bool /*lineStart*/ ) override {
		UnsupportedVoid( __FUNCTION__ );
	}

	void RemoveLine( vint_t /*line*/ ) override {
		UnsupportedVoid( __FUNCTION__ );
	}

	const char *InsertString( vint_t /*position*/, const char * /*s*/, vint_t /*insertLength*/, bool &/*startSequence*/ ) override {
		return Unsupported<char*>( __FUNCTION__ );
	}

	bool SetStyleAt( vint_t /*position*/, char /*styleValue*/ ) override {
		return Unsupported<bool>( __FUNCTION__ );
	}

	bool SetStyleFor( vint_t /*position*/, vint_t /*length*/, char /*styleValue*/ ) override {
		return Unsupported<bool>( __FUNCTION__ );
	}

	const char *DeleteChars( vint_t /*position*/, vint_t /*deleteLength*/, bool &/*startSequence*/ ) override {
		return Unsupported<char*>( __FUNCTION__ );
	}

	bool IsReadOnly( void ) const override {
		return true;
	}
	void SetReadOnly( bool /*set*/ ) override {
		// allow, but ignore
	}

	void SetSavePoint( void ) override {
		UnsupportedVoid( __FUNCTION__ );
	}
	bool IsSavePoint( void ) const override {
		return false;
	}

	void TentativeStart() override {
		UnsupportedVoid( __FUNCTION__ );
	}
	void TentativeCommit() override {
		UnsupportedVoid( __FUNCTION__ );
	}
	bool TentativeActive() const override {
		return false;
	}
	vint_t TentativeSteps() override {
		return Unsupported<vint_t>( __FUNCTION__ );
	}

	bool SetUndoCollection( bool /*collectUndo*/ ) override {
		return Unsupported<bool>( __FUNCTION__ );
	}
	bool IsCollectingUndo( void ) const override {
		return Unsupported<bool>( __FUNCTION__ );
	}

	void BeginUndoAction( void ) override {
		// Scintilla often detects attempts to modify a read-only document very late,
		// and permits a surprising amoung of processing to take place. E.g. a
		// character press or a "paste" when a selection exists triggers calls to this
		// routine. Hence, set silent flag below.
		UnsupportedVoid( __FUNCTION__, true );
	}
	void EndUndoAction( void ) override {
		UnsupportedVoid( __FUNCTION__, true );
	}
	void AddUndoAction( vint_t /*token*/, bool /*mayCoalesce*/ ) override {
		UnsupportedVoid( __FUNCTION__ );
	}
	void DeleteUndoHistory() override {
		UnsupportedVoid( __FUNCTION__ );
	}

	bool CanUndo( void ) const override {
		return false;
	}
	vint_t StartUndo( void ) override {
		return Unsupported<bool>( __FUNCTION__ );
	}

	const Action &GetUndoStep( void ) const override {
		return * Unsupported<Action*>( __FUNCTION__ );
	}
	void PerformUndoStep( void ) override {
		UnsupportedVoid( __FUNCTION__ );
	}

	bool CanRedo( void ) const override {
		return false;
	}
	vint_t StartRedo( void ) override {
		return Unsupported<bool>( __FUNCTION__ );
	}

	const Action &GetRedoStep( void ) const override {
		return * Unsupported<Action*>( __FUNCTION__ );
	}
	void PerformRedoStep( void ) override {
		UnsupportedVoid( __FUNCTION__ );
	}
};

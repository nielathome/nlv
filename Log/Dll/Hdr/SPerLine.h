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

// Scintilla includes
#include <scintilla/src/VContent.h>
#include <scintilla/include/Scintilla.h>
#include <scintilla/src/CellBuffer.h>
#include <scintilla/src/ContractionState.h>
#include <scintilla/src/PerLine.h>

// C++ includes
#include <unordered_map>

// Application includes
#include "Ntypes.h"
#include "Cache.h"



/*-----------------------------------------------------------------------
 * SLineMarkers
 -----------------------------------------------------------------------*/

class SLineMarkers : public VLineMarkers
{
private:
	// most markers are handled via the logfile
	adornments_ptr_t m_Adornments;

	// the history line marker is handled locally
	int m_HistoryLineNo{ -1 };

	// view data
	viewaccessor_ptr_t m_ViewAccessor;
	const ViewMap * m_ViewMap;
	const ViewLineTranslation * m_ViewLineTranslation;

protected:
	vint_t HistoryLineMarkValue( vint_t view_line_no );
	vint_t ViewMarkValue( vint_t line );

public:
	SLineMarkers( adornments_ptr_t adornments, viewaccessor_ptr_t view_accessor )
		:
		m_Adornments{ adornments },
		m_ViewAccessor{ view_accessor },
		m_ViewMap{ view_accessor->GetMap() },
		m_ViewLineTranslation{ view_accessor->GetLineTranslation() }
	{
		if( !m_ViewMap )
			throw std::runtime_error{ "ViewAccessor has no ViewMap" };
		if( !m_ViewLineTranslation )
			throw std::runtime_error{ "ViewAccessor has no ViewLineTranslation" };
	}

	void SetHistoryLine( vint_t line_no ) {
		m_HistoryLineNo = line_no;
	}

	vint_t MarkValue( vint_t line ) override;

	// disable standard Scintilla interfaces

	vint_t MarkerNext( vint_t /* lineStart */, vint_t /* mask */ ) const override {
		return Unsupported<vint_t>( __FUNCTION__ );
	}

	vint_t AddMark( vint_t /* line */, vint_t /* markerNum */, vint_t /* lines */ ) override {
		return Unsupported<vint_t>( __FUNCTION__ );
	}

	void MergeMarkers( vint_t /* pos */ ) override {
		UnsupportedVoid( __FUNCTION__ );
	}

	bool DeleteMark( vint_t /* line */, vint_t /* markerNum */, bool /* all */ ) override {
		return Unsupported<bool>( __FUNCTION__ );
	}

	void DeleteMarkFromHandle( vint_t /* markerHandle */ ) override {
		UnsupportedVoid( __FUNCTION__ );
	}

	vint_t LineFromHandle( vint_t /* markerHandle */ ) override {
		return Unsupported<vint_t>( __FUNCTION__ );
	}
};

using linemarker_ptr_t = boost::intrusive_ptr<SLineMarkers>;



/*-----------------------------------------------------------------------
 * SLineLevels
 -----------------------------------------------------------------------*/

// disable support for line levels
class SLineLevels : public VLineLevels
{
public:
	void ExpandLevels( vint_t /* sizeNew */ ) override {
		UnsupportedVoid( __FUNCTION__ );
	}

	void ClearLevels( void ) override {
		UnsupportedVoid( __FUNCTION__ );
	}

	vint_t SetLevel( vint_t /* line */, vint_t /* level */, vint_t /* lines */ ) override {
		return Unsupported<vint_t>( __FUNCTION__ );
	}

	vint_t GetLevel( vint_t /* line */ ) const override {
		return SC_FOLDLEVELBASE;
	}
};

using linelevel_ptr_t = boost::intrusive_ptr<SLineLevels>;



/*-----------------------------------------------------------------------
 * SLineState
 -----------------------------------------------------------------------*/

// disable support for line state
class SLineState : public VLineState
{
public:
	vint_t SetLineState( vint_t /* line */, vint_t /* state */ ) override {
		return Unsupported<vint_t>( __FUNCTION__ );
	}

	vint_t GetLineState( vint_t /* line */ ) override {
		return 0;
	}

	vint_t GetMaxLineState() const override {
		return Unsupported<vint_t>( __FUNCTION__ );
	}
};

using linestate_ptr_t = boost::intrusive_ptr<SLineState>;



/*-----------------------------------------------------------------------
 * SLineMarginText
 -----------------------------------------------------------------------*/

class SLineMarginText : public VLineAnnotation
{
public:
	enum Type
	{
		e_None,
		e_LineNumber,
		e_Offset
	};

	enum Precision
	{
		e_MsecDotNsec,
		e_Usec,
		e_Msec,
		e_Sec,
		e_MinSec,
		e_HourMinSec,
		e_DayHourMinSec
	};

private:
	// view data
	viewaccessor_ptr_t m_ViewAccessor;
	const ViewLineTranslation * m_ViewLineTranslation;
	const unsigned m_DateFieldId;

protected:
	using create_offsettext_func = void (*)(int64_t sec, int64_t nsec, std::ostringstream & strm);
	static void CreateOffsetText_MsecDotNsec( int64_t sec, int64_t nsec, std::ostringstream & strm );
	static void CreateOffsetText_Usec( int64_t sec, int64_t nsec, std::ostringstream & strm );
	static void CreateOffsetText_Msec( int64_t sec, int64_t nsec, std::ostringstream & strm );
	static void CreateOffsetText_Sec( int64_t sec, int64_t nsec, std::ostringstream & strm );
	static void CreateOffsetText_MinSec( int64_t sec, int64_t nsec, std::ostringstream & strm );
	static void CreateOffsetText_HourMinSec( int64_t sec, int64_t nsec, std::ostringstream & strm );
	static void CreateOffsetText_DayHourMinSec( int64_t sec, int64_t nsec, std::ostringstream & strm );
	create_offsettext_func m_CreateOffsetTextFunc{ nullptr };

	using create_text_func = void (SLineMarginText::*)(vint_t line, std::ostringstream & strm) const;
	void CreateLineNumberText( vint_t line, std::ostringstream & strm ) const;
	void CreateOffsetText( vint_t line, std::ostringstream & strm ) const;
	create_text_func m_CreateTextFunc{ nullptr };

protected:
	// one line text cache
	mutable vint_t m_LineNumber;
	mutable std::string m_LineText;

	void UpdateLineText( vint_t line ) const;
	const std::string & GetLineText( vint_t line ) const;

public:
	SLineMarginText( viewaccessor_ptr_t view_accessor, unsigned date_field_id )
		:
		m_ViewAccessor{ view_accessor },
		m_ViewLineTranslation{ view_accessor->GetLineTranslation() },
		m_DateFieldId{ date_field_id }
	{
		if( !m_ViewLineTranslation )
			throw std::runtime_error{ "ViewAccessor has no ViewLineTranslation" };
	}

	void Setup( Type type, Precision prec );

	// Scintilla interfaces

	vint_t Style( vint_t line ) const override;
	const char *Text( vint_t line ) const override;
	vint_t Length( vint_t line ) const override;

	// disable standard Scintilla interfaces

	bool MultipleStyles( vint_t /* line */ ) const override {
		return false;
	}

	void SetText( vint_t /* line */, const char * /* text */ ) override {
		UnsupportedVoid( __FUNCTION__ );
	}

	void ClearAll( void ) override {
		UnsupportedVoid( __FUNCTION__ );
	}

	void SetStyle( vint_t /* line */, vint_t /* style */ ) override {
		UnsupportedVoid( __FUNCTION__ );
	}

	void SetStyles( vint_t /* line */, const unsigned char * /* styles */ ) override {
		UnsupportedVoid( __FUNCTION__ );
	}

	const unsigned char *Styles( vint_t /* line */ ) const override {
		return nullptr;
	}

	vint_t Lines( vint_t line ) const override {
		return 1;
	}
};

using linemargintext_ptr_t = boost::intrusive_ptr<SLineMarginText>;



/*-----------------------------------------------------------------------
 * SLineAnnotation
 -----------------------------------------------------------------------*/

// forwards
class NAnnotation;
using annotationsizes_list_t = std::vector<std::pair<vint_t, vint_t>>;

class SLineAnnotation : public VLineAnnotation
{
private:
	// logfile annotations
	annotations_ptr_t m_LogAnnotations;
	ChangeTracker m_LogAnnotationsTracker;

	// view data
	viewaccessor_ptr_t m_ViewAccessor;
	const ViewLineTranslation * m_ViewLineTranslation;
	ChangeTracker m_ViewTracker;

protected:
	const NAnnotation * GetAnnotation( vint_t line ) const;

public:
	SLineAnnotation( annotations_ptr_t log_annotations, viewaccessor_ptr_t view_accessor )
		:
		m_LogAnnotations{ log_annotations },
		m_ViewAccessor{ view_accessor },
		m_ViewLineTranslation{ view_accessor->GetLineTranslation() }
	{
		if( !m_ViewLineTranslation )
			throw std::runtime_error{ "ViewAccessor has no ViewLineTranslation" };
	}

	bool HasStateChanged( void ) const;
	annotationsizes_list_t GetAnnotationSizes( void ) const;

	// Scintilla interfaces

	vint_t Style( vint_t line ) const override;
	void SetStyle( vint_t line, vint_t style ) override;
	const char *Text( vint_t line ) const override;
	void SetText( vint_t line, const char * text ) override;
	vint_t Length( vint_t line ) const override;
	vint_t Lines( vint_t line ) const override;

	// disable standard Scintilla interfaces

	bool MultipleStyles( vint_t /* line */ ) const override {
		return false;
	}

	void ClearAll( void ) override {
		UnsupportedVoid( __FUNCTION__ );
	}

	void SetStyles( vint_t /* line */, const unsigned char * /* styles */ ) override {
		UnsupportedVoid( __FUNCTION__ );
	}

	const unsigned char *Styles( vint_t /* line */ ) const override {
		return nullptr;
	}
};

using lineannotation_ptr_t = boost::intrusive_ptr<SLineAnnotation>;



/*-----------------------------------------------------------------------
 * SContractionState
 -----------------------------------------------------------------------*/

//
// It isn't ideal feeding the Editor's contraction state through to content.
// However, the default implementation within Scintilla has some serious flaws - mainly
// related to numerous sites where the processing performance is proportional to the
// number of lines in the document. This isn't acceptable here, so we implement a CS
// tightly coupled to the annotation system to give better behaviour.
//
class SContractionState : public VContractionState
{
private:
	// interface to annotations we're tracking
	lineannotation_ptr_t m_Annotations;

	// view data
	viewaccessor_ptr_t m_ViewAccessor;

	// cached annotation values
	mutable annotationsizes_list_t m_AnnotationSizes;

	// caches for tracking key line number information; it seems Scintilla rarely
	// keeps a copy of a value, even in a local variable, so endlessly re-requests
	// the same information
	using linecache_t = Cache<vint_t, vint_t>;

	static CacheStatistics s_DisplayFromDocStats;
	mutable linecache_t m_DisplayFromDoc{ s_DisplayFromDocStats };

	static CacheStatistics s_DocFromDisplayStats;
	mutable linecache_t m_DocFromDisplay{ s_DocFromDisplayStats };

	static CacheStatistics s_HeightStats;
	mutable linecache_t m_Height{ s_HeightStats };

	mutable vint_t m_LinesinDocument{ 0 };
	mutable vint_t m_LinesDisplayed{ 0 };

protected:
	vint_t SumAnnotationSizes( vint_t line ) const;
	void ValidateCache( void ) const ;

public:
	SContractionState( lineannotation_ptr_t annotations, viewaccessor_ptr_t view_accessor )
		: m_Annotations{ annotations }, m_ViewAccessor{ view_accessor } {}

	vint_t LinesInDoc() const override;
	vint_t LinesDisplayed() const override;
	vint_t DisplayFromDoc( vint_t lineDoc ) const override;
	vint_t DisplayLastFromDoc( int lineDoc ) const override;
	vint_t DocFromDisplay( vint_t lineDisplay ) const override;
	vint_t GetHeight( vint_t lineDoc ) const override;

	// disable standard Scintilla interfaces

	void Clear() override {
		UnsupportedVoid( __FUNCTION__ );
	}

	// ignore internal notifications of lines added/deleted
	void InsertLines( vint_t /* lineDoc */, vint_t /* lineCount */ ) override {}
	void DeleteLines( vint_t /* lineDoc */, vint_t /* lineCount */ ) override {}

	bool GetVisible( vint_t /* lineDoc */ ) const override {
		return true;
	}
	bool SetVisible( vint_t /* lineDocStart */, vint_t /* lineDocEnd */, bool /* visible */ ) override {
		return Unsupported<bool>( __FUNCTION__ );
	}

	// are any lines hidden?
	bool HiddenLines() const override {
		return false;
	}

	const char * GetFoldDisplayText( int /* lineDoc */ ) const override {
		return Unsupported<const char *>( __FUNCTION__ );
	}
	bool SetFoldDisplayText( int /* lineDoc */, const char * /*text */ ) override {
		return Unsupported<bool>( __FUNCTION__ );
	}

	bool GetExpanded( vint_t /* lineDoc */ ) const override {
		return true;
	}
	bool GetFoldDisplayTextShown( int /* lineDoc */ ) const {
		return Unsupported<bool>( __FUNCTION__ );
	}
	bool SetExpanded( vint_t /* lineDoc */, bool /* expanded */ ) override {
		return Unsupported<bool>( __FUNCTION__ );
	}
	vint_t ContractedNext( vint_t /* lineDocStart */ ) const override {
		return Unsupported<vint_t>( __FUNCTION__ );
	}

	bool SetHeight( vint_t /* lineDoc */, vint_t /* height */ ) override {
		return false;
	}

	void ShowAll() override {
		UnsupportedVoid( __FUNCTION__ );
	}
};

using contractionstate_ptr_t = boost::intrusive_ptr<SContractionState>;

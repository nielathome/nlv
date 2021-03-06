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
#include <vector>
#include <set>

// JSON includes
#include "nlohmann/json.hpp"
using json = nlohmann::json;

// Boost includes; must be after JSON, otherwise the JSON headers don't compile (!)
#include <boost/intrusive_ptr.hpp>
#include <boost/python/object_fwd.hpp>

// Application includes
#include "FileMap.h"
#include "LogAccessor.h"
#include "Match.h"
#include "Ntime.h"
#include "SCellBuffer.h"
#include "SPerLine.h"

// forwards
selector_ptr_t MakeSelector( boost::python::object match, bool empty_selects_all, const LogSchemaAccessor * schema = nullptr );



/*-----------------------------------------------------------------------
 * MarkerNumber
 -----------------------------------------------------------------------*/

enum MarkerNumber
{
	e_MarkerNumberStandardBase = 0,
	e_MarkerNumberTrackerBase = 8,
	e_MarkerNumberHistory = 16
};



/*-----------------------------------------------------------------------
 * NLifeTime
 -----------------------------------------------------------------------*/

// implementation of VLifeTime for Nlog DLL objects
class NLifeTime : public VLifeTime
{
protected:
	void Release( void ) override;
};



/*-----------------------------------------------------------------------
 * NStateManager
 -----------------------------------------------------------------------*/

// support for saving and restoring logfile state
class NStateManager
{
protected:
	// generic source/sink of state
	struct NStateProvider
	{
		virtual void GetState( json & store ) = 0;
		virtual void PutState( const json & store ) = 0;
	};

	// Note: not using unique_ptr here, as the Boost Python interface creates a move
	// constructor for NLogFile (and hence, NStateManager), which doesn't play nice
	// with maps of unique_ptrs
	using stateprovider_ptr_t = std::shared_ptr<NStateProvider>;
	using stateprovider_map_t = std::map<std::string, stateprovider_ptr_t>;
	stateprovider_map_t m_StateProviders;

	// implementation of a state provider via the function members of an unrelated
	// class (T_PTR)
	template<typename T_PTR, typename T_GETTER, typename T_PUTTER>
	class NStateProviderMethod : public NStateProvider
	{
	private:
		T_PTR m_Ptr;
		T_GETTER m_GetState;
		T_PUTTER m_PutState;

		void GetState( json & store ) override {
			(m_Ptr->*m_GetState)( store );
		}
		
		void PutState( const json & store ) override {
			(m_Ptr->*m_PutState)( store );
		}

	public:
		NStateProviderMethod( T_PTR ptr, T_GETTER getter, T_PUTTER putter )
			: m_Ptr{ ptr }, m_GetState{ getter }, m_PutState{ putter } {}
	};

	// helper to simplify making a NStateProviderMethod for a raw pointer + methods
	template<typename T_CLASS>
	using NStateProviderMethodRaw = NStateProviderMethod
	<
		T_CLASS*,
		void (T_CLASS::*)( json & ) const,
		void (T_CLASS::*)( const json & )
	>;

	template<typename T_CLASS>
	using stateprovidermethodraw_ptr_t = std::shared_ptr<NStateProviderMethodRaw<T_CLASS>>;

	template<typename T_CLASS>
	stateprovidermethodraw_ptr_t<T_CLASS> MakeStateProvider
	(
		T_CLASS * ptr,
		void (T_CLASS::*getter)( json & store ) const,
		void (T_CLASS::*putter)( const json & store )
	)
	{
		return std::make_shared<NStateProviderMethodRaw<T_CLASS>>( ptr, getter, putter );
	};

	// register a state provider with this state manager
	void RegisterStateProvider( const std::string & guid, stateprovider_ptr_t provider ) {
		m_StateProviders[guid] = provider;
	}

public:
	// Python interfaces

	// State management
	std::string GetState( void );
	void PutState( const std::string & state_text );
};



/*-----------------------------------------------------------------------
 * NAnnotation
 -----------------------------------------------------------------------*/

// user provided annotation for a line in a logfile
class NAnnotation
{
private:
	// the annotation's text and style
	std::string m_Text;
	vint_t m_StyleNo{ 0 };

	// the number of lines in the annotation (>= 1)
	vint_t m_NumLines;

public:
	NAnnotation( const char * text = "" );

	void GetState( json & store ) const;
	void PutState( const json & store );

	const char * GetText( void ) const {
		return m_Text.c_str();
	}
	vint_t GetTextLength( void ) const {
		return vint_cast( m_Text.size() );
	}

	vint_t GetStyle( void ) const {
		return m_StyleNo;
	}
	void SetStyle( vint_t style_no ) {
		m_StyleNo = style_no;
	}

	vint_t GetNumLines( void ) const {
		return m_NumLines;
	}
};



/*-----------------------------------------------------------------------
 * NAnnotations
 -----------------------------------------------------------------------*/

// list of user annotations for a log file
class NAnnotations
	:
	public NLifeTime,
	public NStateManager
{
private:
	// user specified annotations, stored in line number order
	using annotation_map_t = std::map<vint_t, NAnnotation>;
	annotation_map_t m_AnnotationMap;
	ChangeTracker m_Tracker{ true };

	// state support
	void GetState( json & store ) const;
	void PutState( const json & store );

protected:
	NAnnotations( void );

public:
	annotationsizes_list_t GetAnnotationSizes( void ) const;
	const NAnnotation * GetAnnotation( vint_t log_line_no ) const;
	void SetAnnotationText( vint_t log_line_no, const char * text );
	void SetAnnotationStyle( vint_t log_line_no, vint_t style );

	// find next annotated line in the given direction
	vint_t GetNextAnnotation( nlineno_t current, bool forward );

	const ChangeTracker & GetTracker( void ) const {
		return m_Tracker;
	}
};



/*-----------------------------------------------------------------------
 * NAdornments
 -----------------------------------------------------------------------*/

// list of user adornments (annotations, bookmarks etc) for a log file
class NAdornments : public NAnnotations
{
private:
	// auto-markers (derived via line selection)
	std::vector<selector_ptr_t> m_AutoMarkers;

	// user specified markers (aka "bookmarks")
	using UserMarkers = std::set<vint_t>;
	UserMarkers m_UserMarkers;

	// tracked line marker
	vint_t m_LocalTrackerLine{ -1 };

	// state support
	void GetState( json & store ) const;
	void PutState( const json & store );

public:
	NAdornments( void );

	// tracked line
	void SetLocalTrackerLine( vint_t log_line_no ) {
		m_LocalTrackerLine = log_line_no;
	}
	vint_t GetLocalTrackerLine( void ) const {
		return m_LocalTrackerLine;
	}

	// identify the set of log markers to show at a given line
	int LogMarkValue( vint_t log_line_no, const LineAccessor & line );

public:
	// Python interfaces

	// Marker control
	void SetNumAutoMarker( unsigned num_marker ) {
		m_AutoMarkers.clear();
		m_AutoMarkers.resize( num_marker );
	}

	bool SetAutoMarker( unsigned marker, boost::python::object match, logfile_ptr_t logfile );

	void ClearAutoMarker( unsigned marker ) {
		m_AutoMarkers[ marker ] = nullptr;
	}

	bool HasUsermark( vint_t log_line_no ) const;
	void ToggleUsermark( vint_t log_line_no );
	vint_t GetNextUsermark( vint_t log_line_no, bool forward );

	using NStateManager::GetState;
	using NStateManager::PutState;
};
using adornments_ptr_t = boost::intrusive_ptr<NAdornments>;



/*-------------------------------------------------------------------------
 * NLineAdornmentsProvider
 ------------------------------------------------------------------------*/

class NLineAdornmentsProvider : public LineAdornmentsProvider
{
private:
	adornments_ptr_t m_Adornments;

protected:
	// LogAdornmentsProvider interfaces
	bool IsBookMarked( nlineno_t log_line_no ) const override {
		return m_Adornments->HasUsermark( log_line_no );
	}

	bool IsAnnotated( nlineno_t log_line_no ) const override {
		return m_Adornments->GetAnnotation( log_line_no ) != nullptr;
	}

	void GetAnnotationText( nlineno_t log_line_no, const char ** first, const char ** last ) const override{
		const NAnnotation * annotation{ m_Adornments->GetAnnotation( log_line_no ) };
		if( annotation != nullptr )
		{
			*first = annotation->GetText();
			*last = *first + annotation->GetTextLength();
		}
	}

public:
	NLineAdornmentsProvider( adornments_ptr_t adornments )
		: m_Adornments{ adornments } {}

	adornments_ptr_t GetAdornments( void ) {
		return m_Adornments;
	}
};



/*-----------------------------------------------------------------------
 * NHiliter
 -----------------------------------------------------------------------*/

// An interface to control text hiliting in a view; also supports searching
// within the view
class NHiliter : public NLifeTime
{
private:
	// matcher/selector
	bool m_SelectorChanged{ true };
	selector_ptr_t m_Selector;
	
	// the view to search within
	logfile_ptr_t m_Logfile;
	viewaccessor_ptr_t m_ViewAccessor;

	// detect chnages in the underlying view accessor
	ChangeTracker m_ViewTracker;

private:
	// list of lines matched
	std::vector<nlineno_t> m_MatchedLines;
	void SetupMatchedLines( void );

public:
	// the Scintilla "indicator" matching to this hiliter
	unsigned m_Indicator;

	// write highlighting information to the Scintilla document
	void Hilite( const vint_t start, const char * first, const char * last, VControl * vcontrol );

public:
	NHiliter( unsigned indicator, logfile_ptr_t logfile, viewaccessor_ptr_t view_accessor )
		: m_Indicator{ indicator }, m_Logfile{ logfile }, m_ViewAccessor{ view_accessor } {}

public:
	// Python interfaces

	// find next matched line in the given direction
	bool SetMatch( boost::python::object match );
	nlineno_t Search( nlineno_t current, bool forward );
	bool Hit( nlineno_t line_no );
};
using hiliter_ptr_t = boost::intrusive_ptr<NHiliter>;



/*-----------------------------------------------------------------------
 * NViewCore
 -----------------------------------------------------------------------*/

class NViewCore
{
protected:
	NViewCore( logfile_ptr_t logfile = logfile_ptr_t{}, viewaccessor_ptr_t view_accessor = viewaccessor_ptr_t{} );

	// We are a view onto this logfile
	logfile_ptr_t m_Logfile;

	// our view accessor
	viewaccessor_ptr_t m_ViewAccessor;

protected:
	void Filter( selector_ptr_a selector, bool add_irregular );

public:
	bool Filter( boost::python::object match, bool add_irregular );

	// line count
	vint_t GetNumLines( void ) const {
		return m_ViewAccessor->GetNumLines();
	}
};



/*-----------------------------------------------------------------------
 * NViewFieldAccess
 -----------------------------------------------------------------------*/

class NViewFieldAccess : public virtual NViewCore
{
private:
	// numeric access to defined fields
	fieldvalue_t GetFieldValue( vint_t line_no, vint_t field_no );

public:
	// raw text access to defined text/fields

	std::string GetNonFieldText( vint_t line_no );
	std::string GetFieldText( vint_t line_no, vint_t field_no );

	// numeric access to defined fields

	uint64_t GetFieldValueUnsigned( vint_t line_no, vint_t field_no ) {
		return GetFieldValue( line_no, field_no ).Convert<uint64_t>();
	}

	int64_t GetFieldValueSigned( vint_t line_no, vint_t field_no ) {
		return GetFieldValue( line_no, field_no ).Convert<int64_t>();
	}

	double GetFieldValueFloat( vint_t line_no, vint_t field_no ) {
		return GetFieldValue( line_no, field_no ).Convert<double>();
	}
};



/*-----------------------------------------------------------------------
 * NViewLineTranslation
 -----------------------------------------------------------------------*/

class NViewLineTranslation : public virtual NViewCore
{
private:
	// line translation interface
	const ViewLineTranslation * m_ViewLineTranslation;

public:
	NViewLineTranslation( void );

	// line number translation between the view and the underlying logfile
	vint_t ViewLineToLogLine( vint_t view_line_no ) const;
	vint_t LogLineToViewLine( vint_t log_line_no, bool exact ) const;
};



/*-----------------------------------------------------------------------
 * NViewTimecode
 -----------------------------------------------------------------------*/

class NViewTimecode : public virtual NViewCore
{
protected:
	// line translation interface
	const ViewTimecode * m_ViewTimecode;

public:
	NViewTimecode( void );

	// numeric access to a line's timecode, timecode is referenced to UTC
	NTimecode * GetNearestUtcTimecode( vint_t line_no );
};



/*-----------------------------------------------------------------------
 * NViewHiliting
 -----------------------------------------------------------------------*/

class NViewHiliting : public virtual NViewCore
{
protected:
	// array of hiliters
	std::vector<hiliter_ptr_t> m_Hiliters;

public:
	// Python interfaces

	// Hiliting control
	void SetNumHiliter( unsigned num_hiliter );
	hiliter_ptr_t GetHiliter( unsigned hiliter ) {
		return m_Hiliters[ hiliter ];
	}

	// Field visibility
	virtual void SetFieldMask( uint64_t field_mask ) {
		ViewProperties * view_props{ m_ViewAccessor->GetProperties() };
		if( view_props != nullptr )
			view_props->SetFieldMask( field_mask );
	}
};



/*-----------------------------------------------------------------------
 * NLineSet
 -----------------------------------------------------------------------*/

class NLineSet
	:
	public NViewFieldAccess,
	public NViewTimecode,
	public NViewLineTranslation,
	public NLifeTime
{
public:
	NLineSet( logfile_ptr_t logfile, viewaccessor_ptr_t view_accessor );
};



/*-----------------------------------------------------------------------
 * NEventView
 -----------------------------------------------------------------------*/

class NEventView
	:
	public NViewFieldAccess,
	public NViewHiliting,
	public NLifeTime
{
public:
	// Python interfaces

	NEventView( logfile_ptr_t logfile, viewaccessor_ptr_t view_accessor );

	// Select the lines to display in the lineset
	bool Filter( boost::python::object match );

	// determine how the event view is sorted
	void Sort( unsigned col_num, int direction );

	// hierarchy access
	bool IsContainer( vint_t line_no );
	std::vector<int> GetChildren( vint_t line_no, bool view_flat );
	int GetParent( vint_t line_no );
	int LookupEventId( int64_t event_id );
};



/*-----------------------------------------------------------------------
 * NLogView
 -----------------------------------------------------------------------*/

// A particular view of a logfile. Provides a method to create a Scintilla
// compatible (virtualised) content interface of the view.
class NLogView
	:
	public NViewFieldAccess,
	public NViewTimecode,
	public NViewLineTranslation,
	public NViewHiliting,
	public VContent
{
private:
	// interfaces
	const ViewMap * m_ViewMap;
	const ViewLineTranslation * m_ViewLineTranslation;

	// virtualised cell buffer
	SViewCellBuffer m_CellBuffer;

	// virtualised marker/annotation/etc data
	linemarker_ptr_t m_LineMarker;
	linelevel_ptr_t  m_LineLevel;
	linestate_ptr_t m_LineState;
	linemargintext_ptr_t m_LineMargin;
	lineannotation_ptr_t m_LineAnnotation;
	contractionstate_ptr_t m_ContractionState;

	// helper to update Scintilla when document contents change
	class NTextChanged
	{
	private:
		const SViewCellBuffer & m_CellBuffer;
		VControl *m_Control{ nullptr };
		const vint_t m_OrigNumLines{ 0 };
		const vint_t m_OrigTextLength{ 0 };

	public:
		NTextChanged( const SViewCellBuffer & cell_buffer, VControl *control )
			:
			m_CellBuffer{ cell_buffer },
			m_Control{ control },
			m_OrigNumLines{ m_CellBuffer.Lines() },
			m_OrigTextLength{ m_CellBuffer.Length() }
		{}

		~NTextChanged( void ) {
			const vint_t new_text_length{ m_CellBuffer.Length() };
			m_Control->VTextChanged( m_OrigNumLines, m_OrigTextLength, new_text_length );
		}
	};

private:
	adornments_ptr_t GetAdornments( void );
	vint_t GetNextVisibleLine( vint_t view_line_no, bool forward, vint_t( NAdornments::*get_next_log_line )(vint_t, bool) );

protected:
	// VContent interfaces
	void Release( void ) override;
	SViewCellBuffer *__stdcall GetCellBuffer( void ) override;
	void __stdcall ReleaseCellBuffer( VCellBuffer * cell_buffer ) override;
	VLineMarkers * __stdcall GetLineMarkers( void ) override;
	VLineLevels * __stdcall GetLineLevels( void ) override;
	VLineState * __stdcall GetLineState( void ) override;
	VLineAnnotation * __stdcall GetLineMargin( void ) override;
	VLineAnnotation * __stdcall GetLineAnnotation( void ) override;
	VContractionState * __stdcall GetContractionState( void ) override;

	// VObserver interfaces
	void __stdcall Notify_StartDrawLine( vint_t line_no ) override;

public:
	NLogView( logfile_ptr_t logfile, viewaccessor_ptr_t view_accessor );

public:
	// Python interfaces

	// Create an interface Scintilla can use to acces this view of the logfile.
	virtual unsigned long long GetContent( void );

	// Select the lines to display in the view
	bool Filter( boost::python::object match );

	// Field visibility
	void SetFieldMask( uint64_t field_mask ) override;

	// Bookmarks ("user" defined marker)
	void ToggleBookmarks( vint_t view_fm_line, vint_t view_to_line );
	vint_t GetNextBookmark( vint_t view_line_no, bool forward );

	// find next annotated line in this view in the given direction
	vint_t GetNextAnnotation( nlineno_t current, bool forward );

	// tracked line marker support
	void SetLocalTrackerLine( vint_t line_no );
	vint_t GetLocalTrackerLine( void );
	vint_t GetGlobalTrackerLine( unsigned idx );

	// margin setup
	void SetHistoryLine( vint_t line_no );
	void SetupMarginText( SLineMarginText::Type type, SLineMarginText::Precision prec );
};



/*-----------------------------------------------------------------------
 * NLogfile
 -----------------------------------------------------------------------*/

// Interface to an Nlog Logfile.
class NLogfile : public NLifeTime
{
private:
	// the logfile's text
	logaccessor_ptr_t m_LogAccessor;

	// the logfile's adornments
	adornments_ptr_t m_Adornments;


public:
	// Python interfaces

	NLogfile( logaccessor_ptr_t && log_accessor );
	Error Open( const std::wstring & file_path, ProgressMeter * progress );

	// returns raw pointer, caller must hold ownership over this object
	// for as long as the raw-pointer is needed
	LogAccessor * GetLogAccessor( void ) const {
		return m_LogAccessor.get();
	}

	const LogSchemaAccessor * GetSchema( void ) const {
		return GetLogAccessor()->GetSchema();
	}

	adornments_ptr_t GetAdornments( void ) const {
		return m_Adornments;
	}

public:
	// Python interfaces

	// State management
	std::string GetState( void ) {
		return m_Adornments->GetState();
	}

	void PutState( const std::string & state_text ) {
		m_Adornments->PutState( state_text );
	}

	// View management
	logview_ptr_t CreateLogView( void );
	eventview_ptr_t CreateEventView( void );
	lineset_ptr_t CreateLineSet( boost::python::object match );

	// Marker control
	void SetNumAutoMarker( unsigned num_marker ) {
		m_Adornments->SetNumAutoMarker( num_marker );
	}

	bool SetAutoMarker( unsigned marker, boost::python::object match );

	void ClearAutoMarker( unsigned marker ) {
		m_Adornments->ClearAutoMarker( marker );
	}

	void SetTimezoneOffset( int offset_sec ) {
		GetLogAccessor()->SetTimezoneOffset( offset_sec );
	}

	NTimecodeBase * GetTimecodeBase( void ) const {
		const NTimecodeBase & base{ GetLogAccessor()->GetSchema()->GetTimecodeBase() };
		return new NTimecodeBase{ base };
	}
};

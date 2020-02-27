#
# Copyright (C) Niel Clausen 2019-2020. All rights reserved.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#

# Python imports

import comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0
from comtypes import COMObject, GUID, COMMETHOD
from ctypes import c_int, c_ulong, c_wchar_p, HRESULT
import logging
import os
from pathlib import Path
import pythoncom
import sys
import win32com
import win32con
import win32gui
import winreg

# Application imports 
from .DataExplorer import G_DataExplorerProvider
from .DataExplorer import G_DataExplorerSync
from .EventProjector import ConnectDb
from .EventProjector import G_Quantifier
from .EventProjector import G_ProjectionSchema
from .EventProjector import G_ProjectionTypeManager
from .EventProjector import G_ScriptGuard
from .Global import G_Global
from .Global import G_PerfTimerScope
from .StyleNode import G_ColourTraits

# wxWidgets imports
import wx
import wx.html2

# Content provider interface
import Nlog



## IDeveloperConsoleMessageReceiver ########################

#
# Copied/edited from comtypes generated code:
#   >>> import comtypes
#   >>> from comtypes.client import GetModule
#   >>> GetModule("c:/Windows/System32/mshtml.tlb")
#   <module 'comtypes.gen._3050F1C5_98B5_11CF_BB82_00AA00BDCE0B_0_4_0' from 'lib\site-packages\comtypes\gen\_3050F1C5_98B5_11CF_BB82_00AA00BDCE0B_0_4_0.py'>
#

class IDeveloperConsoleMessageReceiver(comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0.IUnknown):
    _case_insensitive_ = True
    'IDeveloperConsoleMessageReceiver interface'
    _iid_ = GUID('{30510808-98B5-11CF-BB82-00AA00BDCE0B}')
    _idlflags_ = []

    WSTRING = c_wchar_p

    # values for enumeration '_DEV_CONSOLE_MESSAGE_LEVEL'
    DCML_INFORMATIONAL = 0
    DCML_WARNING = 1
    DCML_ERROR = 2
    DEV_CONSOLE_MESSAGE_LEVEL_Max = 2147483647
    _DEV_CONSOLE_MESSAGE_LEVEL = c_int # enum

    _methods_ = [
        COMMETHOD([], HRESULT, 'write',
                  ( ['in'], WSTRING, 'source' ),
                  ( ['in'], _DEV_CONSOLE_MESSAGE_LEVEL, 'level' ),
                  ( ['in'], c_int, 'messageId' ),
                  ( ['in'], WSTRING, 'messageText' )),
        COMMETHOD([], HRESULT, 'WriteWithUrl',
                  ( ['in'], WSTRING, 'source' ),
                  ( ['in'], _DEV_CONSOLE_MESSAGE_LEVEL, 'level' ),
                  ( ['in'], c_int, 'messageId' ),
                  ( ['in'], WSTRING, 'messageText' ),
                  ( ['in'], WSTRING, 'fileUrl' )),
        COMMETHOD([], HRESULT, 'WriteWithUrlAndLine',
                  ( ['in'], WSTRING, 'source' ),
                  ( ['in'], _DEV_CONSOLE_MESSAGE_LEVEL, 'level' ),
                  ( ['in'], c_int, 'messageId' ),
                  ( ['in'], WSTRING, 'messageText' ),
                  ( ['in'], WSTRING, 'fileUrl' ),
                  ( ['in'], c_ulong, 'line' )),
        COMMETHOD([], HRESULT, 'WriteWithUrlLineAndColumn',
                  ( ['in'], WSTRING, 'source' ),
                  ( ['in'], _DEV_CONSOLE_MESSAGE_LEVEL, 'level' ),
                  ( ['in'], c_int, 'messageId' ),
                  ( ['in'], WSTRING, 'messageText' ),
                  ( ['in'], WSTRING, 'fileUrl' ),
                  ( ['in'], c_ulong, 'line' ),
                  ( ['in'], c_ulong, 'column' ))
    ]



## G_DeveloperConsoleMessageReceiver #######################

class G_DeveloperConsoleMessageReceiver(COMObject):
    #-------------------------------------------------------
    WantNoisy = False
    Noisy = [
        "Navigation occurred.",
        "The code on this page disabled back and forward caching." # see http://go.microsoft.com/fwlink/?LinkID=291337 
    ]

    @classmethod
    def LevelToText(cls, level):
        if level == IDeveloperConsoleMessageReceiver.DCML_INFORMATIONAL:
            return "info"
        elif level == IDeveloperConsoleMessageReceiver.DCML_WARNING:
            return "warning"
        elif level == IDeveloperConsoleMessageReceiver.DCML_ERROR:
            return "error"
        else:
            return "unknown"


    @classmethod
    def LogMessage(cls, source, level, messageId, messageText, fileUrl = "", line = 0, column = 0):
        if not cls.WantNoisy:
            for text in cls.Noisy:
                if text in messageText:
                    return

        ltext = cls.LevelToText(level)
        ftext = "{}(level:{} id:{} line:{} col:{}) {} {}".format(source, ltext, messageId, line, column, messageText, fileUrl)

        if source == "CONSOLE":
            logging.info(ftext)
        else:
            logging.debug(ftext)


    #-------------------------------------------------------
    _com_interfaces_ = [IDeveloperConsoleMessageReceiver]


    #-------------------------------------------------------
    def write(self, source, level, messageId, messageText):
        self.LogMessage(source, level, messageId, messageText)

    def WriteWithUrl(self, source, level, messageId, messageText, fileUrl):
        self.LogMessage(source, level, messageId, messageText, fileUrl)

    def WriteWithUrlAndLine(self, source, level, messageId, messageText, fileUrl, line):
        self.LogMessage(source, level, messageId, messageText, fileUrl, line)

    def WriteWithUrlLineAndColumn(self, source, level, messageId, messageText, fileUrl, line, column):
        self.LogMessage(source, level, messageId, messageText, fileUrl, line, column)



## G_TableHiliter ##########################################

class G_TableHiliter:

    #-------------------------------------------------------
    def __init__(self, id):
        self._Id = id
        self._Match = None
        self._Colour = None



## G_TableFieldFormatter ###################################

class G_TableFieldFormatter:
    """Mediate the analyser script's access to the table format system"""

    #-------------------------------------------------------
    def __init__(self, item_attr):
        self._ItemAttr = item_attr
        self._FgLocked = False
        self._BgLocked = False


    #-------------------------------------------------------
    def SetBold(self, set):
        self._ItemAttr.SetBold(set)

    def SetItalic(self, set):
        self._ItemAttr.SetItalic(set)

 
    #-------------------------------------------------------
    def SetFgColour(self, colour_id, lock_fg = False):
        if not self._FgLocked:
            self._ItemAttr.SetColour(G_ColourTraits.MakeColour(colour_id))
            self._FgLocked = lock_fg
 
    def SetBgColour(self, colour_id, lock_bg = False):
        if not self._BgLocked:
            self._ItemAttr.SetBackgroundColour(G_ColourTraits.MakeColour(colour_id))
            self._BgLocked = lock_bg



## G_TableDataModel ########################################

class G_TableDataModel(wx.dataview.DataViewModel, G_DataExplorerProvider):

    #-------------------------------------------------------
    def __init__(self, doc_url):
        super().__init__()

        self._ViewFlat = True
        self._DocumentUrl = doc_url
        self._RawFieldMask = 0
        self._IsValid = True
        self._InvalidColour = G_ColourTraits.MakeColour("FIREBRICK")
        self._HistoryColour = G_ColourTraits.MakeColour("LIGHT SLATE BLUE")
        self._ColumnColours = []
        self._FilterMatch = None
        self._Hiliters = []
        self._HistoryKey = None
        self.Reset()

        self._Icons = [
            wx.ArtProvider.GetIcon(wx.ART_NORMAL_FILE, wx.ART_TOOLBAR, (16, 16)),
            wx.ArtProvider.GetIcon(wx.ART_FOLDER, wx.ART_TOOLBAR, (16, 16))
        ]


    #-------------------------------------------------------
    @staticmethod
    def ItemToKey(item):
        # in SQL terms, the key is the entry's line number in
        # the display table (where line number is one less than
        # the "rowid"); note, items cannot be zero, so offset here
        id = item.GetID()
        if id is None:
            return None
        else:
            return int(id) - 1


    @staticmethod
    def KeyToItem(key):
        return wx.dataview.DataViewItem(key + 1)


    #-------------------------------------------------------
    def ClearDataValidity(self, reason):
        self._HistoryKey = None
        self.SetDataValidity(reason)

    def Reset(self, table_schema = None):
        self._N_Logfile = None
        self._N_EventView = None

        if table_schema is None:
            table_schema = G_ProjectionSchema()
        self._TableSchema = table_schema

        self._ModelColumnToFieldId = []
        field_id = 0
        for field_schema in self._TableSchema:
            fid = -1

            if field_schema.Available:
                fid = field_id
                field_id += 1

            self._ModelColumnToFieldId.append(fid)

        self.ClearDataValidity("Model reset")


    #-------------------------------------------------------
    def GetFieldValue(self, item_key, col_num):
        field_schema = self._TableSchema[col_num]
        return G_ProjectionTypeManager.GetValue(field_schema, self._N_EventView, item_key, col_num)

    def GetFieldDisplayValue(self, item, col_num):
        item_key = self.ItemToKey(item)
        field_schema = self._TableSchema[col_num]
        icon = None

        if field_schema.IsFirst:
            icon = self._Icons[self.IsContainer(item)]

        return G_ProjectionTypeManager.GetDisplayValue(field_schema, icon, self._N_EventView, item_key, col_num)


    #-------------------------------------------------------
    def GetTableSchema(self):
        return self._TableSchema

    def GetEventView(self):
        return self._N_EventView

    def GetNumItems(self):
        if self._N_EventView is None:
            return 0
        else:
            return self._N_EventView.GetNumLines()


    #-------------------------------------------------------
    def GetLocation(self, item):
        key = self.ItemToKey(item)
        if key is None:
            return key
        else:
            return str(key)

    def SetHistoryKey(self, key):
        self._HistoryKey = key
        return self.KeyToItem(key)

    def CreateDataExplorerPage(self, builder, location, page):
        schema = self._TableSchema
        if schema.UserDataExplorerOpen is not None:
            schema.UserDataExplorerOpen(builder)

        builder.AddPageHeading("Event")
        if self._DocumentUrl is not None:
            builder.AddLink(self._DocumentUrl, "Show log ...")

        item_key = int(location)
        item = self.KeyToItem(item_key)
        table_schema = self._TableSchema

        for col_num, field in enumerate(self._TableSchema):
            if field.Available:
                display_value = self.GetFieldDisplayValue(item, col_num)
                if isinstance(display_value, str):
                    text = display_value
                elif isinstance(display_value, bool):
                    if display_value:
                        text = "True"
                    else:
                        text = "False"
                else:
                    text = display_value.Text

                if text is not None and len(text) != 0:
                    if field.ExplorerFormatter is not None:
                        with G_ScriptGuard("CreateFieldDataForExplorer"):
                            field.ExplorerFormatter(builder, field.Name, text)
                    else:
                        builder.AddField(field.Name, text)
                    
        if schema.UserDataExplorerClose is not None:
            schema.UserDataExplorerClose(builder)


    #-------------------------------------------------------
    def GetEventRange(self, item):
        table_schema = self._TableSchema
        if table_schema.ColStartOffset is None:
            return (None, None)

        if item is None:
            return (None, None)

        item_key = self.ItemToKey(item)
        start_offset = finish_offset = self.GetFieldValue(item_key, table_schema.ColStartOffset)

        # if we have a duration, then use it
        if table_schema.ColDuration is not None:
            duration = self.GetFieldValue(item_key, table_schema.ColDuration)
            finish_offset = start_offset + duration

        # otherwise, calculate duration based on available finish time
        elif table_schema.ColFinishOffset is not None:
            finish_offset = self.GetFieldValue(item_key, table_schema.ColFinishOffset)

        utc_datum = self._N_Logfile.GetTimecodeBase().GetUtcDatum()
        return (Nlog.Timecode(utc_datum, start_offset),
            Nlog.Timecode(utc_datum, finish_offset)
        )


    #-------------------------------------------------------
    def GetColumnCount(self):
        return len(self._TableSchema)


    def GetColumnType(self, col_num):
        # Maintenance note: have never seen this called
        raise RuntimeError("GetColumnType is unimplemented")


    def GetChildren(self, parent_item, children):
        """
        The view calls this method to find the children of any node in the
        control. There is an implicit hidden root node, and the top level
        item(s) should be reported as children of this node. A List view
        simply provides all items as children of this hidden root. A Tree
        view adds additional items as children of the other items, as needed,
        to provide the tree hierarchy.
        """

        if self._N_EventView is None:
            return 0

        count = 0

        # "children" argument has no 'extend' method, so use iterators here
        def AppendChildren(item_keys):
            nonlocal count
            for item_key in item_keys:
                children.append(self.KeyToItem(item_key))
                count += 1

        item_key = -1
        if parent_item:
            item_key = self.ItemToKey(parent_item)

        AppendChildren(self._N_EventView.GetChildren(item_key, self._ViewFlat))

        return count


    def IsContainer(self, item):
        """Return True if the item has children, False otherwise."""

        # The hidden root is a container
        if not item:
            return True

        if self._ViewFlat:
            return False
        else:
            item_key = self.ItemToKey(item)
            return self._N_EventView.IsContainer(item_key)


    def HasContainerColumns(self, item):
        """
        Override this method to indicate if a container item merely acts as a
        headline (or for categorisation) or if it also acts a normal item with
        entries for further columns.
        """
        return True


    def GetParent(self, item):
        "Return the item which is this item's parent."""
        if self._ViewFlat:
            return wx.dataview.NullDataViewItem

        item_key = self.ItemToKey(item)
        parent_key = self._N_EventView.GetParent(item_key)

        if parent_key < 0:
            return wx.dataview.NullDataViewItem
        else:
            return self.KeyToItem(parent_key)


    def GetAttr(self, item, col_num, attr):
        """Pass formatting request to any formatter registered by the recogniser"""
        wrapped_attr = G_TableFieldFormatter(attr)

        if not self._IsValid:
            wrapped_attr.SetFgColour(self._InvalidColour, True)

        if col_num < len(self._ModelColumnToFieldId):
            field_id = self._ModelColumnToFieldId[col_num]
            if field_id >= 0 and field_id < len(self._ColumnColours):
                wrapped_attr.SetFgColour(self._ColumnColours[field_id])

        item_key = self.ItemToKey(item)
        if item_key == self._HistoryKey:
            wrapped_attr.SetBgColour(self._HistoryColour, True)

        for hiliter in self._Hiliters:
            if self._N_EventView.GetHiliter(hiliter._Id).Hit(item_key):
                wrapped_attr.SetBgColour(hiliter._Colour)
                break

        view_formatter = self._TableSchema[col_num].ViewFormatter
        if view_formatter is not None:
            with G_ScriptGuard("GetFieldAttributesForDisplay"):
                view_formatter(self.GetFieldValue(item_key, col_num), wrapped_attr)

        return True


    def GetValue(self, item, col_num):
        """Return the value to be displayed for this item and column."""
        return self.GetFieldDisplayValue(item, col_num)


    def Compare(self, item_l, item_r, col_num, ascending):
        raise RuntimeError


    #-------------------------------------------------------
    def MapSelectionToEventIds(self, items):
        col_num = self._TableSchema.ColEventId
        return [self.GetFieldValue(self.ItemToKey(item), col_num) for item in items]


    #-------------------------------------------------------
    def LookupEventId(self, event_id):
        ret = None

        if self._N_EventView is not None:
            key = self._N_EventView.LookupEventId(event_id)
            if key >= 0:
                ret = self.KeyToItem(key)

        return ret


    #-------------------------------------------------------
    def GetNextItem(self, what, cur_item, forward, index = 0):
        cur_key = 0
        if cur_item is not None and cur_item:
          cur_key = self.ItemToKey(cur_item)
  
        if what == "hilite":
            next_key = self._N_EventView.GetHiliter(index).Search(cur_key, forward)

        if next_key >= 0:
            return self.KeyToItem(next_key)
        return None


    #-------------------------------------------------------
    def HiliteLineSet(self, hiliter, match = None):
        if match is not None:
            hiliter._Match = match

        if hiliter._Match is None:
            return True

        if self._N_EventView is None:
            return True

        return self._N_EventView.GetHiliter(hiliter._Id).SetMatch(hiliter._Match)

        
    def FilterLineSet(self, match):
        self._FilterMatch = match

        if self._N_Logfile is None:
            return False

        if match is not None and self._N_EventView is not None:
            return self._N_EventView.Filter(match)

        return True


    @G_Global.TimeFunction
    def UpdateContent(self, nesting, table_schema, filename, valid):
        self.Reset(table_schema)
        self.UpdateNesting(nesting, False)
        self.UpdateValidity(valid)

        num_fields = self.GetColumnCount()
        if Path(filename).exists() and num_fields != 0:
            self._N_Logfile = Nlog.MakeLogfile(filename, table_schema, G_Global.PulseProgressMeter)

        # robustness, for broken logfiles ...
        if self._N_Logfile is not None:
            self._N_EventView = self._N_Logfile.CreateEventView()

            self.MaskLineSet()
            self.FilterLineSet(self._FilterMatch)

            self._N_EventView.SetNumHiliter(len(self._Hiliters))
            for hiliter in self._Hiliters:
                self.HiliteLineSet(hiliter)
        
        self.Cleared()


    #-------------------------------------------------------
    def UpdateHiliterMatch(self, hiliter_id, match):
        hiliter = self._Hiliters[hiliter_id]
        return self.HiliteLineSet(hiliter, match)

    def UpdateHiliterColour(self, hiliter_id, colour):
        self._Hiliters[hiliter_id]._Colour = colour

    def SetNumHiliter(self, num_hiliter):
        self._Hiliters = [G_TableHiliter(i) for i in range(num_hiliter)]
        if self._N_EventView is not None:
            self._N_EventView.SetNumHiliter(num_hiliter)


    #-------------------------------------------------------
    def UpdateFilter(self, match):
        if not self.FilterLineSet(match):
            return False
        
        self.ClearDataValidity("Filter: {match}".format(match = match.GetDescription()))
        self.Cleared()
        return True


    #-------------------------------------------------------
    def UpdateSort(self, col_num):
        if self._N_EventView is not None:
            (data_col_offset, direction) = self._TableSchema[col_num].ToggleSortDirection()
            self._N_EventView.Sort(col_num + data_col_offset, direction)
            self.ClearDataValidity("Sorting")
            self.Cleared()
            return True
        else:
            return False


    #-------------------------------------------------------
    def CalcLineSetFieldMask(self, in_mask):
        # need to "unpack" the UI/raw mask to allow for hidden fields
        # in the schema; the result returned and also applied to the
        # _TableSchema array
        in_bit = 1
        out_bit = 1
        out_mask = 0
        is_first = True
        
        for field_schema in self._TableSchema:
            if field_schema.Available:
                field_schema.Visible = visible = bool(in_mask & in_bit)
                if visible:
                    out_mask |= out_bit
                    field_schema.IsFirst = is_first
                    is_first = False
                in_bit <<= 1

            out_bit <<= 1

        return out_mask

    
    def MaskLineSet(self, in_mask = None):
        # set the field_mask of the underlying view - as this can effect
        # the outcome of searching and filtering actions that apply to
        # whole lines (e.g. literals and regular expressions)
        if in_mask is None:
            in_mask = self._RawFieldMask
        self._RawFieldMask = in_mask

        if self._N_EventView is not None:
            full_mask = self.CalcLineSetFieldMask(in_mask)
            self._N_EventView.SetFieldMask(full_mask)

            
    def SetFieldMask(self, in_mask):
        self.MaskLineSet(in_mask)


    #-------------------------------------------------------
    def UpdateFieldColour(self, field_id, colour_id):
        # note: can't depend on the table schema existing yet, so
        # the data structures here are kept separate from the schema
        while field_id >= len(self._ColumnColours):
            self._ColumnColours.append(G_ColourTraits.MakeColour("BLACK"))

        self._ColumnColours[field_id] = G_ColourTraits.MakeColour(colour_id)


    #-------------------------------------------------------
    def UpdateNesting(self, nesting, do_rebuild = True):
        if nesting is None:
            return

        if self._TableSchema is None:
            return

        if not self._TableSchema.PermitNesting:
            return

        view_flat = not nesting
        if self._ViewFlat == view_flat:
            return

        self._ViewFlat = view_flat
        if do_rebuild:
            self.ClearDataValidity("Nesting level")
            self.Cleared()


    def UpdateValidity(self, valid):
        # the view is deemed valid if an analysis has taken place
        # since the last time the recogniser was modified
        if valid is None:
            return False

        if valid == self._IsValid:
            return False

        self._IsValid = valid
        return True


    def UpdateDisplay(self, nesting, valid):
        self.UpdateNesting(nesting)
        return self.UpdateValidity(valid)



## G_DataViewCtrl ##########################################

class G_DataViewCtrl(wx.dataview.DataViewCtrl):

    #-------------------------------------------------------
    def __init__(self, parent, flags, doc_url):
        super().__init__(
            parent,
            style = wx.dataview.DV_ROW_LINES
            | wx.dataview.DV_VERT_RULES
            | flags
        )

        self.AssociateModel(G_TableDataModel(doc_url))
        self.Bind(wx.dataview.EVT_DATAVIEW_COLUMN_HEADER_CLICK, self.OnColClick)


    #-------------------------------------------------------
    def GetTableSchema(self):
        return self.GetModel().GetTableSchema()


    #-------------------------------------------------------
    def GetEventView(self):
        return self.GetModel().GetEventView()


    #-------------------------------------------------------
    def ResetModel(self):
        self.ClearColumns()
        return self.GetModel().Reset()


    #-------------------------------------------------------
    def UpdateColumns(self):
        self.ClearColumns()
        for (model_num, field_schema) in enumerate(self.GetTableSchema()):
            if field_schema.Display():
                self.AppendColumn(G_ProjectionTypeManager.MakeDataViewColumn(field_schema, model_num))



    #-------------------------------------------------------
    def UpdateContent(self, nesting, table_schema, filename, valid):
        """Update the data view with new content"""

        # note: number of DataView columns is not the same as the number of
        # model columns; as some are hidden for internal use
        try:
            self.ClearColumns()
            self.GetModel().UpdateContent(nesting, table_schema, filename, valid)
            self.UpdateColumns()

        except FileNotFoundError as ex:
            pass


    #-------------------------------------------------------
    def UpdateDisplay(self, nesting = None, valid = None):
        if self.GetModel().UpdateDisplay(nesting, valid):
            self.Refresh()        


    #-------------------------------------------------------
    def SetFieldMask(self, field_mask):
        self.GetModel().SetFieldMask(field_mask)
        self.UpdateColumns()


    #-------------------------------------------------------
    def OnColClick(self, evt):
        col_pos = evt.GetColumn()
        column = self.GetColumn(col_pos)
        if column is not None:
            col_num = column.GetModelColumn()
            if self.GetModel().UpdateSort(col_num):
                self.Refresh()        



## G_TableViewCtrl #########################################

class G_TableViewCtrl(G_DataViewCtrl, G_DataExplorerSync):

    #-------------------------------------------------------
    def __init__(self, parent, selection_handler, multiple_selection, doc_url):
        flags = 0
        if multiple_selection:
            flags = wx.dataview.DV_MULTIPLE

        super().__init__(parent, flags, doc_url)

        self._SelectionHandler = selection_handler
        self._IsMultipleSelection = multiple_selection
        self.Bind(wx.dataview.EVT_DATAVIEW_SELECTION_CHANGED, self.OnItemActivated)


    #-------------------------------------------------------
    def GetNumItems(self):
        return self.GetModel().GetNumItems()


    #-------------------------------------------------------
    def GetSelectedEventIds(self):
        return self.GetModel().MapSelectionToEventIds(self.GetSelections())

    def ToggleSelectedEvent(self, event_id):
        item = self.GetModel().LookupEventId(event_id)
        if item is not None:
            if self.IsSelected(item):
                self.Unselect(item)
            else:
                self.Select(item)

            # the control does not generate an event, so fake one
            evt = wx.dataview.DataViewEvent()
            evt.SetItem(item)
            self.OnItemActivated(evt)


    #-------------------------------------------------------
    def GotoNextItem(self, what, forward = None, modifiers = None, index = 0):
        # call should pass either forward or modifiers
        if modifiers is not None:
            if modifiers == 0:
                forward = True
            elif modifiers == wx.MOD_SHIFT:
                forward = False
            else:
                # invalid key combination, so nothing to do
                return

        cur_item = None
        if self.HasSelection():
            cur_item = self.GetSelection()

        next_item = self.GetModel().GetNextItem(what, cur_item, forward, index)

        if next_item is not None:
            if cur_item is not None and self._IsMultipleSelection:
                self.UnselectAll()

            self.Select(next_item)
            self.EnsureVisible(next_item)


    #-------------------------------------------------------
    def UpdateHiliterMatch(self, hiliter_id, match):
        if self.GetModel().UpdateHiliterMatch(hiliter_id, match):
            self.Refresh()       
            return True 
        return False

    def UpdateHiliterColour(self, hiliter_id, colour):
        self.GetModel().UpdateHiliterColour(hiliter_id, colour)
        self.Refresh()       

    def SetNumHiliter(self, num_hiliter):
        self.GetModel().SetNumHiliter(num_hiliter)


    #-------------------------------------------------------
    def UpdateFilter(self, match):
        return self.GetModel().UpdateFilter(match)


    #-------------------------------------------------------
    def UpdateFieldColour(self, field_id, colour_id):
        self.GetModel().UpdateFieldColour(field_id, colour_id)
        self.Refresh()


    #-------------------------------------------------------
    def GetLocation(self, item):
        return self.GetModel().GetLocation(item)

    def ShowLocation(self, location):
        item = self.GetModel().SetHistoryKey(int(location))
        self.EnsureVisible(item)
        return True


    #-------------------------------------------------------
    def GetEventRange(self, event_no):
        return self.GetModel().GetEventRange(event_no)

    def OnItemActivated(self, evt):
        self._SelectionHandler(evt.GetItem())


    #-------------------------------------------------------
    def GetChildCtrl(self):
        """Fetch the Windows control"""
        for window in self.GetChildren():
            if len(window.GetLabel()) != 0: # potentially fragile; but there is no API for this
                return window

        return None



## G_Param #################################################

class G_Param:

    #-------------------------------------------------------
    def __init__(self, name, title, default, values = None):
        self.Name = name
        self.Title = title
        self.Default = default
        self.Values = values


    #-------------------------------------------------------
    def GetValueOrDefault(self, value):
        if value is None:
            value = self.Default
        return value



## G_BoolParam #############################################

class G_BoolParam(G_Param):

    #-------------------------------------------------------
    def __init__(self, name, title, default):
        super().__init__(name, title, default)


    #-------------------------------------------------------
    def MakeControl(self, parent, value, handler):
        self._Ctrl = wx.CheckBox(parent)
        self._Ctrl.SetValue(self.GetValueOrDefault(value))
        self._Ctrl.Bind(wx.EVT_CHECKBOX, handler)
        return self._Ctrl


    #-------------------------------------------------------
    def GetValue(self):
        return self._Ctrl.GetValue()



## G_ChoiceParam ###########################################

class G_ChoiceParam(G_Param):

    #-------------------------------------------------------
    def __init__(self, name, title, default, values):
        super().__init__(name, title, default, values)


    #-------------------------------------------------------
    def MakeControl(self, parent, value, handler):
        self._Ctrl = wx.Choice(parent)
        self._Ctrl.Set(self.Values)

        if value is None or value >= len(self.Values):
            value = self.Default
        self._Ctrl.SetSelection(value)
        self._Ctrl.Bind(wx.EVT_CHOICE, handler)
        return self._Ctrl


    #-------------------------------------------------------
    def GetValue(self):
        return self._Ctrl.GetSelection()



## G_ParameterCollector ####################################

class G_ParameterCollector:
    """Collect parameter data from a chart"""

    #-------------------------------------------------------
    def __init__(self):
        self._Params = []


    #-------------------------------------------------------
    def AddChoice(self, name, title, default, values):
        self._Params.append(G_ChoiceParam(name, title, default, values))


    #-------------------------------------------------------
    def AddBool(self, name, title, default):
        self._Params.append(G_BoolParam(name, title, default))


    #-------------------------------------------------------
    def Close(self):
        return self._Params



## G_ChartViewCtrlProxy ####################################

class G_ChartViewCtrlProxy:

    #-------------------------------------------------------
    def __init__(self, view_ctrl):
        self._ViewCtrl = view_ctrl


    def ExecuteScript(self, script):
        self._ViewCtrl.EnqueueScript(script)



## G_ChartViewCtrl #########################################

class G_ChartViewCtrl(wx.Panel):

    #-------------------------------------------------------
    _InitCharting = True
    _IIDMap = None
    _ConsoleRegistered = False


    @classmethod
    def _SetRegistryValue(cls, name, reg_path, value):
        try:
            winreg.CreateKey(winreg.HKEY_CURRENT_USER, reg_path)
            registry_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_WRITE)
            winreg.SetValueEx(registry_key, name, 0, winreg.REG_DWORD, value)
            winreg.CloseKey(registry_key)
            return True
        except WindowsError:
            return False


    @classmethod
    def _GetRegistryValue(cls,name, reg_path):
        try:
            registry_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_READ)
            value, regtype = winreg.QueryValueEx(registry_key, name)
            winreg.CloseKey(registry_key)
            return value
        except WindowsError:
            return None


    #-------------------------------------------------------
    @classmethod
    def InitCharting(cls):
        if not cls._InitCharting:
            return

        # Ensure JavaScript runs in embedded browser. Can be simplified
        # after wxPython-4.1.0. See https://github.com/wxWidgets/Phoenix/issues/1256.
        reg_path = r"Software\Microsoft\Internet Explorer\Main\FeatureControl\FEATURE_BROWSER_EMULATION"
        cls._SetRegistryValue(os.path.basename(sys.executable), reg_path, 11001)

        # makepy.py -i
        # {3050F1C5-98B5-11CF-BB82-00AA00BDCE0B}, lcid=0, major=4, minor=0
        module = win32com.client.gencache.EnsureModule('{3050F1C5-98B5-11CF-BB82-00AA00BDCE0B}', 0, 4, 0)
        cls._IIDMap = module.NamesToIIDMap

        cls._InitCharting = False


    #-------------------------------------------------------
    @classmethod
    def RegisterConsole(cls, doc):
        if G_ChartViewCtrl._ConsoleRegistered:
            return

        # warning: mixing the two Python COM libraries here.
        # pythoncom/win32com is good for Dispatch/OLE interfaces
        # and comtypes is good for custom interfaces

        # use comtypes to link a IDeveloperConsoleMessageReceiver
        # interface to a Python object, and wrap it into a
        # pythoncom PyIUnknown class
        pyobj = G_DeveloperConsoleMessageReceiver()
        iunknown_c = pyobj.QueryInterface(comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0.IUnknown)
        c_ptr = super(comtypes._compointer_base, iunknown_c).value
        iunknown_p = pythoncom.ObjectFromAddress(c_ptr)

        # access embedded browser's command target interface
        from win32com.axcontrol import axcontrol
        icommandtarget = doc._oleobj_.QueryInterface(axcontrol.IID_IOleCommandTarget)

        # and register our interface as a console
        CGID_MSHTML = pythoncom.MakeIID("{DE4BA900-59CA-11CF-9592-444553540000}")
        IDM_ADDCONSOLEMESSAGERECEIVER = 3800
        OLECMDEXECOPT_DODEFAULT = 0
        icommandtarget.Exec(CGID_MSHTML, IDM_ADDCONSOLEMESSAGERECEIVER, OLECMDEXECOPT_DODEFAULT, iunknown_p)
        G_ChartViewCtrl._ConsoleRegistered = True


    #-------------------------------------------------------
    def __init__(self, parent, chart_info, db_path, table_view_ctrl, error_reporter, node_id):
        super().__init__(parent)

        self._ChartInfo = chart_info
        self._DbPath = db_path
        self._TableViewCtrl = table_view_ctrl
        self._ErrorReporter = error_reporter

        self._ParameterValues = dict()
        self._ScriptQueue = ["SetNodeId({});".format(node_id)]

        self.InitCharting()

        self._Figure = wx.html2.WebView.New(self)
        self._Figure.EnableHistory(False)
        self._Figure.EnableContextMenu(False)

        self.Bind(wx.html2.EVT_WEBVIEW_LOADED, self.OnPageLoaded)

        with G_ScriptGuard("Setup", self._ErrorReporter):
            page_name = self._ChartInfo.Setup()
            self._Figure.LoadURL("http://localhost:8000/{}".format(page_name))

        # layout
        vsizer = wx.BoxSizer(wx.VERTICAL)
        vsizer.Add(self._Figure, proportion = 1, flag = wx.EXPAND)
        self.SetSizer(vsizer)



    #-------------------------------------------------------
    def OnPageLoaded(self, event):
        if not "about:" in event.URL:
            self.RunScriptQueue()


    #-------------------------------------------------------
    def GetIHTMLDocument2(self):

        data = [None]

        def enum_callback(hwnd, data):
            cls =  win32gui.GetClassName(hwnd)
            if cls in ['TabWindowClass', 'Shell DocObject View', 'Internet Explorer_Server']:
                msg = win32gui.RegisterWindowMessage("WM_HTML_GETOBJECT")
                rc, result = win32gui.SendMessageTimeout(hwnd, msg, 0, 0, win32con.SMTO_ABORTIFHUNG, 1000)
                if result != 0:
                    object = pythoncom.ObjectFromLresult(result, pythoncom.IID_IDispatch, 0)
                    if object is not None:
                        # have to force the class ID - not really clear why; without this though,
                        # the returned value is a generic CDispatch for class ID 
                        # '{C59C6B12-F6C1-11CF-8835-00A0C911E8B2}', which doesn't work very well
                        clsid = self._IIDMap["IHTMLDocument2"]
                        document = win32com.client.Dispatch(object, resultCLSID = clsid)
                        if document is not None:
                            data[0] = document
                            return False

            return True
                
        win32gui.EnumChildWindows(self._Figure.GetHandle(), enum_callback, data)
        return data[0]


    #-------------------------------------------------------
    def EnqueueScript(self, script):
        last_script = None
        last_idx = len(self._ScriptQueue) - 1

        if last_idx >= 0:
            last_script = self._ScriptQueue[last_idx]

        if script != last_script:
            self._ScriptQueue.append(script)
            self.RunScriptQueue()
        

    def RunScriptQueue(self):
        doc = self.GetIHTMLDocument2()
        if doc is None:
            return

        self.RegisterConsole(doc)

        for script_text in self._ScriptQueue:
            elem = doc.createElement("script")
            script_elem = win32com.client.Dispatch(elem, resultCLSID = self._IIDMap["IHTMLScriptElement"])
            script_elem.text = script_text

            # add script to DOM; will execute
            node = win32com.client.Dispatch(doc.body, resultCLSID = self._IIDMap["IHTMLDOMNode"])
            script_node = node.appendChild(script_elem)

            # remove script from DOM; don't need it any more
            node.removeChild(script_node)

        self._ScriptQueue = []


    #-------------------------------------------------------
    def DefineParameters(self):
        parameters = None

        with G_ScriptGuard("DefineParameters", self._ErrorReporter):
            connection = ConnectDb(self._DbPath, True)
            if connection is not None:
                cursor = connection.cursor()
                event_ids = self._TableViewCtrl.GetSelectedEventIds()
                collector = G_ParameterCollector()
                self._ChartInfo.DefineParameters(collector, connection, cursor, event_ids)
                parameters = collector.Close()

        return parameters


    #-------------------------------------------------------
    def Realise(self):
        with G_ScriptGuard("Realise", self._ErrorReporter):
            connection = ConnectDb(self._DbPath, True)
            if connection is not None:
                cursor = connection.cursor()
                event_ids = self._TableViewCtrl.GetSelectedEventIds()

                figure = G_ChartViewCtrlProxy(self)
                self._ChartInfo.Realise(figure, connection, cursor, self._ParameterValues, event_ids)


    #-------------------------------------------------------
    def Update(self, data_changed = False, selection_changed = False, parameters = None):
        """Redraw the chart if needed"""

        do_realize = False
        if data_changed:
            do_realize = True

        if selection_changed and self._ChartInfo.WantSelection:
            do_realize = True

        if parameters is not None and parameters != self._ParameterValues:
            do_realize = True
            self._ParameterValues = parameters.copy()

        if do_realize:
            self.Realise()
            


## G_CommonViewCtrl ########################################

class G_CommonViewCtrl(wx.SplitterWindow):
    """
    Common behaviour for G_EventsViewCtrl and G_MetricsViewCtrl.
    """

    #-------------------------------------------------------
    def __init__(self, parent, node_selection_handler, multiple_selection, doc_url = None):
        super().__init__(parent, style = wx.SP_LIVE_UPDATE)
        self._NodeSelectionHandler = node_selection_handler
        self._ChartPane = None

        self.SetMinimumPaneSize(150)
        self.SetSashGravity(0.5)

        self._TableViewCtrl = G_TableViewCtrl(self, self.OnTableSelectionChanged, multiple_selection, doc_url)
        self.Initialize(self.GetTableViewCtrl())


    #-------------------------------------------------------
    def GetTableViewCtrl(self):
        return self._TableViewCtrl


    #-------------------------------------------------------
    def GetChartPane(self, create = False):
        if self._ChartPane is None and create:
            self._ChartPane = wx.Panel(self)
            self._ChartPane.SetSizer(wx.BoxSizer(wx.VERTICAL))
            self.SplitHorizontally(self.GetTableViewCtrl(), self._ChartPane)

        return self._ChartPane


    #-------------------------------------------------------
    def GetChartViewCtrl(self, chart_no, activate):
        pane = self.GetChartPane()
        if pane is None:
            return pane

        pane_sizer = pane.GetSizer()
        if pane_sizer.IsEmpty():
            return None

        sizer_items = pane_sizer.GetChildren()
        if chart_no >= len(sizer_items):
            return None

        if activate:
            pane_sizer.ShowItems(True)

            for (idx, item) in enumerate(sizer_items):
                if idx != chart_no:
                    item.Show(False)
    
            pane_sizer.Layout()

        return sizer_items[chart_no].GetWindow()


    #-------------------------------------------------------
    def OnTableSelectionChanged(self, item):
        self._NodeSelectionHandler(item)
        self.UpdateChartSelection()


    #-------------------------------------------------------
    def UpdateCharts(self, data_changed = False, selection_changed = False):
        pane = self.GetChartPane()
        if pane is not None:
            for chart_view in pane.GetChildren():
                chart_view.Update(data_changed, selection_changed)

    def UpdateChartData(self):
        self.UpdateCharts(data_changed = True)

    def UpdateChartSelection(self):
        return self.UpdateCharts(selection_changed = True)



## G_EventsViewCtrl ########################################

class G_EventsViewCtrl(G_CommonViewCtrl):

    #-------------------------------------------------------
    def __init__(self, parent, node_selection_handler, doc_url):
        super().__init__(parent, node_selection_handler, False, doc_url)




## G_MetricsViewCtrl #######################################

class G_MetricsViewCtrl(G_CommonViewCtrl):

    #-------------------------------------------------------
    def __init__(self, parent, node_selection_handler, quantifier_name):
        super().__init__(parent, node_selection_handler, True)

        self._QuantifierName = quantifier_name

        # one-shot lock to inhibit initial Quantification if
        # table data already exists
        self._CollectorLocked = True


    #-------------------------------------------------------
    @G_Global.TimeFunction
    def Quantify(self, node, quantifier_info, valid, error_reporter):
        G_Global.GetCurrentTimer().AddArgument(self._QuantifierName)
        self.ResetModel(error_reporter)
        with G_ScriptGuard("Quantify", self._ErrorReporter):
            quantifier = G_Quantifier(quantifier_info)
            quantifier.Run(self._CollectorLocked)
            self._CollectorLocked = False

            metrics_db_path = quantifier_info.MetricsDbPath
            table_ctrl = self.GetTableViewCtrl()
            table_ctrl.UpdateContent(False, quantifier_info.MetricsSchema, metrics_db_path, valid)
            table_ctrl.SetFieldMask(-1)

            if len(quantifier_info.Charts) != 0:
                pane = self.GetChartPane(True)
                pane_sizer = pane.GetSizer()

                if pane_sizer.IsEmpty():
                    for chart_info in quantifier_info.Charts:
                        chart_view_ctrl = G_ChartViewCtrl(pane, chart_info, metrics_db_path, table_ctrl, self._ErrorReporter, node.GetNodeId())
                        pane_sizer.Add(chart_view_ctrl, proportion = 1, flag = wx.EXPAND | wx.ALIGN_CENTER | wx.ALIGN_CENTER_VERTICAL)

                    pane_sizer.ShowItems(False)

                self.UpdateChartData()


    #-------------------------------------------------------
    def ResetModel(self, error_reporter = None):
        self._ErrorReporter = error_reporter

        pane = self.GetChartPane()
        if pane is not None:
            pane.GetSizer().Clear(delete_windows = True)

        self.GetTableViewCtrl().ResetModel()

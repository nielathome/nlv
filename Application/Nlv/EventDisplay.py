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

from comtypes import IUnknown, COMObject, GUID, COMMETHOD, _compointer_base
from ctypes import c_int, c_ulong, c_wchar_p, HRESULT
import logging
import os
from pathlib import Path
import pythoncom
import sys
import win32com
import win32com.client as com
import win32con
import win32gui
import winreg

# Application imports 
from .DataExplorer import G_DataExplorerProvider
from .Logfile import G_DisplayControl
from .Logfile import G_NotebookDisplayControl
from .MatchNode import G_MatchItem
from .EventProjector import G_Quantifier
from .EventProjector import G_ProjectionSchema
from .EventProjector import G_ProjectionTypeManager
from .EventProjector import G_ScriptGuard
from .Global import G_Global
from .Global import G_PerfTimerScope
from .StyleNode import G_ColourTraits
from .Theme import GetThemeSupportFile

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

class IDeveloperConsoleMessageReceiver(IUnknown):
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



## G_DataExplorerContext ###################################

class G_DataExplorerContext:

    #-------------------------------------------------------
    def __init__(self, event_id, db_info, ui_node):
        self.EventId = event_id
        self.DbInfo = db_info
        self._UiNode = ui_node

    def GetTargetId(self, node_name):
        ui_nodes = self._UiNode.GetLogAnalysisNode().ListSubNodes(recursive = True)
        for ui_node in ui_nodes:
            if ui_node.GetNodeName() == node_name:
                return ui_node.GetNodeId()

        return None



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



## G_DisplayProperties #####################################

class G_DisplayProperties:

    #-------------------------------------------------------
    def __init__(self, nesting = None, partition = None, valid = None, reason = None):
        self.Nesting = nesting
        self.Partition = partition
        self.Valid = valid
        self.Reason = reason



## G_TableDataModel ########################################

class G_TableDataModel(wx.dataview.DataViewModel, G_DataExplorerProvider):

    #-------------------------------------------------------
    def __init__(self, name):
        super().__init__()

        self._ViewFlat = True
        self._DataPartition = None
        self._Name = name
        self._RawFieldMask = 0
        self._IsValid = True
        self._InvalidColour = G_ColourTraits.MakeColour("FIREBRICK")

        self._DataExplorerColour = G_ColourTraits.MakeColour("WHEAT")
        self._DataExplorerIcon = wx.ArtProvider.GetIcon(wx.ART_REDO, wx.ART_TOOLBAR, (16, 16))
        self._DataExplorerKey = None

        self._SelectedIcon = wx.ArtProvider.GetIcon(wx.ART_TIP, wx.ART_TOOLBAR, (16, 16))
        self._SelectedKeys = set()

        self._ColumnColours = []
        self._FilterMatch = None
        self._Hiliters = []
        self.Reset(reason = "Initialisation")

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
    def IsDataExplorerLine(self, item_key):
        return item_key == self._DataExplorerKey

    def SetDataExplorerLine(self, key):
        changed = self._DataExplorerKey != key
        self._DataExplorerKey = key
        return changed

    def ClearDataExplorerLine(self):
        changed = self._DataExplorerKey is not None
        self._DataExplorerKey = None
        return changed


    #-------------------------------------------------------
    def IsSelectedLine(self, item_key):
        return item_key in self._SelectedKeys

    def SetSelectedLines(self, items):
        self._SelectedKeys.clear()
        self._SelectedKeys.update([self.ItemToKey(item) for item in items])


    #-------------------------------------------------------
    def Reset(self, table_schema = None, db_info = None, reason = None):
        self._N_Logfile = None
        self._N_EventView = None

        self.ClearDataExplorerLine()

        if table_schema is None:
            table_schema = G_ProjectionSchema()
        self._TableSchema = table_schema
        self._DbInfo = db_info

        self._ModelColumnToFieldId = []
        field_id = 0
        for field_schema in self._TableSchema:
            fid = -1

            if field_schema.Available:
                fid = field_id
                field_id += 1

            self._ModelColumnToFieldId.append(fid)

        if reason is None:
            # None effectively means "don't care"
            reason = "Model reset"
        self.SetNavigationValidity("Data cleared: {}".format(reason))


    #-------------------------------------------------------
    def GetFieldValue(self, item_key, col_num):
        field_schema = self._TableSchema[col_num]
        return G_ProjectionTypeManager.GetValue(field_schema, self._N_EventView, item_key, col_num)

    def GetFieldDisplayValue(self, item, col_num):
        item_key = self.ItemToKey(item)
        field_schema = self._TableSchema[col_num]
        icon = None

        if field_schema.IsFirst:
            if self.IsDataExplorerLine(item_key):
                icon = self._DataExplorerIcon
            elif self.IsSelectedLine(item_key):
                icon = self._SelectedIcon
            else:
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
    def UserDataExplorer(self, func, desc, context, builder):
        if func is not None: 
            with G_ScriptGuard(desc):
                func(context, builder)


    def OnDataExplorerLoad(self, ctrl, sync, builder, location, ui_node):
        event_id = location["event_id"]
        item = self.LookupEventId(event_id)
        node_name = ui_node.GetNodeName()

        if not self.IsNavigationValid(builder, location, node_name):
            if self.ClearDataExplorerLine():
                ctrl.Refresh()

        elif item is None:
            if self.ClearDataExplorerLine():
                ctrl.Refresh()

            builder.MakeHiddenLocationErrorPage([
                ("Location", node_name),
                ("Reason", self.GetNavigationValidReason())
            ])

        else:
            schema = self._TableSchema
            context = G_DataExplorerContext(event_id, self._DbInfo, ui_node)

            self.UserDataExplorer(schema.UserDataExplorerOpen, "DataExplorerOpen", context, builder)
            builder.AddPageHeading("{} Item".format(self._Name))

            logfile_url = ui_node.GetLogNode().MakeDataUrl()
            if logfile_url is not None:
                builder.AddLink(logfile_url, "Show log file ...")

            builder.AddField("Location", node_name)

            for col_num, field in enumerate(schema):
                if field.Available or field.ExplorerFormatter is not None:
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
                            with G_ScriptGuard("DataExplorerFormatter"):
                                field.ExplorerFormatter(builder, field.Name, text)
                        else:
                            builder.AddField(field.Name, text)
                    
            self.UserDataExplorer(schema.UserDataExplorerClose, "DataExplorerClose", context, builder)

            if sync:
                if self.SetDataExplorerLine(self.ItemToKey(item)):
                    ctrl.UnselectAll()
                    ctrl.EnsureVisible(item)

            elif self.ClearDataExplorerLine():
                ctrl.Refresh()


    #-------------------------------------------------------
    def OnDataExplorerUnload(self, ctrl):
        if self.ClearDataExplorerLine():
            ctrl.Refresh()


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

        # attr is a DataViewItemAttr
        wrapped_attr = G_TableFieldFormatter(attr)

        if not self._IsValid:
            wrapped_attr.SetFgColour(self._InvalidColour, True)

        item_key = self.ItemToKey(item)
        if self.IsDataExplorerLine(item_key):
            wrapped_attr.SetBgColour(self._DataExplorerColour, True)

        if col_num < len(self._ModelColumnToFieldId):
            field_id = self._ModelColumnToFieldId[col_num]
            if field_id >= 0 and field_id < len(self._ColumnColours):
                wrapped_attr.SetFgColour(self._ColumnColours[field_id])

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
    def GetItemEventId(self, item):
        col_num = self._TableSchema.ColEventId
        return self.GetFieldValue(self.ItemToKey(item), col_num)

    def GetItemsEventIds(self, items):
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

        if self._DataPartition is not None:
            if match is None:
                match = G_MatchItem()
            match.SetDataPartition(self._DataPartition)

        if match is not None and self._N_EventView is not None:
            return self._N_EventView.Filter(match)

        return True


    @G_Global.TimeFunction
    def UpdateContent(self, display_props, table_info):
        table_schema = table_info.GetSchema()
        db_info = table_info.GetDbInfo()

        self.Reset(table_schema, db_info, reason = display_props.Reason)
        self.UpdateNesting(display_props.Nesting, False)
        self.UpdateDataPartition(display_props.Partition, display_props.Reason, False)
        self.UpdateValidity(display_props.Valid)

        num_fields = self.GetColumnCount()
        db_path = db_info.Path
        if Path(db_path).exists() and num_fields != 0:
            self._N_Logfile = Nlog.MakeLogfile(db_path, table_schema, G_Global.PulseProgressMeter)

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
    def UpdateFilter(self, match, reason = None):
        if not self.FilterLineSet(match):
            return False
        
        if reason is None:
            reason = "Filter: {match}".format(match = match.GetDescription())

        self.SetNavigationValidityReason(reason)
        self.ClearDataExplorerLine()
        self.Cleared()
        return True


    #-------------------------------------------------------
    def UpdateSort(self, col_num):
        if self._N_EventView is not None:
            (data_col_offset, direction) = self._TableSchema[col_num].ToggleSortDirection()
            self._N_EventView.Sort(col_num + data_col_offset, direction)
            self.ClearDataExplorerLine()
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
            self.Cleared()


    def UpdateDataPartition(self, partition, reason, do_filter = True):
        if partition is None:
            return

        self._DataPartition = partition
        if do_filter:
            self.UpdateFilter(self._FilterMatch, reason)


    def UpdateValidity(self, valid):
        # the view is deemed valid if an analysis has taken place
        # since the last time the recogniser was modified
        if valid is None:
            return False

        if valid == self._IsValid:
            return False

        self._IsValid = valid
        return True


    def UpdateDisplay(self, display_props):
        self.UpdateNesting(display_props.Nesting)
        self.UpdateDataPartition(display_props.Partition, display_props.Reason)
        return self.UpdateValidity(display_props.Valid)



## G_DataViewCtrl ##########################################

class G_DataViewCtrl(wx.dataview.DataViewCtrl):

    #-------------------------------------------------------
    def __init__(self, parent, flags, name):
        super().__init__(
            parent,
            style = wx.dataview.DV_ROW_LINES
            | wx.dataview.DV_VERT_RULES
            | flags
        )

        self.AssociateModel(G_TableDataModel(name))
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
    def UpdateContent(self, display_props, table_info):
        """Update the data view with new content"""

        # note: number of DataView columns is not the same as the number of
        # model columns; as some are hidden for internal use
        try:
            self.ClearColumns()
            self.GetModel().UpdateContent(display_props, table_info)
            self.UpdateColumns()

        except FileNotFoundError as ex:
            pass


    #-------------------------------------------------------
    def UpdateDisplay(self, display_props):
        if self.GetModel().UpdateDisplay(display_props):
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

class G_TableViewCtrl(G_DataViewCtrl, G_DisplayControl):

    #-------------------------------------------------------
    def __init__(self, parent, multiple_selection, name):
        flags = 0
        if multiple_selection:
            flags = wx.dataview.DV_MULTIPLE

        super().__init__(parent, flags, name)

        self._SelectionHandler = None
        self._IsMultipleSelection = multiple_selection
        self.Bind(wx.dataview.EVT_DATAVIEW_SELECTION_CHANGED, self.OnItemActivated)


    #-------------------------------------------------------
    def GetNumItems(self):
        return self.GetModel().GetNumItems()


    #-------------------------------------------------------
    def GetSelectedEventIds(self):
        return self.GetModel().GetItemsEventIds(self.GetSelections())

    def GenerateSelectionEvent(self, item):
        """
        The control does not generate selection events when calling
        self.UnselectAll, self.Select etc. This routine fakes an event
        to allow the rest of the UI to keep up to date
        """
        evt = wx.dataview.DataViewEvent()
        if item is not None:
            evt.SetItem(item)
        self.OnItemActivated(evt)

    def OnChartSelection(self, event_id, ctrl_key):
        item = self.GetModel().LookupEventId(event_id)
        if item is not None:
            if ctrl_key:
                if self.IsSelected(item):
                    self.Unselect(item)
                    item = None
                else:
                    self.Select(item)
            else:
                self.UnselectAll()
                self.Select(item)

            self.GenerateSelectionEvent(item)


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
            self.GenerateSelectionEvent(next_item)


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
    def GetItemEventId(self, item):
        return self.GetModel().GetItemEventId(item)

    def OnDataExplorerLoad(self, sync, builder, location, ui_node):
        self.GetModel().OnDataExplorerLoad(self, sync, builder, location, ui_node)

    def OnDataExplorerUnload(self, location):
        self.GetModel().OnDataExplorerUnload(self)


    #-------------------------------------------------------
    def GetEventRange(self, event_no):
        return self.GetModel().GetEventRange(event_no)


    #-------------------------------------------------------
    def SetSelectionhandler(self, selection_handler):
        self._SelectionHandler = selection_handler

    def OnItemActivated(self, evt):
        self.GetModel().SetSelectedLines(self.GetSelections())
        if self._SelectionHandler is not None:
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
        self.CtrlId = -1


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
        self.CtrlId = self._Ctrl.GetId()
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
        self.CtrlId = self._Ctrl.GetId()
        self._Ctrl.Set(self.Values)

        if value is None or value >= len(self.Values):
            value = self.Default
        self._Ctrl.SetSelection(value)
        self._Ctrl.Bind(wx.EVT_CHOICE, handler)
        return self._Ctrl


    #-------------------------------------------------------
    def GetValue(self):
        return self._Ctrl.GetSelection()



## G_UpdateDom #############################################

_IIDMap = None

class G_UpdateDom:
    #-------------------------------------------------------
    def __init__(self, script):
        self.Script = script


    #-------------------------------------------------------
    @staticmethod
    def MakeScriptElement(doc):
        elem = doc.createElement("script")
        return com.Dispatch(elem, resultCLSID = _IIDMap["IHTMLScriptElement"])


    #-------------------------------------------------------
    @staticmethod
    def LoadScriptElement(doc, script_elem):
        # add script to DOM; will execute
        dom_node = com.Dispatch(doc.body, resultCLSID = _IIDMap["IHTMLDOMNode"])
        script_node = dom_node.appendChild(script_elem)
        return dom_node, script_node
    

    #-------------------------------------------------------
    @staticmethod
    def UnloadScriptNode(dom_node, script_node):
        # remove script from DOM; often, don't need it any more
        dom_node.removeChild(script_node)



## G_UpdateDomCallJavaScript ###############################

class G_UpdateDomCallJavaScript(G_UpdateDom):

    #-------------------------------------------------------
    def __init__(self, script):
        super().__init__(script)


    #-------------------------------------------------------
    def Update(self, doc):
        script_elem = self.MakeScriptElement(doc)
        script_elem.text = self.Script
        dom_node, script_node = self.LoadScriptElement(doc, script_elem)
        self.UnloadScriptNode(dom_node, script_node)



## G_UpdateDomLoadScript ###################################

class G_UpdateDomLoadScript(G_UpdateDom):

    #-------------------------------------------------------
    def __init__(self, script):
        super().__init__(script)


    #-------------------------------------------------------
    def Update(self, doc):
        # writing the script_elem.src property will load a
        # script, but, always asynchronously. So, stuff the
        # script directly into the page instead.

        script_text = ""
        with open(GetThemeSupportFile(self.Script), "r") as file:
            script_text = "".join(file.readlines())

        script_elem = self.MakeScriptElement(doc)
        script_elem.text = script_text
        dom_node, script_node = self.LoadScriptElement(doc, script_elem)



## G_HtmlHostCtrl ##########################################

class G_HtmlHostCtrl(wx.Panel):

    #-------------------------------------------------------
    _InitCharting = True
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
    @G_Global.TimeFunction
    def InitCharting(self):
        if not __class__._InitCharting:
            return

        # Ensure JavaScript runs in embedded browser. Can be simplified
        # after wxPython-4.1.0. See https://github.com/wxWidgets/Phoenix/issues/1256.
        reg_path = r"Software\Microsoft\Internet Explorer\Main\FeatureControl\FEATURE_BROWSER_EMULATION"
        self._SetRegistryValue(os.path.basename(sys.executable), reg_path, 11001)

        # makepy.py -i
        # {3050F1C5-98B5-11CF-BB82-00AA00BDCE0B}, lcid=0, major=4, minor=0
        global _IIDMap
        module = com.gencache.EnsureModule('{3050F1C5-98B5-11CF-BB82-00AA00BDCE0B}', 0, 4, 0)
        _IIDMap = module.NamesToIIDMap

        __class__._InitCharting = False


    #-------------------------------------------------------
    @classmethod
    def RegisterConsole(cls, doc):
        if G_HtmlHostCtrl._ConsoleRegistered:
            return

        # warning: mixing the two Python COM libraries here.
        # pythoncom/win32com is good for Dispatch/OLE interfaces
        # and comtypes is good for custom interfaces

        # use comtypes to link a IDeveloperConsoleMessageReceiver
        # interface to a Python object, and wrap it into a
        # pythoncom PyIUnknown class
        pyobj = G_DeveloperConsoleMessageReceiver()
        iunknown_c = pyobj.QueryInterface(IUnknown)
        c_ptr = super(_compointer_base, iunknown_c).value
        iunknown_p = pythoncom.ObjectFromAddress(c_ptr)

        # access embedded browser's command target interface
        from win32com.axcontrol import axcontrol
        icommandtarget = doc._oleobj_.QueryInterface(axcontrol.IID_IOleCommandTarget)

        # and register our interface as a console
        CGID_MSHTML = pythoncom.MakeIID("{DE4BA900-59CA-11CF-9592-444553540000}")
        IDM_ADDCONSOLEMESSAGERECEIVER = 3800
        OLECMDEXECOPT_DODEFAULT = 0
        icommandtarget.Exec(CGID_MSHTML, IDM_ADDCONSOLEMESSAGERECEIVER, OLECMDEXECOPT_DODEFAULT, iunknown_p)
        G_HtmlHostCtrl._ConsoleRegistered = True


    #-------------------------------------------------------
    def __init__(self, parent, context, chart_info):
        super().__init__(parent)

        self._ChartInfo = chart_info
        self._CreateContext = context
        self._ParameterValues = dict()
        self._DomUpdateQueue = []

        self.InitCharting()

        self._Figure = wx.html2.WebView.New(self, backend = wx.html2.WebViewBackendIE)
        self._Figure.EnableHistory(False)
        self._Figure.EnableContextMenu(False)
        self._FigureLoaded = False

        self.Bind(wx.html2.EVT_WEBVIEW_LOADED, self.OnPageLoaded)
        self.SetupHtml()

        # layout
        vsizer = wx.BoxSizer(wx.VERTICAL)
        vsizer.Add(self._Figure, proportion = 1, flag = wx.EXPAND)
        self.SetSizer(vsizer)


    def SetupHtml(self):
        class Context:
            #-----------------------------------------------
            def __init__(self, host):
                self._Host = host

            #-----------------------------------------------
            def LoadPage(self, page_name):
                self._Host._Figure.LoadURL("http://localhost:8000/{}".format(page_name))

            def LoadScript(self, script_name):
                self._Host.LoadScript(script_name)

            #-----------------------------------------------
            def CallJavaScript(self, method, *args):
                self._Host.CallJavaScript(method, *args)

        self._ChartInfo.Builder.Setup(Context(self))


    #-------------------------------------------------------
    def OnPageLoaded(self, event):
        if not "about:" in event.URL:
            self._FigureLoaded = True
            self.RunDomUpdateQueue()


    #-------------------------------------------------------
    def GetIHTMLDocument2(self):

        data = [None, None]

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
                        clsid = _IIDMap["IHTMLDocument2"]
                        document = com.Dispatch(object, resultCLSID = clsid)
                        if document is not None:
                            data[0] = document
                            data[1] = hwnd
                            return False

            return True
                
        win32gui.EnumChildWindows(self._Figure.GetHandle(), enum_callback, data)

        # once off setup, now that the visible chart display control is known
        if data[0] is not None and self._CreateContext is not None:
            context = self._CreateContext
            self._CreateContext = None

            self.CallJavaScript("SetNodeId", context.GetNodeId())

            # keep the Python/wxWidgets window alive while we (the parent)
            # window is remains
            html_window = self._HtmlWindow = wx.Window()
            html_window.AssociateHandle(data[1])
            context.OnChartCreate(self, html_window)

        return data[0]


    #-------------------------------------------------------
    def CallJavaScript(self, method, *args):
        def ConvertArg(arg):
            if isinstance(arg, str):
                return "'{}'".format(arg.replace("\n", ""))
            else:
                return str(arg)

        arg_text = ",".join([ConvertArg(arg) for arg in args])
        script = "{method}({args});".format(method = method, args = arg_text)
        self.EnqueueDomUpdate(G_UpdateDomCallJavaScript(script))


    def LoadScript(self, script_name):
        self.EnqueueDomUpdate(G_UpdateDomLoadScript(script_name))


    def EnqueueDomUpdate(self, dom_update):
        append = True
        last_idx = len(self._DomUpdateQueue) - 1
        if last_idx >= 0:
            last_update = self._DomUpdateQueue[last_idx]
            append = dom_update.Script != last_update.Script

        if append:
            self._DomUpdateQueue.append(dom_update)
            self.RunDomUpdateQueue()


    def RunDomUpdateQueue(self):
        doc = self.GetIHTMLDocument2()
        if doc is None:
            return

        self.RegisterConsole(doc)

        if not self._FigureLoaded:
            return

        for dom_update in self._DomUpdateQueue:
            dom_update.Update(doc)

        self._DomUpdateQueue = []


    #-------------------------------------------------------
    def DefineParameters(self, error_reporter):
        db_info = self.GetDbInfo()
        if db_info is None:
            return None


        class Context:
            """Collect parameter data from a chart"""

            #-----------------------------------------------
            def __init__(self, host):
                self._Host = host
                self._Params = []

            def Close(self):
                return self._Params

            #-----------------------------------------------
            def AddChoice(self, name, title, default, values):
                self._Params.append(G_ChoiceParam(name, title, default, values))

            def AddBool(self, name, title, default):
                self._Params.append(G_BoolParam(name, title, default))

            #-------------------------------------------------------
            def GetSelection(self, set = None):
                return self._Host.GetSelectedEventIds(set)


        parameters = None
        with G_ScriptGuard("DefineParameters", error_reporter), db_info.ConnectionManager() as connection:
            cursor = self.MakeDbCursor(connection)
            context = Context(self)
            self._ChartInfo.DefineParameters(connection, cursor, context)
            parameters = context.Close()

        return parameters


    #-------------------------------------------------------
    def Realise(self, error_reporter, data_changed = False, selection_changed = False, parameters = None, changed_parameter_name = None):
        """Redraw the chart if needed"""

        class Context:
            #-----------------------------------------------
            def __init__(self, host, data_changed, selection_changed, changed_parameter_name):
                self._Host = host
                self._DataChanged = data_changed
                self._SelectionChanged = selection_changed
                self._ChangedParameterName = changed_parameter_name

            #-----------------------------------------------
            def DataChanged(self):
                return self._DataChanged

            def SelectionChanged(self):
                return self._SelectionChanged

            def ChangedParameterName(self):
                return self._ChangedParameterName

            #-----------------------------------------------
            def GetSelection(self, set = None):
                return self._Host.GetSelectedEventIds(set)

            def GetParameter(self, name, default):
                return self._Host._ParameterValues.get(name, default)

            #-----------------------------------------------
            def CallJavaScript(self, method, *args):
                self._Host.CallJavaScript(method, *args)


        do_realize = False
        if data_changed:
            do_realize = True

        if selection_changed and self._ChartInfo.WantSelection:
            do_realize = True

        if parameters is not None and parameters != self._ParameterValues:
            do_realize = True
            self._ParameterValues = parameters.copy()

        db_info = self.GetDbInfo()
        if do_realize and db_info is not None:
            with G_ScriptGuard("Realise", error_reporter), db_info.ConnectionManager() as connection:
                cursor = self.MakeDbCursor(connection)
                context = Context(self, data_changed, selection_changed, changed_parameter_name)
                self._ChartInfo.Realise(connection, cursor, context)


            
## G_HtmlChartCtrl #########################################

class G_HtmlChartCtrl(G_HtmlHostCtrl):

    #-------------------------------------------------------
    def __init__(self, parent, context, chart_info, table_view_ctrl):
        super().__init__(parent, context, chart_info)

        self._TableViewCtrl = table_view_ctrl


    #-------------------------------------------------------
    def GetSelectedEventIds(self, set):
        return self._TableViewCtrl.GetSelectedEventIds()


    #-------------------------------------------------------
    def GetDbInfo(self):
        db_info = self._ChartInfo.ChartDbInfo
        if not Path(db_info.Path).exists():
            return None

        return db_info

    @staticmethod
    def MakeDbCursor(connection):
        return connection.cursor()



## G_HtmlNetworkCtrl #######################################

class G_HtmlNetworkCtrl(G_HtmlHostCtrl):

    #-------------------------------------------------------
    def __init__(self, parent, context, chart_info, table_view_ctrls):
        super().__init__(parent, context, chart_info)

        self._TableViewCtrls = table_view_ctrls


    #-------------------------------------------------------
    def GetSelectedEventIds(self, set):
        return self._TableViewCtrls[set].GetSelectedEventIds()


    #-------------------------------------------------------
    def GetDbInfo(self):
        db_info = self._ChartInfo.NodesDbInfo
        if not Path(db_info.Path).exists():
            return None

        links_path = self._ChartInfo.LinksDbInfo.Path
        if not Path(links_path).exists():
            return None

        return db_info

    def MakeDbCursor(self, connection):
        cursor = connection.cursor()
        cursor.execute("ATTACH DATABASE '{db}' AS links".format(db = self._ChartInfo.LinksDbInfo.Path))
        return cursor



## G_CoreViewCtrl ##########################################

class G_CoreViewCtrl(wx.SplitterWindow, G_DisplayControl):
    """
    Common behaviour for G_EventsViewCtrl,  G_MetricsViewCtrl
    and G_NetworkViewCtrl.
    """

    #-------------------------------------------------------
    def __init__(self, parent):
        super().__init__(parent, style = wx.SP_LIVE_UPDATE)
        self._ChartPane = None
        self._TablePane = None
        self._ChartLocation = 0

        self.SetMinimumPaneSize(150)
        self.SetSashGravity(0.5)


    #-------------------------------------------------------
    def ArrangeChildren(self):
        location = self._ChartLocation
        table = self._TablePane
        chart = self._ChartPane

        self.Unsplit()
        if chart is None:
            self.Initialize(table)

        elif location == 0:
            self.SplitHorizontally(table, chart)

        elif location == 1:
            self.SplitHorizontally(chart, table)

        elif location == 2:
            self.SplitVertically(chart, table)

        elif location == 3:
            self.SplitVertically(table, chart)


    #-------------------------------------------------------
    def SetChartLocation(self, location):
        if location == self._ChartLocation:
            return

        self._ChartLocation = location
        self.ArrangeChildren()


    #-------------------------------------------------------
    def GetChartPane(self, create = False):
        if self._ChartPane is None and create:
            self._ChartPane = wx.Panel(self)
            self._ChartPane.SetSizer(wx.BoxSizer(wx.VERTICAL))
            self.ArrangeChildren()

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
    def ResetCharts(self):
        pane = self.GetChartPane()
        if pane is not None:
            pane.GetSizer().Clear(delete_windows = True)


    #-------------------------------------------------------
    def CreateCharts(self, context, chart_list):
        if chart_list is None or len(chart_list) == 0:
            return

        pane = self.GetChartPane(True)
        pane_sizer = pane.GetSizer()

        if pane_sizer.IsEmpty():
            for chart_info in chart_list:
                chart_view_ctrl = self.MakeHtmlChartCtrl(pane, context, chart_info)
                pane_sizer.Add(chart_view_ctrl, proportion = 1, flag = wx.EXPAND)

            pane_sizer.ShowItems(False)

        self.UpdateCharts(context.GetErrorReporter(), data_changed = True)


    #-------------------------------------------------------
    def UpdateCharts(self, error_reporter, data_changed = False, selection_changed = False):
        pane = self.GetChartPane()
        if pane is not None:
            for chart_view in pane.GetChildren():
                chart_view.Realise(error_reporter, data_changed, selection_changed)



## G_CommonViewCtrl ########################################

class G_CommonViewCtrl(G_CoreViewCtrl):
    """
    Common behaviour for G_EventsViewCtrl and G_MetricsViewCtrl.
    """

    #-------------------------------------------------------
    def __init__(self, parent, multiple_selection, name):
        super().__init__(parent)

        self.SetMinimumPaneSize(150)
        self.SetSashGravity(0.5)

        self._TablePane = self._TableViewCtrl = G_TableViewCtrl(self, multiple_selection, name)
        self.ArrangeChildren()


    #-------------------------------------------------------
    def GetTableViewCtrl(self):
        return self._TableViewCtrl


    #-------------------------------------------------------
    def MakeHtmlChartCtrl(self, pane, context, chart_info):
        return G_HtmlChartCtrl(pane, context, chart_info, self.GetTableViewCtrl())


    #-------------------------------------------------------
    def ResetModel(self):
        self.ResetCharts()
        self.GetTableViewCtrl().ResetModel()



## G_EventsViewCtrl ########################################

class G_EventsViewCtrl(G_CommonViewCtrl):

    #-------------------------------------------------------
    def __init__(self, parent, name):
        super().__init__(parent, False, name)



## G_MetricsViewCtrl #######################################

class G_MetricsViewCtrl(G_CommonViewCtrl):

    #-------------------------------------------------------
    def __init__(self, parent, quantifier_name):
        super().__init__(parent, True, quantifier_name)

        self._QuantifierName = quantifier_name

        # one-shot lock to inhibit initial Quantification if
        # table data already exists
        self._CollectorLocked = True


    #-------------------------------------------------------
    @G_Global.TimeFunction
    def Quantify(self, context, quantifier_info, valid):
        G_Global.GetCurrentTimer().AddArgument(self._QuantifierName)
        self.ResetModel()
        with G_ScriptGuard("Quantify", context.GetErrorReporter()):
            quantifier = G_Quantifier(quantifier_info)
            quantifier.Run(self._CollectorLocked)
            self._CollectorLocked = False

            table_ctrl = self.GetTableViewCtrl()
            display_props = G_DisplayProperties(nesting = False, valid = valid, reason = "Metric quantification (triggered when parent data is filtered or when the analysis is re-run)")
            table_ctrl.UpdateContent(display_props, quantifier_info )
            table_ctrl.SetFieldMask(-1)

            self.CreateCharts(context, quantifier_info.Charts)



## G_NetworkViewCtrl #######################################

class G_NetworkViewCtrl(G_CoreViewCtrl):

    #-------------------------------------------------------
    def __init__(self, parent):
        super().__init__(parent)

        self._TablePane = self._Notebook = G_NotebookDisplayControl(self)
        self._TableViewCtrls = [None, None]
        self._TableNodeIds = [None, None]

        self.ArrangeChildren()


    def SetupDataTable(self, idx, name, node_id):
        self._TableNodeIds[idx] = node_id
        self._TableViewCtrls[idx] = table_ctrl = G_TableViewCtrl(self._Notebook, True, name)
        self._Notebook.AddPage(table_ctrl, name)
        return table_ctrl


    #-------------------------------------------------------
    def GetTableViewCtrl(self, idx):
        return self._TableViewCtrls[idx]


    #-------------------------------------------------------
    def MakeHtmlChartCtrl(self, pane, context, chart_info):
        chart = G_HtmlNetworkCtrl(pane, context,  chart_info, self._TableViewCtrls)
        chart.CallJavaScript("SetTableNodeIds", self._TableNodeIds[0], self._TableNodeIds[1])
        return chart


    #-------------------------------------------------------
    def ResetModel(self):
        self.ResetCharts()
        self.GetTableViewCtrl(0).ResetModel()
        self.GetTableViewCtrl(1).ResetModel()

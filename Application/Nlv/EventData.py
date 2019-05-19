#
# Copyright (C) Niel Clausen 2017-2018. All rights reserved.
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
import csv
import logging
import matplotlib
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg
from matplotlib.backends.backend_wx import NavigationToolbar2Wx
from matplotlib.figure import Figure
from pathlib import Path

# has to be before import wx
matplotlib.use('WXAgg')

# Application imports 
from .Logmeta import G_FieldSchemata
from .MatchNode import G_MatchItem
from .Project import G_Global
from .StyleNode import G_ColourTraits

# wxWidgets imports
import wx

# Content provider interface
import Nlog



## GLOBAL ##################################################

# Set the default sans-serif font
matplotlib.rcParams['font.sans-serif'] = "Comic Sans MS"

# Set the default font to teh sans-serif font
matplotlib.rcParams['font.family'] = "sans-serif"



## G_ScriptGuard ###########################################

class G_ScriptGuard:

    """
    All use of the user supplied recogniser script, and any
    objects functions returned from the script, should be
    protected within a try block, and any exceptions reported
    back to the UI
    """
    #-------------------------------------------------------
    def __init__(self, name, reporter):
        self._Name = name
        self._Reporter = reporter


    #-------------------------------------------------------
    def __enter__(self):
        pass


    #-------------------------------------------------------
    def __exit__(self, exc_type, exc_value, exc_traceback):
        if exc_traceback is not None:
            message = G_Global.FormatTraceback(exc_type, exc_value, exc_traceback)
            self._Reporter("{} failed\n{}".format(self._Name, message))
            return True



## G_TypeManager ###########################################

class G_TypeManager:
    """Type management and value conversion services for the data model"""

    #-------------------------------------------------------
    def _GetText(view, line_no, field_no):
        return view.GetFieldText(line_no, field_no)
    def _GetUnsigned(view, line_no, field_no):
        return view.GetFieldValueUnsigned(line_no, field_no)
    def _GetSigned(view, line_no, field_no):
        return view.GetFieldValueSigned(line_no, field_no)
    def _GetFloat(view, line_no, field_no):
        return view.GetFieldValueFloat(line_no, field_no)
    def _GetBool(view, line_no, field_no):
        return bool(view.GetFieldValueUnsigned(line_no, field_no))

    def _DisplayStringIcon(value, icon):
        return wx.dataview.DataViewIconText(value, icon)
    def _DisplayValue(value, icon):
        return value

    # model types
    _c_without_icon = 0
    _c_with_icon = 1

    _c_variant_type = 0
    _c_displayvalue_to_display = 1
    _c_data_view_renderer = 2

    _TextModelInfo = [
        ["string", _DisplayValue, wx.dataview.DataViewTextRenderer], # _c_without_icon
        ["wxDataViewIconText", _DisplayStringIcon, wx.dataview.DataViewIconTextRenderer] # _c_with_icon
    ]
    _BoolModelInfo = [
        ["bool", _DisplayValue, wx.dataview.DataViewToggleRenderer], # _c_without_icon
        ["bool", _DisplayValue, wx.dataview.DataViewToggleRenderer] # _c_with_icon
    ]

    # display types (_DisplayInfo rows)
    _c_text = 0
    _c_unsigned = 1
    _c_signed = 2
    _c_float = 3
    _c_bool = 4

    # _DisplayInfo columns
    _c_store_to_value = 0
    _c_store_to_displayvalue = 1
    _c_model_types = 2

    # identify data accessor and display functors
    _DisplayInfo = [
        [_GetText, _GetText, _TextModelInfo], # _c_text
        [_GetUnsigned, _GetText, _TextModelInfo], # _c_unsigned
        [_GetSigned, _GetText, _TextModelInfo], # _c_signed
        [_GetFloat, _GetText, _TextModelInfo], # _c_float
        [_GetBool, _GetBool, _BoolModelInfo] # _c_bool
    ]

    # map Nlog indexer field-types to display info
    _FieldTypes = dict(
        datetime_unix = _DisplayInfo[_c_signed],
        datetime_us_std = _DisplayInfo[_c_signed],
        datetime_tracefmt_int_std = _DisplayInfo[_c_signed],
        datetime_tracefmt_us_std = _DisplayInfo[_c_signed],
        datetime_tracefmt_int_hires = _DisplayInfo[_c_signed],
        datetime_tracefmt_us_hires = _DisplayInfo[_c_signed],
        bool = _DisplayInfo[_c_bool],
        uint08 = _DisplayInfo[_c_unsigned],
        uint16 = _DisplayInfo[_c_unsigned],
        uint32 = _DisplayInfo[_c_unsigned],
        uint64 = _DisplayInfo[_c_unsigned],
        int08 = _DisplayInfo[_c_signed],
        int16 = _DisplayInfo[_c_signed],
        int32 = _DisplayInfo[_c_signed],
        int64 = _DisplayInfo[_c_signed],
        float32 = _DisplayInfo[_c_float],
        float64 = _DisplayInfo[_c_float],
        enum08 = _DisplayInfo[_c_unsigned],
        enum16 = _DisplayInfo[_c_unsigned],
        emitter = _DisplayInfo[_c_text],
        text = _DisplayInfo[_c_text]
    )


    #-------------------------------------------------------
    def ValidateType(type):
        if not type in __class__._FieldTypes:
            raise RuntimeError("Invalid field type: {}".format(type))


    #-------------------------------------------------------
    def GetValue(type, view, line_no, field_no):
        """Fetch field's binary value"""
        me = __class__
        return me._FieldTypes[type][me._c_store_to_value](view, line_no, field_no)


    #-------------------------------------------------------
    def GetDisplayValue(type, icon, view, line_no, field_no):
        """Fetch field's value converted to a type accepted by the display system"""
        me = __class__
        display_info = me._FieldTypes[type]
        display_value = display_info[me._c_store_to_displayvalue](view, line_no, field_no)
        with_icon = icon is not None
        return display_info[me._c_model_types][with_icon][me._c_displayvalue_to_display](display_value, icon)


    #-------------------------------------------------------
    def MakeDataViewColumn(schema, model_column):
        me = __class__
        me.ValidateType(schema.Type)

        model_info = me._FieldTypes[schema.Type][me._c_model_types][schema.IsFirst]
        varianttype = model_info[me._c_variant_type]
        renderer = model_info[me._c_data_view_renderer](varianttype = varianttype)

        width = schema.Width
        if schema.IsFirst:
            width += 36

        return wx.dataview.DataViewColumn(
            schema.Name,
            renderer,
            model_column,
            width = width,
            align = schema.Align,
            flags = wx.dataview.DATAVIEW_COL_RESIZABLE | wx.dataview.DATAVIEW_COL_SORTABLE | wx.dataview.DATAVIEW_COL_REORDERABLE
        )



## G_TableFieldSchema ######################################

class G_TableFieldSchema:
    """Describe a single table field (database 'colummn')"""

    #-------------------------------------------------------
    def __init__(self, name, type, available, width = 0, align = None, formatter = None):
        # user data
        if align is None:
            align = wx.ALIGN_CENTER

        self.Name = name
        self.Type = type
        self.Width = width
        self.Align = align
        self.Formatter = formatter
        self.Available = self.Visible = available

        # Nlog indexer info
        self.Separator = ","
        self.SeparatorCount = 1
        self.MinWidth = 0

        # management data
        self.IsFirst = False
        self.ColumnColour = None


    #-------------------------------------------------------
    def Display(self):
        return self.Available and self.Visible


    #-------------------------------------------------------
    def Update(self, name = "", width = 0, align = None, formatter = None):
        if name != "":
            self.Name = name
        if width != 0:
            self.Width = width
        if align is not None:
            self.Align = align
        if formatter is not None:
            self.Formatter = formatter

    def SetAsLastField(self):
        self.Separator = "\r"



## G_TableSchema ###########################################

class G_TableSchema(G_FieldSchemata):
    """Describe all the fields of a table (database 'row')"""

    #-------------------------------------------------------
    def __init__(self, guid = ""):
        super().__init__(guid)
        self._SetTextOffsetSize(16)
        self.DurationScale = 1
        self.ColParentId = 0
        self.ColStart = 1
        self.ColFinish = None
        self.ColDuration = None


    #-------------------------------------------------------
    def InitStart(self, name, width, align, formatter):
        self[self.ColStart].Update(name, width, align, formatter)

    def AppendFinish(self, field_schema):
        self.ColFinish = len(self._FieldSchemata)
        self.Append(field_schema)

    def AppendDuration(self, scale, field_schema):
        self.ColDuration = len(self._FieldSchemata)
        self.DurationScale = scale
        self.Append(field_schema)



## G_TableSchemaCollector ##################################

class G_TableSchemaCollector:
    """Collect schema data for a table"""

    #-------------------------------------------------------
    def __init__(self):
        self._TableSchema = G_TableSchema("14C89CE3-E8A4-4F28-99EB-3EF5D5FD3B13")


    #-------------------------------------------------------
    @staticmethod
    def _CalcAlign(align, allow_none = False):
        al = None

        if align is not None and len(align) != 0:
            al = wx.ALIGN_CENTER
            if align[0] == "l":
                al = wx.ALIGN_LEFT
            elif align[0] == "r":
                al = wx.ALIGN_RIGHT

        if al is None and not allow_none:
            raise RuntimeError("Invalid alignment: {}".format(align))

        return al


    @staticmethod
    def MakeTableFieldSchema(name, type, width, align, formatter):
        G_TypeManager.ValidateType(type)
        al = __class__._CalcAlign(align)
        return G_TableFieldSchema(name, type, True, width, al, formatter)


    #-------------------------------------------------------
    def AddField(self, name, type, width = 30, align = "centre", formatter = None):
        field_schema = self.MakeTableFieldSchema(name, type, width, align, formatter)
        self._TableSchema.Append(field_schema)


    #-------------------------------------------------------
    def Close(self):
        self._TableSchema[-1].SetAsLastField()
        return self._TableSchema



## G_EventSchemaCollector ##################################

class G_EventSchemaCollector(G_TableSchemaCollector):
    
    #-------------------------------------------------------
    def __init__(self, date_fieldtype):
        super().__init__()

        # ColParentId
        self._DateFieldType = date_fieldtype
        self._TableSchema.Append(G_TableFieldSchema("ParentId", "int32", False))

        # ColStart
        self._TableSchema.Append(G_TableFieldSchema("Start", self._DateFieldType, True))


    #-------------------------------------------------------
    @staticmethod
    def _CalcScale(scale):
        if scale == "s":
            return 1000000000
        elif scale == "ms":
            return 1000000
        elif scale == "us":
            return 1000
        elif scale == "ns":
            return 1
        else:
            raise RuntimeError("Invalid scale: {}".format(scale))


    #-------------------------------------------------------
    def InitStart(self, name = "", width = 0, align = None, formatter = None):
        al = self._CalcAlign(align, True)
        self._TableSchema.InitStart(name, width, al, formatter)


    #-------------------------------------------------------
    def AddFinish(self, name, width = 30, align = "centre", formatter = None):
        field_schema = self.MakeTableFieldSchema(name, self._DateFieldType, width, align, formatter)
        self._TableSchema.AppendFinish(field_schema)


    #-------------------------------------------------------
    def AddDuration(self, name, scale = "us", width = 30, align = "centre", formatter = None):
        scale_factor = self._CalcScale(scale)
        field_schema = self.MakeTableFieldSchema(name, "int64", width, align, formatter)
        self._TableSchema.AppendDuration(scale_factor, field_schema)

        

## G_EventItem #############################################

class G_EventItem:

    #-------------------------------------------------------
    def __init__(self, log_start_line, log_finish_line, event_number, cookie):
        self.LogStartLine = log_start_line
        self.LogFinishLine = log_finish_line
        self._EventNumber = event_number
        self.Cookie = cookie



## G_EventCollector ########################################

class G_EventCollector:
    """Collect and save event data from an event analyser"""

    #-------------------------------------------------------
    def __init__(self, filename, event_schema, user_analyser, date_fieldid):
        self._CsvFile = open(filename, "w", newline = "")
        self._CsvWriter = csv.writer(self._CsvFile)
        self._EventNo = 0
        self._FieldCount = len(event_schema)
        self._UserAnalyser = user_analyser
        self._EventSchema = event_schema
        self._DateFieldId = date_fieldid

        # note, somewhat arbitrary limit (32-bit signed-int-max)
        max = 2147483647
        self._Stack = [G_EventItem(0, max, -1, None)]

        # row headers
        headers = [field_schema.Name for field_schema in event_schema]
        self._CsvWriter.writerow(headers)


    #-------------------------------------------------------
    def SetStartTimeCode(self, log_lineno, line_accessor):
        self._StartLogLineno = log_lineno
        self._StartDatetext = line_accessor.GetFieldText(self._DateFieldId)
        self._StartTimecode = line_accessor.GetUtcTimecode()


    def SetFinishTimeCode(self, log_lineno, line_accessor):
        self._FinishLogLineno = log_lineno
        self._FinishDatetext = line_accessor.GetFieldText(self._DateFieldId)
        self._FinishTimecode = line_accessor.GetUtcTimecode()
        self._EventIdentified = False


    #-------------------------------------------------------
    def StackBack(self):
        return self._Stack[len(self._Stack) - 1]


    def UpdateStack(self, cookie):
        cur = G_EventItem(self._StartLogLineno, self._FinishLogLineno, self._EventNo, cookie)
 
        # remove any entries that finish before 'cur' starts
        while cur.LogStartLine > self.StackBack().LogFinishLine:
            self._Stack.pop()
 
        # since events are published in start order, we know that
        # 'cur' starts after 'prev' (two events can't start on the
        # same line)
        self._Stack.append(cur)
 
        return cur
 
 
    def CalcParentId(self, cookie):
        # note: relies on the fact that events are discovered in order of their
        # start lines; see G_Analyser.CollectEvents
 
        cur = self.UpdateStack(cookie)
        for idx in range(len(self._Stack) - 2, 0, -1):
            prev = self._Stack[idx]
            if prev.Cookie is not None and prev.LogFinishLine > cur.LogFinishLine:
                if self._UserAnalyser.IsContained(prev.Cookie, cur.Cookie):
                    return prev._EventNumber
 
        return -1


    #-------------------------------------------------------
    def AddEvent(self, cookie, recogniser_values):
        values = [self.CalcParentId(cookie), self._StartDatetext]

        if self._EventSchema.ColFinish is not None:
            values.append(self._FinishDatetext)

        if self._EventSchema.ColDuration is not None:
            ns_duration = self._FinishTimecode.GetOffsetNs() - self._StartTimecode.GetOffsetNs()
            duration = int(ns_duration / self._EventSchema.DurationScale)
            values.append(duration)

        values.extend(recogniser_values)

        if len(values) != self._FieldCount:
            raise RuntimeError("Incorrect number of field values (including hidden): got:{} exp:{}".format(len(values), self._FieldCount))

        self._EventNo += 1
        self._EventIdentified = True

        text_values = [str(v).replace(',', '_').replace('"', "'").rstrip() for v in values]
        self._CsvWriter.writerow(text_values)


    def CancelEvent(self):
        self._EventIdentified = True


    def WasEventIdentified(self):
        return self._EventIdentified


    #-------------------------------------------------------
    def Close(self):
        self._CsvFile.close()


    
## G_LineAccessor ##########################################

class G_LineAccessor:

    #-------------------------------------------------------
    def __init__(self, field_ids, lineset):
        self._FieldIds = field_ids
        self._LineSet = lineset
        self._LineNo = None


    #-------------------------------------------------------
    def SetLineNo(self, line_no):
        self._LineNo = line_no


    #-------------------------------------------------------
    def _CalcFieldIdx(self, field_name_or_idx):
        if isinstance(field_name_or_idx, int):
            return field_name_or_idx
        else:
            return self._FieldIds[field_name_or_idx]

    def GetFieldValueUnsigned(self, field_name_or_idx):
        field_idx = self._CalcFieldIdx(field_name_or_idx)
        return self._LineSet.GetFieldValueUnsigned(self._LineNo, field_idx)

    def GetFieldValueSigned(self, field_name_or_idx):
        field_idx = self._CalcFieldIdx(field_name_or_idx)
        return self._LineSet.GetFieldValueSigned(self._LineNo, field_idx)

    def GetFieldValueFloat(self, field_name_or_idx):
        field_idx = self._CalcFieldIdx(field_name_or_idx)
        return self._LineSet.GetFieldValueFloat(self._LineNo, field_idx)


    #-------------------------------------------------------
    def GetFieldText(self, field_name_or_idx):
        field_idx = self._CalcFieldIdx(field_name_or_idx)
        return self._LineSet.GetFieldText(self._LineNo, field_idx)


    #-------------------------------------------------------
    def GetNonFieldText(self):
        return self._LineSet.GetNonFieldText(self._LineNo)


    #-------------------------------------------------------
    def GetUtcTimecode(self):
        return self._LineSet.GetUtcTimecode(self._LineNo)



## G_Analyser ##############################################

class G_Analyser:
    """Analyse a log, creates an event table (CSV)"""

    #-------------------------------------------------------
    def __init__(self, meta_only, filename, log_schema, prefilter, logfile):
        self._MetaOnly = meta_only
        self._Filename = filename
        self._LogSchema = log_schema
        self._PreFilter = prefilter
        self._LogFile = logfile
        self._EventSchema = G_TableSchema()
        self._EventMetrics = None

        field_ids = dict()
        for (idx, name) in enumerate(log_schema.GetFieldNames()):
            field_ids.update([[name, idx]])
        self._LogFieldIds = field_ids

    def GetDateFieldId(self):
        return self._LogFile.GetTimecodeBase().GetFieldId() - 1


    #-------------------------------------------------------
    def ConvertMatchToLVFText(self, match):
        if match is None or match.IsEmpty():
            return ""

        case = ""
        if not match.MatchCase:
            case = "i"

        selector_id = match.GetSelectorId()
        if selector_id == Nlog.EnumSelector.Literal:
            return 'log ~= "{}"{}'.format(match.MatchText, case)

        elif selector_id == Nlog.EnumSelector.RegularExpression:
            return 'log ~= /{}/{}'.format(match.MatchText, case)

        elif selector_id == Nlog.EnumSelector.LogviewFilter:
            return match.MatchText

        else:
            raise RuntimeError("Unknown match type: {}".format(match.MatchType))


    def BuildLVFText(self, recogniser_match):
        ltext = self.ConvertMatchToLVFText(self._PreFilter)
        lltext = len(ltext)

        rtext = self.ConvertMatchToLVFText(recogniser_match)
        lrtext = len(rtext)

        if lltext == 0  and lrtext == 0:
            raise RuntimeError("Empty line filter")

        if lrtext == 0:
            raise RuntimeError("Empty recogniser line filter")

        if lltext == 0:
            return G_MatchItem("LogView Filter", rtext)
        else:
            return G_MatchItem("LogView Filter", "({}) and ({})".format(ltext, rtext))


    def BuildLineSet(self, recogniser_match):
        match = self.BuildLVFText(recogniser_match)

        selector = match.MakeSelector(self._LogFile)
        if selector is None:
            raise RuntimeError("Broken filter: {}".format(match.MatchText))

        lineset = self._LogFile.CreateLineSet()
        lineset.Filter(selector, False)
        return lineset


    def BuildLineSets(self, user_analyser):
        descs = user_analyser.DefineFilter()
        start_view = self.BuildLineSet(G_MatchItem(descs[0][0], descs[0][1]))
        finish_view = self.BuildLineSet(G_MatchItem(descs[1][0], descs[1][1]))
        return (start_view, finish_view)


    #-------------------------------------------------------
    def CollectEventSchema(self, user_analyser):
        date_fieldtype = self._LogSchema[self.GetDateFieldId()].Type
        schema_collector = G_EventSchemaCollector(date_fieldtype)
        user_analyser.DefineSchema(schema_collector)
        return schema_collector.Close()


    #-------------------------------------------------------
    def CollectEventMetrics(self, event_metrics):
        return event_metrics


    #-------------------------------------------------------
    def CollectEvents(self, event_collector, start_view, finish_view, user_analyser):
        # observation: this could be made multithreaded

        field_ids = self._LogFieldIds

        start_accessor = G_LineAccessor(field_ids, start_view)
        start_line_count = start_view.GetNumLines()

        finish_accessor = G_LineAccessor(field_ids, finish_view)
        finish_line_count = finish_view.GetNumLines()

        for start_lineno in range(start_line_count):
            start_accessor.SetLineNo(start_lineno)
            match_finish_func = user_analyser.MatchEventStart(start_accessor)

            if match_finish_func is None:
                continue

            # convert the index (into the lineset) to the actual logfile line number
            start_log_lineno = start_view.ViewLineToLogLine(start_lineno)
            event_collector.SetStartTimeCode(start_log_lineno, start_accessor)

            # hence find the lineno to the first-event finish candidate in the finish
            # view; negative means "not found"
            first_finish_lineno = finish_view.LogLineToViewLine(start_log_lineno)
            if first_finish_lineno < 0:
                continue

            # now find the event finish line, and, hence, create the event
            for finish_lineno in range(first_finish_lineno, finish_line_count):
                finish_accessor.SetLineNo(finish_lineno)
                finish_log_lineno = finish_view.ViewLineToLogLine(finish_lineno)
                event_collector.SetFinishTimeCode(finish_log_lineno, finish_accessor)

                match_finish_func(finish_accessor, event_collector)
                if event_collector.WasEventIdentified():
                    break

            if not event_collector.WasEventIdentified():
                logging.info("Event close not found (performance warning)")


    #-------------------------------------------------------
    def GetMeta(self):
        return (self._EventSchema, self._EventMetrics)


    #-------------------------------------------------------
    def Register(self, user_analyser, user_metrics = None):
        self._EventSchema = self.CollectEventSchema(user_analyser)
        self._EventMetrics = self.CollectEventMetrics(user_metrics)

        if self._MetaOnly:
            return

        (start_view, finish_view) = self.BuildLineSets(user_analyser)

        event_collector = G_EventCollector(self._Filename, self._EventSchema, user_analyser, self.GetDateFieldId())
        self.CollectEvents(event_collector, start_view, finish_view, user_analyser)
        event_collector.Close()



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

class G_TableDataModel(wx.dataview.DataViewModel):

    #-------------------------------------------------------
    def __init__(self, permit_nesting):
        super().__init__()

        self._PermitNesting = permit_nesting
        self._ViewFlat = True
        self._RawFieldMask = 0
        self._IsValid = True
        self._InvalidColour = G_ColourTraits.MakeColour("FIREBRICK")
        self._ColumnColours = []
        self._FilterMatch = None
        self._Hiliters = []
        self.Reset()

        self._Icons = [
            wx.ArtProvider.GetIcon(wx.ART_NORMAL_FILE, wx.ART_TOOLBAR, (16, 16)),
            wx.ArtProvider.GetIcon(wx.ART_FOLDER, wx.ART_TOOLBAR, (16, 16))
        ]


    #-------------------------------------------------------
    @staticmethod
    def ItemToKey(item):
        return int(item.GetID()) - 1


    @staticmethod
    def KeyToItem(key):
        return wx.dataview.DataViewItem(key + 1)


    #-------------------------------------------------------
    def Reset(self, table_schema = None):
        self._N_Logfile = None
        self._N_LineSet = None

        if table_schema is None:
            table_schema = G_TableSchema()
        self._TableSchema = table_schema

        self._ModelColumnToFieldId = []
        field_id = 0
        for field_schema in self._TableSchema:
            fid = -1

            if field_schema.Available:
                fid = field_id
                field_id += 1

            self._ModelColumnToFieldId.append(fid)

        self._ParentKeyToChildKeys = dict()


    #-------------------------------------------------------
    def GetFieldInfo(self, col_num):
        field_schema = self._TableSchema[col_num]
        return (field_schema.Type, field_schema.IsFirst)

    def GetFieldType(self, col_num):
        return self._TableSchema[col_num].Type

    def GetFieldValue(self, item_key, col_num):
        type = self.GetFieldType(col_num)
        return G_TypeManager.GetValue(type, self._N_LineSet, item_key, col_num)

    def GetFieldDisplayValue(self, item_key, col_num):
        icon = None
        (type, is_first) = self.GetFieldInfo(col_num)
        if is_first:
            icon = self._Icons[item_key in self._ParentKeyToChildKeys]
        return G_TypeManager.GetDisplayValue(type, icon, self._N_LineSet, item_key, col_num)


    #-------------------------------------------------------
    def GetTableSchema(self):
        return self._TableSchema

    def GetLineSet(self):
        return self._N_LineSet

    def GetNumItems(self):
        if self._N_LineSet is None:
            return 0
        else:
            return self._N_LineSet.GetNumLines()


    #-------------------------------------------------------
    def GetRowKeys(self):
        return range(self.GetNumItems())


    #-------------------------------------------------------
    def GetItemKeyParentKey(self, item_key):
        parent_id = self.GetFieldValue(item_key, self._TableSchema.ColParentId)
        if parent_id < 0:
            return parent_id

        candidate_parent_key = self._N_LineSet.LogLineToViewLine(parent_id)
        if candidate_parent_key < 0:
            return candidate_parent_key

        # check for an exact match
        actual_parent_id = self._N_LineSet.ViewLineToLogLine(candidate_parent_key)
        if parent_id == actual_parent_id:
            return candidate_parent_key

        return -1


    #-------------------------------------------------------
    def GetEventRange(self, item):
        table_schema = self._TableSchema
        item_key = self.ItemToKey(item)
        start_offset = finish_offset = self.GetFieldValue(item_key, table_schema.ColStart)

        # if we have a real finish time, then use it
        if table_schema.ColFinish is not None:
            finish_offset = self.GetFieldValue(item_key, table_schema.ColFinish)

        # otherwise, synthesise a finish time; for cases where the duration is rounded
        # this will not be entirely accurate - which may show up in the UI
        elif table_schema.ColDuration is not None:
            scaled_duration = self.GetFieldValue(item_key, table_schema.ColDuration)
            finish_offset = start_offset + scaled_duration * table_schema.DurationScale

        utc_datum = self._N_Logfile.GetTimecodeBase().GetUtcDatum()
        return (Nlog.NTimecode(utc_datum, start_offset),
            Nlog.NTimecode(utc_datum, finish_offset)
        )


    #-------------------------------------------------------
    def GetColumnCount(self):
        return len(self._TableSchema)


    def GetColumnType(self, col_num):
        # Maintenance note: have never seen this called
        return G_TypeManager.GetVariantType(self.GetFieldType(col_num))


    def GetChildren(self, parent_item, children):
        """
        The view calls this method to find the children of any node in the
        control. There is an implicit hidden root node, and the top level
        item(s) should be reported as children of this node. A List view
        simply provides all items as children of this hidden root. A Tree
        view adds additional items as children of the other items, as needed,
        to provide the tree hierarchy.
        """

        if self._N_LineSet is None:
            return 0

        count = 0

        # "children" argument has no 'extend' method, so use iterators here
        def AppendChildren(item_keys):
            nonlocal count
            for item_key in item_keys:
                children.append(self.KeyToItem(item_key))
                count += 1

        if self._ViewFlat:
            if parent_item:
                raise RuntimeError
            AppendChildren(self.GetRowKeys())

        elif parent_item:
            parent_key = self.ItemToKey(parent_item)
            if parent_key in self._ParentKeyToChildKeys:
                AppendChildren(self._ParentKeyToChildKeys[parent_key])

        else:
            # root node; all rows without a stated parent belong here
            keys = [key for key in self.GetRowKeys() if self.GetItemKeyParentKey(key) < 0]
            AppendChildren(keys)

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
            return item_key in self._ParentKeyToChildKeys


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
        parent_key = self.GetItemKeyParentKey(item_key)

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
        for hiliter in self._Hiliters:
            if self._N_LineSet.GetHiliter(hiliter._Id).Hit(item_key):
                wrapped_attr.SetBgColour(hiliter._Colour)
                break

        formatter = self._TableSchema[col_num].Formatter
        if formatter is not None:
            formatter(self.GetFieldValue(item_key, col_num), wrapped_attr)

        return True


    def GetValue(self, item, col_num):
        """Return the value to be displayed for this item and column."""
        item_key = self.ItemToKey(item)
        return self.GetFieldDisplayValue(item_key, col_num)


    def Compare(self, item_l, item_r, col_num, ascending):
        def cmp(l, r):
            if l < r:
                return -1
            elif l > r:
               return 1
            else:
                return 0

        l = self.GetFieldValue(self.ItemToKey(item_l), col_num)
        r = self.GetFieldValue(self.ItemToKey(item_r), col_num)

        if ascending:
            return cmp(l, r)
        else:
            return cmp(r, l)


    #-------------------------------------------------------
    def GetNextItem(self, what, cur_item, forward, index = 0):
        cur_key = 0
        if cur_item is not None:
          cur_key = self.ItemToKey(cur_item)
  
        if what == "hilite":
            next_key = self._N_LineSet.GetHiliter(index).Search(cur_key, forward)

        if next_key >= 0:
            return self.KeyToItem(next_key)
        return None


    #-------------------------------------------------------
    def HiliteLineSet(self, hiliter, match = None):
        if match is not None:
            hiliter._Match = match

        if hiliter._Match is None:
            return True

        if self._N_LineSet is None:
            return True

        selector = hiliter._Match.MakeSelector(self._N_Logfile, empty_selects_all = False)
        if selector is not None:
            self._N_LineSet.GetHiliter(hiliter._Id).SetSelector(selector)
            return True
        return False

        
    def FilterLineSet(self, match):
        self._FilterMatch = match

        if self._N_Logfile is None:
            return False

        if match is not None:
            selector = match.MakeSelector(self._N_Logfile)
            if selector is None:
                return False

            if self._N_LineSet is None:
                return True

            self._N_LineSet.Filter(selector, False)

        map = self._ParentKeyToChildKeys = dict()

        if not self._PermitNesting:
            return True

        for child_key in self.GetRowKeys():
            parent_key = self.GetItemKeyParentKey(child_key)
            if parent_key >= 0:
                if parent_key in map:
                    map[parent_key].append(child_key)
                else:
                    map[parent_key] = [child_key]

        return True


    def UpdateContent(self, nesting, table_schema, filename, valid):
        self.Reset(table_schema)
        self.UpdateNesting(nesting, False)
        self.UpdateValidity(valid)

        num_fields = self.GetColumnCount()
        if Path(filename).exists() and num_fields != 0:
            self._N_Logfile = Nlog.MakeLogfile(filename, table_schema.MakeLogAccessor(), None, 1)

        # robustness, for broken logfiles ...
        if self._N_Logfile is not None:
            self._N_LineSet = self._N_Logfile.CreateLineSet()

            self.MaskLineSet()
            self.FilterLineSet(self._FilterMatch)

            self._N_LineSet.SetNumHiliter(len(self._Hiliters))
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
        if self._N_LineSet is not None:
            self._N_LineSet.SetNumHiliter(num_hiliter)


    #-------------------------------------------------------
    def UpdateFilter(self, match):
        if not self.FilterLineSet(match):
            return False
        
        self.Cleared()
        return True


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

        if self._N_LineSet is not None:
            full_mask = self.CalcLineSetFieldMask(in_mask)
            self._N_LineSet.SetFieldMask(full_mask)

            
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
        if not self._PermitNesting:
            return

        if nesting is None:
            return

        view_flat = not nesting
        if self._ViewFlat == view_flat:
            return

        self._ViewFlat = view_flat
        if do_rebuild:
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
    def __init__(self, parent, permit_nesting, flags):
        super().__init__(
            parent,
            style = wx.dataview.DV_ROW_LINES
            | wx.dataview.DV_VERT_RULES
            | flags
        )

        self.AssociateModel(G_TableDataModel(permit_nesting))


    #-------------------------------------------------------
    def GetTableSchema(self):
        return self.GetModel().GetTableSchema()


    #-------------------------------------------------------
    def GetLineSet(self):
        return self.GetModel().GetLineSet()


    #-------------------------------------------------------
    def ResetModel(self):
        self.ClearColumns()
        return self.GetModel().Reset()


    #-------------------------------------------------------
    def UpdateColumns(self):
        self.ClearColumns()
        for (model_num, field_schema) in enumerate(self.GetTableSchema()):
            if field_schema.Display():
                self.AppendColumn(G_TypeManager.MakeDataViewColumn(field_schema, model_num))



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

        except BaseException as ex:
            analysis_props.ErrorReporter("UpdateContent failed\n{}".format(G_Global.FormatLastTraceback()))


    #-------------------------------------------------------
    def UpdateDisplay(self, nesting = None, valid = None):
        if self.GetModel().UpdateDisplay(nesting, valid):
            self.Refresh()        


    #-------------------------------------------------------
    def SetFieldMask(self, field_mask):
        self.GetModel().SetFieldMask(field_mask)
        self.UpdateColumns()



## G_TableViewCtrl #########################################

class G_TableViewCtrl(G_DataViewCtrl):

    #-------------------------------------------------------
    def __init__(self, parent, node, permit_nesting = True, multiple_selection = False):
        flags = 0
        if multiple_selection:
            flags = wx.dataview.DV_MULTIPLE

        super().__init__(parent, permit_nesting, flags)

        self._SelectionHandlerNode = node
        self.Bind(wx.dataview.EVT_DATAVIEW_SELECTION_CHANGED, self.OnItemActivated)


    #-------------------------------------------------------
    def GetNumItems(self):
        return self.GetModel().GetNumItems()


    #-------------------------------------------------------
    def GetSelectedItems(self):
        return [G_TableDataModel.ItemToKey(item) for item in self.GetSelections()]


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
    def GetEventRange(self, event_no):
        return self.GetModel().GetEventRange(event_no)

    def OnItemActivated(self, evt):
        self._SelectionHandlerNode.OnTableSelectionChanged(evt.GetItem())



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



## G_ChangeTracker #########################################

class G_ChangeTracker:

    #-------------------------------------------------------
    def __init__(self):
        self._MetricsChanged = self._SelectionChanged = self._ParametersChanged = True


    #-------------------------------------------------------
    def Update(self, metrics_changed, selection_changed, parameters, name):
        if metrics_changed:
            self._MetricsChanged = True

        if selection_changed:
            self._SelectionChanged = True

        if parameters is not None:
            self._ParametersChanged = True

        if name is not None:
            if name == "metrics":
                self._MetricsChanged = True
            elif name == "selection":
                self._SelectionChanged = True


    #-------------------------------------------------------
    def Changed(self, include_selection):
        selection = include_selection and self._SelectionChanged
        res = self._MetricsChanged or selection or self._ParametersChanged
        self._MetricsChanged = self._SelectionChanged = self._ParametersChanged = False
        return res



## G_ChartViewCtrl #########################################

class G_ChartViewCtrl(wx.Panel):

    #-------------------------------------------------------
    def __init__(self, parent, chart_designer, table_view_ctrl, error_reporter):
        super().__init__(parent)
        self._ChartDesigner = chart_designer
        self._TableViewCtrl = table_view_ctrl
        self._ErrorReporter = error_reporter

        self._ParameterChangeTracker = G_ChangeTracker()
        self._RealiseChangeTracker = G_ChangeTracker()

        self._Parameters = None
        self._ParamaterValues = dict()

        self._RealiseLock = True

        self._Figure = Figure(frameon = True)
        self._Canvas = FigureCanvasWxAgg(self, -1, self._Figure)
        self._Sizer = wx.BoxSizer(wx.VERTICAL)
        self._Sizer.Add(self._Canvas, flag = wx.ALL | wx.EXPAND | wx.ALIGN_CENTER)
        self.SetSizer(self._Sizer)


    #-------------------------------------------------------
    def GetTableData(self):
        metrics = self._TableViewCtrl.GetLineSet()
        num_metrics = metrics.GetNumLines()
        selection = self._TableViewCtrl.GetSelectedItems()
        return (metrics, num_metrics, selection)


    #-------------------------------------------------------
    def DefineParameters(self):
        with G_ScriptGuard("DefineParameters", self._ErrorReporter):
            if self._ParameterChangeTracker.Changed(self._ChartDesigner.WantSelection):
                (metrics, num_metrics, selection) = self.GetTableData()
                collector = G_ParameterCollector()
                self._ChartDesigner.DefineParameters(collector, metrics, num_metrics, selection)
                self._Parameters = collector.Close()

        return self._Parameters


    #-------------------------------------------------------
    def Realise(self):
        """Redraw the chart if needed"""
        with G_ScriptGuard("Realise", self._ErrorReporter):
            if not self._RealiseLock and self._RealiseChangeTracker.Changed(self._ChartDesigner.WantSelection):
                (metrics, num_metrics, selection) = self.GetTableData()
                self._Figure.clear()
                self._ChartDesigner.Realise(self._Figure, metrics, num_metrics, self._ParamaterValues, selection)
                self._Canvas.draw()


    #-------------------------------------------------------
    def Update(self, metrics_changed = False, selection_changed = False, parameters = None, name = None):
        for tracker in [self._ParameterChangeTracker, self._RealiseChangeTracker]:
            tracker.Update(metrics_changed, selection_changed, parameters, name)

        if parameters is not None:
            self._ParamaterValues = parameters

        if name is not None and name == "unlock":
            self._RealiseLock = False

        return self
            


## G_MetricsCollector ######################################

class G_MetricsCollector:
    """Collect and save metrics data from an event quantifier"""

    #-------------------------------------------------------
    def __init__(self, filename, metric_schema, event_field_names):
        self._CsvFile = open(filename, "w", newline = "")
        self._CsvWriter = csv.writer(self._CsvFile)
        self._FieldCount = len(metric_schema)

        # row headers
        self._CsvWriter.writerow(metric_schema.GetFieldNames())

        # map event field names to their indexes
        self._FieldIds = dict()
        for (idx, name) in enumerate(event_field_names):
            # allow for the "parent" hidden field
            self._FieldIds.update([[name, idx + 1]])


    #-------------------------------------------------------
    def GetFieldId(self, field_name):
        return self._FieldIds[field_name]


    #-------------------------------------------------------
    def AddMetric(self, values):
        if len(values) != self._FieldCount:
            raise RuntimeError("Incorrect number of values: got:{} exp:{}".format(len(values), self._FieldCount))

        text_values = [str(v).replace(',', '_').replace('"', "'") for v in values]
        self._CsvWriter.writerow(text_values)


    #-------------------------------------------------------
    def Close(self):
        self._CsvFile.close()



## G_MetricsViewCtrl #######################################

class G_MetricsViewCtrl(wx.SplitterWindow):

    #-------------------------------------------------------
    def __init__(self, parent, quantifier_name, id):
        super().__init__(parent, style = wx.SP_LIVE_UPDATE)

        # the ID distinguishes different tables in the event,
        # but otherwise, has no real meaning
        self._ID = id
        self._Quantifier = None
        self._QuantifierName = quantifier_name
        self._CollectorLocked = True

        self.SetMinimumPaneSize(150)
        self.SetSashGravity(0.5)

        self._TableViewCtrl = G_TableViewCtrl(self, self, permit_nesting = False, multiple_selection = True)

        self._ChartPane = wx.Panel(self)
        self._ChartPane.SetSizer(wx.BoxSizer(wx.VERTICAL))

        self.SplitHorizontally(self._TableViewCtrl, self._ChartPane)


    #-------------------------------------------------------
    def GetChartViewCtrl(self, chart_no, activate):
        if self._Quantifier is None:
            return None

        pane = self._ChartPane
        pane_sizer = pane.GetSizer()

        if pane_sizer.IsEmpty():
            activate = True
            for chart_designer in self._Quantifier.Charts:
                chart_view_ctrl = G_ChartViewCtrl(pane, chart_designer, self._TableViewCtrl, self._ErrorReporter)
                pane_sizer.Add(chart_view_ctrl, flag = wx.EXPAND | wx.ALIGN_CENTER)

        sizer_items = pane_sizer.GetChildren()

        if activate:
            pane_sizer.ShowItems(True)

            for (idx, item) in enumerate(sizer_items):
                if idx != chart_no:
                    item.Show(False)
    
            pane_sizer.Layout()

        return sizer_items[chart_no].GetWindow()


    #-------------------------------------------------------
    def GetTableViewCtrl(self):
        return self._TableViewCtrl


    #-------------------------------------------------------
    def Assemble(self, events, analysis_props):
        self.ResetModel(analysis_props.ErrorReporter)
        with G_ScriptGuard("Assemble", self._ErrorReporter):
            self._Quantifier = analysis_props.GetQuantifier(self._QuantifierName)

            schema_collector = G_TableSchemaCollector()
            self._Quantifier.DefineSchema(schema_collector)
            self._TableSchema = schema_collector.Close()

            path = Path(analysis_props.FileName)
            path = path.with_name("{}.{}.csv".format(path.stem, self._ID))
            self._TableFileName = str(path)

            if not self._CollectorLocked or not path.exists():
                event_field_names = analysis_props.EventSchema.GetFieldNames()
                collector = G_MetricsCollector(self._TableFileName, self._TableSchema, event_field_names)

                self._Quantifier.Assemble(events, events.GetNumLines(), collector)
                collector.Close()

            self._TableViewCtrl.UpdateContent(False, self._TableSchema, self._TableFileName, analysis_props.Valid)
            self._TableViewCtrl.SetFieldMask(-1)


    #-------------------------------------------------------
    def UpdateCharts(self, name):
        active_chart = self.GetChartViewCtrl(0, False)

        for chart_view in self._ChartPane.GetChildren():
            chart_view.Update(name = name)
            if chart_view.IsShown():
                active_chart = chart_view

        return active_chart


    def UnlockCharts(self):
        self._CollectorLocked = False
        return self.UpdateCharts("unlock")


    def UpdateMetrics(self):
        return self.UpdateCharts("metrics")


    def UpdateSelection(self):
        return self.UpdateCharts("selection")


    #-------------------------------------------------------
    def OnTableSelectionChanged(self, item):
        self.UpdateSelection().Realise()


    #-------------------------------------------------------
    def ResetModel(self, error_reporter = None):
        self._Quantifier = None
        self._TableSchema = None
        self._TableFileName = None
        self._ErrorReporter = error_reporter

        self._ChartPane.GetSizer().Clear(delete_windows = True)

        self._TableViewCtrl.ResetModel()
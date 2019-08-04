#
# Copyright (C) Niel Clausen 2017-2019. All rights reserved.
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
from .Project import G_Project

# may not be needed
from .MatchNode import G_MatchItem
from .Project import G_Global
from .Project import G_PerfTimerScope
from .StyleNode import G_ColourTraits

# wxWidgets imports
import wx

# may not be needed
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
    protected within a 'with' block, and any exceptions reported
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



## G_ProjectionTypeManager #################################

class G_ProjectionTypeManager:
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



## G_ProjectionFieldSchema #################################

class G_ProjectionFieldSchema:
    """Describe a single projector field (database 'colummn')"""

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
        self.SortDirection = 0
        self.SortColumn = None


    #-------------------------------------------------------
    def Display(self):
        return self.Available and self.Visible

    def ToggleSortDirection(self):
        if self.SortDirection == 0:
            self.SortDirection = 1
        else:
            self.SortDirection *= -1

        return (self.SortColumn, self.SortDirection)


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



## G_ProjectionSchema ######################################

class G_ProjectionSchema(G_FieldSchemata):
    """Describe all the projected fields (database 'row')"""

    #-------------------------------------------------------
    def __init__(self, guid = ""):
        super().__init__("sql", guid)
        self._SetTextOffsetSize(16)
        self.DurationScale = 1
        self.ColParentId = None
        self.ColStart = None
        self.ColStartOffset = None
        self.ColFinish = None
        self.ColFinishOffset = None
        self.ColDuration = None


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


    #-------------------------------------------------------
    def MakeHiddenFieldSchema(self, name, type):
        G_ProjectionTypeManager.ValidateType(type)
        return self.Append(G_ProjectionFieldSchema(name, type, False))


    def MakeFieldSchema(self, name, type, width = 30, align = "centre", formatter = None):
        G_ProjectionTypeManager.ValidateType(type)
        al = __class__._CalcAlign(align)
        return self.Append(G_ProjectionFieldSchema(name, type, True, width, al, formatter))


    #-------------------------------------------------------
    def AddNesting(self):
        self.ColParentId = self.MakeHiddenFieldSchema("parent_id", "int32")

    def AddField(self, name, type, width, align, formatter):
        self.MakeFieldSchema(name, type, width, align, formatter)

    def AddStart(self, name, width, align, formatter):
        self.ColStart = self.MakeFieldSchema(name, "text", width, align, formatter)
        self.ColStartOffset = self.MakeHiddenFieldSchema("start_offset_ns", "uint64")
        self[self.ColStart].SortColumn = self.ColStartOffset

    def AddFinish(self, name, width, align, formatter):
        self.ColFinish = self.MakeFieldSchema(name, "text", width, align, formatter)
        self.ColFinishOffset = self.MakeHiddenFieldSchema("finish_offset_ns", "uint64")
        self[self.ColFinish].SortColumn = self.ColFinishOffset

    def AddDuration(self, scale, name, width, align, formatter):
        self.ColDuration = self.MakeFieldSchema(name, "int64", width, align, formatter)
        self.DurationScale = scale



## G_CoreProjectionSchemaCollector #########################

class G_CoreProjectionSchemaCollector:
    """Collect schema data for a projector's table"""

    #-------------------------------------------------------
    def __init__(self):
        self._ProjectionSchema = G_ProjectionSchema("14C89CE3-E8A4-4F28-99EB-3EF5D5FD3B13")


    #-------------------------------------------------------
    def AddField(self, name, type, width = 30, align = "centre", formatter = None):
        self._ProjectionSchema.AddField(name, type, width, align, formatter)


    #-------------------------------------------------------
    def Close(self):
        return self._ProjectionSchema



## G_ProjectionSchemaCollector #############################

class G_ProjectionSchemaCollector(G_CoreProjectionSchemaCollector):
    
    #-------------------------------------------------------
    def __init__(self):
        super().__init__()


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
    def AddNesting(self):
        self._ProjectionSchema.AddNesting(field_schema)

    def AddStart(self, name, width = 30, align = "centre", formatter = None):
        self._ProjectionSchema.AddStart(name, width, align, formatter)

    def AddFinish(self, name, width = 30, align = "centre", formatter = None):
        self._ProjectionSchema.AddFinish(name, width, align, formatter)

    def AddDuration(self, name, scale = "us", width = 30, align = "centre", formatter = None):
        name = "{} ({})".format(name, scale)
        scale_factor = self._CalcScale(scale)
        self._ProjectionSchema.AddDuration(scale_factor, name, width, align, formatter)

        

## G_ProjectionItem ########################################

class G_ProjectionItem:

    #-------------------------------------------------------
    def __init__(self, event_number = -1, start_line_no = None, finish_line_no = None, event_data = None):
        if event_data is None:
            # note, somewhat arbitrary limit (32-bit signed-int-max)
            max = 2147483647
            self.LogStartLine = 0
            self.LogFinishLine = max

        else:
            self.LogStartLine = start_line_no
            self.LogFinishLine = finish_line_no

        self.EventNumber = event_number
        self.EventData = event_data



## G_ProjectionCollector ###################################

class G_ProjectionCollector:
    """Collect event data from any number of event analyses"""

    #-------------------------------------------------------
    _SqlTypeMap = dict(
        bool = "INT",
        uint08 = "INT",
        uint16 = "INT",
        uint32 = "INT",
        uint64 = "INT",
        int08 = "INT",
        int16 = "INT",
        int32 = "INT",
        int64 = "INT",
        float32 = "REAL",
        float64 = "REAL",
        enum08 = "INT",
        enum16 = "INT",
        text = "TEXT"
    )


    #-------------------------------------------------------
    def __init__(self, log_node, projection_schema):
        self._LogNode = log_node
        self._EventNo = 0
        self._ProjectionSchema = projection_schema

        # note, somewhat arbitrary limit (32-bit signed-int-max)
        max = 2147483647
        self._Stack = [G_ProjectionItem()]


    #-------------------------------------------------------
    def _StackBack(self):
        return self._Stack[len(self._Stack) - 1]


    def _UpdateStack(self, start_line_no, finish_line_no, event_data):
        cur = G_ProjectionItem(self._EventNo, start_line_no, finish_line_no, event_data)
        self._EventNo += 1

        # remove any entries that finish before 'cur' starts
        while cur.LogStartLine > self._StackBack().LogFinishLine:
            self._Stack.pop()
 
        # since events are published in start order, we know that
        # 'cur' starts after 'prev' (two events can't start on the
        # same line)
        self._Stack.append(cur)
 
        return cur
 
 
    def CalcParentId(self, start_line_no, finish_line_no, event_data, containment_test):
        # note: relies on the fact that events are discovered in start order
        cur = self._UpdateStack(start_line_no, finish_line_no, event_data)
        for idx in range(len(self._Stack) - 2, 0, -1):
            prev = self._Stack[idx]
            if prev.EventData is not None and prev.LogFinishLine >= cur.LogFinishLine:
                if containment_test(prev.EventData, cur.EventData):
                    return prev.EventNumber
 
        return -1


    #-------------------------------------------------------
    def FindDbFile(self, theme_id):
        for node in self._LogNode.ListSubNodes(factory_id = G_Project.NodeID_LogAnalysis, recursive = True):
            if node.GetCurrentThemeId("event") == theme_id:
                return node.MakeTemporaryFilename(".db")

        return None


    #-------------------------------------------------------
    def CalcDuration(self, duration):
        return int(duration / self._ProjectionSchema.DurationScale)


    #-------------------------------------------------------
    def MakeProjectionMetaTable(self, cursor, utc_datum):
        cursor.execute("DROP TABLE IF EXISTS projection_meta")
        cursor.execute("""
            CREATE TABLE projection_meta
            (
                utc_datum INT,
                field_id INT
            )""")

        field_id = self._ProjectionSchema.ColStartOffset
        if field_id is None:
            field_id = 0

        cursor.execute("""
            INSERT INTO projection_meta
            (
                utc_datum,
                field_id
            )
            VALUES
            (
                {utc_datum},
                {field_id}
            )""".format(utc_datum = utc_datum, field_id = field_id))


    #-------------------------------------------------------
    def MakeProjectionTable(self, cursor):
        ct_columns = ["[{}] {}".format(field_schema.Name, self._SqlTypeMap[field_schema.Type]) for field_schema in self._ProjectionSchema]

        cursor.execute("DROP TABLE IF EXISTS projection")
        cursor.execute("""
            CREATE TABLE projection
            (
                {}
            )""".format(", ".join(ct_columns)))

        cursor.execute("DROP TABLE IF EXISTS filter")
        cursor.execute("""
            CREATE TABLE filter
            (
                log_row_no INT
            )""")

#        cursor.execute("""
#            CREATE VIEW IF NOT EXISTS filtered_projection
#            (
#                ?
#            )
#            AS
#            SELECT *
#            """)
#look at parent handling - want to design out view-to-log line conversions in python ...



    #-------------------------------------------------------
    def Close(self):
        self._LogNode = None


    
## G_Projector #############################################

class G_Projector:
    """Project event analyses, creates an event table"""

    #-------------------------------------------------------
    def __init__(self, connection, meta_only, log_node):
        self._Connection = connection
        self._MetaOnly = meta_only
        self._ProjectionSchema = G_ProjectionSchema()
        self._LogNode = log_node
        self._EventMetrics = None


    #-------------------------------------------------------
    def CollectProjectionSchema(self, user_projector):
        schema_collector = G_ProjectionSchemaCollector()
        user_projector.DefineSchema(schema_collector)
        return schema_collector.Close()


    #-------------------------------------------------------
    def GetMeta(self):
        return (self._ProjectionSchema, self._EventMetrics)


    #-------------------------------------------------------
    def Project(self, name, user_projector, user_metrics = None):
        self._ProjectionSchema = self.CollectProjectionSchema(user_projector)
        self._EventMetrics = user_metrics

        if self._MetaOnly:
            return

        event_collector = G_ProjectionCollector(self._LogNode, self._ProjectionSchema)
        self._LogNode = None

        with G_PerfTimerScope("G_Projector.Project") as timer:
            user_projector.Project(self._Connection, event_collector)

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

        self._ParentKeyToChildKeys = dict()


    #-------------------------------------------------------
    def GetFieldInfo(self, col_num):
        field_schema = self._TableSchema[col_num]
        return (field_schema.Type, field_schema.IsFirst)

    def GetFieldType(self, col_num):
        return self._TableSchema[col_num].Type

    def GetFieldValue(self, item_key, col_num):
        type = self.GetFieldType(col_num)
        return G_ProjectionTypeManager.GetValue(type, self._N_EventView, item_key, col_num)

    def GetFieldDisplayValue(self, item_key, col_num):
        icon = None
        (type, is_first) = self.GetFieldInfo(col_num)
        if is_first:
            icon = self._Icons[item_key in self._ParentKeyToChildKeys]
        return G_ProjectionTypeManager.GetDisplayValue(type, icon, self._N_EventView, item_key, col_num)


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
    def GetRowKeys(self):
        return range(self.GetNumItems())


    #-------------------------------------------------------
    def GetItemKeyParentKey(self, item_key):
        parent_id = -1
        if self._TableSchema.ColParentId is not None:
            parent_id = self.GetFieldValue(item_key, self._TableSchema.ColParentId)

        if parent_id < 0:
            return parent_id

        candidate_parent_key = self._N_EventView.LogLineToViewLine(parent_id)
        if candidate_parent_key < 0:
            return candidate_parent_key

        # check for an exact match
        actual_parent_id = self._N_EventView.ViewLineToLogLine(candidate_parent_key)
        if parent_id == actual_parent_id:
            return candidate_parent_key

        return -1


    #-------------------------------------------------------
    def GetEventRange(self, item):
        table_schema = self._TableSchema
        if table_schema.ColStartOffset is None:
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
        return G_ProjectionTypeManager.GetVariantType(self.GetFieldType(col_num))


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
            if self._N_EventView.GetHiliter(hiliter._Id).Hit(item_key):
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
        raise RuntimeError


    #-------------------------------------------------------
    def GetNextItem(self, what, cur_item, forward, index = 0):
        cur_key = 0
        if cur_item is not None:
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

        if match is not None:
            if self._N_EventView is None:
                return True

            return self._N_EventView.Filter(match)

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
            self._N_Logfile = Nlog.MakeLogfile(filename, table_schema, None)

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
        
        self.Cleared()
        return True


    #-------------------------------------------------------
    def UpdateSort(self, col_num_in):
        (col_num, direction) = self._TableSchema[col_num_in].ToggleSortDirection()
        if col_num is None:
            col_num = col_num_in

        if self._N_EventView is not None:
            self._N_EventView.Sort(col_num, direction)
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


    #-------------------------------------------------------
    def OnColClick(self, evt):
        col_pos = evt.GetColumn()
        column = self.GetColumn(col_pos)
        if column is not None:
            col_num = column.GetModelColumn()
            if self.GetModel().UpdateSort(col_num):
                self.Refresh()        



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
        metrics = self._TableViewCtrl.GetEventView()
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
    @G_Global.TimeFunction
    def Realise(self):
        """Redraw the chart if needed"""
        with G_ScriptGuard("Realise", self._ErrorReporter):
            if not self._RealiseLock and self._RealiseChangeTracker.Changed(self._ChartDesigner.WantSelection):
                (metrics, num_metrics, selection) = self.GetTableData()
                self._Figure.clear()
                with G_PerfTimerScope("Design"):
                    self._ChartDesigner.Realise(self._Figure, metrics, num_metrics, self._ParamaterValues, selection)

                with G_PerfTimerScope("Draw"):
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
    @G_Global.TimeFunction
    def Assemble(self, events, analysis_props):
        self.ResetModel(analysis_props.ErrorReporter)
        with G_ScriptGuard("Assemble", self._ErrorReporter):
            self._Quantifier = analysis_props.GetQuantifier(self._QuantifierName)

            schema_collector = G_CoreProjectionSchemaCollector()
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
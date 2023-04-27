#
# Copyright (C) Niel Clausen 2017-2023. All rights reserved.
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
from pathlib import Path
import sqlite3

# Application imports 
from .Global import G_Global
from .Global import G_PerfTimerScope
from .Logmeta import G_FieldSchemata
from .MatchNode import G_MatchItem
from .Project import G_Project

# wxWidgets imports
import wx

# Content provider interface
import NlvLog


## Locals ##################################################

#-----------------------------------------------------------
def MakeProjectionView(cursor):
    cursor.execute("DROP TABLE IF EXISTS main.filter")
    cursor.execute("""
        CREATE TABLE main.filter
        (
            event_id INT NOT NULL PRIMARY KEY
        )""")



## G_DbConnection ##########################################

class G_DbConnection:
    """
    Guarantees DB shutdown semantics.
    """

    #-------------------------------------------------------
    def __init__(self, path):
        self._Connection = connection = sqlite3.connect(path)
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()
        cursor.execute("PRAGMA synchronous = OFF")

        # commented out, as it yields strange "sqlite3.OperationalError:
        # database table is locked" errors on the first db execute
        #cursor.execute("PRAGMA journal_mode = MEMORY")


    #-------------------------------------------------------
    def __enter__(self):
        return self._Connection


    #-------------------------------------------------------
    def __exit__(self, exc_type, exc_value, exc_traceback):
        if self._Connection is not None:
            self._Connection.close()



## G_ScriptGuard ###########################################

class G_ScriptGuard:
    """
    All use of the user supplied recogniser script, and any
    objects/functions returned from the script, should be
    protected within a 'with' block, and any exceptions reported
    back to the UI
    """

    #-------------------------------------------------------
    def __init__(self, name, reporter = None):
        self._Name = name
        self._Reporter = logging.warn
        if reporter is not None:
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
        return self._LineSet.GetNearestUtcTimecode(self._LineNo)



## G_NullRecogniser ########################################

class G_NullRecogniser:
    """Do nothing version of G_Recogniser"""

    #-------------------------------------------------------
    def __init__(self, event_id):
        self._EventId = event_id


    #-------------------------------------------------------
    def Recognise(self, user_analyser, start_desc, finish_desc = None):
        pass


    #-------------------------------------------------------
    def Close(self):
        return self._EventId



## G_Recogniser ############################################

class G_Recogniser:
    """Assess a log, creates any number of event/feature tables"""

    #-------------------------------------------------------
    def __init__(self, event_id, db_info, log_schema, logfile):
        self._EventId = event_id
        self._DbInfo = db_info
        self._LogFile = logfile
        self._DateFieldId = logfile.GetTimecodeBase().GetFieldId()

        field_ids = dict()
        for (idx, name) in enumerate(log_schema.GetFieldNames()):
            field_ids.update([[name, idx]])
        self._LogFieldIds = field_ids


    #-------------------------------------------------------
    def ConvertMatchToLVFText(self, match):
        if match is None or match.IsEmpty():
            return ""

        case = ""
        if not match.MatchCase:
            case = "i"

        selector_id = match.GetSelectorId()
        if selector_id == NlvLog.EnumSelector.Literal:
            return 'log ~= "{}"{}'.format(match.MatchText, case)

        elif selector_id == NlvLog.EnumSelector.RegularExpression:
            return 'log ~= /{}/{}'.format(match.MatchText, case)

        elif selector_id == NlvLog.EnumSelector.LogviewFilter:
            return match.MatchText

        else:
            raise RuntimeError("Unknown match type: {}".format(match.MatchType))


    def BuildLVFText(self, recogniser_match):
        lvf_text = self.ConvertMatchToLVFText(recogniser_match)

        if len(lvf_text) == 0:
            raise RuntimeError("Empty line filter")

        return G_MatchItem("LogView Filter", lvf_text)


    def BuildLineSet(self, recogniser_match):
        match = self.BuildLVFText(recogniser_match)

        lineset = self._LogFile.CreateLineSet(match)
        if lineset is None:
            raise RuntimeError("Broken filter: {}".format(match.MatchText))

        return lineset


    @G_Global.TimeFunction
    def BuildLineSets(self, start_desc, finish_desc):
        start_view = self.BuildLineSet(G_MatchItem(start_desc[0], start_desc[1]))

        if finish_desc is not None:
            finish_view = self.BuildLineSet(G_MatchItem(finish_desc[0], finish_desc[1]))
        else:
            finish_view = start_view

        return (start_view, finish_view)


    #-------------------------------------------------------
    def GetEventId(self):
        next_id = self._EventId
        self._EventId += 1
        return next_id


    def GetEventStartText(self):
        return self._StartAccessor.GetFieldText(self._DateFieldId)


    def GetEventStartTime(self):
        """
        Return the following details about the event, as a tuple:
            0 (start_utc INT) - UTC date/time of event start, to previous whole second
            1 (start_offset_ns INT) - offset from #2 to event start, in ns
        """

        start_timecode = self._StartAccessor.GetUtcTimecode()
        start_timecode.Normalise()
        return (start_timecode.GetUtcDatum(), start_timecode.GetOffsetNs())


    def GetEventStartDetails(self):
        """
        Return the following details about the event, as a tuple:
            0 (event_id INT) - unique event number
            1 (start_text TEXT) - start time as text; in the same format as the logfile
            2 (start_line_no INT) - start line number
            3 (start_utc INT) - UTC date/time of event start, to previous whole second
            4 (start_offset_ns INT) - offset from #2 to event start, in ns
            5 (duration_ns INT) - event duration, in ns
            6 (finish_line_no INT) - finish line number
        """

        start_timecode = self._StartAccessor.GetUtcTimecode()
        start_timecode.Normalise()

        finish_timecode = self._FinishAccessor.GetUtcTimecode()

        return (
            self.GetEventId(),

            # event start details
            self._StartAccessor.GetFieldText(self._DateFieldId),
            self._StartLine,
            start_timecode.GetUtcDatum(),
            start_timecode.GetOffsetNs(),

            # duration
            finish_timecode.Subtract(start_timecode),

            # finish line
            self._FinishLine
        )


    def GetEventFullDetails(self):
        """
        Return the following details about the event, as a tuple:
            0 (event_id INT) - unique event number
            1 (start_text TEXT) - start time as text; in the same format as the logfile
            2 (start_line_no INT) - start line number
            3 (start_utc INT) - UTC date/time of event start, to previous whole second
            4 (start_offset_ns INT) - offset from #2 to event start, in ns
            5 (finish_text TEXT) - finish time as text; in the same format as the logfile
            6 (finish_line_no INT) - finish line number
            7 (finish_utc INT) - UTC date/time of event finish, to previous whole second
            8 (finish_offset_ns INT) - offset from #6 to event finish, in ns
            9 (duration_ns INT) - event duration, in ns
        """

        start_timecode = self._StartAccessor.GetUtcTimecode()
        start_timecode.Normalise()

        finish_timecode = self._FinishAccessor.GetUtcTimecode()
        finish_timecode.Normalise()

        return (
            self.GetEventId(),

            # event start details
            self._StartAccessor.GetFieldText(self._DateFieldId),
            self._StartLine,
            start_timecode.GetUtcDatum(),
            start_timecode.GetOffsetNs(),

            # event finish details
            self._FinishAccessor.GetFieldText(self._DateFieldId),
            self._FinishLine,
            finish_timecode.GetUtcDatum(),
            finish_timecode.GetOffsetNs(),

            # other (duration)
            finish_timecode.Subtract(start_timecode)
        )


    #-------------------------------------------------------
    def DoRecognise(self, user_analyser, start_desc, finish_desc, connection, cursor):
        """Implements user analyse script Recognise() function"""
        # observation: this could be made multithreaded

        field_ids = self._LogFieldIds

        (start_view, finish_view) = self.BuildLineSets(start_desc, finish_desc)

        self._StartAccessor = start_accessor = G_LineAccessor(field_ids, start_view)
        start_line_count = start_view.GetNumLines()

        self._FinishAccessor = finish_accessor = G_LineAccessor(field_ids, finish_view)
        finish_line_count = finish_view.GetNumLines()

        user_analyser.Begin(connection, cursor)

        for start_lineno in range(start_line_count):
            start_accessor.SetLineNo(start_lineno)
            match_finish_func = user_analyser.MatchEventStart(self, start_accessor)

            if match_finish_func is None:
                continue

            elif isinstance(match_finish_func, bool) and match_finish_func:
                continue

            # convert the index (into the lineset) to the actual logfile line number
            self._StartLine = start_log_lineno = start_view.ViewLineToLogLine(start_lineno)

            # hence find the lineno to the first-event finish candidate in the finish
            # view; negative means "not found"
            first_finish_lineno = finish_view.LogLineToViewLine(start_log_lineno, False)
            if first_finish_lineno < 0:
                continue

            # now find the event finish line, and, hence, create the event
            got_finish = False
            for finish_lineno in range(first_finish_lineno, finish_line_count):
                finish_accessor.SetLineNo(finish_lineno)
                self._FinishLine = finish_log_lineno = finish_view.ViewLineToLogLine(finish_lineno)

                if match_finish_func(self, finish_accessor):
                    got_finish = True
                    break

            if not got_finish:
                logging.warn("Match '{}' failed: Event close not found (performance warning)".format(str(match_finish_func)))

        user_analyser.End()
        user_analyser = None


    @G_Global.TimeFunction
    def Recognise(self, user_analyser, start_desc, finish_desc = None):
        with G_DbConnection(self._DbInfo.Path) as connection:
            cursor = connection.cursor()
            self.DoRecognise(user_analyser, start_desc, finish_desc, connection, cursor)
            cursor.close()
            connection.commit()


    #-------------------------------------------------------
    def Close(self):
        return self._EventId



## G_ProjectionTypeManager #################################

class G_ProjectionTypeManager:
    """Type management and value conversion services for the data model"""

    #-------------------------------------------------------
    def _GetText(field_schema, view, line_no, field_no):
        return view.GetFieldText(line_no, field_no)

    def _GetSignedText(field_schema, view, line_no, field_no):
        scale_factor = field_schema.ScaleFactor
        if scale_factor is not None:
            return str(int(view.GetFieldValueSigned(line_no, field_no) / scale_factor))
        else:
            return view.GetFieldText(line_no, field_no)

    def _GetFloatText(field_schema, view, line_no, field_no):
        scale_factor = field_schema.ScaleFactor
        if scale_factor is not None:
            return str(view.GetFieldValueFloat(line_no, field_no) / scale_factor)
        else:
            return view.GetFieldText(line_no, field_no)


    def _GetSigned(field_schema, view, line_no, field_no):
        # raw data access, so no scaling
        return view.GetFieldValueSigned(line_no, field_no)

    def _GetFloat(field_schema, view, line_no, field_no):
        # raw data access, so no scaling
        return view.GetFieldValueFloat(line_no, field_no)

    def _GetBool(field_schema, view, line_no, field_no):
        return bool(view.GetFieldValueUnsigned(line_no, field_no))


    def _DisplayStringIcon(value, icon):
        return wx.dataview.DataViewIconText(value, icon)

    def _DisplayValue(value, icon):
        return value


    # model types - model info rows
    _c_without_icon = 0
    _c_with_icon = 1


    # model info columns
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
    _c_signed = 1
    _c_float = 2
    _c_bool = 3


    # _DisplayInfo columns
    _c_store_to_value = 0
    _c_store_to_displayvalue = 1
    _c_model_types = 2


    # identify data accessor and display functors
    _DisplayInfo = [
        [_GetText, _GetText, _TextModelInfo], # _c_text
        [_GetSigned, _GetSignedText, _TextModelInfo], # _c_signed
        [_GetFloat, _GetFloatText, _TextModelInfo], # _c_float
        [_GetBool, _GetBool, _BoolModelInfo] # _c_bool
    ]


    # map display field-types to display info
    _FieldTypes = dict(
        bool = _DisplayInfo[_c_bool],
        int = _DisplayInfo[_c_signed],
        real = _DisplayInfo[_c_float],
        text = _DisplayInfo[_c_text]
    )


    #-------------------------------------------------------
    def ValidateType(type):
        if not type in __class__._FieldTypes:
            raise RuntimeError("Invalid field type: {}".format(type))


    #-------------------------------------------------------
    def GetValue(field_schema, view, line_no, field_no):
        """Fetch field's binary value"""
        me = __class__
        return me._FieldTypes[field_schema.Type][me._c_store_to_value](field_schema, view, line_no, field_no)


    #-------------------------------------------------------
    def GetDisplayValue(field_schema, icon, view, line_no, field_no):
        """Fetch field's value converted to a type accepted by the display system"""
        me = __class__
        display_info = me._FieldTypes[field_schema.Type]
        display_value = display_info[me._c_store_to_displayvalue](field_schema, view, line_no, field_no)
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
    def __init__(self, name, description, type, available, width = 0, align = None, view_formatter = None, data_col_offset = 0, scale_factor = None, initial_visibility = None, initial_colour = None, explorer_formatter = None):
        # user data
        if align is None:
            align = wx.ALIGN_CENTER

        self.Name = name
        self.Description = description
        self.Type = type
        self.Available = self.Visible = available
        self.Width = width
        self.Align = align
        self.ViewFormatter = view_formatter
        self.ScaleFactor = scale_factor
        self.InitialVisibility = initial_visibility
        self.InitialColour = initial_colour
        self.ExplorerFormatter = explorer_formatter

        # NlvLog indexer info
        self.Separator = ","
        self.SeparatorCount = 1
        self.MinWidth = 0
        self.LeftTrim = False
        self.RightTrim = False

        # management data
        self.IsFirst = False
        self.SortDirection = 0
        self.DataColumnOffset = data_col_offset


    #-------------------------------------------------------
    def Display(self):
        return self.Available and self.Visible

    def ToggleSortDirection(self):
        if self.SortDirection == 0:
            self.SortDirection = 1
        else:
            self.SortDirection *= -1

        return (self.DataColumnOffset, self.SortDirection)



## G_ProjectionSchema ######################################

class G_ProjectionSchema(G_FieldSchemata):
    """
    Describes all the projected fields (database 'row').
    Passed to user script to allow the schema to be built up.
    """

    #-------------------------------------------------------
    def __init__(self, guid = ""):
        super().__init__("sql", guid)
        self._SetTextOffsetSize(16)
        self.PermitNesting = False
        self.DurationScale = 1
        self.ColStartOffset = None
        self.ColFinishOffset = None
        self.ColDuration = None

        self.UserDataExplorerOpen = None
        self.UserDataExplorerClose = None

        self.ColEventId = self.MakeHiddenFieldSchema("event_id", "int")


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
    @staticmethod
    def _CalcScaleFactor(name, description, scale):
        if scale is None:
            sf = None

        elif isinstance(scale, int):
            sf = scale

        else:
            if scale == "s":
                sf = 1000000000
                d = "seconds"
            elif scale == "ms":
                sf = 1000000
                d = "milliseconds"
            elif scale == "us":
                sf = 1000
                d = "microseconds"
            elif scale == "ns":
                sf = 1
                d = "nanoseconds"
            else:
                raise RuntimeError("Invalid temporal scale: {}".format(scale))

            name = "{} ({})".format(name, scale)
            description = "{} (Measured in {}.)".format(description, d)

        return name, description, sf


    #-------------------------------------------------------
    def MakeHiddenFieldSchema(self, name, type, explorer_formatter = None):
        G_ProjectionTypeManager.ValidateType(type)
        return self.Append(G_ProjectionFieldSchema(name, "None", type, False, explorer_formatter = explorer_formatter))


    def MakeFieldSchema(self, name, description, type, width = 30, align = "centre", view_formatter = None, data_col_offset = 0, scale_factor = None, initial_visibility = True, initial_colour = "BLACK", explorer_formatter = None):
        G_ProjectionTypeManager.ValidateType(type)
        al = __class__._CalcAlign(align)
        return self.Append(G_ProjectionFieldSchema(name, description, type, True, width, al, view_formatter, data_col_offset, scale_factor, initial_visibility, initial_colour, explorer_formatter))


    #-------------------------------------------------------
    def AddNesting(self, enable = True):
        self.PermitNesting = enable
        return self

    def AddHiddenField(self, name, type, explorer_formatter = None):
        self.MakeHiddenFieldSchema(name, type, explorer_formatter)
        return self

    def AddField(self, name, description, type, width = 30, align = "centre", view_formatter = None, scale = None, initial_visibility = True, initial_colour = "BLACK", explorer_formatter = None):
        name, description, sf = self._CalcScaleFactor(name, description, scale)
        self.MakeFieldSchema(name, description, type, width, align, view_formatter, scale_factor = sf, initial_visibility = initial_visibility, initial_colour = initial_colour, explorer_formatter = explorer_formatter)
        return self

    def AddStart(self, name, description, width = 30, align = "centre", view_formatter = None, initial_visibility = True, initial_colour = "BLACK", explorer_formatter = None):
        self.MakeFieldSchema(name, description, "text", width, align, view_formatter, data_col_offset = 1, initial_visibility = initial_visibility, initial_colour = initial_colour, explorer_formatter = explorer_formatter)
        self.ColStartOffset = self.MakeHiddenFieldSchema("start_offset_ns", "int")
        return self

    def AddFinish(self, name, description, width = 30, align = "centre", view_formatter = None, initial_visibility = True, initial_colour = "BLACK", explorer_formatter = None):
        self.MakeFieldSchema(name, description, "text", width, align, view_formatter, data_col_offset = 1, initial_visibility = initial_visibility, initial_colour = initial_colour, explorer_formatter = explorer_formatter)
        self.ColFinishOffset = self.MakeHiddenFieldSchema("finish_offset_ns", "int")
        return self

    def AddDuration(self, name, description, width = 30, align = "centre", view_formatter = None, scale = "us", initial_visibility = True, initial_colour = "BLACK", explorer_formatter = None):
        name, description, sf = self._CalcScaleFactor(name, description, scale)
        self.ColDuration = self.MakeFieldSchema(name, description, "int", width, align, view_formatter, scale_factor = sf, initial_visibility = initial_visibility, initial_colour = initial_colour, explorer_formatter = explorer_formatter)
        return self


    #-------------------------------------------------------
    def OnDataExplorerOpen(self, func):
        self.UserDataExplorerOpen = func
        return self

    def OnDataExplorerClose(self, func):
        self.UserDataExplorerClose = func
        return self



## G_DbInfo ################################################

class G_DbInfo:

    #-------------------------------------------------------
    def __init__(self, db_name, path, base_info = None):
        self.DbName = db_name
        self.Path = path
        self.BaseInfo = base_info


    #-------------------------------------------------------
    def ConnectionManager(self):
        return G_DbConnection(self.Path)


    #-------------------------------------------------------
    def Attach(self, cursor):
        cursor.execute("ATTACH DATABASE '{db_path}' AS {db_name}".format(db_path = self.Path, db_name = self.DbName))
        self.AttachBases(cursor)

    def AttachBases(self, cursor):
        base_info = self.BaseInfo
        if base_info is not None:
            base_info.Attach(cursor)



## G_ChartInfo #############################################

class G_ChartInfo:

    #-------------------------------------------------------
    def __init__(self, name, want_selection, builder, chart_db_info):
        self.Name = name
        self.WantSelection = want_selection
        self.Builder = builder
        self.ChartDbInfo = chart_db_info


    #-------------------------------------------------------
    def DefineParameters(self, connection, cursor, context):
        self.Builder.DefineParameters(connection, cursor, context)

    def Realise(self, connection, cursor, context):
        self.Builder.Realise(self.Name, connection, cursor, context)



## G_QuantifierInfo ########################################

def MakeRelatedDbInfo(info, name, db_name):
    # db_name is the name given to the database when attach'ed
    # into a child connection/cursor
    short_name = name.strip()
    base_path = Path(info.Path)
    new_path = base_path.with_name("{}.{}({}).db".format(base_path.stem, short_name, db_name))
    return G_DbInfo(db_name, str(new_path), info)


class G_QuantifierInfo:

    #-------------------------------------------------------
    def __init__(self, name, quantifier, metrics_schema, projection_db_info):
        self.Name = name
        self.UserQuantifier = quantifier
        self.MetricsSchema = metrics_schema
        self.MetricsDbInfo = MakeRelatedDbInfo(projection_db_info, name, "quantifier")
        self.Charts = []


    #-------------------------------------------------------
    def Chart(self, name, want_selection, builder):
        """Implements user analyse script Quantifier.Chart() function"""
        self.Charts.append(G_ChartInfo(name, want_selection, builder, self.MetricsDbInfo))


    #-------------------------------------------------------
    def GetSchema(self):
        return self.MetricsSchema

    def GetDbInfo(self):
        return self.MetricsDbInfo



## G_ProjectorInfo #########################################

class G_ProjectorInfo:

    #-------------------------------------------------------
    def __init__(self, name, projection_schema, analysis_db_info):
        self.ProjectionName = name
        self.ProjectionSchema = projection_schema
        self.ProjectionDbInfo = MakeRelatedDbInfo(analysis_db_info, name, "events")
        self.DocumentNodeID = G_Project.NodeID_EventProjector
        self.Quantifiers = dict()
        self.Charts = []


    #-------------------------------------------------------
    def Quantify(self, name, user_quantifier, metrics_schema):
        """Implements user analyse script Quantify() function"""

        info = G_QuantifierInfo(name, user_quantifier, metrics_schema, self.ProjectionDbInfo)
        self.Quantifiers.update([(name, info)])
        return info


    #-------------------------------------------------------
    def Chart(self, name, want_selection, builder):
        """Implements user analyse script Projector.Chart() function"""
        self.Charts.append(G_ChartInfo(name, want_selection, builder, self.ProjectionDbInfo))


    #-------------------------------------------------------
    def GetQuantifierInfo(self, name):
        return self.Quantifiers[name]

    def GetSchema(self):
        return self.ProjectionSchema

    def GetDbInfo(self):
        return self.ProjectionDbInfo



## G_NetworkChartInfo ######################################

class G_NetworkChartInfo:

    #-------------------------------------------------------
    def __init__(self, name, want_selection, builder, nodes_db_info, links_db_info):
        self.Name = name
        self.WantSelection = want_selection
        self.Builder = builder
        self.NodesDbInfo = nodes_db_info
        self.LinksDbInfo = links_db_info


    #-------------------------------------------------------
    def DefineParameters(self, connection, cursor, context):
        self.Builder.DefineParameters(connection, cursor, context)

    def Realise(self, connection, cursor, context):
        return self.Builder.Realise(self.Name, connection, cursor, context)



## G_NetworkInfo ###########################################

class G_NetworkInfo:

    #-------------------------------------------------------
    def __init__(self, name, nodes_projector, links_projector, partitions):
        self.ProjectionName = name
        self.Charts = []
        self.DocumentNodeID = G_Project.NodeID_NetworkProjector
        self.NetworkProjectors = [nodes_projector, links_projector]
        self.Partitions = partitions


    #-------------------------------------------------------
    def Chart(self, name, want_selection, builder):
        nodes_db_info = self.NetworkProjectors[0].ProjectionDbInfo
        links_db_info = self.NetworkProjectors[1].ProjectionDbInfo
        self.Charts.append(G_NetworkChartInfo(name, want_selection, builder, nodes_db_info, links_db_info))


    #-------------------------------------------------------
    def GetNetworkProjector(self, projection_name):
        if self.NetworkProjectors[0].ProjectionName == projection_name:
            return self.NetworkProjectors[0]

        elif self.NetworkProjectors[1].ProjectionName == projection_name:
            return self.NetworkProjectors[1]

        else:
            return None


## G_AnalysisResults #######################################

class G_AnalysisResults:

    #-------------------------------------------------------
    def __init__(self, analysis_db_path, event_id):
        self.AnalysisDbInfo = G_DbInfo("analysis", analysis_db_path)
        self.EventId = event_id
        self.Projectors = dict()


    #-------------------------------------------------------
    def Project(self, name, projection_schema, record):
        info = G_ProjectorInfo(name, projection_schema, self.AnalysisDbInfo)
        if record:
            self.Projectors.update([(name, info)])
        return info


    #-------------------------------------------------------
    def Network(self, name, node_projector, link_projector, partitions):
        info = G_NetworkInfo(name, node_projector, link_projector, partitions)
        self.Projectors.update([(name, info)])
        return info


    #-------------------------------------------------------
    def GetProjectorInfo(self, name):
        return self.Projectors[name]



## G_ProjectionContext #####################################

class G_ProjectionContext:
    """Context object passed to user script 'projector' function."""

    #-------------------------------------------------------
    def __init__(self, log_node, col_start):
        self._LogNode = log_node
        self._ColStart = col_start


    #-------------------------------------------------------
    # currently unused; may be bad design
    def FindDbFile(self, theme_id):
        for node in self._LogNode.ListSubNodes(factory_id = G_Project.NodeID_LogAnalysis, recursive = True):
            if node.GetCurrentThemeId("event") == theme_id:
                return node.MakeTemporaryFilename(".db")

        return None


    #-------------------------------------------------------
    def CalcUtcDatum(self, cursor, tables):
        """Each table in tables must contain a 'start_utc' column"""

        utc_datum = 0
        for table in tables:
            cursor.execute("""
                SELECT
                    start_utc
                FROM
                    {table}
                ORDER BY
                    start_utc ASC
                LIMIT
                    1
                """.format(table = table))

            row = cursor.fetchone()
            if row is not None:
                datum = row[0]
                if datum is not None and (utc_datum == 0 or datum < utc_datum):
                    utc_datum = datum

        cursor.execute("DROP TABLE IF EXISTS main.projection_meta")
        cursor.execute("""
            CREATE TABLE projection_meta
            (
                utc_datum INT,
                field_id INT
            )""")

        field_id = self._ColStart
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

        return utc_datum


    #-------------------------------------------------------
    def Close(self):
        self._LogNode = None


    
## G_Projector #############################################

class G_Projector:
    """
    Project event analyses, creates an event view
    Also collects metadata, including event quantifiers.
    """

    #-------------------------------------------------------
    def __init__(self, schema_only, log_node, results):
        self._SchemaOnly = schema_only
        self._LogNode = log_node
        self._Results = results


    #-------------------------------------------------------
    def DoProject(self, name, user_projector, projection_schema, record):
        projection = self._Results.Project(name, projection_schema, record)
        if self._SchemaOnly:
            return projection

        db_info = projection.ProjectionDbInfo
        with db_info.ConnectionManager() as connection:
            cursor = connection.cursor()
            db_info.AttachBases(cursor)

            projection_context = G_ProjectionContext(self._LogNode, projection_schema.ColStartOffset)
            self._LogNode = None

            with G_PerfTimerScope("G_Projector.Project") as timer:
                user_projector(connection, cursor, projection_context)

            projection_context.Close()
            MakeProjectionView(cursor)

            cursor.close()
            connection.commit()

        return projection


    #-------------------------------------------------------
    def DefinePartitions(self, db_info, user_partition):
        if self._SchemaOnly:
            return

        with db_info.ConnectionManager() as connection:
            cursor = connection.cursor()
            db_info.AttachBases(cursor)

            user_partition(connection, cursor, None)

            cursor.close()
            connection.commit()
    

    def GetPartitions(self, db_info):
        partitions = []

        with db_info.ConnectionManager() as connection:
            cursor = connection.cursor()
            db_info.AttachBases(cursor)

            cursor.execute("""
                SELECT
                    id,
                    description
                FROM
                    partitions
            """)

            for row in cursor:
                partitions.append((row[0], row[1]))

        return partitions


    #-------------------------------------------------------
    def Project(self, name, user_projector, projection_schema):
        """Implements user analyse script Project() function"""
        return self.DoProject(name, user_projector, projection_schema, True)

    def Nodes(self, name, user_projector, projection_schema):
        """Implements user analyse script Nodes() function"""
        return self.DoProject(name, user_projector, projection_schema, False)

    def Links(self, name, user_projector, projection_schema):
        """Implements user analyse script Links() function"""
        return self.DoProject(name, user_projector, projection_schema, False)


    #-------------------------------------------------------
    def Network(self, name, node_projector, link_projector, define_partitions = None):
        """Implements user analyse script Network() function"""
        partitions = []
        if define_partitions is not None:
            self.DefinePartitions(node_projector.ProjectionDbInfo, define_partitions)
            partitions = self.GetPartitions(node_projector.ProjectionDbInfo)

        return self._Results.Network(name, node_projector, link_projector, partitions)




## G_Analyser ##############################################

class Nlv:
    pass

class G_Analyser:
    """
    Analyse a logfile; combines event recognition, projection
    and metrics collection
    """

    #-------------------------------------------------------
    def __init__(self, analysis_db_path, event_id):
        self._Results = G_AnalysisResults(analysis_db_path, event_id)


    #-------------------------------------------------------
    def MakeDisplaySchema(self):
        return G_ProjectionSchema("14C89CE3-E8A4-4F28-99EB-3EF5D5FD3B13")


    #-------------------------------------------------------
    def SetEntryPoints(self, meta_only, log_schema, log_file, log_node):
        self._Projector = G_Projector(meta_only, log_node, self._Results)

        event_id = self._Results.EventId
        if meta_only:
            self._Recogniser = G_NullRecogniser(event_id)
        else:
            self._Recogniser = G_Recogniser(event_id, self._Results.AnalysisDbInfo, log_schema, log_file)
        
        nlv = Nlv()
        nlv.Recognise = self._Recogniser.Recognise
        nlv.Project = self._Projector.Project
        nlv.Nodes = self._Projector.Nodes
        nlv.Links = self._Projector.Links
        nlv.Network = self._Projector.Network
        nlv.MakeDisplaySchema = self.MakeDisplaySchema
        nlv.SessionDir = log_node.MakeSessionDir()

        script_globals = dict(
            Recognise = nlv.Recognise,
            Project = nlv.Project,
            Nodes = nlv.Nodes,
            Links = nlv.Links,
            Network = nlv.Network,
            MakeDisplaySchema = nlv.MakeDisplaySchema,
            Nlv = nlv
        )

        return script_globals


    #-------------------------------------------------------
    def Close(self):
        self._Results.EventId = self._Recogniser.Close()
        return self._Results



## G_Quantifier ############################################

class G_Quantifier:

    #-------------------------------------------------------
    def __init__(self, quantifier_info):
        self._QuantifierInfo = quantifier_info


    #-------------------------------------------------------
    def Run(self, locked):
        db_info = self._QuantifierInfo.MetricsDbInfo
        if not Path(db_info.BaseInfo.Path).exists():
            return

        if locked and Path(db_info.Path).exists():
            return

        with db_info.ConnectionManager() as connection:
            cursor = connection.cursor()
            db_info.AttachBases(cursor)
            
            self._QuantifierInfo.UserQuantifier(connection, cursor)
        
            MakeProjectionView(cursor)
            cursor.close()
            connection.commit()

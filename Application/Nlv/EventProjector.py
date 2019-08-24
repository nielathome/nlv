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
from pathlib import Path
import sqlite3

# Application imports 
from .Logmeta import G_FieldSchemata
from .Project import G_Project
from .MatchNode import G_MatchItem
from .Project import G_Global
from .Project import G_PerfTimerScope

# wxWidgets imports
import wx

# Content provider interface
import Nlog


## Locals ##################################################

#-----------------------------------------------------------
def ConnectDb(path, read_only = False):
    # can't read from a non-existand database
    if read_only and not Path(path).exists():
        return None
        
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()
    cursor.execute("PRAGMA synchronous = OFF")

    # commented out, as it yields strange "sqlite3.OperationalError:
    # database table is locked" errors on the first db execute
    #cursor.execute("PRAGMA journal_mode = MEMORY")

    return connection


#-----------------------------------------------------------
def MakeProjectionView(cursor):
    cursor.execute("DROP TABLE IF EXISTS main.filter")
    cursor.execute("""
        CREATE TABLE main.filter
        (
            log_row_no INT
        )""")

    cursor.execute("""
        CREATE VIEW IF NOT EXISTS main.filtered_projection AS
		SELECT
			*
		FROM
			projection
			JOIN
				filter
			ON
				projection.rowid = filter.log_row_no
        """)



## G_ScriptGuard ###########################################

class G_ScriptGuard:
    """
    All use of the user supplied recogniser script, and any
    objects/functions returned from the script, should be
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
    def __init__(self, event_id, connection, log_schema, logfile):
        self._EventId = event_id
        self._Connection = connection
        self._Cursor = connection.cursor()
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
        if selector_id == Nlog.EnumSelector.Literal:
            return 'log ~= "{}"{}'.format(match.MatchText, case)

        elif selector_id == Nlog.EnumSelector.RegularExpression:
            return 'log ~= /{}/{}'.format(match.MatchText, case)

        elif selector_id == Nlog.EnumSelector.LogviewFilter:
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
            finish_timecode.Subtract(start_timecode)
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
            7 (finish_utc" INT) - UTC date/time of event finish, to previous whole second
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
    @G_Global.TimeFunction
    def Recognise(self, user_analyser, start_desc, finish_desc = None):
        """Implements user analyse script Recognise() function"""
        # observation: this could be made multithreaded

        field_ids = self._LogFieldIds

        (start_view, finish_view) = self.BuildLineSets(start_desc, finish_desc)

        self._StartAccessor = start_accessor = G_LineAccessor(field_ids, start_view)
        start_line_count = start_view.GetNumLines()

        self._FinishAccessor = finish_accessor = G_LineAccessor(field_ids, finish_view)
        finish_line_count = finish_view.GetNumLines()

        user_analyser.Begin(self._Connection, self._Cursor)

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
            first_finish_lineno = finish_view.LogLineToViewLine(start_log_lineno)
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
                logging.info("Event close not found (performance warning)")

        user_analyser.End()
        user_analyser = None

        self._Cursor.close()
        self._Connection.commit()


    #-------------------------------------------------------
    def Close(self):
        return self._EventId



## G_ProjectionTypeManager #################################

class G_ProjectionTypeManager:
    """Type management and value conversion services for the data model"""

    #-------------------------------------------------------
    def _GetText(view, line_no, field_no):
        return view.GetFieldText(line_no, field_no)
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
        [_GetSigned, _GetText, _TextModelInfo], # _c_signed
        [_GetFloat, _GetText, _TextModelInfo], # _c_float
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
    def __init__(self, name, type, available, width = 0, align = None, formatter = None, data_col_offset = 0):
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
    """Describe all the projected fields (database 'row')"""

    #-------------------------------------------------------
    def __init__(self, guid = ""):
        super().__init__("sql", guid)
        self._SetTextOffsetSize(16)
        self.DurationScale = 1
        self.ColParentId = None
        self.ColStartOffset = None
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
    def MakeHiddenFieldSchema(self, name, type):
        G_ProjectionTypeManager.ValidateType(type)
        return self.Append(G_ProjectionFieldSchema(name, type, False))


    def MakeFieldSchema(self, name, type, width = 30, align = "centre", formatter = None, data_col_offset = 0):
        G_ProjectionTypeManager.ValidateType(type)
        al = __class__._CalcAlign(align)
        return self.Append(G_ProjectionFieldSchema(name, type, True, width, al, formatter, data_col_offset))


    #-------------------------------------------------------
    def AddNesting(self):
        self.ColParentId = self.MakeHiddenFieldSchema("parent_id", "int")
        return self

    def AddEventId(self):
        self.MakeHiddenFieldSchema("event_id", "int")
        return self

    def AddField(self, name, type, width = 30, align = "centre", formatter = None):
        self.MakeFieldSchema(name, type, width, align, formatter)
        return self

    def AddStart(self, name, width = 30, align = "centre", formatter = None):
        self.MakeFieldSchema(name, "text", width, align, formatter, 1)
        self.ColStartOffset = self.MakeHiddenFieldSchema("start_offset_ns", "int")
        return self

    def AddFinish(self, name, width = 30, align = "centre", formatter = None):
        self.MakeFieldSchema(name, "text", width, align, formatter, 1)
        self.ColFinishOffset = self.MakeHiddenFieldSchema("finish_offset_ns", "int")
        return self

    def AddDuration(self, name, scale = "us", width = 30, align = "centre", formatter = None):
        name = "{} ({})".format(name, scale)
        self.DurationScale = self._CalcScale(scale)
        self.ColDuration = self.MakeFieldSchema(name, "int", width, align, formatter)
        return self



## G_ChartInfo #############################################

class G_ChartInfo:

    #-------------------------------------------------------
    def __init__(self, name, want_selection, builder):
        self.Name = name
        self.WantSelection = want_selection
        self.Builder = builder



## G_QuantifierInfo ########################################

class G_QuantifierInfo:

    #-------------------------------------------------------
    def __init__(self, name, quantifier, metrics_schema, metrics_db_path, charts):
        self.Name = name
        self.UserQuantifier = quantifier
        self.MetricsSchema = metrics_schema
        self.MetricsDbPath = str(metrics_db_path)

        self.Charts = []
        for chart in charts:
            self.Charts.append(G_ChartInfo(chart[0], chart[1], chart[2]))



## G_AnalysisResults #######################################

class G_AnalysisResults:

    #-------------------------------------------------------
    def __init__(self, events_db_path, event_id):
        self.EventsDbPath = events_db_path
        self.EventId = event_id
        self.EventSchema = G_ProjectionSchema()
        self.Quantifiers = dict()


    #-------------------------------------------------------
    def AddQuantifierInfo(self, name, user_quantifier, metrics_schema, charts):
        id = len(self.Quantifiers)
        metrics_db_path = Path(self.EventsDbPath)
        metrics_db_path = metrics_db_path.with_name("{}.{}.db".format(metrics_db_path.stem, id))
        self.Quantifiers.update([(name, G_QuantifierInfo(name, user_quantifier, metrics_schema, metrics_db_path, charts))])


    #-------------------------------------------------------
    def GetQuantifierInfo(self, name):
        return self.Quantifiers[name]



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



## G_ProjectionContext #####################################

class G_ProjectionContext:
    """Collect event data from any number of event analyses"""

    #-------------------------------------------------------
    def __init__(self, log_node, col_start):
        self._LogNode = log_node
        self._EventNo = 0
        self._ColStart = col_start

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

            datum = cursor.fetchone()[0]
            if utc_datum == 0 or datum < utc_datum:
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
    def __init__(self, connection, schema_only, log_node, results):
        self._Connection = connection
        self._SchemaOnly = schema_only
        self._LogNode = log_node
        self._Results = results


    #-------------------------------------------------------
    def Project(self, name, user_projector, event_schema):
        """Implements user analyse script Project() function"""

        self._Results.EventSchema = event_schema
        if self._SchemaOnly:
            return

        projection_context = G_ProjectionContext(self._LogNode, event_schema.ColStartOffset)
        self._LogNode = None

        cursor = self._Connection.cursor()
        with G_PerfTimerScope("G_Projector.Project") as timer:
            user_projector(self._Connection, cursor, projection_context)

        projection_context.Close()
        MakeProjectionView(cursor)

        cursor.close()
        self._Connection.commit()



## G_Analyser ##############################################

class G_Analyser:
    """
    Analyse a logfile; combines event recognition, projection
    and metrics collection
    """

    #-------------------------------------------------------
    def __init__(self, events_db_path, event_id):
        self._Results = G_AnalysisResults(events_db_path, event_id)
        self._Connection = None


    #-------------------------------------------------------
    def MakeDisplaySchema(self):
        return G_ProjectionSchema("14C89CE3-E8A4-4F28-99EB-3EF5D5FD3B13")


    #-------------------------------------------------------
    def Quantify(self, name, user_quantifier, metrics_schema, charts):
        self._Results.AddQuantifierInfo(name, user_quantifier, metrics_schema, charts)


    #-------------------------------------------------------
    def SetEntryPoints(self, meta_only, log_schema, log_file, log_node):
        script_globals = dict()

        event_id = self._Results.EventId
        if meta_only:
            self._Recogniser = G_NullRecogniser(event_id)
        else:
            self._Connection = ConnectDb(self._Results.EventsDbPath)
            self._Recogniser = G_Recogniser(event_id, self._Connection, log_schema, log_file)
        
        script_globals.update(Recognise = self._Recogniser.Recognise)

        self._Projector = G_Projector(self._Connection, meta_only, log_node, self._Results)
        script_globals.update(Project = self._Projector.Project)

        script_globals.update(MakeDisplaySchema = self.MakeDisplaySchema)
        script_globals.update(Quantify = self.Quantify)

        return script_globals


    #-------------------------------------------------------
    def Close(self):
        self._Results.EventId = self._Recogniser.Close()

        if self._Connection is not None:
            self._Connection.close()

        return self._Results



## G_Quantifier ############################################

class G_Quantifier:

    #-------------------------------------------------------
    def __init__(self, quantifier_info, events_db_path):
        self._QuantifierInfo = quantifier_info
        self._EventsDbPath = events_db_path


    #-------------------------------------------------------
    def Run(self, locked):
        if not  Path(self._EventsDbPath).exists():
            return

        if locked and Path(self._QuantifierInfo.MetricsDbPath).exists():
            return

        connection = ConnectDb(self._QuantifierInfo.MetricsDbPath)
        cursor = connection.cursor()

        self._QuantifierInfo.UserQuantifier(self._EventsDbPath, connection, cursor)
        
        MakeProjectionView(cursor)
        cursor.close()
        connection.commit()

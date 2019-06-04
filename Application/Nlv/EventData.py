#
# Copyright (C) Niel Clausen 2019. All rights reserved.
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


# Application imports 
from .Logmeta import G_FieldSchemata
from .MatchNode import G_MatchItem

# Content provider interface
import Nlog



## G_EventTypeManager ######################################

class G_EventTypeManager:
    """Type management and value conversion services for SQL"""

    _FieldTypes = dict(
        bool = "integer",
        uint08 = "integer",
        uint16 = "integer",
        uint32 = "integer",
        uint64 = "integer",
        int08 = "integer",
        int16 = "integer",
        int32 = "integer",
        int64 = "integer",
        float32 = "real",
        float64 = "real",
        enum08 = "integer",
        enum16 = "integer",
        text = "text"
    )


    #-------------------------------------------------------
    def ValidateType(type):
        me = __class__

        if not type in me._FieldTypes:
            raise RuntimeError("Invalid field type: {}".format(type))

        return me._FieldTypes[type]



## G_EventFieldSchema ######################################

class G_EventFieldSchema:
    """Describe a single event field (database 'colummn')"""

    #-------------------------------------------------------
    def __init__(self, name, type):
        self.Name = name
        self.Type = type



## G_EventSchema ###########################################

class G_EventSchema(G_FieldSchemata):
    """Describe all the fields of a table (database 'row')"""

    #-------------------------------------------------------
    def __init__(self, guid = ""):
        super().__init__(guid)



## G_CoreSchemaCollector ###################################

class G_CoreSchemaCollector:
    """Collect schema data for a SQL table"""

    #-------------------------------------------------------
    def __init__(self):
        self._Schema = G_EventSchema("B2ADC6BF-AEBC-452B-B604-4EDCCCE2CBCD")


    #-------------------------------------------------------
    @staticmethod
    def MakeFieldSchema(name, type):
        return G_EventFieldSchema(name, G_EventTypeManager.ValidateType(type))


    #-------------------------------------------------------
    def AddField(self, name, type):
        field_schema = self.MakeFieldSchema(name, type)
        self._Schema.Append(field_schema)


    #-------------------------------------------------------
    def Close(self):
        return self._Schema



## G_EventSchemaCollector ##################################

class G_EventSchemaCollector(G_CoreSchemaCollector):
    
    #-------------------------------------------------------
    def __init__(self, date_fieldtype):
        super().__init__()

        self.AddField("start_text", "text")
        self.AddField("start_line_no", "uint32")
        self.AddField("start_utc", "uint64")
        self.AddField("start_offset_ns", "uint64")

        self.AddField("finish_text", "text")
        self.AddField("finish_line_no", "uint32")
        self.AddField("finish_utc", "uint64")
        self.AddField("finish_offset_ns", "uint64")

        self.AddField("duration_ns", "uint64")



## G_EventDateTime ###########################################==

class G_EventDateTime:

    #-------------------------------------------------------
    def __init__(self, log_line_no, accessor, date_field_id):
        self.LogLineNumber = log_line_no

        self.Text = accessor.GetFieldText(date_field_id)

        timecode = accessor.GetUtcTimecode()
        timecode.Normalise()
        self.Timecode = timecode


    #-------------------------------------------------------
    def AsFields(self):
        return [self.Text, self.LogLineNumber, self.Timecode.GetUtcDatum(), self.Timecode.GetOffsetNs()]



## G_EventCollector ########################################

class G_EventCollector:
    """Collect and save event data from an event analyser"""

    #-------------------------------------------------------
    def __init__(self, database, table_name, event_schema, date_fieldid, start_accessor, finish_accessor):
        self._Database = database
        self._DateFieldId = date_fieldid
        self._StartAccessor = start_accessor
        self._FinishAccessor = finish_accessor

        self._FieldCount = len(event_schema)

        # initialise SQL table
        self._Cursor = cursor = database.cursor()
        cursor.execute("DROP TABLE IF EXISTS {}".format(table_name))

        sql_columns = ["{} {}".format(field_schema.Name, field_schema.Type) for field_schema in event_schema]
        cursor.execute("CREATE TABLE {} ({})".format(table_name, ", ".join(sql_columns)))
        database.commit()

        placeholders = ", ".join(["?" for i in range(self._FieldCount)])
        self._InsertCmd = "INSERT INTO {} VALUES ({})".format(table_name, placeholders)


    #-------------------------------------------------------
    def SetStartLine(self, log_lineno):
        self._StartLine = log_lineno

    def SetFinishLine(self, log_lineno):
        self._FinishLine = log_lineno


    #-------------------------------------------------------
    def AddEvent(self, recogniser_values):
        start_date = G_EventDateTime(self._StartLine, self._StartAccessor, self._DateFieldId)
        finish_date = G_EventDateTime(self._FinishLine, self._FinishAccessor, self._DateFieldId)

        duration = finish_date.Timecode.Subtract(start_date.Timecode)

        values = start_date.AsFields()
        values.extend(finish_date.AsFields())
        values.append(duration)
        values.extend(recogniser_values)

        if len(values) != self._FieldCount:
            raise RuntimeError("Incorrect number of field values: got:{} exp:{}".format(len(values), self._FieldCount))

        self._Cursor.execute(self._InsertCmd, values)
        self._EventIdentified = True


    def CancelEvent(self):
        self._EventIdentified = True


    def WasEventIdentified(self):
        return self._EventIdentified


    #-------------------------------------------------------
    def Close(self):
        self._Database.commit()



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
    """Analyse a log, creates an event table"""

    #-------------------------------------------------------
    def __init__(self, database, instance_guid, log_schema, logfile):
        self._Database = database
        self._Guid = instance_guid.replace("-", "_")
        self._LogSchema = log_schema
        self._LogFile = logfile

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
        lvf_text = self.ConvertMatchToLVFText(recogniser_match)

        if len(lvf_text) == 0:
            raise RuntimeError("Empty line filter")

        return G_MatchItem("LogView Filter", lvf_text)


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
    def CollectEvents(self, user_analyser, full_table_name):
        # observation: this could be made multithreaded

        field_ids = self._LogFieldIds

        (start_view, finish_view) = self.BuildLineSets(user_analyser)

        start_accessor = G_LineAccessor(field_ids, start_view)
        start_line_count = start_view.GetNumLines()

        finish_accessor = G_LineAccessor(field_ids, finish_view)
        finish_line_count = finish_view.GetNumLines()

        event_collector = G_EventCollector(self._Database, full_table_name, self._EventSchema, self.GetDateFieldId(), start_accessor, finish_accessor)

        for start_lineno in range(start_line_count):
            start_accessor.SetLineNo(start_lineno)
            match_finish_func = user_analyser.MatchEventStart(start_accessor)

            if match_finish_func is None:
                continue

            # convert the index (into the lineset) to the actual logfile line number
            start_log_lineno = start_view.ViewLineToLogLine(start_lineno)
            event_collector.SetStartLine(start_log_lineno)

            # hence find the lineno to the first-event finish candidate in the finish
            # view; negative means "not found"
            first_finish_lineno = finish_view.LogLineToViewLine(start_log_lineno)
            if first_finish_lineno < 0:
                continue

            # now find the event finish line, and, hence, create the event
            for finish_lineno in range(first_finish_lineno, finish_line_count):
                finish_accessor.SetLineNo(finish_lineno)
                finish_log_lineno = finish_view.ViewLineToLogLine(finish_lineno)
                event_collector.SetFinishLine(finish_log_lineno)

                match_finish_func(finish_accessor, event_collector)
                if event_collector.WasEventIdentified():
                    break

            if not event_collector.WasEventIdentified():
                logging.info("Event close not found (performance warning)")

        event_collector.Close()


    #-------------------------------------------------------
    def RegisterAnalyser(self, table_name, user_analyser):
        full_table_name = "t_{}_{}".format(table_name, self._Guid)
        self._EventSchema = self.CollectEventSchema(user_analyser, full_table_name)
        self.CollectEvents(user_analyser)

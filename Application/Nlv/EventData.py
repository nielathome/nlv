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
    """Analyse a log, creates any number of event/feature tables"""

    #-------------------------------------------------------
    _EventColumnNames = [
        "start_text",
        "start_line_no",
        "start_utc",
        "start_offset_ns",
        "finish_text",
        "finish_line_no",
        "finish_utc",
        "finish_offset_ns",
        "duration_ns"
    ]

    _EventColumnTypes = [
        "TEXT",
        "INT",
        "INT",
        "INT",
        "TEXT",
        "INT",
        "INT",
        "INT",
        "INT"
    ]


    #-------------------------------------------------------
    @classmethod
    def GetCreateTableColumnsText(cls):
        cols = ["{} {}".format(n, t) for n, t in zip(cls._EventColumnNames, cls._EventColumnTypes)]
        return ", ".join(cols)

    def GetInsertColumnsText(cls):
        return ", ".join(["?" for i in range(len(cls._EventColumnNames))])


    #-------------------------------------------------------
    def __init__(self, connection, log_schema, logfile):
        self.Connection = connection
        self._LogFile = logfile
        self._DateFieldId = logfile.GetTimecodeBase().GetFieldId() - 1

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
    def GetInsertValues(self):
        start_timecode = self._StartAccessor.GetUtcTimecode()
        start_timecode.Normalise()

        finish_timecode = self._FinishAccessor.GetUtcTimecode()
        finish_timecode.Normalise()

        return [
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
        ]


    #-------------------------------------------------------
    def Analyse(self, user_analyser):
        # observation: this could be made multithreaded

        field_ids = self._LogFieldIds

        (start_view, finish_view) = self.BuildLineSets(user_analyser)

        self._StartAccessor = start_accessor = G_LineAccessor(field_ids, start_view)
        start_line_count = start_view.GetNumLines()

        self._FinishAccessor = finish_accessor = G_LineAccessor(field_ids, finish_view)
        finish_line_count = finish_view.GetNumLines()

        user_analyser.Begin(self)

        for start_lineno in range(start_line_count):
            start_accessor.SetLineNo(start_lineno)
            match_finish_func = user_analyser.MatchEventStart(self, start_accessor)

            if match_finish_func is None:
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

        user_analyser.End(self)
        user_analyser = None

        self.Connection.commit()

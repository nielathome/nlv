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

# Python imports
import logging

# Application imports 
from .Logmeta import G_FieldSchemata
from .MatchNode import G_MatchItem
from .Project import G_Global

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

        lineset = self._LogFile.CreateLineSet(match)
        if lineset is None:
            raise RuntimeError("Broken filter: {}".format(match.MatchText))

        return lineset


    @G_Global.TimeFunction
    def BuildLineSets(self, user_analyser):
        user_descs = user_analyser.DefineFilter()

        start_desc = user_descs[0]
        start_view = self.BuildLineSet(G_MatchItem(start_desc[0], start_desc[1]))

        have_finish_desc = len(user_descs) > 1
        if have_finish_desc:
            finish_desc = user_descs[1]
            finish_view = self.BuildLineSet(G_MatchItem(finish_desc[0], finish_desc[1]))
        else:
            finish_view = start_view

        return (start_view, finish_view)


    #-------------------------------------------------------
    def GetEventStartDetails(self):
        """
        Return the following details about the event, as an array:
            0 (start_text TEXT) - start time as text; in the same format as the logfile
            1 (start_utc INT) - UTC date/time of event start, to previous whole second
            2 (start_offset_ns INT) - offset from #2 to event start, in ns
        """

        start_timecode = self._StartAccessor.GetUtcTimecode()
        start_timecode.Normalise()

        return [
            # event start details
            self._StartAccessor.GetFieldText(self._DateFieldId),
            start_timecode.GetUtcDatum(),
            start_timecode.GetOffsetNs(),
        ]


    def GetEventDetails(self):
        """
        Return the following details about the event, as an array:
            0 (start_text TEXT) - start time as text; in the same format as the logfile
            1 (start_line_no INT) - start line number
            2 (start_utc INT) - UTC date/time of event start, to previous whole second
            3 (start_offset_ns INT) - offset from #2 to event start, in ns
            4 (finish_text TEXT) - finish time as text; in the same format as the logfile
            5 (finish_line_no INT) - finish line number
            6 (finish_utc" INT) - UTC date/time of event finish, to previous whole second
            7 (finish_offset_ns INT) - offset from #6 to event finish, in ns
            8 (duration_ns INT) - event duration, in ns
        """

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
    @G_Global.TimeFunction
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

        user_analyser.End(self)
        user_analyser = None

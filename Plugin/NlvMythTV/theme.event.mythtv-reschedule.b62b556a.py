#
# Copyright (C) Niel Clausen 2018-2019. All rights reserved.
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
import re



## Analyser ####################################################

class Analyser:

    """
    A class which identifies events in a logfile. The results of
    an analysis are written to the corresponding events table.
    """

    #-----------------------------------------------------------
    class MatchEventFinish:
        """
        Callable object. Called during event analysis to identify
        the finish of an event.
        """

        #-------------------------------------------------------
        _RegexPlace = re.compile("([\d.]+)\splace")


        #-------------------------------------------------------
        def __init__(self, analyser):
            self.Analyser = analyser


        #-------------------------------------------------------
        def __call__(self, context, line):
            """
            Called to determine whether a log line (candidate) marks
            the finish of the event of interest. Only lines matching
            the finish filter (see DefineFilter) will be passed to
            this method.

            :param `line`: provides access to the log line under
            consideration. It provides the following methods:

                . GetFieldText( field_name ) - fetches a field's value as text
                . GetFieldValueUnsigned( field_name ) - fetches an unsigned field's value
                . GetFieldValueSigned( field_name ) - fetches an integer field's value
                . GetFieldValueFloat( field_name ) - fetches a float field's value
                . GetNonFieldText() - fetches the non-field part of the log line

            where the field_name is the log file's field name as defined
            by its schema.
        
            :param `collector`: results accessor. The collector provides
            two methods:

                . AddEvent( recogniser_values )
                . CancelEvent()

            where:
                * `recogniser_values` is a list of event field values.
                  The length and types of the list members must match
                  the descriptions provided by the analysers `DefineSchema`.
            """

            f_place = 0.0
            match = re.search(self._RegexPlace, line.GetNonFieldText())
            if match and match.lastindex == 1:
                f_place = float(match[1])
            f_bool = f_place > 0.16

            values = context.GetInsertValues()
            values.extend([f_place, f_bool])

            analyser = self.Analyser
            analyser.Cursor.execute(analyser.InsertCmd, values)

            return True


    #-----------------------------------------------------------
    @staticmethod
    def DefineFilter():
        """
        Called to define the event start and event finish filters.
        During event analysis only lines matching the event start
        filter are considered as event start candidates, and similarly
        for event finish.

        Return an array of two filters. Each filter is a tuple of
        two strings:

        1. The filter type. Must be one of 'Literal, 'Regular Expression'
           or 'LogView Filter'
        2. The filter's match text.
        """

        return [
            ('LogView Filter', 'function = "HandleReschedule" and log ~= "Reschedule"'),
            ('LogView Filter', 'function = "HandleReschedule" and log ~= "Scheduled"')
        ]


    #-----------------------------------------------------------
    def Begin(self, context):
        self.Cursor = cursor = context.Connection.cursor()
        self.InsertCmd = "INSERT INTO reschedule VALUES ({}, ?, ?)".format(context.GetInsertColumnsText())
        cursor.execute("DROP TABLE IF EXISTS reschedule")
        cursor.execute("CREATE TABLE reschedule ({}, place REAL, abool INT)".format(context.GetCreateTableColumnsText()))


    #-----------------------------------------------------------
    def MatchEventStart(self, context, line):
        """
        Called to determine whether a log line (candidate) marks
        the start of an event of interest. Only lines matching
        the start filter (see DefineFilter) will be passed.

        If the log line matches the start of an event, then return
        a callable object which adheres to the MatchEventFinish
        concept.
        """
        return self.MatchEventFinish(self)


    #-----------------------------------------------------------
    def End(self, context):
        self.Cursor.close()



## Projector ###################################################

class Projector:

    """
    A class which maps one or more raw analysed event tables ready
    to be displayed in the UI.
    """

    #-----------------------------------------------------------
    @staticmethod
    def SimpleFormatter(value, attr):
        """
        Formatters are executed in the UI when the projected table
        is displayed.

        :param `value`: the field value to be displayed.

        :param `attr`: an attributes object. Controls the formatting
         of the displayed field value.  Supported methods on the
         attributes object are:
            . SetBold(set)
            . SetItalic(set)
            . SetFgColour(colour_name_or_rgb)
            . SetBgColour(colour_name_or_rgb)
        """

        if value > 1:
            attr.SetBold(True)


    #-----------------------------------------------------------
    @classmethod
    def DefineSchema(cls, schema):
        """
        Called to define the schema of the resulting event list.
        Optionally call InitStart to customise the start date/time
        field added by NLV. Also, call AddFinish to add a finish
        date/time field, and/or AddDuration to add a duration time
        field. Adding at least one of AddFinish or AddDuration is
        recommended for long lived events, as it results in better
        visibility when tracking events in the UI.

        Then call AddField to define each further field (column)
        that will be populated for an event. 

        Available schema methods are shown below. They must be
        called in the order shown. Only AddField can be called
        more than once.
            AddNesting(self)

            AddStart(self, name, width = 30, align = None,
             formatter = None)

            AddFinish(self, name, width = 30, align = "centre",
             formatter = None)

            AddDuration(self, name, scale = "us", width = 30,
             align = "centre", formatter = None)

            AddField(self, name, type, width = 30, align = "centre",
             formatter = None)

        where:
            * `name` is the field's display name as a string

            * `type` is the field'd binary type. It must be one of
               the string values defined for schema:
                - 'bool'
                - 'enum08', 'enum16'
                - 'uint08', 'uint16', 'uint32', 'uint64'
                - 'int08', 'int16', 'int32', 'int64'
                - 'float32', 'float64'
                - 'enum08', 'enum16'
                - 'text'

            * `width` is the field's preferred display width in
               pixels (int)

            * `align` is the fields preferred display alignment.
              For InitStart it can be an empty string, meaning
              'leave as default'. Otherwise, it must be one of the
              following string values:
                - 'left'
                - 'centre'
                - 'right'

            * `formatter` (optional) is a callable Python object
              called during event display to control the formatting
              of the field's value

            * `scale` (optional) divisor for the calculated duration.
              Internally, NLV uses nanoseconds for all time values.
              The calculated duration is adjusted by `scale` before
              storage/display. Values are:
                - 'ns' to display nanoseconds
                - 'us' to display microseconds
                - 'ms' to display milliseconds
                - 's' to display seconds

        It is recommended to include the finish time, as the UI
        can then always correctly locate the end of the event.
        """

        schema.AddStart("Start", width = 100)
        schema.AddDuration("Duration", scale = "s", width = 60, formatter = cls.SimpleFormatter)
        schema.AddField("Place", "float32", 60)
        schema.AddField("Abool", "bool", 60)



    #-----------------------------------------------------------
    @staticmethod
    def Project(connection, context):
        cursor = connection.cursor()
        cursor.execute("SELECT start_text, duration_ns, place, abool FROM reschedule")

        for event in cursor:
            context.AddEvent([
                event[0],
                context.CalcDuration(event[1]),
                event[2],
                event[3]
            ])



## GLOBAL ##################################################

"""
Recogniser configuration. Call the global Register function as
follows:

    Register(log_analyser)

where:
    * `log_analyser` is an object, behaving as per `LogfileAnalyser`
"""

Analyse(Analyser())
Project("Reschedule", Projector())
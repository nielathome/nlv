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

    #-----------------------------------------------------------
    _RegexPlace = re.compile("([\d.]+)\splace")


    #-----------------------------------------------------------
    @staticmethod
    def DefineFilter():
        return [
            ('LogView Filter', 'function = "HandleReschedule" and log ~= "Reschedule"'),
            ('LogView Filter', 'function = "HandleReschedule" and log ~= "Scheduled"')
        ]


    #-----------------------------------------------------------
    def Begin(self, context):
        self.Cursor = cursor = context.Connection.cursor()
        cursor.execute("DROP TABLE IF EXISTS reschedule")
        cursor.execute("""
            CREATE TABLE reschedule
            (
                start_text TEXT,
                start_line_no INT,
                start_utc INT,
                start_offset_ns INT,
                finish_text TEXT,
                finish_line_no INT,
                finish_utc INT,
                finish_offset_ns INT,
                duration_ns INT,
                process INT,
                place REAL,
                abool INT
            )""")


    #-----------------------------------------------------------
    def MatchEventStart(self, context, line):
        self.Process = line.GetFieldValueUnsigned("Process")
        return self.MatchEventFinish


    #-----------------------------------------------------------
    def MatchEventFinish(self, context, line):
        ed = context.GetEventDetails()

        f_place = 0.0
        match = re.search(self._RegexPlace, line.GetNonFieldText())
        if match and match.lastindex == 1:
            f_place = float(match[1])
        f_bool = f_place > 0.16


        self.Cursor.execute("INSERT INTO reschedule VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            ed[0], ed[1], ed[2], ed[3], ed[4], ed[5], ed[6], ed[7], ed[8],
            self.Process,
            f_place,
            f_bool
        ])

        return True


    #-----------------------------------------------------------
    def End(self, context):
        self.Cursor.close()
        context.Connection.commit()



## Projector ###################################################

class Projector:

    """
    A class which maps one or more raw analysed event tables ready
    to be displayed in the UI.
    """

    #-----------------------------------------------------------
    @staticmethod
    def SimpleFormatter(value, attr):
        if value > 1:
            attr.SetBold(True)


    #-----------------------------------------------------------
    @classmethod
    def DefineSchema(cls, schema):
        schema.AddStart("Start", width = 100)
        schema.AddFinish("Finish", width = 100)
        schema.AddDuration("Duration", scale = "s", width = 60, formatter = cls.SimpleFormatter)
        schema.AddField("Place", "float32", 60)
        schema.AddField("Abool", "bool", 60)


    #-----------------------------------------------------------
    @staticmethod
    def Project(connection, context):
        cursor = connection.cursor()

        table_name = context.MakeProjectionTable(cursor)

        cursor.execute("""
            INSERT INTO {}
            SELECT
                start_text,
                start_utc,
                start_offset_ns,
                finish_text,
                finish_utc,
                finish_offset_ns,
                duration_ns,
                place,
                abool
            FROM
                reschedule
            """.format(table_name))

        cursor.close()
        connection.commit()



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
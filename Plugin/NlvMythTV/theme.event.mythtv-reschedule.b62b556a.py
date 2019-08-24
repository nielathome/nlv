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



## Recognise ###################################################

class Recogniser:

    #-----------------------------------------------------------
    _RegexPlace = re.compile("([\d.]+)\splace")


    #-----------------------------------------------------------
    def Begin(self, connection, cursor):
        self.Cursor = cursor

        cursor.execute("DROP TABLE IF EXISTS main.reschedule")
        cursor.execute("""
            CREATE TABLE reschedule
            (
                event_id INT,
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
        f_place = 0.0
        match = re.search(self._RegexPlace, line.GetNonFieldText())
        if match and match.lastindex == 1:
            f_place = float(match[1])
        f_bool = f_place > 0.16

        self.Cursor.execute("INSERT INTO reschedule VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            *context.GetEventFullDetails(),
            self.Process,
            f_place,
            f_bool
        ))

        return True


    #-----------------------------------------------------------
    def End(self):
        pass


Recognise(
    Recogniser(),
    ('LogView Filter', 'function = "HandleReschedule" and log ~= "Reschedule"'),
    ('LogView Filter', 'function = "HandleReschedule" and log ~= "Scheduled"')
)



## Project #####################################################

def Projector(connection, cursor, context):
    utc_datum = context.CalcUtcDatum(cursor, ["reschedule"])

    cursor.execute("DROP TABLE IF EXISTS main.projection")
    cursor.execute("""
        CREATE TABLE projection
        (
            event_id INT,
            start_text TEXT,
            start_offset_ns INT,
            finish_text TEXT,
            finish_offset_ns INT,
            duration_ns INT,
            place REAL,
            abool INT
        )""")

    cursor.execute("""
        INSERT INTO projection
        SELECT
            event_id,
            start_text,
            start_offset_ns + (start_utc - {utc_datum}) * 1000000000,
            finish_text,
            finish_offset_ns + (finish_utc - {utc_datum}) * 1000000000,
            duration_ns,
            place,
            abool
        FROM
            reschedule
        """.format(utc_datum = utc_datum))


def SimpleFormatter(value, attr):
    if value > 1:
        attr.SetBold(True)


Project(
    "Reschedule",
    Projector,
    MakeDisplaySchema()
        .AddEventId()
        .AddStart("Start", width = 100)
        .AddFinish("Finish", width = 100)
        .AddDuration("Duration", scale = "s", width = 60, formatter = SimpleFormatter)
        .AddField("Place", "real", 60)
        .AddField("Abool", "bool", 60)
)
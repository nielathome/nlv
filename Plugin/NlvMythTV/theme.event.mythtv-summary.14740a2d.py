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

import Nlv.Chart as ch
import re



## Recognise ###################################################

class RescheduleRecogniser:

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
    RescheduleRecogniser(),
    ('LogView Filter', 'function = "HandleReschedule" and log ~= "Reschedule"'),
    ('LogView Filter', 'function = "HandleReschedule" and log ~= "Scheduled"')
)



## Recognise ###################################################

class SummaryRecogniser:

    #-----------------------------------------------------------
    def Begin(self, connection, cursor):
        self.Cursor = cursor

        cursor.execute("DROP TABLE IF EXISTS main.expire")
        cursor.execute("""
            CREATE TABLE expire
            (
                event_id INT,
                start_text TEXT,
                start_line_no INT,
                start_utc INT,
                start_offset_ns INT,
                duration_ns INT,
                finish_line_no INT,
                process INT
            )""")


    #-----------------------------------------------------------
    def MatchEventStart(self, context, line):
        self.Process = line.GetFieldValueUnsigned("Process")
        return self.MatchEventFinish


    #-----------------------------------------------------------
    def MatchEventFinish(self, context, line):
        self.Cursor.execute("INSERT INTO expire VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            * context.GetEventStartDetails(),
            self.Process
        ))

        return True


    #-----------------------------------------------------------
    def End(self):
        pass


Recognise(
    SummaryRecogniser(),
    ('LogView Filter', 'function = "CalcParams"'),
    ('LogView Filter', 'function = "HandleAnnounce" and log ~= "adding"')
)



## Project #####################################################

def RescheduleProjector(connection, cursor, context):
    utc_datum = context.CalcUtcDatum(cursor, ["analysis.reschedule"])

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
            process INT,
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
            process,
            place,
            abool
        FROM
            analysis.reschedule
        """.format(utc_datum = utc_datum))


def SimpleFormatter(value, attr):
    if value > 1:
        attr.SetBold(True)


Project(
    "Reschedule",
    RescheduleProjector,
    MakeDisplaySchema()
        .AddStart("Start", width = 100)
        .AddFinish("Finish", width = 100, initial_visibility = False)
        .AddDuration("Duration", scale = "s", width = 60, formatter = SimpleFormatter)
        .AddField("Process", "int", 60)
        .AddField("Place", "real", 60)
        .AddField("Abool", "bool", 60)
)



## Project #####################################################

def SummaryProjector(connection, cursor, context):
    utc_datum = context.CalcUtcDatum(cursor, ["analysis.reschedule", "analysis.expire"])

    cursor.execute("DROP TABLE IF EXISTS main.projection")
    cursor.execute("""
        CREATE TABLE projection
        (
            event_id INT,
            start_text TEXT,
            start_offset_ns INT,
            duration_ns INT,
            summary TEXT,
            start_line_no INT,
            finish_line_no INT,
            process INT
        )""")

    cursor.execute("""
        INSERT INTO projection
        SELECT
            event_id,
            start_text,
            start_offset_ns + (start_utc - {utc_datum}) * 1000000000,
            duration_ns,
            'P=[' || place || ']' AS summary,
            start_line_no,
            finish_line_no,
            process
        FROM
            analysis.reschedule
        UNION ALL
        SELECT
            event_id INT,
            start_text,
            start_offset_ns + (start_utc - {utc_datum}) * 1000000000,
            duration_ns,
            'expire' AS summary,
            start_line_no,
            finish_line_no,
            process
        FROM
            analysis.expire
        """.format(utc_datum = utc_datum))

    cursor.execute("DROP TABLE IF EXISTS main.hierarchy")
    cursor.execute("""
        CREATE TABLE hierarchy
        (
            child_event_id INT NOT NULL PRIMARY KEY,
            parent_event_id INT
        )""")

    cursor.execute("""
        SELECT
            event_id,
            start_line_no,
            finish_line_no,
            process
        FROM
            projection
        ORDER BY
            start_line_no
        """)

    candidates = []
    c2 = connection.cursor()

    for row in cursor:
        # remove any candidate rows that finish before 'row' starts
        start_line = row[1]
        finish_line = row[2]
        process = row[3]

        idx = len(candidates) - 1
        while idx >= 0:
            if candidates[idx][2] < start_line:
                candidates.pop(idx)
            idx -= 1

        # since events are processed in start order, we know that
        # 'row' starts after candidates (two events can't start on the
        # same line)
        candidates.append(row)

        for idx in range(len(candidates) - 2, -1, -1):
            prev = candidates[idx]
            if prev[2] >= finish_line and prev[3] == process:
                c2.execute("INSERT INTO hierarchy VALUES (?, ?)", (row[0], prev[0]))
                break

    c2.close()


projection = Project(
    "Summary",
    SummaryProjector,
    MakeDisplaySchema()
        .AddNesting()
        .AddStart("Start", width = 100)
        .AddDuration("Duration", scale = "s", width = 60)
        .AddField("Event Summary", "text", 150, "left", initial_colour = "ROYAL BLUE")
)



## SummaryQuantifier ###########################################

def SummaryQuantifier(connection, cursor):
    cursor.execute("DROP TABLE IF EXISTS main.projection")
    cursor.execute("""
        CREATE TABLE projection
        (
            summary TEXT,
            count INT,
            sum INT,
            average REAL
        )""")

    cursor.execute("""
        INSERT INTO projection
        SELECT
            summary,
            count(duration_ns),
            sum(duration_ns / 1000000000),
            round(avg(duration_ns / 1000000000), 2)
        FROM
            events.filtered_projection
        GROUP BY
            summary
        """)


metrics = projection.Quantify(
    "Breakdown",
    SummaryQuantifier,
    MakeDisplaySchema()
        .AddField("Summary", "text", 150, "left")
        .AddField("Count", "int", 80, "left")
        .AddField("Duration (s)", "int", 80, "left")
        .AddField("Average (s)", "real", 80, "left")
)


metrics.Chart("By Count", True, ch.PieChart("summary", "count"))
metrics.Chart("By Duration", True, ch.PieChart("summary", "sum"))
#metrics.Chart("Durations", True, ch.BarChart("summary", "average"))



## TimingQuantifier ############################################

#class TimingQuantifier:

#    #-----------------------------------------------------------
#    @staticmethod
#    def DefineSchema(schema):
#        schema.AddField("Category", "text", 150, "left")
#        schema.AddField("Duration (s)", "uint32", 80, "left")


#    #-----------------------------------------------------------
#    def __init__(self):
#        self.Name = "Histogram"
#        self.Charts = [
#            EventMetrics.HistogramChart("Histogram", 0, 1),
#        ]


#    #-----------------------------------------------------------
#    def Assemble(self, metrics, num_metrics, collector):
#        category_id = collector.GetFieldId("Event Summary")
#        value_id = collector.GetFieldId("Duration (s)")

#        for evt_no in range(num_metrics):
#            category = metrics.GetFieldText(evt_no, category_id)
#            value = metrics.GetFieldValueUnsigned(evt_no, value_id)
#            collector.AddMetric([category, value])

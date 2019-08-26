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

class Recogniser:

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
                process INT
            )""")


    #-----------------------------------------------------------
    def MatchEventStart(self, context, line):
        self.Process = line.GetFieldValueUnsigned("Process")
        return self.MatchEventFinish


    #-----------------------------------------------------------
    def MatchEventFinish(self, context, line):
        self.Cursor.execute("INSERT INTO expire VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            * context.GetEventStartDetails(),
            self.Process
        ))

        return True


    #-----------------------------------------------------------
    def End(self):
        pass


Recognise(
    Recogniser(),
    ('LogView Filter', 'function = "CalcParams"'),
    ('LogView Filter', 'function = "HandleAnnounce" and log ~= "adding"')
)



## Project #####################################################

class Projector:

    #-----------------------------------------------------------
    @staticmethod
    def IsSameProcess(parent_process, child_process):
        """
        Called to determine whether the `child` event can be
        considered subordinate-to, or contained-within, the `parent`
        event.

        Both `parent` and `child` are objects returned via the
        select query. The function should return True
        if the child event is to be considered "contained by"
        (or "subordinate to") the parent event, and False otherwise.
        Contained events mey be displayed nested in the UI.

        This routine is only called where schema.AddNesting()
        was called in the DefineSchema() method.
        """
        return parent_process == child_process


#---------------------------------------------------------------
def Projector(connection, cursor, context):

    tables = ["expire"]
    db_file = context.FindDbFile("B62B556A-DABA-4886-A469-F739492750D3")

    if db_file is not None:
        cursor.execute("ATTACH DATABASE '{db}' AS db".format(db = db_file))
        tables.append("db.reschedule")

    utc_datum = context.CalcUtcDatum(cursor, tables)

    select_expire = """
        SELECT
            event_id INT,
            start_text,
            start_offset_ns + (start_utc - {utc_datum}) * 1000000000,
            duration_ns,
            'expire' AS summary
        FROM
            expire
        """.format(utc_datum = utc_datum)

    select_reschedule = """
        SELECT
            event_id,
            start_text,
            start_offset_ns + (start_utc - {utc_datum}) * 1000000000,
            duration_ns,
            'P=[' || place || ']' AS summary
        FROM
            db.reschedule
        """.format(utc_datum = utc_datum)

    if db_file is None:
        select = select_expire
    else:
        select = """
            {}
            UNION ALL
            {}
        """.format(select_expire, select_reschedule)

    cursor.execute("DROP TABLE IF EXISTS main.projection")
    cursor.execute("""
        CREATE TABLE projection
        (
            event_id,
            start_text TEXT,
            start_offset_ns INT,
            duration_ns INT,
            summary TEXT
        )""")

    cursor.execute("""
        INSERT INTO projection
            {}
        """.format(select))


Project(
    "Summary",
    Projector,
    MakeDisplaySchema()
        .AddEventId()
        .AddStart("Start", width = 100)
        .AddDuration("Duration", scale = "s", width = 60)
        .AddField("Event Summary", "text", 150, "left")
)



## GeneralQuantifier ###########################################

def GeneralQuantifier(events_db_path, connection, cursor):
    cursor.execute("ATTACH DATABASE '{db}' AS db".format(db = events_db_path))

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
            db.filtered_projection
        GROUP BY
            summary
        """)


Quantify(
    "General",
    GeneralQuantifier,

    MakeDisplaySchema()
        .AddField("Summary", "text", 150, "left")
        .AddField("Count", "int", 80, "left")
        .AddField("Duration (s)", "int", 80, "left")
        .AddField("Average (s)", "real", 80, "left"),

    [
        ("Breakdown by Count", True, ch.PieChart("summary", "count")),
        ("Breakdown by Duration", True, ch.PieChart("summary", "sum")),
        ("Durations", True, ch.BarChart("summary", "average"))
    ]
)



## TimingQuantifier ############################################

class TimingQuantifier:

    #-----------------------------------------------------------
    @staticmethod
    def DefineSchema(schema):
        schema.AddField("Category", "text", 150, "left")
        schema.AddField("Duration (s)", "uint32", 80, "left")


    #-----------------------------------------------------------
    def __init__(self):
        self.Name = "Histogram"
        self.Charts = [
            EventMetrics.HistogramChart("Histogram", 0, 1),
        ]


    #-----------------------------------------------------------
    def Assemble(self, metrics, num_metrics, collector):
        category_id = collector.GetFieldId("Event Summary")
        value_id = collector.GetFieldId("Duration (s)")

        for evt_no in range(num_metrics):
            category = metrics.GetFieldText(evt_no, category_id)
            value = metrics.GetFieldValueUnsigned(evt_no, value_id)
            collector.AddMetric([category, value])

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
import collections
from matplotlib import cm
import numpy as np
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



## BarChart ####################################################

class BarChart:

    #-----------------------------------------------------------
    def __init__(self, category_field, value_field, std_field = None):
        self._CategoryField = category_field
        self._ValueField = value_field
        self._StdField = std_field


    #-----------------------------------------------------------
    def DefineParameters(self, params, connection, cursor, selection):
        params.AddBool("show_std", "Show error bars", True)


    #-----------------------------------------------------------
    def Realise(self, name, figure, connection, cursor, param_values, selection):
        labels = []
        values = []
        stds = None

        cursor.execute("""
            SELECT
                {category},
                {value},
                log_row_no
            FROM
                filtered_projection
            """.format(category = self._CategoryField, value = self._ValueField))

        hilites = []
        for idx, row in enumerate(cursor):
            labels.append(row[0])
            values.append(row[1])
            if row[2] in selection:
                hilites.append(idx)
#            stds.append(metrics.GetFieldValueFloat(i, self._StdField))

        #if not param_values.get("show_std", True):
        #    stds = None

        x = np.arange(len(labels))
        axes = figure.add_subplot(111)
        axes.tick_params(labelsize = "small")
        bars = axes.bar(x, values, yerr = stds)
        axes.set_ylabel('Average (s)')
        axes.set_xticks(x)
        axes.set_xticklabels(labels, {"rotation": 75})

        for col in hilites:
            bars[col].set_edgecolor("black")

        figure.subplots_adjust(bottom = 0.25)



## PieChart ####################################################

class PieChart:

    #-----------------------------------------------------------
    c_OtherPcts = ["5%", "10%", "15%"]

    def __init__(self, category_field, value_field):
        self._CategoryField = category_field
        self._ValueField = value_field


    #-----------------------------------------------------------
    def DefineParameters(self, params, connection, cursor, selection):
        params.AddChoice("other_pct", "Approx. limit for 'Other'", 0, self.c_OtherPcts)


    #-----------------------------------------------------------
    def Realise(self, name, figure, connection, cursor, param_values, selection):
        cursor.execute("""
            SELECT
                count({value}),
                sum({value})
            FROM
                filtered_projection
            """.format(value = self._ValueField))

        (count, sum) = cursor.fetchone()
        if count == 0:
            return

        cursor.execute("""
            SELECT
                {category},
                {value},
                log_row_no
            FROM
                filtered_projection
            ORDER BY
                {value} DESC
            """.format(category = self._CategoryField, value = self._ValueField))

        param = param_values.get("other_pct", 0)
        accum = 0
        limit = sum * (1 - (0.05 * (1 + param)))

        labels = []
        values = []
        explodes = []
        other_explode = 0

        for row in cursor:
            selected = row[2] in selection

            if accum >= limit:
                if selected:
                    other_explode = 0.1

            else:
                value = row[1]
                accum += value

                labels.append(row[0])
                values.append(value)
            
                explode = 0.0
                if selected:
                    explode = 0.1
                explodes.append(explode)
            
        other = sum - accum
        if other > 0:            
            labels.append("Other")
            values.append(other)
            explodes.append(other_explode)

        cmap = cm.get_cmap('tab20c', len(values))
        axes = figure.add_subplot(111)
        axes.pie(values, labels = labels, autopct = '%1.1f%%', startangle = 90,
            explode = explodes, colors = cmap.colors, shadow = True
        )

        figure.suptitle(name, x = 0.02, y = 0.5,
            horizontalalignment = 'left', verticalalignment = 'center'
        )



## HistogramChart ##############################################

class HistogramChart:

    #-----------------------------------------------------------
    def __init__(self, category_field, value_field):
        self._CategoryField = category_field
        self._ValueField = value_field
        self._CachedCategoryLengths = None


    #-----------------------------------------------------------
    def _GetCategoryLengths(self, metrics, num_metrics, force = False):
        if self._CachedCategoryLengths is not None and not force:
            return self._CachedCategoryLengths

        lengths = self._CachedCategoryLengths = collections.Counter()
        for i in range(num_metrics):
            category = metrics.GetFieldText(i, self._CategoryField)
            lengths[category] += 1

        return lengths


    #-----------------------------------------------------------
    def DefineParameters(self, params, connection):
        lengths = self._GetCategoryLengths(metrics, num_metrics)
        for category in lengths.keys():
            params.AddBool(category, category, True)


    #-----------------------------------------------------------
    def Realise(self, figure, connection, param_values, selection):
        lengths = self._GetCategoryLengths(metrics, num_metrics, True)

        data = dict()
        for (category, length) in lengths.items():
            if param_values.get(category, True):
                data[category] = [0, np.empty(length, dtype = np.uint32)]
                
        for i in range(num_metrics):
            category = metrics.GetFieldText(i, self._CategoryField)
            entry = data.get(category, None)
            if entry is not None:
                (idx, array) = entry
                array[idx] = metrics.GetFieldValueUnsigned(idx, self._ValueField)
                entry[0] += 1

        series = [a for (i, a) in data.values()]
        axes = figure.add_subplot(111)
        axes.hist(series, 20, histtype='bar', label = data.keys())
        axes.legend()



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
        ("Breakdown by Count", True, PieChart("summary", "count")),
        ("Breakdown by Duration", True, PieChart("summary", "sum")),
        ("Durations", True, BarChart("summary", "average"))
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

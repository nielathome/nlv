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
from math import sqrt
from matplotlib import cm
import numpy as np
import re


## Analyser ####################################################

class Analyser:

    #-----------------------------------------------------------
    @staticmethod
    def DefineFilter():
        return [
            ('LogView Filter', 'function = "CalcParams"'),
            ('LogView Filter', 'function = "HandleAnnounce" and log ~= "adding"')
        ]


    #-----------------------------------------------------------
    def Begin(self, context):
        self.Cursor = cursor = context.Connection.cursor()
        cursor.execute("DROP TABLE IF EXISTS expire")
        cursor.execute("""
            CREATE TABLE expire
            (
                start_text TEXT,
                start_line_no INT,
                finish_text TEXT,
                finish_line_no INT,
                duration_ns INT,
                process INT
            )""")


    #-----------------------------------------------------------
    def MatchEventStart(self, context, line):
        self.Process = line.GetFieldValueUnsigned("Process")
        return self.MatchEventFinish


    #-----------------------------------------------------------
    def MatchEventFinish(self, context, line):
        ed = context.GetEventDetails()

        self.Cursor.execute("INSERT INTO expire VALUES (?, ?, ?, ?, ?, ?)",
        [
            ed[0], ed[1], ed[4], ed[5], ed[8],
            self.Process
        ])

        return True


    #-----------------------------------------------------------
    def End(self, context):
        self.Cursor.close()



## Projector ###################################################

class Projector:

    #-----------------------------------------------------------
    @staticmethod
    def DefineSchema(schema):
        schema.AddNesting()
        schema.AddStart("Start", width = 100)
        schema.AddFinish("Finish", 100)
        schema.AddDuration("Duration", scale = "s", width = 60)
        schema.AddField("Event Summary", "text", 150, "left")


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


    #-----------------------------------------------------------
    def Project(self, connection, context):
        cursor = connection.cursor()

        select_expire = """
            SELECT
                start_line_no,
                finish_line_no,
                process,
                start_text,
                finish_text,
                duration_ns,
                'expire'
            FROM expire"""

        select_reschedule = """
            SELECT
                start_line_no,
                finish_line_no,
                process,
                start_text,
                finish_text,
                duration_ns,
                'P=[' || place || ']'
            FROM dbs.reschedule"""

        file = context.FindDbFile("B62B556A-DABA-4886-A469-F739492750D3")
        if file is None:
            select = """
                {}
                ORDER BY start_line_no ASC
            """.format(select_expire)
        else:
            cursor.execute("ATTACH DATABASE '{}' AS dbs".format(file))
            select = """
                {}
                UNION
                {}
                 ORDER BY start_line_no ASC
            """.format(select_expire, select_reschedule)

        cursor.execute(select)
        for event in cursor:
            context.AddEvent([
                context.CalcParentId(event[0], event[1], event[2], self.IsSameProcess),
                event[3],
                event[4],
                context.CalcDuration(event[5]),
                event[6]
            ])



## EventMetrics ################################################

class EventMetrics:

    #-----------------------------------------------------------
    def __init__(self):
        self.Tables = [
            __class__.CategoryTable(),
            __class__.HistogramTable()
        ]



    ## Chart ###################################################

    class Chart:
        #-------------------------------------------------------
        def __init__(self, name, want_selection = False):
            self.Name = name
            self.WantSelection = want_selection

        #-------------------------------------------------------
        def DefineParameters(self, params, metrics, num_metrics, selection):
            pass



    ## BarChart ################################################

    class BarChart(Chart):

        #-------------------------------------------------------
        def __init__(self, name, category_field, value_field, std_field):
            super().__init__(name, want_selection = True)
            self._CategoryField = category_field
            self._ValueField = value_field
            self._StdField = std_field

        #-------------------------------------------------------
        def DefineParameters(self, params, metrics, num_metrics, selection):
            params.AddBool("show_std", "Show error bars", True)


        #-------------------------------------------------------
        def Realise(self, figure, metrics, num_metrics, param_values, selection):
            labels = []
            values = []
            stds = []

            for i in range(num_metrics):
                labels.append(metrics.GetFieldText(i, self._CategoryField))
                values.append(metrics.GetFieldValueFloat(i, self._ValueField))
                stds.append(metrics.GetFieldValueFloat(i, self._StdField))

            if not param_values.get("show_std", True):
                stds = None

            x = np.arange(len(labels))
            axes = figure.add_subplot(111)
            axes.tick_params(labelsize = "small")
            bars = axes.bar(x, values, yerr = stds)
            axes.set_ylabel('Average (s)')
            axes.set_xticks(x)
            axes.set_xticklabels(labels, {"rotation": 75})

            for event_no in selection:
                bars[event_no].set_edgecolor("black")

            figure.subplots_adjust(bottom=0.25)



    ## PieChart ################################################

    class PieChart(Chart):

        #-------------------------------------------------------
        c_OtherPcts = ["5%", "10%", "15%"]

        def __init__(self, name, category_field, value_field):
            super().__init__(name, want_selection = True)
            self._CategoryField = category_field
            self._ValueField = value_field


        #-------------------------------------------------------
        def DefineParameters(self, params, metrics, num_metrics, selection):
            params.AddChoice("other_pct", "Approx. limit for 'Other'", 0, self.c_OtherPcts)


        #-------------------------------------------------------
        def Realise(self, figure, metrics, num_metrics, param_values, selection):
            sum = 0
            for i in range(num_metrics):
                sum += metrics.GetFieldValueUnsigned(i, self._ValueField)

            other = 0
            param = param_values.get("other_pct", 0)
            min = sum * 0.05 * (1 + param)
            labels = []
            values = []
            explodes = []
            other_explode = 0

            for i in range(num_metrics):
                selected = i in selection
                value = metrics.GetFieldValueUnsigned(i, self._ValueField)

                if value < min:
                    other += value
                    if selected:
                        other_explode = 0.1

                else:
                    labels.append(metrics.GetFieldText(i, self._CategoryField))
                    values.append(value)
            
                    explode = 0.0
                    if selected:
                        explode = 0.1
                    explodes.append(explode)
            
            labels.append("Other ({})".format(self.c_OtherPcts[param]))
            values.append(other)
            explodes.append(other_explode)

            cmap = cm.get_cmap('tab20c', len(values))
            axes = figure.add_subplot(111)
            axes.pie(values, labels = labels, autopct = '%1.1f%%', startangle = 90,
                explode = explodes, colors = cmap.colors, shadow = True
            )

            figure.suptitle(self.Name, x = 0.02, y = 0.5,
                horizontalalignment = 'left', verticalalignment = 'center'
            )



    ## HistogramChart ##########################################

    class HistogramChart(Chart):

        #-------------------------------------------------------
        def __init__(self, name, category_field, value_field):
            super().__init__(name)
            self._CategoryField = category_field
            self._ValueField = value_field
            self._CachedCategoryLengths = None


        #-------------------------------------------------------
        def _GetCategoryLengths(self, metrics, num_metrics, force = False):
            if self._CachedCategoryLengths is not None and not force:
                return self._CachedCategoryLengths

            lengths = self._CachedCategoryLengths = collections.Counter()
            for i in range(num_metrics):
                category = metrics.GetFieldText(i, self._CategoryField)
                lengths[category] += 1

            return lengths


        #-------------------------------------------------------
        def DefineParameters(self, params, metrics, num_metrics, selection):
            lengths = self._GetCategoryLengths(metrics, num_metrics)
            for category in lengths.keys():
                params.AddBool(category, category, True)


        #-------------------------------------------------------
        def Realise(self, figure, metrics, num_metrics, param_values, selection):
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



    ## CategoryTable ###########################################

    class CategoryTable:

        #-------------------------------------------------------
        @staticmethod
        def DefineSchema(schema):
            schema.AddField("Category", "text", 150, "left")
            schema.AddField("Count", "uint32", 80, "left")
            schema.AddField("Duration (s)", "uint32", 80, "left")
            schema.AddField("Average (s)", "float32", 80, "left")
            schema.AddField("Stddev (s)", "float32", 80, "left")


        #-------------------------------------------------------
        def __init__(self):
            self.Name = "Category"
            self.Charts = [
                EventMetrics.PieChart("Category by Count", 0, 1),
                EventMetrics.PieChart("Category by Duration", 0, 2),
                EventMetrics.BarChart("Durations", 0, 3, 4)
            ]


        #-------------------------------------------------------
        # http://jonisalonen.com/2013/deriving-welfords-method-for-computing-variance/
        # https://www.johndcook.com/blog/standard_deviation/
        def Assemble(self, metrics, num_metrics, collector):
            data = dict()
            category_id = collector.GetFieldId("Event Summary")
            value_id = collector.GetFieldId("Duration (s)")

            for evt_no in range(num_metrics):
                category = metrics.GetFieldText(evt_no, category_id)
                value = metrics.GetFieldValueUnsigned(evt_no, value_id)

                if category in data:
                    (old_count, sum, old_M, old_S) = data[category]
                    count = old_count + 1
                    M = old_M + (value - old_M) / count
                    S = old_S + (value - old_M) * (value - M)
                    data[category]  = (count, sum + value, M, S)
                else:
                    data[category] = (1, value, value, 0)

            for (category, values) in data.items():
                (count, sum, mean, S) = data[category]
                sigma = 0.0
                if count > 1:
                    sigma = sqrt(S / (count - 1))

                values = [category, count, sum, round(mean, 2), round(sigma,2)]
                collector.AddMetric(values)



    ## HistogramTable ##########################################

    class HistogramTable:

        #-------------------------------------------------------
        @staticmethod
        def DefineSchema(schema):
            schema.AddField("Category", "text", 150, "left")
            schema.AddField("Duration (s)", "uint32", 80, "left")


        #-------------------------------------------------------
        def __init__(self):
            self.Name = "Histogram"
            self.Charts = [
                EventMetrics.HistogramChart("Histogram", 0, 1),
            ]


        #-------------------------------------------------------
        def Assemble(self, metrics, num_metrics, collector):
            category_id = collector.GetFieldId("Event Summary")
            value_id = collector.GetFieldId("Duration (s)")

            for evt_no in range(num_metrics):
                category = metrics.GetFieldText(evt_no, category_id)
                value = metrics.GetFieldValueUnsigned(evt_no, value_id)
                collector.AddMetric([category, value])



## GLOBAL ######################################################

Analyse(Analyser())
Project("Summary", Projector(), EventMetrics())


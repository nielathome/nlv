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


## BarChart ####################################################

class BarChart:

    #-----------------------------------------------------------
    def __init__(self, category_field, value_field):
        self._CategoryField = category_field
        self._ValueField = value_field


    #-----------------------------------------------------------
    def DefineParameters(self, params, connection, cursor, selection):
        pass


    #-----------------------------------------------------------
    @classmethod
    def Setup(cls, name):
        return "BarChart.html"


    #-----------------------------------------------------------
    def Realise(self, name, figure, connection, cursor, param_values, selection):
        labels = []
        values = []

        cursor.execute("""
            SELECT
                {category},
                {value},
                event_id
            FROM
                display
            """.format(category = self._CategoryField, value = self._ValueField))

        hilites = []
        for idx, row in enumerate(cursor):
            labels.append(row[0])
            values.append(row[1])
            if row[2] in selection:
                hilites.append(idx)

        figure.ExecuteScript("CreateChart({});".format(repr(values)))

#        figure.ExecuteScript('document.body.style.backgroundColor = "brown;";')

        #axes.set_ylabel('Average (s)')
        #axes.set_xticklabels(labels, {"rotation": 75})

        #for col in hilites:
        #    bars[col].set_edgecolor("black")




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
                display
            """.format(value = self._ValueField))

        (count, sum) = cursor.fetchone()
        if count == 0:
            return

        cursor.execute("""
            SELECT
                {category},
                {value},
                event_id
            FROM
                display
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




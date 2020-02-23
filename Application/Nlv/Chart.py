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
import json

        

## Bar #########################################################

def ReduceFieldName(name):
    """Convert a 'long' field name to a 'short' field name"""
    return name.split(" ")[0].lower()


class Bar:

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
        cursor.execute("""
            SELECT
                {category},
                {value},
                event_id
            FROM
                display
            """.format(category = ReduceFieldName(self._CategoryField), value = ReduceFieldName(self._ValueField)))

        data = []
        for row in cursor:
            event_id = row[2]
            selected = event_id in selection
            data.append(dict(zip(["category", "value", "selected", "event_id"], [row[0], row[1], selected, event_id])))

        # chart transition time in msec
        switch_time = 1000
        if len(selection) != 0:
            switch_time = 250

        json_text = json.dumps(data)
        figure.ExecuteScript("CreateChart('{}', '{}', '{}', '{}', {});".format(name, self._CategoryField, self._ValueField, json_text, switch_time))



## Pie #########################################################

class Pie:

    #-----------------------------------------------------------
    c_OtherPcts = ["5%", "10%", "15%"]

    def __init__(self, category_field, value_field):
        self._CategoryField = category_field
        self._ValueField = value_field


    #-----------------------------------------------------------
    def DefineParameters(self, params, connection, cursor, selection):
        params.AddChoice("other_pct", "Approx. limit for 'Other'", 0, self.c_OtherPcts)


    #-----------------------------------------------------------
    @classmethod
    def Setup(cls, name):
        return "PieChart.html"


    #-----------------------------------------------------------
    def Realise(self, name, figure, connection, cursor, param_values, selection):
        cursor.execute("""
            SELECT
                count({value}),
                sum({value})
            FROM
                display
            """.format(value = ReduceFieldName(self._ValueField)))

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
            """.format(category = ReduceFieldName(self._CategoryField), value = ReduceFieldName(self._ValueField)))

        param = param_values.get("other_pct", 0)
        accum = 0
        limit = sum * (1 - (0.05 * (1 + param)))

        data = []
        other_selected = False

        for row in cursor:
            event_id = row[2]
            selected = event_id in selection

            if accum >= limit:
                if selected:
                    other_selected = True
            else:
                value = row[1]
                accum += value
                data.append(dict(zip(["category", "value", "selected", "event_id"], [row[0], value, selected, event_id])))

        other = sum - accum
        if other > 0:            
            data.append(dict(zip(["category", "value", "selected", "event_id"], ["Other", other, other_selected, -1])))

        # chart transition time in msec
        switch_time = 1000
        if len(selection) != 0:
            switch_time = 250

        json_text = json.dumps(data)
        figure.ExecuteScript("CreateChart('{}', '{}', '{}');".format(self._ValueField, json_text, switch_time))

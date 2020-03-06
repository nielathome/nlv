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
    def DefineParameters(self, connection, cursor, context):
        pass


    #-----------------------------------------------------------
    @classmethod
    def Setup(cls, name):
        return "BarChart.html"


    #-----------------------------------------------------------
    def Realise(self, name, connection, cursor, context):
        cursor.execute("""
            SELECT
                {category},
                {value},
                event_id
            FROM
                display
            """.format(category = ReduceFieldName(self._CategoryField), value = ReduceFieldName(self._ValueField)))

        selection = context.GetSelection()
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
        context.ExecuteScript("CreateChart('{}', '{}', '{}', '{}', {});".format(name, self._CategoryField, self._ValueField, json_text, switch_time))



## Pie #########################################################

class Pie:

    #-----------------------------------------------------------
    c_OtherPcts = ["5%", "10%", "15%"]

    def __init__(self, category_field, value_field):
        self._CategoryField = category_field
        self._ValueField = value_field


    #-----------------------------------------------------------
    def DefineParameters(self, connection, cursor, context):
        context.AddChoice("other_pct", "Approx. limit for 'Other'", 0, self.c_OtherPcts)


    #-----------------------------------------------------------
    @classmethod
    def Setup(cls, name):
        return "PieChart.html"


    #-----------------------------------------------------------
    def Realise(self, name, connection, cursor, context):
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

        param = context.GetParameter("other_pct", 0)
        accum = 0
        limit = sum * (1 - (0.05 * (1 + param)))

        selection = context.GetSelection()
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
        context.ExecuteScript("CreateChart('{}', '{}', '{}');".format(self._ValueField, json_text, switch_time))



## Network #####################################################

class Network:

    #-----------------------------------------------------------
    def DefineParameters(self, connection, cursor, context):
        pass


    #-----------------------------------------------------------
    @classmethod
    def Setup(cls, name):
        return "Network.html"


    #-----------------------------------------------------------
    def Realise(self, name, connection, cursor, context):
        cursor.execute("""
            SELECT
                event_id,
                type,
                title,
                size
            FROM
                main.display
            """)

#        selection = context.GetSelection()
        nodes = []
        for row in cursor:
            event_id = row[0]
#            selected = event_id in selection
            nodes.append(dict(zip(["event_id", "type", "title", "size"], [event_id, row[1], row[2], row[3]])))


        cursor.execute("""
            SELECT
                event_id,
                source,
                target
            FROM
                links.display
            """)

        links = []
        for row in cursor:
            event_id = row[0]
#            selected = event_id in selection
            links.append(dict(zip(["event_id", "source", "target"], [event_id, row[1], row[2]])))

        network = dict(nodes = nodes, links = links)

        # chart transition time in msec
        switch_time = 1000
        #if len(selection) != 0:
        #    switch_time = 250

        json_text = json.dumps(network)
        context.ExecuteScript("CreateChart('{}', '{}', {});".format(name, json_text, switch_time))

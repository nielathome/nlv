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

        data_json = json.dumps(data)
        context.CallJavaScript("CreateChart", name, self._CategoryField, self._ValueField, data_json, switch_time)



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

        data_json = json.dumps(data)
        context.CallJavaScript("CreateChart", self._ValueField, data_json, switch_time)



## Network #####################################################

class Network:

    #-----------------------------------------------------------
    def DefineParameters(self, connection, cursor, context):
        context.AddBool("graph_is_disjoint", "Network is disjoint", False)
        

    #-----------------------------------------------------------
    @classmethod
    def Setup(cls, name):
        return "Network.html"


    #-----------------------------------------------------------
    def SetSelection(self, connection, cursor, context):
        selected_nodes = set(context.GetSelection(0))
        selected_links = set(context.GetSelection(1))

        have_nodes = len(selected_nodes) != 0
        have_links = len(selected_links) != 0

        if have_nodes or have_links:
            where = ""
            if have_nodes:
                nodes = ", ".join([str(node) for node in selected_nodes])
                where = "source_id IN ({nodes}) OR target_id IN ({nodes})".format(nodes = nodes)

            if have_links:
                if have_nodes:
                    where = where + " OR "
                links = ", ".join([str(link) for link in selected_links])
                text = " event_id IN ({links})".format(links = links)
                where = where + text

            # find everything "reachable" from the selected links
            cursor.execute("""
                SELECT
                    event_id,
                    source_id,
                    target_id
                FROM
                    links.display
                WHERE
                    {where}
                """.format(where = where))

            for row in cursor:
                selected_links.add(row[0])
                selected_nodes.add(row[1])
                selected_nodes.add(row[2])

        selection = dict(nodes = [node for node in selected_nodes], links = [link for link in selected_links])
        selection_json = json.dumps(selection)
        context.CallJavaScript("SetSelection", selection_json)


    #-----------------------------------------------------------
    def CreateChart(self, connection, cursor, context):
        cursor.execute("""
            SELECT
                event_id,
                type,
                title,
                size
            FROM
                main.display
            """)

        nodes = []
        for row in cursor:
            nodes.append(dict(zip(["event_id", "type", "title", "size"], [row[0], row[1], row[2], row[3]])))


        cursor.execute("""
            SELECT
                event_id,
                source_id,
                target_id
            FROM
                links.display
            WHERE
                source_id IN (SELECT event_id FROM main.display) AND
                target_id IN (SELECT event_id FROM main.display)
            """)

        links = []
        for row in cursor:
            links.append(dict(zip(["event_id", "source", "target"], [row[0], row[1], row[2]])))

        config = dict(graph_is_disjoint = context.GetParameter("graph_is_disjoint", False))
        config_json = json.dumps(config)

        network = dict(nodes = nodes, links = links)
        data_json = json.dumps(network)
        context.CallJavaScript("CreateChart", data_json, config_json)

        self.SetSelection(connection, cursor, context)


    #-----------------------------------------------------------
    def Realise(self, name, connection, cursor, context):
        if context.DataChanged() or context.ParamatersChanged():
            self.CreateChart(connection, cursor, context)

        elif context.SelectionChanged():
            self.SetSelection(connection, cursor, context)

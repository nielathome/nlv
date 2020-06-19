#
# Copyright (C) Niel Clausen 2019-2020. All rights reserved.
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

def SqlColumnNames(cursor, table_name, database = None):
    if database is None:
        database = ""
    else:
        database = database + "."

    cursor.execute("""
        SELECT
			sql
		FROM
			{database}sqlite_master
		WHERE
			tbl_name = "{table_name}"
			AND type = "table"        
            """.format(table_name = table_name, database = database))

    #
    # result looks something like:
    #
	#   CREATE TABLE projection
    #   (
    #       event_id INTEGER PRIMARY KEY ASC AUTOINCREMENT,
    #       type TEXT,
    #       source_entity_id INT,
    #       target_entity_id INT,
    #       ...
    #   )
    #
    text = cursor.fetchone()[0]
    columns = text[text.find("(") + 1:].split(",")
    return [col.strip().split(" ")[0] for col in columns]



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
    def Setup(cls, context):
        context.LoadPage("BarChart.html")


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
    def Setup(cls, context):
        context.LoadPage("PieChart.html")


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

def _EscapeJsonField(field):
    # the JavaScript JSON decoder doesn't like quoted backslashes in string
    # values - even though that is correct. Workaround here for the time being.
    if isinstance(field, str):
        field = field.replace("\\", "/")
    return field        

class Network:

    #-----------------------------------------------------------
    def __init__(self, setup_script = None):
        self._SetupScript = setup_script


    #-----------------------------------------------------------
    def DefineParameters(self, connection, cursor, context):
        context.AddBool("graph_is_disjoint", "Network is disjoint", False)
        

    #-----------------------------------------------------------
    def Setup(self, context):
        context.LoadPage("Network.html")
        if self._SetupScript is not None:
            context.LoadScript(self._SetupScript)


    #-----------------------------------------------------------
    def SetSelection(self, connection, cursor, context):
        selected_nodes_event_ids = set(context.GetSelection(0))
        selected_links_event_ids = set(context.GetSelection(1))

        have_selected_nodes = len(selected_nodes_event_ids) != 0
        have_selected_links = len(selected_links_event_ids) != 0

        if have_selected_nodes or have_selected_links:
            where = ""
            if have_selected_nodes:
                node_event_ids = ", ".join([str(event_id) for event_id in selected_nodes_event_ids])
                where = "source_id IN ({node_event_ids}) OR target_id IN ({node_event_ids})".format(node_event_ids = node_event_ids)

            if have_selected_links:
                if have_selected_nodes:
                    where = where + " OR "
                link_event_ids = ", ".join([str(event_id) for event_id in selected_links_event_ids])
                text = " event_id IN ({link_event_ids})".format(link_event_ids = link_event_ids)
                where = where + text

            # find everything "reachable" from the selected nodes & links
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
                selected_links_event_ids.add(row[0])
                selected_nodes_event_ids.add(row[1])
                selected_nodes_event_ids.add(row[2])

        selection = dict(nodes = [node for node in selected_nodes_event_ids], links = [link for link in selected_links_event_ids])
        selection_json = json.dumps(selection)
        context.CallJavaScript("SetSelection", selection_json)


    #-----------------------------------------------------------
    def CreateChart(self, connection, cursor, context):
        node_fields = SqlColumnNames(cursor, "display", "main")
        cursor.execute("""
            SELECT
                *
            FROM
                main.display
            """)

        nodes = [dict(zip(node_fields, [_EscapeJsonField(field) for field in row])) for row in cursor]

        link_fields = SqlColumnNames(cursor, "display", "links")
        cursor.execute("""
            SELECT
                *
            FROM
                links.display
            WHERE
                source IN (SELECT event_id FROM main.display) AND
                target IN (SELECT event_id FROM main.display)
            """)

        links = [dict(zip(link_fields, [_EscapeJsonField(field) for field in row])) for row in cursor]

        options = dict(graph_is_disjoint = context.GetParameter("graph_is_disjoint", False))
        options_json = json.dumps(options)

        network = dict(nodes = nodes, links = links)
        data_json = json.dumps(network)
        context.CallJavaScript("CreateChart", data_json, options_json)

        self.SetSelection(connection, cursor, context)


    #-----------------------------------------------------------
    def Realise(self, name, connection, cursor, context):
        if context.DataChanged() or context.ParamatersChanged():
            self.CreateChart(connection, cursor, context)

        elif context.SelectionChanged():
            self.SetSelection(connection, cursor, context)

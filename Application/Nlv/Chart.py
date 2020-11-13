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

# Application imports
from Nlv.TangledTree import Tree


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
            data.append(dict(category = row[0], value = row[1], selected = selected, event_id = event_id))

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
                data.append(dict(category = row[0], value = value, selected = selected, event_id = event_id))

        other = sum - accum
        if other > 0:            
            data.append(dict(category = "Other", value = other, selected = selected, event_id = -1))

        # chart transition time in msec
        switch_time = 1000
        if len(selection) != 0:
            switch_time = 250

        data_json = json.dumps(data)
        context.CallJavaScript("CreateChart", self._ValueField, data_json, switch_time)



## NetworkCore #################################################

def _EscapeJsonField(field):
    # the JavaScript JSON decoder doesn't like quoted backslashes in string
    # values - even though that is correct. Workaround here for the time being.
    if isinstance(field, str):
        field = field.replace("\\", "/")
    return field        


class NetworkCore:

    #-----------------------------------------------------------
    def __init__(self, html_page, setup_script = None):
        self.HtmlPage = html_page
        self._SetupScript = setup_script


    #-----------------------------------------------------------
    def DefineParameters(self, connection, cursor, context):
        pass


    #-----------------------------------------------------------
    def Setup(self, context):
        context.LoadPage(self.HtmlPage)
        if self._SetupScript is not None:
            context.LoadScript(self._SetupScript)


    #-----------------------------------------------------------
    def MakeOptions(self, context):
        return "{}"


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
                where = "source IN ({node_event_ids}) OR target IN ({node_event_ids})".format(node_event_ids = node_event_ids)

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
                    source,
                    target
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
        context.CallJavaScript("SetSelection", selection_json, self.MakeOptions(context))


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

        data_json = self.NetworkToJson(nodes, links)
        context.CallJavaScript("CreateChart", data_json, self.MakeOptions(context))

        self.SetSelection(connection, cursor, context)



## Network #####################################################

class Network(NetworkCore):

    #-----------------------------------------------------------
    def __init__(self, setup_script = None):
        super().__init__("Network.html", setup_script)


    #-----------------------------------------------------------
    def DefineParameters(self, connection, cursor, context):
        context.AddBool("graph_is_disjoint", "Network is disjoint", False)
        context.AddBool("show_link_labels", "Show relationship names", False)
        

    #-----------------------------------------------------------
    def MakeOptions(self, context):
        options = dict(
            graph_is_disjoint = context.GetParameter("graph_is_disjoint", False),
            show_link_labels = context.GetParameter("show_link_labels", False)
        )
        return json.dumps(options)


    #-----------------------------------------------------------
    def NetworkToJson(self, nodes, links):
        return json.dumps(dict(nodes = nodes, links = links))


    #-----------------------------------------------------------
    def Realise(self, name, connection, cursor, context):
        structural_param_change = False
        display_param_change = False

        changed_parameter = context.ChangedParameterName()
        if changed_parameter is not None:
            if changed_parameter == "graph_is_disjoint":
                structural_param_change = True
            else:
                display_param_change = True

        if context.DataChanged() or structural_param_change:
            self.CreateChart(connection, cursor, context)

        elif context.SelectionChanged() or display_param_change:
            self.SetSelection(connection, cursor, context)



## TangledTree #################################################

class TangledTree(NetworkCore):

    #-----------------------------------------------------------
    def __init__(self, entity_name_field, setup_script = None):
        super().__init__("TangledTree.html", setup_script)
        self._EntityNameField = entity_name_field


    #-----------------------------------------------------------
    def NetworkToJson(self, nodes, links):
        tree = Tree()
        for node in nodes:
            tree.AddEntity(node[self._EntityNameField], node)

        for link in links:
            tree.AddRelationship(link)

        return tree.Extract()


    #-----------------------------------------------------------
    def Realise(self, name, connection, cursor, context):
        self.CreateChart(connection, cursor, context)



## TreeMap #####################################################

class TreeMap:

    #-----------------------------------------------------------
    def __init__(self, path_field, value_field):
        self._PathField = path_field
        self._ValueField = value_field


    #-----------------------------------------------------------
    def DefineParameters(self, connection, cursor, context):
        pass


    #-----------------------------------------------------------
    @classmethod
    def Setup(cls, context):
        context.LoadPage("TreeMap.html")


    #-----------------------------------------------------------
    def Realise(self, name, connection, cursor, context):
        cursor.execute("""
            SELECT
                {path},
                {value},
                event_id
            FROM
                display
            """.format(path = ReduceFieldName(self._PathField), value = ReduceFieldName(self._ValueField)))

        selection = context.GetSelection()

        root = dict(name = "Map", children = [], selected = False, event_id = 0)
        hierarchy = dict()
        hierarchy["R"] = root

        for row in cursor:
            path = row[0]
            name = path.split("/")[-1]

            event_id = row[2]
            selected = event_id in selection

            node = dict(name = name, children = [], value = row[1], selected = selected, event_id = event_id)

            hierarchy["R/" + path] = node

        for key_path in hierarchy.keys():
            dirs = key_path.split("/")[0:-1]
            if dirs:
                parent_path = "/".join(dirs)
                node = hierarchy[key_path]
                hierarchy[parent_path]["children"].append(node)

        # chart transition time in msec
        switch_time = 1000
        if len(selection) != 0:
            switch_time = 250

        data_json = json.dumps(root)
        context.CallJavaScript("CreateChart", data_json, switch_time)

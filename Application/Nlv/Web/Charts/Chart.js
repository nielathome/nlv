//
// Copyright (C) 2019-2020 Niel Clausen. All rights reserved.
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program. If not, see <https://www.gnu.org/licenses/>.
//

//----------------------------------------------------------
var g_node_id = 0;

function SetNodeId(node_id) {
    g_node_id = node_id;
}

var g_nodes_table_node_id = 0,
    g_links_table_node_id = 0;

function SetTableNodeIds(nodes_table_node_id, links_table_node_id) {
    g_nodes_table_node_id = nodes_table_node_id;
    g_links_table_node_id = links_table_node_id;
}

function CallPython(target_node_id, method, args_object) {
    args_json_text = JSON.stringify(args_object);
    args_encoded_text = btoa(args_json_text);
    cgi_text = "/" + target_node_id + "." + method + "?" + args_encoded_text;

    d3.json(cgi_text, function (error, results_json) {
        if (error)
            throw error;
    });
}


//----------------------------------------------------------
function OnResize() {
    DoCreateChart(0);
}

function SetupOnResize(){
    window.addEventListener("resize", OnResize);
}


//----------------------------------------------------------
const g_tip_transition_time = 200;
var g_tip_html_func = null;
var g_tip = null;

function OnTipShow(data) {
    g_tip
      .transition(g_tip_transition_time)
        .style("opacity", 1);

    d3.select(this)
      .transition(g_tip_transition_time)
        .style("opacity", 0.8);
}

function OnTipMove(data) {
    g_tip
        .html(g_tip_html_func(data))
        .style("left", (d3.event.pageX + 15) + "px")
        .style("top", (d3.event.pageY) + "px");
}

function OnTipHide(data) {
    g_tip
      .transition(g_tip_transition_time)
        .style("opacity", "0");

    d3.select(this)
      .transition(g_tip_transition_time)
        .style("stroke", "none")
        .style("opacity", 1);
}

function SetupTip(tip_html_func) {
    g_tip = d3.select("#graph")
        .append("div")
        .attr('class', 'tool-tip')
        .style("opacity", 0);

    g_tip_html_func = tip_html_func;
}
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
    ResetTip();
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
    const ref_transition = d3.transition("tip-show")
        .duration(g_tip_transition_time);

    g_tip
      .transition(ref_transition)
        .style("opacity", 1);

    d3.select(this)
      .transition(ref_transition)
        .style("opacity", 0.8);
}

function OnTipMove(data) {
    g_tip
        .html(g_tip_html_func(data));

    const window_pos = document.documentElement.getBoundingClientRect();
    const item_pos = this.getBoundingClientRect();
    const tip_pos = g_tip.node().getBoundingClientRect();

    var tip_left = item_pos.left + (item_pos.width - tip_pos.width) / 2;
    const tip_x_overflow = (tip_left + tip_pos.width) - window_pos.right;
    if (tip_x_overflow > 0) {
        tip_left -= tip_x_overflow;
    }
    else if (tip_left < 0) {
        tip_left = 0;
    }

    var tip_top = item_pos.top + (item_pos.height - tip_pos.height) / 2;
    const tip_y_overflow = (tip_top + tip_pos.height) - window_pos.bottom;
    if (tip_y_overflow > 0) {
        tip_top -= tip_y_overflow;
    }
    else if (tip_top < 0) {
        tip_top = 0;
    }

    const ref_transition = d3.transition("tip-move")
        .duration(g_tip_transition_time)
        .ease(d3.easeLinear);

    g_tip
      .transition(ref_transition)
        .style("left", tip_left + "px")
        .style("top", tip_top + "px");
}

function OnTipHide(data) {
    const ref_transition = d3.transition("tip-show")
        .duration(g_tip_transition_time);

    g_tip
      .transition(ref_transition)
        .style("opacity", "0");

    d3.select(this)
      .transition(ref_transition)
        .style("opacity", 1);
}

function ResetTip() {
    if (g_tip !== null) {
        g_tip
            .style("opacity", 0)
            .style("left", "0px")
            .style("top", "0px");
    }
}

function SetupTip(tip_html_func) {
    g_tip = d3.select("#graph")
      .append("div")
        .attr('class', 'tool-tip');

    ResetTip();

    g_tip_html_func = tip_html_func;
}
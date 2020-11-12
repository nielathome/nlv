//
// Copyright (C) 2017-2018 Niel Clausen. All rights reserved.
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
function OnResize() {
    DoCreateChart(0);
}

function SetupOnResize(){
    window.addEventListener("resize", OnResize);
}


//----------------------------------------------------------
const g_tip_transition_time = 200;
var g_tip_html_func = null;

var g_tooltip = d3.select("#graph")
  .append("div")
    .attr('class', 'tool-tip')
    .style("opacity", 0);

function OnTipShow(data) {
    g_tooltip
      .transition(g_tip_transition_time)
        .style("opacity", 1);

    d3.select(this)
      .transition(g_tip_transition_time)
        .style("stroke", "black")
        .style("opacity", 0.8);
}

function OnTipMove(data) {
    g_tooltip
        .html(g_tip_html_func(data))
        .style("left", (d3.event.pageX + 15) + "px")
        .style("top", (d3.event.pageY) + "px");
}

function OnTipHide(data) {
    g_tooltip
      .transition(g_tip_transition_time)
        .style("opacity", "0");

    d3.select(this)
      .transition(g_tip_transition_time)
        .style("stroke", "none")
        .style("opacity", 1);
}

function SetupTip(tip_html_func) {
    g_tip_html_func = tip_html_func;
}
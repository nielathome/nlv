//
// Copyright (C) 2020 Niel Clausen. All rights reserved.
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

// global data
var g_data = null;

// append the svg object to the body of the page
var g_svg = d3.select("#graph")
  .append("svg")
    .attr("width", "100%")
    .attr("height", "100%");

var g_treemap = g_svg.append("g");

var g_element_colour = null;
var g_number_formatter = null;


//----------------------------------------------------------
var g_uid_count = 0;

function Uid(name) {
    return "O-" + name + "-" + g_uid_count++;
}


//----------------------------------------------------------
function EnterLeaf(leaf) {
    leaf
      .append("rect")
        .attr("class", "leaf")
        .attr("id", function (node) {
            return node.leafUid = Uid("leaf");
        });

    leaf
      .append("clipPath")
        .attr("id", function (node) {
            return node.clipUid = Uid("clip");
        })
      .append("use")
        .attr("xlink:href", function (node) {
            return " #" + node.leafUid;
        });

    leaf
      .append("text")
        .attr("class", "label")
        .attr("clip-path", function (node) {
            return "url(#" + node.clipUid + ")";
        })
}


function UpdateLeaf(leaf) {
    leaf
        .attr("transform", function (node) {
            return "translate(" + node.x0 + ", " + node.y0 + ")";
         });

    leaf
      .select("rect")
        .attr("fill", function (node) {
            return g_element_colour(node.value);
        })
        .attr("width", function (node) {
            return node.x1 - node.x0;
        })
        .attr("height", function (node) {
            return node.y1 - node.y0;
        });

    leaf
      .select("text")
      .selectAll("tspan")
        .data(function (node) {
            return [node.data.name, g_number_formatter(node.value)];
        })
        .join("tspan")
        .attr("x", 3)
        .attr("y", function (data, index) {
            return (1 + index) * 1.1 + "em";
        })
        .attr("fill-opacity", function (data, index) {
            return index > 0 ? 0.7 : 1.0;
        })
        .text(function (data) {
            return data;
        });
}


function DoCreateChart(switch_time) {
    const min_window = 300, margin = 10;
    const window_width = Math.max(min_window, document.documentElement.clientWidth);
    const window_height = Math.max(min_window, document.documentElement.clientHeight);

    const hierarchy = d3.hierarchy(g_data)
        .sum(function (data) {
            return data.value;
        })
        .sort(function (a, b) {
            return b.value - a.value;
        });

    const treemap_layout = d3.treemap()
        .size([window_width - 2 * margin, window_height - 2 * margin]);

    root_node = treemap_layout(hierarchy);

    const max_value = root_node.leaves().reduce(function (max, node) {
        return Math.max(max, node.value);
    }, 0);
    g_element_colour = d3.scaleSequential([0, max_value], d3.interpolateMagma);
    g_number_formatter = d3.format(",d");

    g_treemap
        .attr("transform", "translate(" + margin + ", " + margin + ")")
      .selectAll("g")
      .data(root_node.leaves())
      .join(
        function (enter) {
            return enter
              .append("g")
                .call(EnterLeaf)
        }
      )
        .call(UpdateLeaf)
        .on("mouseover", OnTipShow)
        .on("mousemove", OnTipMove)
        .on("mouseleave", OnTipHide);
}


//----------------------------------------------------------

SetupOnResize();
SetupTip(function (data) {
    const path = data.ancestors().reverse().map(function (n) {
        return n.data.name;
    }).join("/");

    const value = g_number_formatter(data.value);

    return "<strong>" + path + ":</strong> <span style='color:white'>" + value + "</span>";
});

function CreateChart(data_json, options_json) {
    g_data = JSON.parse(data_json);
    g_options = JSON.parse(options_json);

    DoCreateChart(0);
}


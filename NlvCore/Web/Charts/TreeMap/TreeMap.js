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

var g_treemap = g_svg
  .append("g");

var g_leaf_colour = null;
var g_container_colour = null;
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
        .attr("transform", function (d) {
            return "translate(" + d.x0 + ", " + d.y0 + ")";
         });

    leaf
      .select("rect")
        .attr("fill", function (d) {
            c = d3.rgb(d.children ? g_container_colour(d.value) : g_leaf_colour(d.value));

            const lighten = 1;
            c.r = (255 + (lighten * c.r)) / 2
            c.g = (255 + (lighten * c.g)) / 2
            c.b = (255 + (lighten * c.b)) / 2
            return c.toString();
        })
        .attr("width", function (d) {
            return d.x1 - d.x0;
        })
        .attr("height", function (d) {
            return d.y1 - d.y0;
        });

    leaf
      .select("text")
      .selectAll("tspan")
      .data(function (d) {
          return [d.data.name, g_number_formatter(d.value)];
      })
      .join("tspan")
        .attr("fill-opacity", function (data, index) {
            return index > 0 ? 0.7 : 1.0;
        })
        .text(function (data) {
            return data;
        });

    leaf
      .filter(function (d) {
          return d.children;
      })
      .selectAll("tspan")
        .attr("dx", 3)
        .attr("y", "1.1em");

    leaf
      .filter(function (d) {
          return ! d.children;
      })
      .selectAll("tspan")
        .attr("x", 3)
        .attr("y", function (data, index) {
            return (1 + index) * 1.2 + "em";
        });
}


function DoCreateChart(switch_time) {
    const min_window = 300;
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
        .size([window_width, window_height])
        .paddingOuter(5)
        .paddingTop(19)
        .round(true);

    var root_node = treemap_layout(hierarchy);

    const max_value = root_node.leaves().reduce(function (max, node) {
        return Math.max(max, node.value);
    }, 0);
    g_leaf_colour = d3.scaleSequential([0, max_value], d3.interpolateMagma);
    g_container_colour = d3.scaleSequential([0, root_node.value], d3.interpolateMagma);
    g_number_formatter = d3.format(",d");

    g_treemap
      .selectAll("g")
      .data(root_node.descendants())
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


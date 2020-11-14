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
function OnClick(d) {
    CallPython(g_node_id, "OnChartSelection", { event_id: d.data.event_id, ctrl_key: d3.event.ctrlKey });
}


//----------------------------------------------------------

// global data
var g_data = null;
var g_title_text = null;

// append the svg object to the body of the page
var g_svg = d3.select("#graph")
  .append("svg")
    .attr("width", "100%")
    .attr("height", "100%");

var g_chart = g_svg.append("g");

var g_title = g_chart
  .append("text")
    .attr("class", "title");


//----------------------------------------------------------
function DoCreateChart(switch_time) {
    if (g_data == null)
        return;

    // set the dimensions and margins of the graph
    var margin = 30, min_window = 300;
    var window_width = Math.max(min_window, document.documentElement.clientWidth);
    var window_height = Math.max(min_window, document.documentElement.clientHeight);
    var radius = (Math.min(window_width, window_height) - (2 * margin)) / 2;

    g_chart
        .attr("transform", "translate(" + window_width / 2 + "," + window_height / 2 + ")");

    g_title.text(g_title_text);
    var title_bbox = g_title.node().getBBox();
    g_title
        .attr("x", -title_bbox.width / 2)
        .attr("y", title_bbox.height / 2);

    // Compute the angle data for each slice in the pie
    var pie_generator = d3.pie()
        .startAngle(-0.75)
        .sort(null) // Do not sort by size
        .value(function (d) {
            return d.value;
        });

    var slice_data = pie_generator(g_data);

    // The "slice" generator
    var slice_generator = d3.arc()
        .innerRadius(radius * 0.5)
        .outerRadius(radius * 0.8);

    // Build the pie chart: each part of the pie is a path built using the arc function.
    const ref_transition = d3.transition()
        .duration(switch_time);

    g_chart.selectAll(".slice")
      .data(slice_data, function (d) {
          return d.data.category;
      })
      .join(
        function (enter) {
            return enter.append("path")
                .style("opacity", 0);
        },
        function (update) {
            return update;
        },
        function (exit) {
            return exit
                .call(function (exit) {
                   exit.transition(ref_transition)
                       .style("opacity", 0)
                       .on('end', function () {
                           d3.select(this).remove();
                       })
               })
        }
      )
        .on("click", OnClick)
        .on("mouseover", OnTipShow)
        .on("mousemove", OnTipMove)
        .on("mouseleave", OnTipHide)
        .attr("class", "slice")
      .transition(ref_transition)
        .style("opacity", 1)
        .attr('d', slice_generator)
        .attr('fill', function (d) {
            return d.data.selected ? "DarkOrange" : "DarkSlateBlue";
        })

    // Arc for label line elbows
    var elbow_generator = d3.arc()
        .innerRadius(radius * 0.9)
        .outerRadius(radius * 0.9);

    // Add the polylines between chart and labels
    g_chart.selectAll('.line')
      .data(slice_data, function (d) {
          return d.data.category;
      })
      .join(
        function (enter) {
            return enter.append("polyline")
                .style("opacity", 0);
        },
        function (update) {
            return update;
        },
        function (exit) {
            return exit
                .call(function (exit) {
                   exit.transition(ref_transition)
                       .style("opacity", 0)
                       .on('end', function () {
                           d3.select(this).remove();
                       })
               })
        }
      )
        .attr("class", "line")
      .transition(ref_transition)
        .style("opacity", 1)
        .attr('points', function (d) {
            var slice_centre = slice_generator.centroid(d);
            var elbow = elbow_generator.centroid(d);
            var text = elbow_generator.centroid(d);

            // we need the angle to see if the X position will be at the extreme right or extreme left
            var midangle = d.startAngle + (d.endAngle - d.startAngle) / 2;
            text[0] = radius * 0.95 * (midangle < Math.PI ? 1 : -1);
            return [slice_centre, elbow, text];
        });

    // Add the labels
    g_chart.selectAll('.label')
      .data(slice_data, function (d) {
          return d.data.category;
      })
      .join(
        function (enter) {
            return enter.append("text")
                .style("opacity", 0);
        },
        function (update) {
            return update;
        },
        function (exit) {
            return exit
               .call(function (exit) {
                   return exit.transition(ref_transition)
                       .style("opacity", 0)
                       .on('end', function () {
                           d3.select(this).remove();
                       })
               })
        }
      )
        .attr("class", "label")
        .text(function (d) {
            return d.data.category;
        })
        .attr('transform', function (d) {
            var pos = elbow_generator.centroid(d);
            var midangle = d.startAngle + (d.endAngle - d.startAngle) / 2;
            pos[0] = radius * 0.99 * (midangle < Math.PI ? 1 : -1);
            return 'translate(' + pos + ')';
        })
        .style('text-anchor', function (d) {
            var midangle = d.startAngle + (d.endAngle - d.startAngle) / 2;
            return (midangle < Math.PI ? 'start' : 'end')
        })
    .transition(ref_transition)
      .style("opacity", 1);
}


//----------------------------------------------------------

SetupOnResize();
SetupTip(function (data) {
    return "<strong>" + data.data.category + "</strong> <span style='color:white'>" + data.value + "</span>";
});

function CreateChart(title, data_json, switch_time) {
    g_data = JSON.parse(data_json);
    g_title_text = title;
    DoCreateChart(switch_time);
}



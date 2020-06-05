//
// Copyright (C) Niel Clausen 2020. All rights reserved.
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

// Customise the network configuration
var f_nodeScale = null;
function ProgramConfig(data) {
    // map node weights to a node size
    const minNodeWeight = d3.min(data.nodes, function (node_data) {
        return node_data.size;
    });

    const maxNodeWeight = d3.max(data.nodes, function (node_data) {
        return node_data.size;
    });

    f_nodeScale = d3.scaleLinear()
        .domain([minNodeWeight, maxNodeWeight])
        .range([4, 20])
        .clamp(true);

    // base "class"
    Config.call(this, data);
}

ProgramConfig.prototype = Object.create(Config.prototype);

ProgramConfig.prototype.constructor = ProgramConfig;

var f_nodeColourScale = d3.scaleOrdinal(d3.schemeCategory10);
ProgramConfig.prototype.CreateNode = function (display_nodes) {
    display_nodes
      .append("text")
        .attr("class", "node-text")
        .attr("text-anchor", "middle")
        .attr("dominant-baseline", "middle")
        .text(function (node_data) {
            return node_data.title;
        })
        .each(function (node_data) {
            node_data.text_bbox = d3.select(this).node().getBBox();
        });

    var pad = 5;
    display_nodes
      .insert("rect", ":first-child")
        .attr("rx", 5)
        .attr("ry", 5)
        .attr("x", function (node_data) {
            return node_data.text_bbox.x - pad;
        })
        .attr("y", function (node_data) {
            return node_data.text_bbox.y - pad;
        })
        .attr("width", function (node_data) {
            return node_data.text_bbox.width + (2 * pad);
        })
        .attr("height", function (node_data) {
            return node_data.text_bbox.height + (2 * pad);
        })
        .attr("style", "stroke: white; stroke-width: 1.5px;")
        .attr("fill", function (node_data) {
            return f_nodeColourScale(node_data.type)
        });
}

ProgramConfig.prototype.StyleNode = function (display_nodes) {
    display_nodes
        .attr("opacity", function (node_data) {
            return IsNodeSelected(node_data) ? 1.0 : 0.3;
        });

    display_nodes
        .attr("opacity", function (node_data) {
            return IsNodeSelected(node_data) ? 1.0 : 0.3;
        });
}

SetConfigConstructor(ProgramConfig);

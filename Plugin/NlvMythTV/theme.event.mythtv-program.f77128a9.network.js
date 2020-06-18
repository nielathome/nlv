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
function ProgramConfig(data, svg) {
    // base "class"
    Config.call(this, data, svg);

    // map node weights to node "padding"
    const minNodeWeight = d3.min(data.nodes, function (node_data) {
        return node_data.size;
    });

    const maxNodeWeight = d3.max(data.nodes, function (node_data) {
        return node_data.size;
    });

    f_nodeScale = d3.scaleLinear()
        .domain([minNodeWeight, maxNodeWeight])
        .range([1, 5])
        .clamp(true);

    // arrow head
    svg.append('defs').selectAll('marker')
        .data(['end'])
      .enter()
      .append('marker')
        .attr('id', String)
        .attr('viewBox', '0 -5 10 10')
        .attr('refX', 10)
        .attr('refY', 0)
        .attr('markerWidth', 6)
        .attr('markerHeight', 6)
        .attr('orient', 'auto')
        .attr("style", "fill: #666; stroke: #666; stroke-width: 1.5px;")
      .append('path')
        .attr('d', 'M0,-5L10,0L0,5');
}

ProgramConfig.prototype = Object.create(Config.prototype);

ProgramConfig.prototype.constructor = ProgramConfig;

var f_nodeColourScale = d3.scaleOrdinal(d3.schemeCategory10);
ProgramConfig.prototype.CreateNode = function (display_nodes) {
    function calc_pad(node_data) {
        return f_nodeScale(node_data.size) + 4;
    }

    function calc_colour(node_data, darken) {
        return d3.color(f_nodeColourScale(node_data.type)).darker(darken).toString();
    }

    display_nodes
      .append("text")
        .attr("class", "node-text")
        .attr("text-anchor", "middle")
        .attr("dominant-baseline", "middle")
        .text(function (node_data) {
            return node_data.title;
        })
        .each(function (node_data) {
            node_data.text_extent = d3.select(this).node().getBBox();
        });

    display_nodes
      .insert("rect", ":first-child")
        .attr("rx", 5)
        .attr("ry", 5)
        .attr("x", function (node_data) {
            return node_data.text_extent.x - calc_pad(node_data);
        })
        .attr("y", function (node_data) {
            return node_data.text_extent.y - calc_pad(node_data);
        })
        .attr("width", function (node_data) {
            return node_data.text_extent.width + (2 * calc_pad(node_data));
        })
        .attr("height", function (node_data) {
            return node_data.text_extent.height + (2 * calc_pad(node_data));
        })
        .style("fill", function (node_data) {
            return calc_colour(node_data, -0.1);
        })
        .style("stroke", function (node_data) {
            return calc_colour(node_data, 0.7);
        })
        .style("stroke-width", "2px")
        .each(function (node_data) {
            node_data.node_extent = d3.select(this).node().getBBox();
        });
}

ProgramConfig.prototype.StyleLink = function (display_links) {
    // base "class"
    Config.prototype.StyleLink.call(this, display_links);

    display_links
        .attr("style", "stroke: #666; marker-end: url(#end);");
}

ProgramConfig.prototype.StyleSimulation = function (simulation) {
    simulation.force("link")
        .distance(100);

    simulation
        .force("collision", d3.forceCollide()
            .radius(function (node_data) {
                var w = node_data.text_extent.width / 2;
                var h = node_data.text_extent.height / 2;
                return 1.5 * Math.sqrt(w * w + h * h);
            })
            .iterations(1)
        );
}

SetConfigConstructor(ProgramConfig);

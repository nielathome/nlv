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
    const minNodeWeight = d3.min(data.nodes, function (node) {
        return node.size;
    });

    const maxNodeWeight = d3.max(data.nodes, function (node) {
        return node.size;
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
ProgramConfig.prototype.StyleNode = function (selection) {
    selection
        .attr("r", function (node) {
            return f_nodeScale(node.size);
        })
        .attr("fill", function (node) {
            return f_nodeColourScale(node.type)
        })
        .attr("opacity", function (node) {
            return IsNodeSelected(node) ? 1.0 : 0.3;
        })
        .attr("style", "stroke: white; stroke-width: 1.5px;")
}

ProgramConfig.prototype.StyleLabel = function (selection) {
    selection
        .text(function (node) {
            return node.title;
        })
        .attr("x", function (node) {
            return f_nodeScale(node.size) + 3;
        })
        .attr("opacity", function (node) {
            return IsNodeSelected(node) ? 1.0 : 0.3;
        });
}

SetConfigConstructor(ProgramConfig);

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
// <script>
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
            .attr("style", "stroke-width: 1.5px;")
          .append('path')
            .attr('d', 'M0,-5L10,0L0,5');
    }

    ProgramConfig.prototype = Object.create(Config.prototype);

    ProgramConfig.prototype.constructor = ProgramConfig;

    ProgramConfig.prototype.GetNodeId = function (node_data) {
        return node_data.event_id;
    }

    var f_colourScale = d3.scaleOrdinal(d3.schemeCategory10);
    ProgramConfig.prototype.EnterNode = function (display_node) {
        display_node
          .append("text");

        display_node
          .insert("rect", ":first-child");
    }

    ProgramConfig.prototype.UpdateNode = function (display_node) {
        function calc_pad(node_data) {
            return f_nodeScale(node_data.size) + 4;
        }

        function calc_node_colour(node_data, darken) {
            return d3.color(f_colourScale(node_data.type)).darker(darken).toString();
        }

        display_node
          .select("text")
            .attr("class", "node-text")
            .attr("text-anchor", "middle")
            .attr("dominant-baseline", "middle")
            .text(function (node_data) {
                return node_data.title;
            })
            .each(function (node_data) {
                node_data.text_extent = d3.select(this).node().getBBox();
            });

        display_node
          .select("rect")
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
                return calc_node_colour(node_data, -0.1);
            })
            .style("stroke", function (node_data) {
                return calc_node_colour(node_data, 0.7);
            })
            .style("stroke-width", "2px")
            .each(function (node_data) {
                node_data.node_extent = d3.select(this).node().getBBox();
            });
    }

    ProgramConfig.prototype.EnterLink = function (display_link) {
        display_link
          .append("line");

        label = display_link
            .append("g");

        label
            .append("text");

        label
            .insert("rect", ":first-child");
    }

    ProgramConfig.prototype.UpdateLink = function (display_link) {
        label = display_link.select("g")

        label
          .select("text")
            .attr("class", "link-text")
            .text(function (link_data) {
                return link_data.label;
            })
            .each(function (link_data) {
                link_data.label_extent = d3.select(this).node().getBBox();
            })
            .attr("text-anchor", "middle")
            .attr("y", function (link_data) {
                return link_data.label_extent.height / 2;
            });

        label
          .select("rect", ":first-child")
            .attr("x", function (link_data) {
                return - link_data.label_extent.width / 2;
            })
            .attr("y", function (link_data) {
                return - link_data.label_extent.height / 2;
            })
            .attr("width", function (link_data) {
                return link_data.label_extent.width;
            })
            .attr("height", function (link_data) {
                return link_data.label_extent.height;
            })
            .style("stroke", "white")
            .style("fill", "white");
    }

    ProgramConfig.prototype.StyleLink = function (display_link) {
        function calc_link_colour(link_data, darken) {
            if (link_data.type) {
                return d3.color(f_colourScale(link_data.type)).darker(darken).toString();
            }
            else {
                return "#666";
            }
        }

        display_link
          .select("line")
            .attr("style", function (link_data) {
                colour = calc_link_colour(link_data, 0.7);
                return "marker-end: url(#end); stroke: " + colour + "; fill: " + colour + ";"
            });

        Config.prototype.StyleLink.call(this, display_link);
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
// </script>

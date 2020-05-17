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
function ProgramConfig() {}

ProgramConfig.prototype = Object.create(Config.prototype);
ProgramConfig.prototype.constructor = ProgramConfig;

ProgramConfig.prototype.GetNodeWeight = function (node) {
    return node.size;
}

ProgramConfig.prototype.GetNodeSizeRange = function () {
    return [4, 20];
}

var _NodeColourScale = d3.scaleOrdinal(d3.schemeCategory10);
ProgramConfig.prototype.GetNodeFillColour = function (node) {
    return _NodeColourScale(node.type)
}

SetConfig(new ProgramConfig());

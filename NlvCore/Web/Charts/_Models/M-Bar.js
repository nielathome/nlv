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

const data1 = '[{"category":"P=[0.08]","value":185,"selected":false},{"category":"P=[0.09]","value":526,"selected":false},{"category":"P=[0.11]","value":5,"selected":false},{"category":"P=[0.12]","value":2,"selected":false},{"category":"P=[0.13]","value":1,"selected":false},{"category":"P=[0.14]","value":21,"selected":false},{"category":"P=[0.15]","value":829,"selected":false},{"category":"P=[0.16]","value":1151,"selected":false},{"category":"P=[0.17]","value":799,"selected":false},{"category":"P=[0.18]","value":267,"selected":false},{"category":"P=[0.19]","value":74,"selected":false},{"category":"P=[0.1]","value":26,"selected":false},{"category":"P=[0.21]","value":24,"selected":false},{"category":"P=[0.22]","value":21,"selected":false},{"category":"P=[0.23]","value":15,"selected":false},{"category":"P=[0.24]","value":16,"selected":false},{"category":"P=[0.25]","value":12,"selected":false},{"category":"P=[0.26]","value":6,"selected":false},{"category":"P=[0.27]","value":12,"selected":false},{"category":"P=[0.28]","value":4,"selected":false},{"category":"P=[0.29]","value":2,"selected":false},{"category":"P=[0.2]","value":30,"selected":false},{"category":"P=[0.31]","value":2,"selected":false},{"category":"P=[0.32]","value":4,"selected":false},{"category":"P=[0.33]","value":1,"selected":false},{"category":"P=[0.34]","value":6,"selected":false},{"category":"P=[0.35]","value":4,"selected":false},{"category":"P=[0.36]","value":2,"selected":false},{"category":"P=[0.37]","value":2,"selected":false},{"category":"P=[0.38]","value":2,"selected":false},{"category":"P=[0.39]","value":2,"selected":false},{"category":"P=[0.3]","value":4,"selected":false},{"category":"P=[0.42]","value":1,"selected":false},{"category":"P=[0.43]","value":2,"selected":false},{"category":"P=[0.45]","value":1,"selected":false},{"category":"P=[0.46]","value":2,"selected":false},{"category":"P=[0.48]","value":1,"selected":false},{"category":"P=[0.4]","value":1,"selected":false},{"category":"P=[0.51]","value":1,"selected":false},{"category":"P=[0.52]","value":1,"selected":false},{"category":"P=[0.54]","value":2,"selected":false},{"category":"P=[0.56]","value":3,"selected":false},{"category":"P=[0.57]","value":3,"selected":false},{"category":"P=[0.59]","value":1,"selected":false},{"category":"P=[0.61]","value":1,"selected":false},{"category":"P=[0.65]","value":2,"selected":false},{"category":"P=[0.68]","value":1,"selected":false},{"category":"P=[0.71]","value":1,"selected":false},{"category":"P=[1.16]","value":1,"selected":false},{"category":"P=[1.55]","value":1,"selected":false},{"category":"expire","value":1050,"selected":false}]';
const data2 = '[{"category":"P=[0.08]","value":185,"selected":false},{"category":"P=[0.09]","value":526,"selected":false},{"category":"P=[0.14]","value":21,"selected":false},{"category":"P=[0.15]","value":829,"selected":false},{"category":"P=[0.16]","value":1151,"selected":false},{"category":"P=[0.17]","value":799,"selected":false},{"category":"P=[0.18]","value":267,"selected":false},{"category":"P=[0.19]","value":74,"selected":false},{"category":"P=[0.1]","value":26,"selected":false},{"category":"P=[0.21]","value":24,"selected":false},{"category":"P=[0.22]","value":21,"selected":false},{"category":"P=[0.23]","value":15,"selected":false},{"category":"P=[0.24]","value":16,"selected":false},{"category":"P=[0.25]","value":12,"selected":false},{"category":"P=[0.26]","value":6,"selected":false},{"category":"P=[0.27]","value":12,"selected":false},{"category":"P=[0.2]","value":30,"selected":false},{"category":"P=[0.34]","value":6,"selected":false}]';

function Update(json_text) {
    CreateChart("Title", "X label", "Y label", json_text, 1000);
}

Update(data1);
Update(data2);
                        
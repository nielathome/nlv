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

const data1 = '[{"category": "expire", "value": 129722, "selected": false}, {"category": "Other", "value": 4774, "selected": false}]';
const data2 = '[{"category": "P=[0.16]", "value": 1360, "selected": false}, {"category": "P=[0.17]", "value": 978, "selected": false}, {"category": "P=[0.15]", "value": 932, "selected": false}, {"category": "P=[0.09]", "value": 512, "selected": false}, {"category": "P=[0.18]", "value": 336, "selected": false}, {"category": "P=[0.08]", "value": 185, "selected": false}, {"category": "P=[0.19]", "value": 101, "selected": false}, {"category": "P=[0.22]", "value": 36, "selected": false}, {"category": "Other", "value": 218, "selected": false}]';

function Update(json_text) {
    CreateChart("Title", json_text, 1000);
}

Update(data1);
Update(data2);

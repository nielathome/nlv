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

function Update() {
    const data = " \
        { \
            \"bundles\": [ \
                { \
                    \"id\": \"Channel-2001-CardID-1\", \
                    \"links\": [ \
                        { \
                            \"cx\": 292, \
                            \"cy\": 146, \
                            \"id\": \"Channel-2001 -> Casualty\", \
                            \"px\": 30, \
                            \"py\": 30, \
                            \"x\": 264 \
                        }, \
                        { \
                            \"cx\": 292, \
                            \"cy\": 190, \
                            \"id\": \"Channel-2001 -> MasterChef\", \
                            \"px\": 30, \
                            \"py\": 30, \
                            \"x\": 264 \
                        }, \
                        { \
                            \"cx\": 292, \
                            \"cy\": 146, \
                            \"id\": \"CardID-1 -> Casualty\", \
                            \"px\": 30, \
                            \"py\": 56, \
                            \"x\": 264 \
                        }, \
                        { \
                            \"cx\": 292, \
                            \"cy\": 190, \
                            \"id\": \"CardID-1 -> MasterChef\", \
                            \"px\": 30, \
                            \"py\": 56, \
                            \"x\": 264 \
                        } \
                    ] \
                }, \
                { \
                    \"id\": \"Channel-2001-CardID-1-CardID-7\", \
                    \"links\": [ \
                        { \
                            \"cx\": 292, \
                            \"cy\": 168, \
                            \"id\": \"Channel-2001 -> EastEnders\", \
                            \"px\": 30, \
                            \"py\": 34, \
                            \"x\": 250 \
                        }, \
                        { \
                            \"cx\": 292, \
                            \"cy\": 168, \
                            \"id\": \"CardID-1 -> EastEnders\", \
                            \"px\": 30, \
                            \"py\": 60, \
                            \"x\": 250 \
                        }, \
                        { \
                            \"cx\": 292, \
                            \"cy\": 168, \
                            \"id\": \"CardID-7 -> EastEnders\", \
                            \"px\": 30, \
                            \"py\": 98, \
                            \"x\": 250 \
                        } \
                    ] \
                }, \
                { \
                    \"id\": \"Channel-2002-CardID-1\", \
                    \"links\": [ \
                        { \
                            \"cx\": 292, \
                            \"cy\": 300, \
                            \"id\": \"Channel-2002 -> Top Gear\", \
                            \"px\": 30, \
                            \"py\": 120, \
                            \"x\": 236 \
                        }, \
                        { \
                            \"cx\": 292, \
                            \"cy\": 300, \
                            \"id\": \"CardID-1 -> Top Gear\", \
                            \"px\": 30, \
                            \"py\": 64, \
                            \"x\": 236 \
                        } \
                    ] \
                }, \
                { \
                    \"id\": \"Channel-2003-CardID-1\", \
                    \"links\": [ \
                        { \
                            \"cx\": 292, \
                            \"cy\": 234, \
                            \"id\": \"Channel-2003 -> Nightly Show with Gordon Ramsay\", \
                            \"px\": 30, \
                            \"py\": 142, \
                            \"x\": 222 \
                        }, \
                        { \
                            \"cx\": 292, \
                            \"cy\": 234, \
                            \"id\": \"CardID-1 -> Nightly Show with Gordon Ramsay\", \
                            \"px\": 30, \
                            \"py\": 68, \
                            \"x\": 222 \
                        } \
                    ] \
                }, \
                { \
                    \"id\": \"Channel-2005-CardID-1\", \
                    \"links\": [ \
                        { \
                            \"cx\": 292, \
                            \"cy\": 212, \
                            \"id\": \"Channel-2005 -> Neighbours\", \
                            \"px\": 30, \
                            \"py\": 164, \
                            \"x\": 208 \
                        }, \
                        { \
                            \"cx\": 292, \
                            \"cy\": 278, \
                            \"id\": \"Channel-2005 -> The Gadget Show\", \
                            \"px\": 30, \
                            \"py\": 164, \
                            \"x\": 208 \
                        }, \
                        { \
                            \"cx\": 292, \
                            \"cy\": 212, \
                            \"id\": \"CardID-1 -> Neighbours\", \
                            \"px\": 30, \
                            \"py\": 72, \
                            \"x\": 208 \
                        }, \
                        { \
                            \"cx\": 292, \
                            \"cy\": 278, \
                            \"id\": \"CardID-1 -> The Gadget Show\", \
                            \"px\": 30, \
                            \"py\": 72, \
                            \"x\": 208 \
                        } \
                    ] \
                }, \
                { \
                    \"id\": \"Channel-2011-CardID-1\", \
                    \"links\": [ \
                        { \
                            \"cx\": 292, \
                            \"cy\": 256, \
                            \"id\": \"Channel-2011 -> Snake Boss\", \
                            \"px\": 30, \
                            \"py\": 186, \
                            \"x\": 194 \
                        }, \
                        { \
                            \"cx\": 292, \
                            \"cy\": 256, \
                            \"id\": \"CardID-1 -> Snake Boss\", \
                            \"px\": 30, \
                            \"py\": 76, \
                            \"x\": 194 \
                        } \
                    ] \
                } \
            ], \
            \"config\": { \
                \"BallRadius\": 4, \
                \"Border\": 30, \
                \"BundleWidth\": 14, \
                \"Height\": 330, \
                \"LinkRadius\": 16, \
                \"MinLevelOffset\": 48, \
                \"NodeSpacing\": 22, \
                \"NodeWidth\": 150, \
                \"OutboundBundleSpacing\": 4, \
                \"TextOffsetX\": 2, \
                \"TextOffsetY\": 4, \
                \"Width\": 472 \
            }, \
            \"nodes\": [ \
                { \
                    \"bundle_height\": 4, \
                    \"event_id\": 14, \
                    \"size\": 10, \
                    \"title\": \"Channel-2001\", \
                    \"type\": \"Channel\", \
                    \"x\": 30, \
                    \"y\": 30 \
                }, \
                { \
                    \"bundle_height\": 20, \
                    \"event_id\": 23, \
                    \"size\": 28, \
                    \"title\": \"CardID-1\", \
                    \"type\": \"CardID\", \
                    \"x\": 30, \
                    \"y\": 56 \
                }, \
                { \
                    \"bundle_height\": 0, \
                    \"event_id\": 25, \
                    \"size\": 2, \
                    \"title\": \"CardID-7\", \
                    \"type\": \"CardID\", \
                    \"x\": 30, \
                    \"y\": 98 \
                }, \
                { \
                    \"bundle_height\": 0, \
                    \"event_id\": 15, \
                    \"size\": 2, \
                    \"title\": \"Channel-2002\", \
                    \"type\": \"Channel\", \
                    \"x\": 30, \
                    \"y\": 120 \
                }, \
                { \
                    \"bundle_height\": 0, \
                    \"event_id\": 16, \
                    \"size\": 4, \
                    \"title\": \"Channel-2003\", \
                    \"type\": \"Channel\", \
                    \"x\": 30, \
                    \"y\": 142 \
                }, \
                { \
                    \"bundle_height\": 0, \
                    \"event_id\": 18, \
                    \"size\": 9, \
                    \"title\": \"Channel-2005\", \
                    \"type\": \"Channel\", \
                    \"x\": 30, \
                    \"y\": 164 \
                }, \
                { \
                    \"bundle_height\": 0, \
                    \"event_id\": 20, \
                    \"size\": 2, \
                    \"title\": \"Channel-2011\", \
                    \"type\": \"Channel\", \
                    \"x\": 30, \
                    \"y\": 186 \
                }, \
                { \
                    \"bundle_height\": 0, \
                    \"event_id\": 1, \
                    \"size\": 2, \
                    \"title\": \"Casualty\", \
                    \"type\": \"Program\", \
                    \"x\": 292, \
                    \"y\": 146 \
                }, \
                { \
                    \"bundle_height\": 0, \
                    \"event_id\": 4, \
                    \"size\": 4, \
                    \"title\": \"EastEnders\", \
                    \"type\": \"Program\", \
                    \"x\": 292, \
                    \"y\": 168 \
                }, \
                { \
                    \"bundle_height\": 0, \
                    \"event_id\": 7, \
                    \"size\": 3, \
                    \"title\": \"MasterChef\", \
                    \"type\": \"Program\", \
                    \"x\": 292, \
                    \"y\": 190 \
                }, \
                { \
                    \"bundle_height\": 0, \
                    \"event_id\": 8, \
                    \"size\": 7, \
                    \"title\": \"Neighbours\", \
                    \"type\": \"Program\", \
                    \"x\": 292, \
                    \"y\": 212 \
                }, \
                { \
                    \"bundle_height\": 0, \
                    \"event_id\": 9, \
                    \"size\": 4, \
                    \"title\": \"Nightly Show with Gordon Ramsay\", \
                    \"type\": \"Program\", \
                    \"x\": 292, \
                    \"y\": 234 \
                }, \
                { \
                    \"bundle_height\": 0, \
                    \"event_id\": 11, \
                    \"size\": 2, \
                    \"title\": \"Snake Boss\", \
                    \"type\": \"Program\", \
                    \"x\": 292, \
                    \"y\": 256 \
                }, \
                { \
                    \"bundle_height\": 0, \
                    \"event_id\": 12, \
                    \"size\": 2, \
                    \"title\": \"The Gadget Show\", \
                    \"type\": \"Program\", \
                    \"x\": 292, \
                    \"y\": 278 \
                }, \
                { \
                    \"bundle_height\": 0, \
                    \"event_id\": 13, \
                    \"size\": 2, \
                    \"title\": \"Top Gear\", \
                    \"type\": \"Program\", \
                    \"x\": 292, \
                    \"y\": 300 \
                } \
            ] \
        }";
    CreateChart(data, "{ \"show_link_labels\" : true }");
}

Update();

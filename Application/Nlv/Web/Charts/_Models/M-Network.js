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

function Update1() {
    const data = " \
        { \
            \"nodes\": [{ \
                \"event_id\": 1, \
                \"title\": \"Neighbours\", \
                \"type\": 1, \
                \"size\": 7 \
            }, { \
                \"event_id\": 100, \
                \"title\": \"The Gadget Show\", \
                \"type\": 1, \
                \"size\": 2 \
            }, { \
                \"event_id\": 3, \
                \"title\": \"Casualty\", \
                \"type\": 1, \
                \"size\": 2 \
            }, { \
                \"event_id\": 4, \
                \"title\": \"Top Gear\", \
                \"type\": 1, \
                \"size\": 2 \
            }, { \
                \"event_id\": 5, \
                \"title\": \"EastEnders\", \
                \"type\": 1, \
                \"size\": 4 \
            }, { \
                \"event_id\": 6, \
                \"title\": \"Room 101\", \
                \"type\": 1, \
                \"size\": 1 \
            }, { \
                \"event_id\": 7, \
                \"title\": \"Nightly Show with Gordon Ramsay\", \
                \"type\": 1, \
                \"size\": 4 \
            }, { \
                \"event_id\": 8, \
                \"title\": \"MasterChef\", \
                \"type\": 1, \
                \"size\": 3 \
            }, { \
                \"event_id\": 9, \
                \"title\": \"Eddie Stobart\", \
                \"type\": 1, \
                \"size\": 1 \
            }, { \
                \"event_id\": 10, \
                \"title\": \"Channel-2005\", \
                \"type\": 2, \
                \"size\": 9 \
            }, { \
                \"event_id\": 11, \
                \"title\": \"Channel-2001\", \
                \"type\": 2, \
                \"size\": 10 \
            }, { \
                \"event_id\": 12, \
                \"title\": \"Channel-2002\", \
                \"type\": 2, \
                \"size\": 2 \
            }, { \
                \"event_id\": 13, \
                \"title\": \"Channel-2003\", \
                \"type\": 2, \
                \"size\": 4 \
            }, { \
                \"event_id\": 14, \
                \"title\": \"Channel-2012\", \
                \"type\": 2, \
                \"size\": 1 \
            }, { \
                \"event_id\": 15, \
                \"title\": \"Channel-2055\", \
                \"type\": 2, \
                \"size\": 1 \
            }, { \
                \"event_id\": 16, \
                \"title\": \"CardId-1\", \
                \"type\": 3, \
                \"size\": 29 \
            }, { \
                \"event_id\": 17, \
                \"title\": \"CardId-2\", \
                \"type\": 3, \
                \"size\": 1 \
            }, { \
                \"event_id\": 18, \
                \"title\": \"CardId-7\", \
                \"type\": 3, \
                \"size\": 2 \
            }], \
            \"links\": [{ \
                \"event_id\": 19, \
                \"source\": \"Neighbours\", \
                \"target\": \"Channel-2005\", \
                \"type\": 2, \
                \"label\": \"h\" \
            }, { \
                \"event_id\": 20, \
                \"source\": \"Neighbours\", \
                \"target\": \"CardId-1\", \
                \"label\": \"d\" \
            }, { \
                \"event_id\": 21, \
                \"source\": \"The Gadget Show\", \
                \"target\": \"Channel-2005\", \
                \"type\": 2, \
                \"label\": \"h\" \
            }, { \
                \"event_id\": 22, \
                \"source\": \"The Gadget Show\", \
                \"target\": \"CardId-1\", \
                \"type\": 3, \
                \"label\": \"d\" \
            }, { \
                \"event_id\": 23, \
                \"source\": \"Casualty\", \
                \"target\": \"Channel-2001\", \
                \"type\": 2, \
                \"label\": \"h\" \
            }, { \
                \"event_id\": 24, \
                \"source\": \"Casualty\", \
                \"target\": \"CardId-1\", \
                \"type\": 3, \
                \"label\": \"d\" \
            }, { \
                \"event_id\": 25, \
                \"source\": \"Top Gear\", \
                \"target\": \"Channel-2002\", \
                \"type\": 2, \
                \"label\": \"h\" \
            }, { \
                \"event_id\": 26, \
                \"source\": \"Top Gear\", \
                \"target\": \"CardId-1\", \
                \"type\": 3, \
                \"label\": \"d\" \
            }, { \
                \"event_id\": 27, \
                \"source\": \"EastEnders\", \
                \"target\": \"Channel-2001\", \
                \"type\": 2, \
                \"label\": \"h\" \
            }, { \
                \"event_id\": 28, \
                \"source\": \"EastEnders\", \
                \"target\": \"CardId-1\", \
                \"type\": 3, \
                \"label\": \"d\" \
            }, { \
                \"event_id\": 29, \
                \"source\": \"EastEnders\", \
                \"target\": \"CardId-7\", \
                \"type\": 3 \
            }, { \
                \"event_id\": 30, \
                \"source\": \"Room 101\", \
                \"target\": \"Channel-2012\", \
                \"type\": 2, \
                \"label\": \"h\" \
            }, { \
                \"event_id\": 31, \
                \"source\": \"Room 101\", \
                \"target\": \"CardId-7\", \
                \"type\": 3, \
                \"label\": \"d\" \
            }, { \
                \"event_id\": 32, \
                \"source\": \"Nightly Show with Gordon Ramsay\", \
                \"target\": \"Channel-2003\", \
                \"type\": 2, \
                \"label\": \"h\" \
            }, { \
                \"event_id\": 33, \
                \"source\": \"Nightly Show with Gordon Ramsay\", \
                \"target\": \"CardId-1\", \
                \"type\": 3, \
                \"label\": \"d\" \
            }, { \
                \"event_id\": 34, \
                \"source\": \"MasterChef\", \
                \"target\": \"Channel-2001\", \
                \"type\": 2, \
                \"label\": \"h\" \
            }, { \
                \"event_id\": 35, \
                \"source\": \"MasterChef\", \
                \"target\": \"CardId-1\", \
                \"type\": 3, \
                \"label\": \"d\" \
            }, { \
                \"event_id\": 36, \
                \"source\": \"MasterChef\", \
                \"target\": \"CardId-2\", \
                \"type\": 3, \
                \"label\": \"d\" \
            }, { \
                \"event_id\": 37, \
                \"source\": \"Eddie Stobart\", \
                \"target\": \"Channel-2055\", \
                \"type\": 2, \
                \"label\": \"h\" \
            }, { \
                \"event_id\": 38, \
                \"source\": \"Eddie Stobart\", \
                \"target\": \"CardId-1\", \
                \"type\": 3, \
                \"label\": \"d\" \
            }] \
        }";
    CreateChart(data, "{ \"show_link_labels\" : true }");
}

function Update2() {
    const data = " \
        { \
            \"nodes\": [{ \
                \"event_id\": 1, \
                \"type\": \"Program\", \
                \"title\": \"Casualty\", \
                \"size\": 2 \
            }, { \
                \"event_id\": 2, \
                \"type\": \"Program\", \
                \"title\": \"Celebrity Apprentice USA\", \
                \"size\": 1 \
            }, { \
                \"event_id\": 3, \
                \"type\": \"Program\", \
                \"title\": \"Come Dine with Me\", \
                \"size\": 1 \
            }, { \
                \"event_id\": 4, \
                \"type\": \"Program\", \
                \"title\": \"EastEnders\", \
                \"size\": 4 \
            }, { \
                \"event_id\": 5, \
                \"type\": \"Program\", \
                \"title\": \"Eddie Stobart\", \
                \"size\": 1 \
            }, { \
                \"event_id\": 6, \
                \"type\": \"Program\", \
                \"title\": \"Good Will Hunting\", \
                \"size\": 1 \
            }, { \
                \"event_id\": 7, \
                \"type\": \"Program\", \
                \"title\": \"MasterChef\", \
                \"size\": 3 \
            }, { \
                \"event_id\": 8, \
                \"type\": \"Program\", \
                \"title\": \"Neighbours\", \
                \"size\": 7 \
            }, { \
                \"event_id\": 9, \
                \"type\": \"Program\", \
                \"title\": \"Nightly Show with Gordon Ramsay\", \
                \"size\": 4 \
            }, { \
                \"event_id\": 10, \
                \"type\": \"Program\", \
                \"title\": \"Room 101\", \
                \"size\": 1 \
            }, { \
                \"event_id\": 11, \
                \"type\": \"Program\", \
                \"title\": \"Snake Boss\", \
                \"size\": 2 \
            }, { \
                \"event_id\": 12, \
                \"type\": \"Program\", \
                \"title\": \"The Gadget Show\", \
                \"size\": 2 \
            }, { \
                \"event_id\": 13, \
                \"type\": \"Program\", \
                \"title\": \"Top Gear\", \
                \"size\": 2 \
            }, { \
                \"event_id\": 14, \
                \"type\": \"Channel\", \
                \"title\": \"Channel-2001\", \
                \"size\": 10 \
            }, { \
                \"event_id\": 15, \
                \"type\": \"Channel\", \
                \"title\": \"Channel-2002\", \
                \"size\": 2 \
            }, { \
                \"event_id\": 16, \
                \"type\": \"Channel\", \
                \"title\": \"Channel-2003\", \
                \"size\": 4 \
            }, { \
                \"event_id\": 17, \
                \"type\": \"Channel\", \
                \"title\": \"Channel-2004\", \
                \"size\": 1 \
            }, { \
                \"event_id\": 18, \
                \"type\": \"Channel\", \
                \"title\": \"Channel-2005\", \
                \"size\": 9 \
            }, { \
                \"event_id\": 19, \
                \"type\": \"Channel\", \
                \"title\": \"Channel-2010\", \
                \"size\": 1 \
            }, { \
                \"event_id\": 20, \
                \"type\": \"Channel\", \
                \"title\": \"Channel-2011\", \
                \"size\": 2 \
            }, { \
                \"event_id\": 21, \
                \"type\": \"Channel\", \
                \"title\": \"Channel-2012\", \
                \"size\": 1 \
            }, { \
                \"event_id\": 22, \
                \"type\": \"Channel\", \
                \"title\": \"Channel-2055\", \
                \"size\": 1 \
            }, { \
                \"event_id\": 23, \
                \"type\": \"CardID\", \
                \"title\": \"CardID-1\", \
                \"size\": 28 \
            }, { \
                \"event_id\": 24, \
                \"type\": \"CardID\", \
                \"title\": \"CardID-2\", \
                \"size\": 1 \
            }, { \
                \"event_id\": 25, \
                \"type\": \"CardID\", \
                \"title\": \"CardID-7\", \
                \"size\": 2 \
            }], \
            \"links\": [{ \
                \"event_id\": 14, \
                \"source\": \"Neighbours\", \
                \"target\": \"CardID-1\", \
                \"label\": \"d\" \
            }, { \
                \"event_id\": 15, \
                \"source\": \"The Gadget Show\", \
                \"target\": \"CardID-1\", \
                \"label\": \"d\" \
            }, { \
                \"event_id\": 16, \
                \"source\": \"Good Will Hunting\", \
                \"target\": \"CardID-1\", \
                \"label\": \"d\" \
            }, { \
                \"event_id\": 17, \
                \"source\": \"Casualty\", \
                \"target\": \"CardID-1\", \
                \"label\": \"d\" \
            }, { \
                \"event_id\": 18, \
                \"source\": \"Snake Boss\", \
                \"target\": \"CardID-1\", \
                \"label\": \"d\" \
            }, { \
                \"event_id\": 19, \
                \"source\": \"Top Gear\", \
                \"target\": \"CardID-1\", \
                \"label\": \"d\" \
            }, { \
                \"event_id\": 20, \
                \"source\": \"Celebrity Apprentice USA\", \
                \"target\": \"CardID-1\", \
                \"label\": \"d\" \
            }, { \
                \"event_id\": 21, \
                \"source\": \"EastEnders\", \
                \"target\": \"CardID-1\", \
                \"label\": \"d\" \
            }, { \
                \"event_id\": 23, \
                \"source\": \"Nightly Show with Gordon Ramsay\", \
                \"target\": \"CardID-1\", \
                \"label\": \"d\" \
            }, { \
                \"event_id\": 24, \
                \"source\": \"MasterChef\", \
                \"target\": \"CardID-1\", \
                \"label\": \"d\" \
            }, { \
                \"event_id\": 27, \
                \"source\": \"Come Dine with Me\", \
                \"target\": \"CardID-1\", \
                \"label\": \"d\" \
            }, { \
                \"event_id\": 28, \
                \"source\": \"Eddie Stobart\", \
                \"target\": \"CardID-1\", \
                \"label\": \"d\" \
            }, { \
                \"event_id\": 25, \
                \"source\": \"MasterChef\", \
                \"target\": \"CardID-2\", \
                \"label\": \"d\" \
            }, { \
                \"event_id\": 22, \
                \"source\": \"Room 101\", \
                \"target\": \"CardID-7\", \
                \"label\": \"d\" \
            }, { \
                \"event_id\": 26, \
                \"source\": \"EastEnders\", \
                \"target\": \"CardID-7\", \
                \"label\": \"d\" \
            }, { \
                \"event_id\": 4, \
                \"source\": \"Casualty\", \
                \"target\": \"Channel-2001\", \
                \"label\": \"h\" \
            }, { \
                \"event_id\": 7, \
                \"source\": \"Celebrity Apprentice USA\", \
                \"target\": \"Channel-2001\", \
                \"label\": \"h\" \
            }, { \
                \"event_id\": 8, \
                \"source\": \"EastEnders\", \
                \"target\": \"Channel-2001\", \
                \"label\": \"h\" \
            }, { \
                \"event_id\": 11, \
                \"source\": \"MasterChef\", \
                \"target\": \"Channel-2001\", \
                \"label\": \"h\" \
            }, { \
                \"event_id\": 6, \
                \"source\": \"Top Gear\", \
                \"target\": \"Channel-2002\", \
                \"label\": \"h\" \
            }, { \
                \"event_id\": 10, \
                \"source\": \"Nightly Show with Gordon Ramsay\", \
                \"target\": \"Channel-2003\", \
                \"label\": \"h\" \
            }, { \
                \"event_id\": 12, \
                \"source\": \"Come Dine with Me\", \
                \"target\": \"Channel-2004\", \
                \"label\": \"h\" \
            }, { \
                \"event_id\": 1, \
                \"source\": \"Neighbours\", \
                \"target\": \"Channel-2005\", \
                \"label\": \"h\" \
            }, { \
                \"event_id\": 2, \
                \"source\": \"The Gadget Show\", \
                \"target\": \"Channel-2005\", \
                \"label\": \"h\" \
            }, { \
                \"event_id\": 3, \
                \"source\": \"Good Will Hunting\", \
                \"target\": \"Channel-2010\", \
                \"label\": \"h\" \
            }, { \
                \"event_id\": 5, \
                \"source\": \"Snake Boss\", \
                \"target\": \"Channel-2011\", \
                \"label\": \"h\" \
            }, { \
                \"event_id\": 9, \
                \"source\": \"Room 101\", \
                \"target\": \"Channel-2012\", \
                \"label\": \"h\" \
            }, { \
                \"event_id\": 13, \
                \"source\": \"Eddie Stobart\", \
                \"target\": \"Channel-2055\", \
                \"label\": \"h\" \
            }] \
        }";
    CreateChart(data, "{}");

    const selection = " \
        { \
            \"nodes\": [25, 10, 21], \
            \"links\": [9, 22] \
        }";
    SetSelection(selection, "{}");
}

Update1();

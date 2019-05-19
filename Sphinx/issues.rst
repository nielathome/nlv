..  
  Copyright (C) Niel Clausen 2018. All rights reserved.
  
  This program is free software: you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation, either version 3 of the License, or
  (at your option) any later version.
  
  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
  GNU General Public License for more details.
  
  You should have received a copy of the GNU General Public License
  along with this program. If not, see <https://www.gnu.org/licenses/>.


Caveats and Issues
==================

Known Limits
------------

* The maximum size of a logfile is 2GB.
* The maximum number of fields supported is 30.
* The application only supports plain text log files (8-bit Ascii).
* The time span of a log file must be less than 292 years.


Known Issues
------------

* The table control doesn't always resize columns correctly.
* Filtering an event view whose table display has been sorted appears to enter
* a near infinite loop re-sorting the data
* Graph drawing performance is poor for large datasets
* Clicking in the event views does not always cause the session navigator to
  select the corresponding event, causing the two views to be out of sync.
* There is no documentation on events; UI pictures are out of date.
* When setting a marker to hilite the location of an event, the system assumes
  that the date/time field name contains the text "date".
* Where several lines have the same timecode; the global marker is set to the
  first such line, but the screen scrolls to the last. This is confusing when
  the two aren't visible at the same time.
* Leading irregular lines in the log are not displayed.
* Only one instance of NLV can run at a time on a system.
* There is no regression testing.

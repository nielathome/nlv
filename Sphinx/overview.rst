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


Overview
========

NLV is designed to aid the analysis of one or more log files relating to 
some topic of interest. There is an assumption that the logs are large and/or 
contain significant amounts of information which is unrelated to the analysis. 
Hence the main task for the user is to sift the logs for relevent information, 
and make associations between events described in the logs. This may include 
making correlations between logs from different systems, which may have 
timestamps referenced to different timezones or other sources of clock drift 
or offset.

.. image:: view.png

All of the logs needed for a study are held together in a :doc:`session <session>`.
A session is a project, relating logs, their views, search history, filtering etc.
Sessions are stored as XML files.

The contents of a session are structured as a hierarchy:

* :doc:`Session <session>`

  * :doc:`Log files <logfile>`

    * :doc:`Log views <views>`
    * :doc:`Events <events>`

These items are clearly displayed in the explorer window in the tear-off panel
shown to the left side of the main application window.

.. image:: session.png

The "type" of a log is determined by the structure of each line in the log.
Normally, log lines consist of a common structured part followed by free-form
text. The structured part identifies a number **fields**. Typical fields are
a date or timestamp, machine name, process number etc.

NLV interprets the fields present in a log with the aid of a :doc:`schema <schema>`. A suitable
schema must be chosen when the log is added to the session. The schema may also
define a relationship between log lines and the system source code which emitted
the log line. With a suitable :doc:`plug-in <vsnlv>`, the source code can then
be displayed in an IDE, permitting a deeper understanding of the system's behaviour.

There can be any number of :doc:`views <views>` of a log file. The views are 
shown in the main area of the application. Each view can be tailored to meet a 
purpose by choosing which :ref:`fields <viewfields>` are displayed, 
:ref:`filtering <viewfilters>` out log lines which do not meet a relevent criteria 
and :ref:`searching/hiliting <viewhiliters>` terms of interest to make them stand 
out from the rest of the text.

Events of interest in a logfile can be :ref:`bookmarked <markers>` or
:ref:`annotated <annotation>`.

Events in different views can be correlated by :ref:`trackers <viewtracking>` such
that moving the cursor in one view causes related views to scroll to the same
(or a nearby) line.

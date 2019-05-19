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


Log File
========

:guilabel:`Logfile` nodes in the explorer view define aspects common to all
:doc:`views <views>` of the log file. These are the markers, trackers and timezone
information.


.. _openview:

Open New View
-------------

TBD.


.. _markers:

Markers
-------

Markers are displayed in the margin to the left of a view. Four markers are
available. Their colours and styles can be set using the drop-down lists in the
:guilabel:`Logfile | Markers` panel.

Each line in the log file can be associated with a marker in one of two ways:

* via text matching, or
* explicitly selected

The text matched markers identify marked lines via the search text box. For more
information, see :doc:`searching <searching>`.

Explicitly selected markers identify user chosen lines. In the log view, place 
the cursor in the line to be marked and press the :kbd:`Ctrl-B` key.

.. image:: markers.png


.. _trackers:

Trackers
--------

A tracker is a special mark in the view margin which indicates the line 
containing the cursor. There are two types of tracker:

* Local tracker. This tracks a location within a single log file. All views of 
  the logfile show the same tracker at the same line. If the tracker is not
  visible for a view, then it is the case that the corresponding line has been
  filtered out of that view.
* Global trackers. These trackers are common to all views of all logfiles in the 
  session. They identify the **nearest** line in the current view to the tracked 
  line. Correlation of lines in different log files is made by comparing the 
  date/time stamp of the lines.

For more information on how to set the location of a tracker, and how different
views can be set to scroll to keep a tracker displayed on-screen,
see :ref:`Tracking <viewtracking>`.

Tracker colours and styles can be set using the drop-down lists in the 
:guilabel:`Logfile | Trackers` panel.

.. image:: trackers.png


.. _timezone:

Timezone Info
-------------

Global trackers use log line date/time information to compare locations in
different logfiles. All such caluclations are performed in UTC. Set the timezone
here to allow for offsets between the logfiles in the session.

.. image:: timezone.png


Themes
------

Logfiles interact with Navigation themes and Log pattern themes.


.. _lognavigation:

Navigation
..........

Any local changes to a marker or tracker colour or style can be saved
or cleared via the :guilabel:`Logfile | Theme | Changes to navigation theme`
panel.

.. image:: markers-theme.png

To change the selected navigation theme, see :ref:`themes`.


.. _logpatterns:

Log Patterns
............

Log pattern themes are the search patterns used to define all of the
markers. A gallery of available themes can be found at
:guilabel:`Logfile | Theme | Log theme gallery`.

.. image:: logfile-theme-gallery.png

Where local changes to a Log pattern theme exist, they can be saved or
cleared via the :guilabel:`Logfile | Theme | Changes to log theme` panel.

.. image:: logfile-theme.png

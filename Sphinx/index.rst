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

..
  NLV documentation master file, created by
  sphinx-quickstart on Sun Dec 17 09:32:18 2017.
  You can adapt this file completely to your liking, but it should at least
  contain the root `toctree` directive.


NLV
===

NLV is a viewer tool which supports the analysis of one or more log files in order
to understand why a system behaved in a particular way.

NLV allows multiple views of a log file to be opened. Text and lines of interest within
a view may be hilited, bookmarked and annotated. The log lines presented in a view can be
filtered to display only lines of interest. The filter engine supports regular expressions
and can match on log file fields, as well as bookmarks and annotations.

Lines in different views can be associated so that scrolling in one view automatically
scrolls to the same position in related views. Where the views correspond to different
log files, the association is made via the line's time stamp.

NLV works with 3'rd party IDEs and editors to synchronise display of the source code
which emitted a log line with the NLV view, providing a way to browse the system's source code.


Contents
--------

.. toctree::
   :maxdepth: 3

   overview
   session
   logfile
   views
   events
   searching
   schema
   vsnlv
   keyboard
   building
   issues
   references
   licenses


Indices and tables
------------------

* :ref:`genindex`
* :ref:`search`

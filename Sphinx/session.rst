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


Sessions
========

To create a new session, save the current session, or open a recent session, right
click the :guilabel:`Session` node in the explorer view and choose an item from
the popup menu.

.. image:: session-menu.png


.. _opensession:

Open Session
------------

TBD.


.. _openlog:

Open Log File
-------------

To open a log file and add it to the current session, select :guilabel:`Session | Open`,
then choose the correct schema from the drop down & any preferred log builder and click the
:guilabel:`Open ...` button. A standard :guilabel:`File Open` dialog will appear,
allowing one or more log files to be opened.

A log builder consists of a :ref:`log file pattern theme <logpatterns>` and one or more
:ref:`view pattern themes <viewpatterns>`. When the log file is opened, the log file pattern
is applied, and one view is opened for each listed view pattern. This permits one or more
views to be opened with predefined markers, searches etc. The available log builders
are defined by the schema.

.. image:: open-log.png
  

.. _themes:

Navigation Themes
-----------------

Colours and styles in NLV can be stored as a theme. This includes:

* :ref:`markers`
* :ref:`trackers`, and
* :ref:`viewhiliters`

The gallery of available themes can be found at the :guilabel:`Session | Themes` panel.
Themes can be activated, copied, renamed and deleted. Either right click the
theme in the list and choose the appropriate option, or enter the equivalent
keyboard shortcut.

.. image:: session-theme.png

For information on editing navigation themes, see the :doc:`logfile` and :doc:`views` pages.
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


Views
=====

:guilabel:`View` nodes in the explorer view customise a view of a :doc:`logfile 
<logfile>` and permit annotating, searching, filtering and tracking.


.. _annotation:

Annotations
-----------

Arbitrary comment text can be placed below any line in the view. Place the cursor
on the line and either type :kbd:`Ctrl-A` or select :guilabel:`Session | Annotate`
in the explorer view. Enter the annotation text in the text area that appears to
the left of the view area: 

.. image:: annotation.png

The annotation text can be displayed with one of four styles in the view. Select
the required style from the drop-down below the annotation area:

.. image:: annotation-style.png


.. _viewhiliters:

Searching & Hiliting
--------------------

By default, seven searcher/hiliters are available. Their colours and styles can
be set using the drop-down lists in the :guilabel:`View | Search` panel.

Choosing the search text is determined in one of two ways:

* the **selection** hiliter hilites the text selected in the view
* by specifying search text in the :guilabel:`View | Search | Search properties`
  panel. For more information, see :doc:`searching <searching>`.

.. image:: hiliters.png


.. _viewfilters:

Filtering
---------

A filter is applied applied to each regular log line. Where the filter matches,
the log line is displayed in the view.

Irregular log lines (i.e. lines without all the fields defined in the schema) are not filtered
directly, but rather, are **associated** with the most recent regular line. Where
a regular line is visible, any following irregular lines will also be visible.

The filter is entered into the :guilabel:`View | Filter | Filter description` panel.
For more information, see :doc:`searching <searching>`.

.. image:: filters.png

If the filter text is invalid for some reason, the background colour is set to red:

.. image:: filter-bad.png

and the :guilabel:`Console` panel will contain an explanation; in this case, no
value for the Category field matches "e":

.. image:: filter-bad-reason.png


.. _viewtracking:

Tracking
--------

For more information on tracker types and their appearance,
see :ref:`Trackers <trackers>`.

A view interacts with the trackers in two ways:

* a tracker's location may be set from the cursor's position
* the view can be scrolled to ensure a specific tracker is visible

Use the options in the :guilabel:`View | Track` panel to control this behaviour:

* :guilabel:`Set local tracker from cursor` - when checked, the local tracker's
  line location is updated to follow the cursor.
* :guilabel:`Set global tracker from cursor` - when selected, the identified
  global tracker's date/time location is updated to follow the cursor.
* :guilabel:`Synchronise view to tracker` - when selected, the view will scroll
  to ensure the identified local/global tracker is visible whenever it is updated.
  
.. image:: tracking.png

The timestamps associated with each tracker can be seen in the :guilabel:`Status`
panel:

.. image:: tracker-status.png


.. _viewfields:

Field Visibility
----------------

The :guilabel:`View | Fields` panel determines which field(s) are visible 
in the view as well as the colour the field's text is displayed in.

.. image:: fields.png



Themes
------

Views interact with Navigation themes and View pattern themes.


.. _viewnavigation:

Navigation
..........

Any local changes to hiliter colour or style can be saved
or cleared via the :guilabel:`View | Theme | Changes to navigation theme`
panel.

.. image:: hiliters-theme.png

To change the selected navigation theme, see :ref:`themes`.


.. _viewpatterns:

View Patterns
.............

View pattern themes contain all the search and filter patterns, as well as
field visibility, field colour and tracker choices A gallery of available
themes can be found at :guilabel:`View | Theme | View theme gallery`.

.. image:: view-theme-gallery.png

Where local changes to a View pattern theme exist, they can be saved or
cleared via the :guilabel:`View | Theme | Changes to view theme` panel.

.. image:: view-theme.png

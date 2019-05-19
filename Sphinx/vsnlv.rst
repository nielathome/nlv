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


vsNLV
=====

vsNLV is a plugin for Visual Studio 2015 or newer. The plugin displays the source
code corresponding to the current log line in NLV. Note that the current implementation
requires that only one instance if Visual Studio is running.

In Visual Studio, 

* Open the Solution containing the source files referenced from the logfile.
  Note that this does not have to be the Solution that built the software, as
  Visual Studio is being used as a source code viewer. In general though,
  IntelliSense will give better results if the Solution can build the software.
 
* If the :guilabel:`NLV Listener` pane is not already open, select the
  :guilabel:`View | Other Windows | NLV Listener` menu item.

* Select a channel from the :guilabel:`Notifier Channel` dropdown.

* In the :guilabel:`Output` panel, select "NLV Listener" from the
  :guilabel:`Show output from` drop down.

In NLV:

* Move the cursor in a view. 

The :guilabel:`Console` pane in NLV will show that a connection to vsNLV
has been established:

.. image:: vsnlv-console.png

Similarly, the :guilabel:`Output` panel in Visual Studio will also show the
connection has been established:

.. image:: vsnlv-output.png

Moving the cursor in NLV will result in the :guilabel:`NLV Listener` pane
displaying the log text and the source code being displayed.
   
.. image:: vsnlv-listener.png

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


Schema
======

The type, or **schema**, of a log file is determined by the common **fields** available
on every line in the logfile. The :guilabel:`Session | Open | Log file schema` drop-down
list contains the names of all schemata recognised by the installation. The text
just below this list shows the fields, and their details, for the chosen schema.

Log lines which don't have fields present are termed **irregular**. Not all
searching and filtering will work with irregular lines.

.. image:: open-log.png


Field Types
-----------

The currently recognised field types are:

datetime_unix
  A Unix date/time without the year - ``Mar 31 23:58:15``. 

datetime_us_std
  US date time (month/day/year) - ``12/9/2016 11:42:03 PM``.
    
datetime_tracefmt_int_std
  A tracefmt date/time in international date format (day/month/year) - ``12/06/2017-18:03:17.839``.
   
datetime_tracefmt_us_std
  A tracefmt date/time in US date format (month/day/year) - ``06/12/2017-18:03:17.839``.

datetime_tracefmt_int_hires
  A hi-resolution tracefmt date/time in international date format (day/month/year) - ``12/06/2017-18:03:17.839.222100``.

datetime_tracefmt_us_hires
  A hi-resolution tracefmt date/time in US date format (month/day/year) - ``06/12/2017-18:03:17.839.222100``.

enum08
  A text string which takes one of 256 values.
  
enum16
  A text string which takes one of 65,536 values.

text
  An uninterpreted text sequence.

emitter
  A text string which locates the source code which emitted the log line.
  
uint08
  An unsigned number between 0 and 255.
  
uint16
  An unsigned  number between 0 and 65,535.

uint32
  An unsigned  number between 0 and 4,294,967,295.
  
uint64
  An unsigned  number between 0 and 18,446,744,073,709,551,615.

int08
  A signed number between -128 and 127.
  
int16
  A signed  number between -32,768 and 37,767.

int32
  A signed  number between -2,147,483,648 and 2,147,483,647.
  
int64
  A signed  number between -9,223,372,036,854,775,808 and 9,223,372,036,854,775,807.

float32
  A floating point number in the range -/+ 1.17549e-38

float64
  A floating point number in the range -/+ 1.79769e+308


Implementation
--------------

A schema is an XML file, normally distributed as part of a Python NLV extension.
See the MythTV extension for an example.

As well as defining the schema, an extension can define:

* logfile formatting
* :ref:`Log file <logpatterns>` and :ref:`view <viewpatterns>` pattern themes
* logfile builders
* a channel identifier for the notifier

All data used by NLV is in XML format.


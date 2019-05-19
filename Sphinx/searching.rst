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


Searching
=========

NLV has a common searching and filtering engine used to:

* select lines for :ref:`marking <markers>` -
  :guilabel:`Logfile | Markers | Marker properties` panel.
* :ref:`filter <viewfilters>` lines to be shown in a view -
  :guilabel:`View | Filter | Filter description` panel. 
* :ref:`search <viewhiliters>` text in, views -
  :guilabel:`View | Search | Search properties` panel.

NLV supports two  mechanisms for searching, and three for marking & filtering,
as described in the following sections.

In all cases, the search mechanism is selected via a drop-down list. The
:guilabel:`Case sensitive` check-box controls the case sensitivity of the
search.

The :guilabel:`Recent items` history list identifies previous searches
within the current :doc:`session <session>`. Click the
:guilabel:`All items | Show ...` button to see all searches/filters
recorded for the current user. In either case, to re-apply a previous
seach, double-click it in the list.
 
Literal
-------

The text in the displayed log line must exactly match the supplied text. Note that
the displayed log line text is effected by the field visibility controls.

For example, a case sensitive literal match of the text "EITScanner" in the 
:guilabel:`Lofgile | Markers` panel places a marker next to every log line containing 
the text "EITScanner".

Regular Expression
------------------

The regular expression syntax is defined by ECMA-262. See :doc:`references` 
for links to Web resources describing this syntax.

For example, a regular expression match of the text "EIT.*Scanner" in the 
:guilabel:`View | Search` panel would hilite any text sequence within a line in the 
view starting with "Eit" and finishing with "Scanner"

LogView Filter (LVF)
--------------------

LVF is only available as an option in the :guilabel:`View | Filter` panel. 
The filter is applied to each log line. Where the final expression evaluates to 
"true", the log line is displayed in the view.

Examples
........

MythTV logfiles have a "Category" field, whose value is one of "I", "N" or "E".

To display lines whose category is not "I"::

  category in [^"I"]
  
To display lines whose category is neither "I" nor "N"::

  category in [^"I", ^"N"]  

To show error lines (category is "E") on 30 March (European locale)::

  cat in ["E"]
  and date in [30/3 .. 31/3]

which is equivalent to::

  cat in ["E"] 
  and date >= 30/3 and date < 31/3

To filter out all lines whose non-field text contains the word "reschedule"::

  not log ~= "reschedule"i

Syntax
......

An LVF expression is a logical expression:

.. productionlist::
   lvf: `logical_or_expr`

Boolean operations
..................

The language supports C-like and Python-like boolean operations.

.. productionlist::
   logical_or_expr: `logical_and_expr` ( `logical_or_op` `logical_and_expr` )*
   logical_or_op: "||" | "or"
   logical_and_expr: `logical_not_expr` ( `logical_and_op` `logical_not_expr` )*
   logical_and_op: "&&" | "and"
   logical_not_expr: `logical_not_op`? `primary_expr`
   logical_not_op: "!" | "not"
   primary_expr: `match_clause`
               : | "(" `logical_or_expr` ")"

Match operations
................

The core of the language is the ability to match field data and log line text 
against literals, ranges and regular expressions.

.. productionlist::
   match_clause: `text_match_clause`
			   : | `user_adornments_clause`
               : | `field_match_clause`
               : | `field_compare_clause`
   text_match_clause: `text_identifier` "~=" `text_value`
   text_identifier: "log" | "annotation" | `field_name`
   user_adornments_clause: "annotated" | "bookmarked"
   field_match_clause: `field_name` "in" `field_range`
   field_compare_clause: `field_name` `field_compare_op` `field_value`
   field_name: ? field name defined by the log file schema ?
   field_compare_op: "=" | "==" | "<" | "<=" | ">" | ">=" | "!="

where:

* "log" refers to the log line text remaining after all fields have been 
  processed, and
* "annotation" refers to the text of any annotation associated with the log 
  line at the time the filter is run.
* "annotated" and "bookmarked" evaluate to true where a line is the subject
  of a user annotation or bookmark at the time the filter is run.

Also, see :doc:`schema`.

The :token:`text_match_clause` evaluates to true when the :token:`text_value` 
matches any part of the text identified by :token:`text_identifier`.

:token:`field_name` can match any part of the field name defined for the log 
file, but must be unique. The comparison is case-insensitive.

Textual Matches
...............

.. productionlist::
   text_value: ( `plain_string` | `raw_string` ) `qualifier`?
   plain_string: `quote` `string_text` `quote`
   raw_string: "r" `quote` `delimiter`?
             : `(` `string_text` `)`
             : `delimiter`? `quote`
   qualifier: "i"
   quote: '"' | '/'
   string_text: ? string ?
   delimiter: ? string ?

The match :token:`text_value` can be literal text or a regular expression, as 
determined by the :token:`quote` character used:

* "\"" (double quote) for literal text, and;
* "/" (forward slash) for a regular expression.

The match behaviour can be modified by specifing a postfix :token:`qualifier`. 
Currently, the only qualifier supported is "i" (case-insensitive match). Where 
"i" is not specified, the match is case-sensitive.

Two styles of quoting are supported, "plain" and "raw".

* Plain strings are delimited by a single :token:`quote` character at each end. 
  The same quote character should be used at both ends of the string. The 
  :token:`string_text` cannot include the quote character.
* Raw strings allow a user specified :token:`delimiter` to be used at each end 
  of the string. The delimiter must be the same at each end of the 
  :token:`string_text` and should not contain the "(" (open round bracket) 
  character.

Note that no escaping is performed on the :token:`string_text`.

The regular expression grammar is defined by ECMA-262 - see :doc:`references` 
for more information.

Field Matches
.............

Fields can be matched against a range of field values.

.. productionlist::
   field_range: "[" `excluded_range` ("," `excluded_range`)* "]"
   excluded_range: "^" ? `included_range`
   included_range: `field_value` ( ".." `field_value` )?

The :token:`field_range` evaluates to true when no :token:`excluded_range` 
matches and an :token:`included_range` matches. For the special case where 
:token:`field_range` has no :token:`included_range` parts, it evaluates to 
true when no :token:`excluded_range` matches.

An individual field value is either a number, or an enumeration value.

.. productionlist::
   field_value: `datetime` | `number` | `enum_value`
   enum_value: `text_value`

The :token:`enum_value` is first compared to the set of known enumeration
values. The comparison is performed case-insensitively. A match occurs
where the :token:`text_value` describes some or all of the enumeration
value. If the :token:`enum_value` is not followed by a :token:`qualifier`,
then it is an error if no enumeration value is matched. If an "i"
:token:`qualifier` is present, then the error is ignored.

The :token:`enum_value` evaluates to true when the line contains the
matched enumeration value. For field comparisons, the match must be unique,
i.e. it only matches a single enumeration value. For field range matches,
the match does not have to be unique - all matched enumeration values will
be added to the range.

Numeric values are represented internally with 64-bit precision.

.. productionlist::
   number: `dec_number` | `hex_number` | `real_number`
   dec_number: [ "+" | "-" ] `dec_digit` `dec_digit`*
   hex_number: "0x" `hex_digit` `hex_digit`*
   real_number: [ "+" | "-" ] `dec_digit` `dec_digit`* "." `dec_digit` `dec_digit`*
			  : [ ("e" | "E") [ "+" | "-" ] `dec_digit` `dec_digit`* ]
   dec_digit: "0" | "1" | "2" | "3" | "4" | "5" | "6" | "7" | "8" | "9"
   hex_digit: `dec_digit` | "a" | "b" | "c" | "d" | "e" | "f"
            : | "A" | "B" | "C" | "D" | "E" | "F""

A date/time permits specification of fractional seconds to nano-second 
resolution.

.. productionlist::
   datetime: [ `date` ] [ `time` [ `time_fraction` ] ]
   date: `dec_number` "/" `dec_number` [ "/" `dec_number`]
   time: `dec_number` ":" `dec_number` ":" `dec_number`
   time_fraction: "." `dec_number`

One of :token:`date` or :token:`time` must be specified.
Where the :token:`date` is omitted, the date is taken as the date identified 
on the first line in the log file. Where only two elements are supplied for 
the date, they are taken as the day number and month number. In all cases, the 
order of day number, month number and year is taken from the current locale.

#
# Copyright (C) Niel Clausen 2018-2019. All rights reserved.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#
import re



## Recognise ###################################################

class Recogniser:

    #-----------------------------------------------------------
    _RegexProgram = re.compile("UpdateRecStatus2 \\| ([^\\|]+)")


    #-----------------------------------------------------------
    def Begin(self, context, cursor):
        self.Cursor = cursor
        cursor.execute("DROP TABLE IF EXISTS main.program")
        cursor.execute("""
            CREATE TABLE program
            (
                start_text TEXT,
                title TEXT
            )""")


    #-----------------------------------------------------------
    def MatchEventStart(self, context, line):
        f_title = "_UNK_"
        match = re.search(self._RegexProgram, line.GetNonFieldText())
        if match and match.lastindex == 1:
            f_title = match[1]

        self.Cursor.execute("INSERT INTO program VALUES (?, ?)",
        (
            context.GetEventStartText(),
            f_title
        ))

        return True


    #-----------------------------------------------------------
    def End(self):
        pass


Recognise(
    Recogniser(),
    ('LogView Filter', 'function = "HandleReschedule" and log ~= "UpdateRecStatus2"')
)



## Projector ###################################################

def Projector(connection, cursor, context):

    cursor.execute("DROP TABLE IF EXISTS main.projection")
    cursor.execute("""
        CREATE TABLE projection
        (
            title TEXT,
            count INT
        )""")

    cursor.execute("""
        INSERT INTO projection
        SELECT
            title,
            count(title) AS cnt
        FROM program
        GROUP BY title
        ORDER BY cnt DESC
    """)


Project(
    "Programs",
    Projector,
    MakeDisplaySchema()
        .AddField("Program", "text", 400)
        .AddField("Count", "int", 60)
)

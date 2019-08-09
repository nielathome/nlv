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



## Analyser ####################################################

class Analyser:

    #-----------------------------------------------------------
    _RegexProgram = re.compile("UpdateRecStatus2 \\| ([^\\|]+)")


    #-----------------------------------------------------------
    @staticmethod
    def DefineFilter():
        return [
            ('LogView Filter', 'function = "HandleReschedule" and log ~= "UpdateRecStatus2"')
        ]


    #-----------------------------------------------------------
    def Begin(self, context):
        self.Cursor = cursor = context.Connection.cursor()
        cursor.execute("DROP TABLE IF EXISTS program")
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

        ed = context.GetEventStartDetails()

        self.Cursor.execute("INSERT INTO program VALUES (?, ?)",
        [
            ed[0],
            f_title
        ])

        return True


    #-----------------------------------------------------------
    def End(self, context):
        self.Cursor.close()
        context.Connection.commit()



## Projector ###################################################

class Projector:

    #-----------------------------------------------------------
    @classmethod
    def DefineSchema(cls, schema):
        schema.AddField("Program", "text", 400)
        schema.AddField("Count", "uint16", 60)


    #-----------------------------------------------------------
    @staticmethod
    def Project(connection, context):
        cursor = connection.cursor()
        context.MakeProjectionTable(cursor)

        cursor.execute("""
            INSERT INTO projection
            SELECT
                title,
                count(title) AS cnt
            FROM program
            GROUP BY title
            ORDER BY cnt DESC
        """)

        cursor.close()
        connection.commit()



## GLOBAL ##################################################

Analyse(Analyser())
Project("Programs", Projector())
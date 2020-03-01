#
# Copyright (C) Niel Clausen 2018-2020. All rights reserved.
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

import Nlv.Chart as Chart
import re



## Recognise ###################################################

class Recogniser:

    #-----------------------------------------------------------
    _RegexProgram = re.compile('Tuning recording: "?([^":]+).*channel (\d+) on cardid (\d+)')


    #-----------------------------------------------------------
    def Begin(self, context, cursor):
        self.Cursor = cursor
        cursor.execute("DROP TABLE IF EXISTS main.program")
        cursor.execute("""
            CREATE TABLE program
            (
                start_text TEXT,
                title TEXT,
                channel INT,
                cardid INT
            )""")


    #-----------------------------------------------------------
    def MatchEventStart(self, context, line):
        match = re.search(self._RegexProgram, line.GetNonFieldText())
        if match and match.lastindex == 3:
            f_title = match[1]
            f_channel = int(match[2])
            f_cardid = int(match[3])

            self.Cursor.execute("INSERT INTO program VALUES (?, ?, ?, ?)",
            (
                context.GetEventStartText(),
                f_title,
                f_channel,
                f_cardid
            ))

        return True


    #-----------------------------------------------------------
    def End(self):
        pass


Recognise(
    Recogniser(),
    ('LogView Filter', 'function = "HandleRecordingStatusChange"')
)



## Projector ###################################################

def ProgramProjector(connection, cursor, context):

    cursor.execute("DROP TABLE IF EXISTS main.projection")
    cursor.execute("""
        CREATE TABLE projection
        (
            event_id INTEGER PRIMARY KEY ASC AUTOINCREMENT,
            title TEXT,
            count INT
        )""")

    cursor.execute("""
        INSERT INTO projection
        (
            title,
            count
        )
        SELECT
            title,
            count(title) as cnt
        FROM
            analysis.program
        GROUP BY
            title
        ORDER BY
            cnt DESC
    """)


projection = Project(
    "Programs",
    ProgramProjector,
    MakeDisplaySchema()
        .AddField("Name", "text", 400)
        .AddField("Count", "int", 60)
)


projection.Chart("Bar", True, Chart.Bar("Title", "Count"))
projection.Chart("Pie", True, Chart.Pie("Title", "Count"))



## Projector ###################################################

#def NetworkProjector(connection, cursor, context):
#    cursor.execute("DROP TABLE IF EXISTS main.projection")
#    cursor.execute("""
#        CREATE TABLE projection
#        (
#            event_id INTEGER PRIMARY KEY ASC AUTOINCREMENT,
#            title TEXT,
#            channel INT,
#            cardid INT
#        )""")

#    cursor.execute("""
#        INSERT INTO projection
#        (
#            title,
#            channel,
#            cardid
#        )
#        SELECT
#            title,
#            channel,
#            cardid
#        FROM
#            analysis.program
#        """)



#Project(
#    "Network",
#    NetworkProjector,
#    MakeDisplaySchema()
#        .AddField("Title", "text", 400)
#        .AddField("Channel", "int", 60)
#        .AddField("CardID", "int", 60)
#)





def NodesProjector(connection, cursor, context):
    cursor.execute("DROP TABLE IF EXISTS main.projection")
    cursor.execute("""
        CREATE TABLE projection
        (
            event_id INTEGER PRIMARY KEY ASC AUTOINCREMENT,
            type TEXT,
            title TEXT,
            size INT
        )""")

    cursor.execute("""
        INSERT INTO projection
        (
            type,
            title,
            size
        )
        SELECT
            'Program',
            title,
            count(title)
        FROM
            analysis.program
        GROUP BY
            title

        UNION ALL
        SELECT
            'Channel',
            'Channel-' || channel,
            count(channel)
        FROM
            analysis.program
        GROUP BY
            channel

        UNION ALL
        SELECT
            'CardID',
            'CardID-' || cardid,
            count(cardid)
        FROM
            analysis.program
        GROUP BY
            cardid
        """)


Nodes(
    "Entities",
    NodesProjector,
    MakeDisplaySchema()
        .AddField("Type", "text", 70)
        .AddField("Title", "text", 200, align = "left")
        .AddField("Size", "int", 60)
)




def LinksProjector(connection, cursor, context):
    cursor.execute("DROP TABLE IF EXISTS main.projection")
    cursor.execute("""
        CREATE TABLE projection
        (
            event_id INTEGER PRIMARY KEY ASC AUTOINCREMENT,
            source TEXT,
            target TEXT
        )""")

    cursor.execute("""
        INSERT INTO projection
        (
            source,
            target
        )
        SELECT DISTINCT
            title as source,
            'Channel-' || channel as target
        FROM
            analysis.program

        UNION ALL
        SELECT DISTINCT
            title as source,
            'CardID-' || cardid as target
        FROM
            analysis.program
    """)


Links(
    "Relationships",
    LinksProjector,
    MakeDisplaySchema()
        .AddField("Source", "text", 200)
        .AddField("Target", "text", 200, align = "left")
)





def tomorrow():
    cursor.execute("DROP TABLE IF EXISTS main.projection")
    cursor.execute("""
        CREATE TABLE projection
        (
            event_id INTEGER PRIMARY KEY ASC AUTOINCREMENT,
            name TEXT,
            type TEXT,
            count INT
        )""")

    cursor.execute("""
        SELECT
            title as name,
            'program' as type,
            count(title) as size
        FROM
            display
        GROUP BY
            title

        UNION ALL
        SELECT
            channel,
            'channel',
            count(channel)
        FROM
            display
        GROUP BY
            channel

        UNION ALL
        SELECT
            cardid,
            'cardid',
            count(cardid)
        FROM
            display
        GROUP BY
            cardid
    """)



    cursor.execute("""
        SELECT DISTINCT
            title as source,
            channel as target
        FROM
            display

        UNION ALL
        SELECT DISTINCT
            title as source,
            cardid as target
        FROM
            display
    """)

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
                event_id INT,
                start_text TEXT,
                start_utc INT,
                start_offset_ns INT,
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

            self.Cursor.execute("INSERT INTO program VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                context.GetEventId(),
                context.GetEventStartText(),
                *context.GetEventStartTime(),
                f_title,
                f_channel,
                f_cardid
            ))

        return True


    #-----------------------------------------------------------
    def End(self):
        self.Cursor.execute("DROP TABLE IF EXISTS main.entities")
        self.Cursor.execute("""
            CREATE TABLE entities
            (
                event_id INTEGER PRIMARY KEY ASC AUTOINCREMENT,
                type TEXT,
                title TEXT,
                size INT
            )""")

        self.Cursor.execute("""
            INSERT INTO entities
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
                program
            GROUP BY
                title

            UNION ALL
            SELECT
                'Channel',
                'Channel-' || channel,
                count(channel)
            FROM
                program
            GROUP BY
                channel

            UNION ALL
            SELECT
                'CardID',
                'CardID-' || cardid,
                count(cardid)
            FROM
                program
            GROUP BY
                cardid
            """)

        self.Cursor.execute("DROP TABLE IF EXISTS main.relationships")
        self.Cursor.execute("""
            CREATE TABLE relationships
            (
                event_id INTEGER PRIMARY KEY ASC AUTOINCREMENT,
                source TEXT,
                source_id INT,
                target TEXT,
                target_id INT
            )""")

        self.Cursor.execute("""
            INSERT INTO relationships
            (
                source,
                source_id,
                target,
                target_id
            )
            SELECT DISTINCT
                program.title as source,
                source_entities.event_id as source_id,
                'Channel-' || program.channel as target,
                target_entities.event_id as target_id
            FROM
                program
            JOIN
                entities as source_entities
                ON
                    program.title = source_entities.title
            JOIN
                entities as target_entities
                ON
                    'Channel-' || program.channel = target_entities.title

            UNION ALL
            SELECT DISTINCT
                program.title as source,
                source_entities.event_id as source_id,
                'CardID-' || program.cardid as target,
                target_entities.event_id as target_id
            FROM
                program
            JOIN
                entities as source_entities
                ON
                    program.title = source_entities.title
            JOIN
                entities as target_entities
                ON
                    'CardID-' || program.cardid = target_entities.title
        """)


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


def DateExplorerProgramDetails(event_id, db_info, builder):
    builder.AddPageHeading("Details")
    builder.AddFieldHeading("Events")

    with db_info.ConnectionManager() as connection:
        cursor = connection.cursor()
        db_info.AttachBases(cursor)
        cursor.execute("""
            SELECT
                program.start_text,
                program.channel,
                program.cardid
            FROM
                display
            JOIN
                analysis.program as program
                ON
                    display.title = program.title
            WHERE
                display.event_id = {event_id}
        """.format(event_id = event_id))

        for row in cursor:
            builder.AddFieldValue("Time: {} Channel: {} Card:{}".format(row[0], row[1], row[2]))
        

projection = Project(
    "Programs",
    ProgramProjector,
    MakeDisplaySchema()
        .AddField("Name", "text", 400)
        .AddField("Count", "int", 60)
        .OnDataExplorerClose(DateExplorerProgramDetails)
)


projection.Chart("Bar", True, Chart.Bar("Title", "Count"))
projection.Chart("Pie", True, Chart.Pie("Title", "Count"))



## Network #####################################################

def NodesProjector(connection, cursor, context):
    cursor.execute("DROP TABLE IF EXISTS main.projection")
    cursor.execute("""
        CREATE TABLE projection
        (
            event_id INT,
            type TEXT,
            title TEXT,
            size INT
        )""")

    cursor.execute("""
        INSERT INTO projection
        (
            event_id,
            type,
            title,
            size
        )
        SELECT
            event_id,
            type,
            title,
            size
        FROM
            analysis.entities
        """)


def DateExplorerNodesDetails(event_id, db_info, builder):
    builder.AddPageHeading("Relations")
    builder.AddFieldHeading("Entities")

    with db_info.ConnectionManager() as connection:
        cursor = connection.cursor()
        db_info.AttachBases(cursor)

        cursor.execute("""
            SELECT
                target,
                target_id
            FROM
                analysis.relationships
            WHERE
                source_id = {event_id}
        """.format(event_id = event_id))

        for row in cursor:
            builder.AddFieldValue("Id: {} Name: {}".format(row[1], row[0]))

        cursor.execute("""
            SELECT
                source,
                source_id
            FROM
                analysis.relationships
            WHERE
                target_id = {event_id}
        """.format(event_id = event_id))

        for row in cursor:
            builder.AddFieldValue("Id: {} Name: {}".format(row[1], row[0]))


nodes = Nodes(
    "Entities",
    NodesProjector,
    MakeDisplaySchema()
        .AddField("Type", "text", 70)
        .AddField("Title", "text", 200, align = "left")
        .AddField("Size", "int", 60)
        .OnDataExplorerClose(DateExplorerNodesDetails)
)


def LinksProjector(connection, cursor, context):
    cursor.execute("DROP TABLE IF EXISTS main.projection")
    cursor.execute("""
        CREATE TABLE projection
        (
            event_id INT,
            source TEXT,
            source_id INT,
            target TEXT,
            target_id INT
        )""")

    cursor.execute("""
        INSERT INTO projection
        (
            event_id,
            source,
            source_id,
            target,
            target_id
        )
        SELECT
            event_id,
            source,
            source_id,
            target,
            target_id
        FROM
            relationships
    """)


links = Links(
    "Relationships",
    LinksProjector,
    MakeDisplaySchema()
        .AddField("Source", "text", 200)
        .AddHiddenField("SourceId", "int")
        .AddField("Target", "text", 200, align = "left")
        .AddHiddenField("TargetId", "int")
)


Network(
    "Recordings",
    nodes,
    links
).Chart(True, Chart.Network())


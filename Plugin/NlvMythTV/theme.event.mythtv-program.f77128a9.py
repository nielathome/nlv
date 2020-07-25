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
                source_name TEXT,
                source INT,
                target_name TEXT,
                target INT,
                label TEXT
            )""")

        self.Cursor.execute("""
            INSERT INTO relationships
            (
                source_name,
                source,
                target_name,
                target,
                label
            )
            SELECT DISTINCT
                program.title as source_name,
                source_entities.event_id as source,
                'Channel-' || program.channel as target_name,
                target_entities.event_id as target,
                'Channel'
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
                program.title as source_name,
                source_entities.event_id as source,
                'CardID-' || program.cardid as target_name,
                target_entities.event_id as target,
                'CardID'
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


def DataExplorerProgramDetails(context, builder):
    builder.AddPageHeading("Details")
    builder.AddFieldHeading("Events")

    with context.DbInfo.ConnectionManager() as connection:
        cursor = connection.cursor()
        context.DbInfo.AttachBases(cursor)
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
        """.format(event_id = context.EventId))

        for row in cursor:
            builder.AddFieldValue("Time: {} Channel: {} Card:{}".format(row[0], row[1], row[2]))
        

projection = Project(
    "Programs",
    ProgramProjector,
    MakeDisplaySchema()
        .AddField("Name", "Name of the recorded program.", "text", 400)
        .AddField("Count", "Number of times the program was recorded.", "int", 60)
        .OnDataExplorerClose(DataExplorerProgramDetails)
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


def DataExplorerNodesDetails(context, builder):
    builder.AddPageHeading("Goto")
    node_id = context.GetTargetId("Entities")

    with context.DbInfo.ConnectionManager() as connection:
        cursor = connection.cursor()
        context.DbInfo.AttachBases(cursor)

        cursor.execute("""
            SELECT
                target_name,
                target
            FROM
                analysis.relationships
            WHERE
                source = {event_id}

            UNION ALL
            SELECT
                source_name,
                source
            FROM
                analysis.relationships
            WHERE
                target = {event_id}
        """.format(event_id = context.EventId))

        for row in cursor:
            builder.AddAction(node_id, row[0], row[1])


nodes = Nodes(
    "Entities",
    NodesProjector,
    MakeDisplaySchema()
        .AddField("Type", "The entity type: program, channel, or card.", "text", 70)
        .AddField("Title", "The entity title: a program name, channel number, or card ID.", "text", 200, align = "left")
        .AddField("Size", "The number of times the entity is referenced: the number of recordings for a program, the number of time a particular channel was recorded from, or the number of times a particular card was recorded from.", "int", 60)
        .OnDataExplorerClose(DataExplorerNodesDetails)
)


def LinksProjector(connection, cursor, context):
    cursor.execute("DROP TABLE IF EXISTS main.projection")
    cursor.execute("""
        CREATE TABLE projection
        (
            event_id INT,
            source_name TEXT,
            source INT,
            target_name TEXT,
            target INT,
            label TEXT,
            type TEXT
        )""")

    cursor.execute("""
        INSERT INTO projection
        (
            event_id,
            source_name,
            source,
            target_name,
            target,
            label,
            type
        )
        SELECT
            event_id,
            source_name,
            source,
            target_name,
            target,
            label,
            label
        FROM
            relationships
    """)


links = Links(
    "Relationships",
    LinksProjector,
    MakeDisplaySchema()
        .AddField("Source", "A program, channel, or card.", "text", 200)
        .AddHiddenField("SourceEventId", "int")
        .AddField("Target", "A program, channel, or card.", "text", 200, align = "left")
        .AddHiddenField("TargetEventId", "int")
        .AddHiddenField("Label", "text")
        .AddHiddenField("Type", "text")
)


Network(
    "Recordings",
    nodes,
    links
).Chart(True, Chart.Network(setup_script = "theme.event.mythtv-program.f77128a9.network.js"))


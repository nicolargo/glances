#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2025 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""TimescaleDB interface class."""

import sys
import time
from platform import node

import psycopg

from glances.exports.export import GlancesExport
from glances.logger import logger

# Define the type conversions for TimescaleDB
# https://www.postgresql.org/docs/current/datatype.html
convert_types = {
    'bool': 'BOOLEAN',
    'int': 'BIGINT',
    'float': 'DOUBLE PRECISION',
    'str': 'TEXT',
    'tuple': 'TEXT',  # Store tuples as TEXT (comma-separated)
    'list': 'TEXT',  # Store lists as TEXT (comma-separated)
    'NoneType': 'DOUBLE PRECISION',  # Use DOUBLE PRECISION for NoneType to avoid issues with NULL
}


class Export(GlancesExport):
    """This class manages the TimescaleDB export module."""

    def __init__(self, config=None, args=None):
        """Init the TimescaleDB export IF."""
        super().__init__(config=config, args=args)

        # Mandatory configuration keys (additional to host and port)
        self.db = None

        # Optional configuration keys
        self.user = None
        self.password = None
        self.hostname = None

        # Load the configuration file
        self.export_enable = self.load_conf(
            'timescaledb', mandatories=['host', 'port', 'db'], options=['user', 'password', 'hostname']
        )
        if not self.export_enable:
            exit('Missing TimescaleDB config')

        # The hostname is always add as an identifier in the TimescaleDB table
        # so we can filter the stats by hostname
        self.hostname = self.hostname or node().split(".")[0]

        # Init the TimescaleDB client
        self.client = self.init()

    def init(self):
        """Init the connection to the TimescaleDB server."""
        if not self.export_enable:
            return None

        try:
            # See https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-CONNSTRING
            conn_str = f"host={self.host} port={self.port} dbname={self.db} user={self.user} password={self.password}"
            db = psycopg.connect(conn_str)
        except Exception as e:
            logger.critical(f"Cannot connect to TimescaleDB server {self.host}:{self.port} ({e})")
            sys.exit(2)
        else:
            logger.info(f"Stats will be exported to TimescaleDB server: {self.host}:{self.port}")

        return db

    def normalize(self, value):
        """Normalize the value to be exportable to TimescaleDB."""
        if value is None:
            return 'NULL'
        if isinstance(value, bool):
            return str(value).upper()
        if isinstance(value, (list, tuple)):
            return ', '.join([f"'{v}'" for v in value])
        if isinstance(value, str):
            return f"'{value}'"

        return f"{value}"

    def update(self, stats):
        """Update the TimescaleDB export module."""
        if not self.export_enable:
            return False

        # Get all the stats & limits
        # Current limitation with sensors and fs plugins because fields list is not the same
        self._last_exported_list = [p for p in self.plugins_to_export(stats) if p not in ['sensors', 'fs']]
        all_stats = stats.getAllExportsAsDict(plugin_list=self.last_exported_list())
        all_limits = stats.getAllLimitsAsDict(plugin_list=self.last_exported_list())

        # Loop over plugins to export
        for plugin in self.last_exported_list():
            if isinstance(all_stats[plugin], dict):
                all_stats[plugin].update(all_limits[plugin])
                # Remove the <plugin>_disable field
                all_stats[plugin].pop(f"{plugin}_disable", None)
                # user is a special field that should not be exported
                # rename it to user_<plugin>
                if 'user' in all_stats[plugin]:
                    all_stats[plugin][f'user_{plugin}'] = all_stats[plugin].pop('user')
            elif isinstance(all_stats[plugin], list):
                for i in all_stats[plugin]:
                    i.update(all_limits[plugin])
                    # Remove the <plugin>_disable field
                    i.pop(f"{plugin}_disable", None)
                    # user is a special field that should not be exported
                    # rename it to user_<plugin>
                    if 'user' in i:
                        i[f'user_{plugin}'] = i.pop('user')
            else:
                continue

            plugin_stats = all_stats[plugin]
            creation_list = []  # List used to create the TimescaleDB table
            segmented_by = []  # List of columns used to segment the data
            values_list = []  # List of values to insert (list of lists, one list per row)
            if isinstance(plugin_stats, dict):
                # Stats is a dict
                # Create the list used to create the TimescaleDB table
                creation_list.append('time TIMESTAMPTZ NOT NULL')
                creation_list.append('hostname_id TEXT NOT NULL')
                segmented_by.extend(['hostname_id'])  # Segment by hostname
                for key, value in plugin_stats.items():
                    creation_list.append(f"{key} {convert_types[type(value).__name__]} NULL")
                values_list.append('NOW()')  # Add the current time (insertion time)
                values_list.append(f"'{self.hostname}'")  # Add the hostname
                values_list.extend([self.normalize(value) for value in plugin_stats.values()])
                values_list = [values_list]
            elif isinstance(plugin_stats, list) and len(plugin_stats) > 0 and 'key' in plugin_stats[0]:
                # Stats is a list
                # Create the list used to create the TimescaleDB table
                creation_list.append('time TIMESTAMPTZ NOT NULL')
                creation_list.append('hostname_id TEXT NOT NULL')
                creation_list.append('key_id TEXT NOT NULL')
                segmented_by.extend(['hostname_id', 'key_id'])  # Segment by hostname and key
                for key, value in plugin_stats[0].items():
                    creation_list.append(f"{key} {convert_types[type(value).__name__]} NULL")
                # Create the values list (it is a list of list to have a single datamodel for all the plugins)
                for plugin_item in plugin_stats:
                    item_list = []
                    item_list.append('NOW()')  # Add the current time (insertion time)
                    item_list.append(f"'{self.hostname}'")  # Add the hostname
                    item_list.append(f"'{plugin_item.get('key')}'")
                    item_list.extend([self.normalize(value) for value in plugin_item.values()])
                    values_list.append(item_list[:-1])
            else:
                continue

            # Export stats to TimescaleDB
            self.export(plugin, creation_list, segmented_by, values_list)

        return True

    def export(self, plugin, creation_list, segmented_by, values_list):
        """Export the stats to the TimescaleDB server."""
        logger.debug(f"Export {plugin} stats to TimescaleDB")

        with self.client.cursor() as cur:
            # Is the table exists?
            cur.execute(f"select exists(select * from information_schema.tables where table_name='{plugin}')")
            if not cur.fetchone()[0]:
                # Create the table if it does not exist
                # https://github.com/timescale/timescaledb/blob/main/README.md#create-a-hypertable
                # Execute the create table query
                create_query = f"""
CREATE TABLE {plugin} (
    {', '.join(creation_list)}
)
WITH (
    timescaledb.hypertable,
    timescaledb.partition_column='time',
    timescaledb.segmentby = '{", ".join(segmented_by)}'
);"""
                logger.debug(f"Create table: {create_query}")
                try:
                    cur.execute(create_query)
                except Exception as e:
                    logger.error(f"Cannot create table {plugin}: {e}")
                    return

            # Insert the data
            # https://github.com/timescale/timescaledb/blob/main/README.md#insert-and-query-data
            insert_list = [f"({','.join(i)})" for i in values_list]
            insert_query = f"INSERT INTO {plugin} VALUES {','.join(insert_list)};"
            logger.debug(f"Insert data into table: {insert_query}")
            try:
                cur.execute(insert_query)
            except Exception as e:
                logger.error(f"Cannot insert data into table {plugin}: {e}")
                return

        # Commit the changes (for every plugin or to be done at the end ?)
        self.client.commit()

    def exit(self):
        """Close the TimescaleDB export module."""
        # Force last write
        self.client.commit()

        # Close the TimescaleDB client
        time.sleep(3)  # Wait a bit to ensure all data is written
        self.client.close()

        # Call the father method
        super().exit()

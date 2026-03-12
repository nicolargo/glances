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
from datetime import datetime, timezone
from platform import node

import psycopg
from psycopg import sql

from glances.exports.export import GlancesExport
from glances.logger import logger

# Define the type conversions for TimescaleDB
# https://www.postgresql.org/docs/current/datatype.html
convert_types = {
    'bool': 'BOOLEAN',
    'int': 'BIGINT',
    'float': 'DOUBLE PRECISION',
    'str': 'TEXT',
    'tuple': 'TEXT',
    'list': 'TEXT',
    'NoneType': 'DOUBLE PRECISION',
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
            # In Glances plugins, it is generally recommended to log errors instead of exiting directly
            logger.critical("Missing TimescaleDB config")
            return

        # The hostname is always add as an identifier in the TimescaleDB table
        # so we can filter the stats by hostname
        self.hostname = self.hostname or node().split(".")[0]

        # Init the TimescaleDB client
        self.client = self.init()

    def init(self):
        """Init the connection to the TimescaleDB server."""
        if not self.export_enable:
            return None
        # lazy import psycopg
        try:
            import psycopg
        except ImportError:
            logger.critical(
                "TimescaleDB export requires 'psycopg' library. Install it with: pip install psycopg[binary]")
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
        """Normalize the value for use in a parameterized psycopg query (returns raw Python value)."""
        if isinstance(value, (list, tuple)):
            # Special case for list of one boolean
            if len(value) == 1 and isinstance(value[0], bool):
                return value[0]
            return ', '.join(str(v) for v in value)
        return value  # None → NULL, bool/str/int/float handled natively by psycopg

    def _prepare_stats(self, plugin, plugin_stats, plugin_limits):
        """Clean and normalize plugin data. Return a list regardless of whether the original data is a dictionary or a list"""
        # Normalize to a list for unified processing
        raw_items = [plugin_stats] if isinstance(plugin_stats, dict) else plugin_stats

        processed_items = []
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            # Perform a shallow copy and update to avoid modifying the original stats object
            new_item = item.copy()
            new_item.update(plugin_limits)
            new_item.pop(f"{plugin}_disable", None)

            # Handle special field 'user'
            if 'user' in new_item:
                new_item[f'user_{plugin}'] = new_item.pop('user')

            processed_items.append(new_item)

        return processed_items

    def update(self, stats):
        """Update the TimescaleDB export module."""
        if not self.export_enable or self.client is None:
            return False

        # Get all the stats & limits
        # @TODO: Current limitation with sensors, fs and diskio plugins because fields list is not the same

        # Filter out unsupported plugins
        self._last_exported_list = [p for p in self.plugins_to_export(stats) if p not in ['sensors', 'fs', 'diskio']]

        all_stats = stats.getAllExportsAsDict(plugin_list=self.last_exported_list())
        all_limits = stats.getAllLimitsAsDict(plugin_list=self.last_exported_list())

        for plugin in self.last_exported_list():
            # 1. Data preprocessing (reduce nesting depth)
            items = self._prepare_stats(plugin, all_stats.get(plugin), all_limits.get(plugin))
            if not items:
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
                values_list.append(datetime.now(timezone.utc))  # Add the current time (insertion time)
                values_list.append(self.hostname)  # Add the hostname
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
                    item_list.append(datetime.now(timezone.utc))  # Add the current time (insertion time)
                    item_list.append(self.hostname)  # Add the hostname
                    item_list.append(plugin_item.get('key'))
                    item_list.extend([self.normalize(value) for value in plugin_item.values()])
                    values_list.append(item_list[:-1])
            else:
                continue

                row.extend([self.normalize(v) for v in item.values()])

                # The original logic applies a special truncation (item_list[:-1]) for list types
                # This behavior is preserved here to ensure compatibility
                values_list.append(row[:-1] if is_list_type else row)

            # 4. Execute export
            self.export(plugin, creation_list, values_list, segmented_by=segmented_by)

        return True

    def export(self, plugin, creation_list, values_list, segmented_by=None):
        """Export the stats to the TimescaleDB server."""
        logger.debug(f"Export {plugin} stats to TimescaleDB")

        with self.client.cursor() as cur:
            # Is the table exists?
            cur.execute(
                "SELECT EXISTS(SELECT * FROM information_schema.tables WHERE table_name=%s)",
                [plugin],
            )
            if not cur.fetchone()[0]:
                # Create the table if it does not exist
                # https://github.com/timescale/timescaledb/blob/main/README.md#create-a-hypertable
                # Build CREATE TABLE using sql.Identifier for column names (prevents injection)
                # Each item in creation_list is "colname TYPE [NULL|NOT NULL]"
                fields = sql.SQL(', ').join(
                    sql.SQL("{} {}").format(sql.Identifier(item.split(' ')[0]), sql.SQL(' '.join(item.split(' ')[1:])))
                    for item in creation_list
                )
                create_query = sql.SQL(
                    "CREATE TABLE {table} ({fields}) WITH ("
                    "timescaledb.hypertable, "
                    "timescaledb.partition_column='time', "
                    "timescaledb.segmentby = {segmentby});"
                ).format(
                    table=sql.Identifier(plugin),
                    fields=fields,
                    segmentby=sql.Literal(', '.join(segmented_by)),
                )
                logger.debug(f"Create table: {create_query}")
                try:
                    cur.execute(create_query)
                except Exception as e:
                    logger.error(f"Cannot create table {plugin}: {e}")
                    return

            # Insert the data using parameterized queries (prevents injection)
            # https://github.com/timescale/timescaledb/blob/main/README.md#insert-and-query-data
            col_names = [item.split(' ')[0] for item in creation_list]
            cols = sql.SQL(', ').join(sql.Identifier(c) for c in col_names)
            placeholders = sql.SQL(', ').join(sql.Placeholder() for _ in col_names)
            insert_query = sql.SQL("INSERT INTO {table} ({cols}) VALUES ({vals})").format(
                table=sql.Identifier(plugin),
                cols=cols,
                vals=placeholders,
            )
            logger.debug(f"Insert data into table: {insert_query}")
            try:
                cur.executemany(insert_query, values_list)
            except Exception as e:
                logger.error(f"Cannot insert data into table {plugin}: {e}")
                return

            self.client.commit()
        except Exception as e:
            logger.error(f"TimescaleDB export error for {plugin}: {e}")
            self.client.rollback()

    def _create_hypertable(self, cursor, plugin, creation_list, segmented_by):
        """Create a TimescaleDB hypertable."""
        create_query = f"""
            CREATE TABLE {plugin} ({', '.join(creation_list)})
            WITH (
                timescaledb.hypertable,
                timescaledb.partition_column='time',
                timescaledb.segmentby = '{", ".join(segmented_by)}'
            );
        """
        logger.debug(f"Creating table: {plugin}")
        cursor.execute(create_query)

    def exit(self):
        """Close the TimescaleDB export module."""
        if self.client:
            try:
                self.client.commit()
                # Only wait if the connection is still alive
                time.sleep(1)
                self.client.close()
            except Exception as e:
                self.logger.debug(f"TimescaleDB export failed: {e}")
        super().exit()

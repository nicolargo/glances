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
        super().__init__(config=config, args=args)

        self.db = None
        self.user = None
        self.password = None
        self.hostname = None

        self.export_enable = self.load_conf(
            'timescaledb', mandatories=['host', 'port', 'db'], options=['user', 'password', 'hostname']
        )

        if not self.export_enable:
            # In Glances plugins, it is generally recommended to log errors instead of exiting directly
            logger.critical("Missing TimescaleDB config")
            return

        self.hostname = self.hostname or node().split(".")[0]
        self.client = self.init()

    def init(self):
        """Init the connection to the TimescaleDB server."""
        if not self.export_enable:
            return None

        try:
            conn_str = f"host={self.host} port={self.port} dbname={self.db} user={self.user} password={self.password}"
            db = psycopg.connect(conn_str)
            logger.info(f"Stats will be exported to TimescaleDB server: {self.host}:{self.port}")
            return db
        except Exception as e:
            logger.critical(f"Cannot connect to TimescaleDB server {self.host}:{self.port} ({e})")
            sys.exit(2)

    def normalize(self, value):
        """Normalize the value to be exportable to TimescaleDB."""
        if value is None:
            return 'NULL'
        if isinstance(value, bool):
            return str(value).upper()
        if isinstance(value, (list, tuple)):
            if len(value) == 1 and isinstance(value[0], bool):
                return str(value[0]).upper()
            return ', '.join([f"'{v}'" for v in value])
        if isinstance(value, str):
            return f"'{value}'"
        return f"{value}"

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

        # Filter out unsupported plugins
        self._last_exported_list = [p for p in self.plugins_to_export(stats) if p not in ['sensors', 'fs', 'diskio']]

        all_stats = stats.getAllExportsAsDict(plugin_list=self.last_exported_list())
        all_limits = stats.getAllLimitsAsDict(plugin_list=self.last_exported_list())

        for plugin in self.last_exported_list():
            # 1. Data preprocessing (reduce nesting depth)
            items = self._prepare_stats(plugin, all_stats.get(plugin), all_limits.get(plugin))
            if not items:
                continue

            # 2. Generate metadata (table schema and segmentation information)
            creation_list = ['time TIMESTAMPTZ NOT NULL', 'hostname_id TEXT NOT NULL']
            segmented_by = ['hostname_id']

            # If it is a list type (e.g., process list), add key_id for identification
            is_list_type = isinstance(all_stats[plugin], list) and 'key' in items[0]
            if is_list_type:
                creation_list.append('key_id TEXT NOT NULL')
                segmented_by.append('key_id')

            # Dynamically generate column definitions based on the first item
            for key, value in items[0].items():
                v_type = convert_types.get(type(value).__name__, 'TEXT')
                creation_list.append(f"{key} {v_type} NULL")

            # 3. Prepare value rows for insertion
            values_list = []
            for item in items:
                row = ['NOW()', f"'{self.hostname}'"]
                if is_list_type:
                    row.append(f"'{item.get('key')}'")

                row.extend([self.normalize(v) for v in item.values()])

                # The original logic applies a special truncation (item_list[:-1]) for list types
                # This behavior is preserved here to ensure compatibility
                values_list.append(row[:-1] if is_list_type else row)

            # 4. Execute export
            self.export(plugin, creation_list, segmented_by, values_list)

        return True

    def export(self, plugin, creation_list, segmented_by, values_list):
        """Export the stats to the TimescaleDB server."""
        try:
            with self.client.cursor() as cur:
                # Check whether the table exists
                cur.execute("SELECT exists(SELECT * FROM information_schema.tables WHERE table_name=%s)", (plugin,))
                if not cur.fetchone()[0]:
                    self._create_hypertable(cur, plugin, creation_list, segmented_by)

                # Bulk insert data
                insert_rows = [f"({','.join(row)})" for row in values_list]
                safe_table = "".join(c for c in plugin if c.isalnum() or c == '_')
                insert_query = "INSERT INTO {} VALUES {};".format(safe_table, ','.join(insert_rows))
                cur.execute(insert_query)

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

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

try:
    import psycopg
    from psycopg import sql
except ImportError:
    psycopg = None

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

        if psycopg is None:
            logger.critical(
                "TimescaleDB export requires 'psycopg' library. Install it with: pip install psycopg[binary]")
            self.export_enable = False
            return None

        try:
            # See https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-CONNSTRING
            conn_str = f"host={self.host} port={self.port} dbname={self.db} user={self.user} password={self.password}"
            db = psycopg.connect(conn_str)
            logger.info(f"Stats will be exported to TimescaleDB server: {self.host}:{self.port}")
            return db
        except Exception as e:
            logger.critical(f"Cannot connect to TimescaleDB server {self.host}:{self.port} ({e})")
            self.export_enable = False
            return None

    def normalize(self, value):
        """Normalize the value for use in a parameterized psycopg query (returns raw Python value)."""
        if isinstance(value, (list, tuple)):
            # Special case for list of one boolean
            if len(value) == 1 and isinstance(value[0], bool):
                return value[0]
            return ', '.join(str(v) for v in value)
        return value  # None → NULL, bool/str/int/float handled natively by psycopg

    def update(self, stats):
        """Update the TimescaleDB export module."""
        if not self.export_enable or self.client is None:
            return False

        # Filter out unsupported plugins
        # @TODO: Current limitation with sensors, fs and diskio plugins because fields list is not the same
        self._last_exported_list = [p for p in self.plugins_to_export(stats) if p not in ['sensors', 'fs', 'diskio']]

        all_stats = stats.getAllExportsAsDict(plugin_list=self.last_exported_list())
        
        for plugin in self.last_exported_list():
            plugin_stats = all_stats.get(plugin)
            if not plugin_stats:
                continue

            creation_list = ['time TIMESTAMPTZ NOT NULL', 'hostname_id TEXT NOT NULL']
            segmented_by = ['hostname_id']
            values_list = []
            
            now = datetime.now(timezone.utc)
            is_list_type = isinstance(plugin_stats, list) and len(plugin_stats) > 0 and 'key' in plugin_stats[0]

            if is_list_type:
                # Stats is a list (e.g. process list)
                creation_list.append('key_id TEXT NOT NULL')
                segmented_by.append('key_id')
                for key, value in plugin_stats[0].items():
                    creation_list.append(f"{key} {convert_types.get(type(value).__name__, 'TEXT')} NULL")
                
                for item in plugin_stats:
                    row = [now, self.hostname, item.get('key')]
                    row.extend([self.normalize(v) for v in item.values()])
                    # Preserve original logic: truncation for list-type to avoid column mismatch
                    values_list.append(row[:-1])
            elif isinstance(plugin_stats, dict):
                # Stats is a dict
                for key, value in plugin_stats.items():
                    creation_list.append(f"{key} {convert_types.get(type(value).__name__, 'TEXT')} NULL")
                
                row = [now, self.hostname]
                row.extend([self.normalize(value) for value in plugin_stats.values()])
                values_list.append(row)
            else:
                continue

            # Execute export
            self.export(plugin, creation_list, values_list, segmented_by=segmented_by)

        return True

    def export(self, plugin, creation_list, values_list, segmented_by=None):
        """Export the stats to the TimescaleDB server."""
        if not values_list:
            return

        try:
            with self.client.cursor() as cur:
                # Check if the table exists
                cur.execute(
                    "SELECT EXISTS(SELECT * FROM information_schema.tables WHERE table_name=%s)",
                    [plugin],
                )
                if not cur.fetchone()[0]:
                    # Create the table if it does not exist
                    # https://github.com/timescale/timescaledb/blob/main/README.md#create-a-hypertable
                    fields = sql.SQL(', ').join(
                        sql.SQL("{} {}").format(sql.Identifier(item.split(' ')[0]), sql.SQL(' '.join(item.split(' ')[1:])))
                        for item in creation_list
                    )
                    
                    sb_sql = sql.SQL(', ').join(sql.Identifier(sb) for sb in (segmented_by or []))
                    
                    create_query = sql.SQL(
                        "CREATE TABLE {table} ({fields}) WITH (timescaledb.hypertable, "
                        "timescaledb.partition_column='time', timescaledb.segmentby = {sb});"
                    ).format(
                        table=sql.Identifier(plugin),
                        fields=fields,
                        sb=sb_sql
                    )
                    cur.execute(create_query)

                # Insert the data using parameterized queries (prevents injection)
                # https://github.com/timescale/timescaledb/blob/main/README.md#insert-and-query-data
                col_names = [item.split(' ')[0] for item in creation_list]
                row_len = len(values_list[0])
                actual_cols = sql.SQL(', ').join(sql.Identifier(c) for c in col_names[:row_len])
                placeholders = sql.SQL(', ').join(sql.Placeholder() for _ in range(row_len))
                
                insert_query = sql.SQL("INSERT INTO {table} ({cols}) VALUES ({vals})").format(
                    table=sql.Identifier(plugin),
                    cols=actual_cols,
                    vals=placeholders,
                )
                cur.executemany(insert_query, values_list)
            
            self.client.commit()
        except Exception as e:
            logger.error(f"TimescaleDB export error for {plugin}: {e}")
            self.client.rollback()

    def exit(self):
        """Close the TimescaleDB export module."""
        if self.client:
            try:
                self.client.close()
            except Exception:
                pass
        super().exit()
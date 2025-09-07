#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2025 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""DuckDB interface class."""

import sys
import time
from datetime import datetime
from platform import node

import duckdb

from glances.exports.export import GlancesExport
from glances.logger import logger

# Define the type conversions for DuckDB
# https://duckdb.org/docs/stable/clients/python/conversion
convert_types = {
    'bool': 'BOOLEAN',
    'int': 'BIGINT',
    'float': 'DOUBLE',
    'str': 'VARCHAR',
    'tuple': 'VARCHAR',  # Store tuples as VARCHAR (comma-separated)
    'list': 'VARCHAR',  # Store lists as VARCHAR (comma-separated)
    'NoneType': 'VARCHAR',
}


class Export(GlancesExport):
    """This class manages the DuckDB export module."""

    def __init__(self, config=None, args=None):
        """Init the DuckDB export IF."""
        super().__init__(config=config, args=args)

        # Mandatory configuration keys (additional to host and port)
        self.db = None

        # Optional configuration keys
        self.user = None
        self.password = None
        self.hostname = None

        # Load the configuration file
        self.export_enable = self.load_conf(
            'duckdb', mandatories=['database'], options=['user', 'password', 'hostname']
        )
        if not self.export_enable:
            exit('Missing DuckDB config')

        # The hostname is always add as an identifier in the DuckDB table
        # so we can filter the stats by hostname
        self.hostname = self.hostname or node().split(".")[0]

        # Init the DuckDB client
        self.client = self.init()

    def init(self):
        """Init the connection to the DuckDB server."""
        if not self.export_enable:
            return None

        try:
            db = duckdb.connect(database=self.database)
        except Exception as e:
            logger.critical(f"Cannot connect to DuckDB {self.database} ({e})")
            sys.exit(2)
        else:
            logger.info(f"Stats will be exported to DuckDB: {self.database}")

        return db

    def normalize(self, value):
        # Nothing to do...
        if isinstance(value, list) and len(value) == 1 and value[0] in ['True', 'False']:
            return bool(value[0])
        return value

    def update(self, stats):
        """Update the DuckDB export module."""
        if not self.export_enable:
            return False

        # Get all the stats & limits
        # Current limitation with sensors and fs plugins because fields list is not the same
        self._last_exported_list = [p for p in self.plugins_to_export(stats) if p not in ['sensors', 'fs']]
        all_stats = stats.getAllExportsAsDict(plugin_list=self.last_exported_list())
        all_limits = stats.getAllLimitsAsDict(plugin_list=self.last_exported_list())

        # Loop over plugins to export
        for plugin in self.last_exported_list():
            # Remove some fields
            if isinstance(all_stats[plugin], dict):
                all_stats[plugin].update(all_limits[plugin])
                # Remove the <plugin>_disable field
                all_stats[plugin].pop(f"{plugin}_disable", None)
            elif isinstance(all_stats[plugin], list):
                for i in all_stats[plugin]:
                    i.update(all_limits[plugin])
                    # Remove the <plugin>_disable field
                    i.pop(f"{plugin}_disable", None)
            else:
                continue

            plugin_stats = all_stats[plugin]
            creation_list = []  # List used to create the DuckDB table
            values_list = []  # List of values to insert (list of lists, one list per row)
            if isinstance(plugin_stats, dict):
                # Create the list to create the table
                creation_list.append('time TIMETZ')
                creation_list.append('hostname_id VARCHAR')
                for key, value in plugin_stats.items():
                    creation_list.append(f"{key} {convert_types[type(self.normalize(value)).__name__]}")
                # Create the list of values to insert
                item_list = []
                item_list.append(self.normalize(datetime.now().replace(microsecond=0)))
                item_list.append(self.normalize(f"{self.hostname}"))
                item_list.extend([self.normalize(value) for value in plugin_stats.values()])
                values_list = [item_list]
            elif isinstance(plugin_stats, list) and len(plugin_stats) > 0 and 'key' in plugin_stats[0]:
                # Create the list to create the table
                creation_list.append('time TIMETZ')
                creation_list.append('hostname_id VARCHAR')
                creation_list.append('key_id VARCHAR')
                for key, value in plugin_stats[0].items():
                    creation_list.append(f"{key} {convert_types[type(self.normalize(value)).__name__]}")
                # Create the list of values to insert
                for plugin_item in plugin_stats:
                    item_list = []
                    item_list.append(self.normalize(datetime.now().replace(microsecond=0)))
                    item_list.append(self.normalize(f"{self.hostname}"))
                    item_list.append(self.normalize(f"{plugin_item.get('key')}"))
                    item_list.extend([self.normalize(value) for value in plugin_item.values()])
                    values_list.append(item_list)
            else:
                continue

            # Export stats to DuckDB
            self.export(plugin, creation_list, values_list)

        return True

    def export(self, plugin, creation_list, values_list):
        """Export the stats to the DuckDB server."""
        logger.debug(f"Export {plugin} stats to DuckDB")

        # Create the table if it does not exist
        table_list = [t[0] for t in self.client.sql("SHOW TABLES").fetchall()]
        if plugin not in table_list:
            # Execute the create table query
            create_query = f"""
CREATE TABLE {plugin} (
{', '.join(creation_list)}
);"""
            logger.debug(f"Create table: {create_query}")
            try:
                self.client.execute(create_query)
            except Exception as e:
                logger.error(f"Cannot create table {plugin}: {e}")
                return

        # Commit the changes
        self.client.commit()

        # Insert values into the table
        for values in values_list:
            insert_query = f"""
INSERT INTO {plugin} VALUES (
{', '.join(['?' for _ in values])}
);"""
            logger.debug(f"Insert values into table {plugin}: {values}")
            try:
                self.client.execute(insert_query, values)
            except Exception as e:
                logger.error(f"Cannot insert data into table {plugin}: {e}")

        # Commit the changes
        self.client.commit()

    def exit(self):
        """Close the DuckDB export module."""
        # Force last write
        self.client.commit()

        # Close the DuckDB client
        time.sleep(3)  # Wait a bit to ensure all data is written
        self.client.close()

        # Call the father method
        super().exit()

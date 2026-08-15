#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""ClickHouse interface class."""

import sys
import threading
import time
from datetime import datetime, timezone
from platform import node

import clickhouse_connect

from glances.exports.export import GlancesExport
from glances.logger import logger

# Define the type conversions for ClickHouse
# https://clickhouse.com/docs/en/sql-reference/data-types/
convert_types = {
    'bool': 'Nullable(Bool)',
    'int': 'Nullable(Int64)',
    'float': 'Nullable(Float64)',
    'str': 'Nullable(String)',
    'tuple': 'Nullable(String)',  # Store tuples as TEXT (comma-separated)
    'list': 'Nullable(String)',  # Store lists as TEXT (comma-separated)
    'NoneType': 'Nullable(String)',  # None could be any type, use String as safest default
}


def _infer_ch_type(values):
    """Infer the best ClickHouse type from a list of values.

    Priority: if any value is a str → String, else float > int > bool.
    If all values are None → String (safest default).
    """
    has_str = False
    has_float = False
    has_int = False
    has_bool = False
    for v in values:
        if v is None:
            continue
        if isinstance(v, str):
            has_str = True
            break  # str wins, no need to check further
        if isinstance(v, bool):
            has_bool = True
        elif isinstance(v, float):
            has_float = True
        elif isinstance(v, int):
            has_int = True
        else:
            # list, tuple, dict, etc. → store as string
            has_str = True
            break
    if has_str:
        return 'Nullable(String)'
    if has_float:
        return 'Nullable(Float64)'
    if has_int:
        return 'Nullable(Int64)'
    if has_bool:
        return 'Nullable(Bool)'
    return 'Nullable(String)'


class Export(GlancesExport):
    """This class manages the ClickHouse export module."""

    def __init__(self, config=None, args=None):
        """Init the ClickHouse export IF."""
        super().__init__(config=config, args=args)

        # Mandatory configuration keys (additional to host and port)
        self.db = None

        # Optional configuration keys
        self.hostname = None

        # Load the configuration file
        self.export_enable = self.load_conf(
            'clickhouse', mandatories=['host', 'port', 'db', 'user', 'password'], options=['hostname']
        )
        if not self.export_enable:
            exit('Missing ClickHouse config')

        # The hostname is always add as an identifier in the ClickHouse table
        # so we can filter the stats by hostname
        self.hostname = self.hostname or node().split(".")[0]

        # Init the ClickHouse client
        self._lock = threading.Lock()
        self.client = self.init()

    def init(self):
        """Init the connection to the ClickHouse server."""
        if not self.export_enable:
            return None

        try:
            client = clickhouse_connect.get_client(
                host=self.host, port=self.port, username=self.user, password=self.password, database=self.db
            )
        except Exception as e:
            logger.critical(f"Cannot connect to ClickHouse server {self.host}:{self.port} ({e})")
            sys.exit(2)
        else:
            logger.info(f"Stats will be exported to ClickHouse server: {self.host}:{self.port}")

        return client

    def normalize(self, value):
        """Normalize the value for use in a parameterized ClickHouse query."""
        return value

    def update(self, stats):
        """Update the ClickHouse export module."""
        if not self.export_enable:
            return False

        # Get all the stats & limits
        # @TODO: Current limitation with sensors, fs and diskio plugins because fields list is not the same
        self._last_exported_list = list(self.plugins_to_export(stats))
        all_stats = stats.getAllExportsAsDict(plugin_list=self.last_exported_list())
        all_limits = stats.getAllLimitsAsDict(plugin_list=self.last_exported_list())

        # Loop over plugins to export
        for plugin in self.last_exported_list():
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
            creation_list = []  # List used to create the ClickHouse table
            values_list = []  # List of values to insert (list of lists, one list per row)
            if isinstance(plugin_stats, dict):
                # Stats is a dict
                # Create the list used to create the ClickHouse table
                creation_list.append('`time` DateTime')
                creation_list.append('`hostname_id` String')
                for key, value in plugin_stats.items():
                    ch_type = _infer_ch_type([value])
                    creation_list.append(f"`{key}` {ch_type}")
                values_list.append('NOW()')  # Add the current time (insertion time)
                values_list.append(self.hostname)  # Add the hostname
                values_list.extend([self.normalize(value) for value in plugin_stats.values()])
                values_list = [values_list]
            elif isinstance(plugin_stats, list) and len(plugin_stats) > 0 and 'key' in plugin_stats[0]:
                # Stats is a list
                # Collect all keys across all items to handle varying schemas
                all_keys = []
                seen = set()
                for item in plugin_stats:
                    for k in item:
                        if k == 'key':
                            continue
                        if k not in seen:
                            seen.add(k)
                            all_keys.append(k)
                # Create the list used to create the ClickHouse table
                creation_list.append('`time` DateTime')
                creation_list.append('`hostname_id` String')
                creation_list.append('`key_id` String')
                # Infer type by scanning ALL values across all items for each key
                for col_key in all_keys:
                    col_values = [item.get(col_key) for item in plugin_stats]
                    ch_type = _infer_ch_type(col_values)
                    creation_list.append(f"`{col_key}` {ch_type}")
                # Create the values list
                for plugin_item in plugin_stats:
                    item_list = []
                    item_list.append('NOW()')  # Add the current time (insertion time)
                    item_list.append(self.hostname)  # Add the hostname
                    item_list.append(plugin_item.get('key'))
                    for col_key in all_keys:
                        item_list.append(self.normalize(plugin_item.get(col_key)))
                    values_list.append(item_list)
            else:
                continue

            # Export stats to ClickHouse
            self.export(plugin, creation_list, values_list)

        return True

    def export(self, plugin, creation_list, values_list):
        """Export the stats to the ClickHouse server."""
        logger.debug(f"Export {plugin} stats to ClickHouse")

        # Build column names from creation_list (format: "`name` Type")
        # Strip backticks for the insert column_names parameter
        column_names = [col.split()[0].strip('`') for col in creation_list]

        # Prepare all rows before acquiring the lock
        rows = []
        for values in values_list:
            row = []
            for v in values:
                if v == 'NOW()':
                    row.append(datetime.now(tz=timezone.utc))
                elif isinstance(v, (list, tuple)):
                    row.append(str(v))
                else:
                    row.append(v)
            rows.append(row)

        # Serialize all ClickHouse operations to avoid concurrent session errors
        with self._lock:
            # Create the table if it does not exist
            create_query = f"""
                CREATE TABLE IF NOT EXISTS `{plugin}`
                ({', '.join(creation_list)})
                ENGINE = MergeTree()
                ORDER BY `time`
            """
            try:
                self.client.command(create_query)
            except Exception as e:
                logger.error(f"Error creating ClickHouse table {plugin} ({e})")
                return False

            # Schema evolution: add missing columns or fix type mismatches
            try:
                existing_cols = {row[0]: row[1] for row in self.client.query(f"DESCRIBE TABLE `{plugin}`").result_rows}
                for col_def in creation_list:
                    parts = col_def.split(maxsplit=1)
                    col_name = parts[0].strip('`')
                    col_type = parts[1]
                    if col_name not in existing_cols:
                        self.client.command(f"ALTER TABLE `{plugin}` ADD COLUMN IF NOT EXISTS `{col_name}` {col_type}")
                    elif existing_cols[col_name] != col_type and col_name not in ('time', 'hostname_id', 'key_id'):
                        # Type mismatch: modify the column type
                        logger.debug(
                            f"ClickHouse table {plugin}: changing column `{col_name}` "
                            f"from {existing_cols[col_name]} to {col_type}"
                        )
                        self.client.command(f"ALTER TABLE `{plugin}` MODIFY COLUMN `{col_name}` {col_type}")
            except Exception as e:
                logger.warning(f"Error checking/adding columns for {plugin} ({e})")

            # Insert all rows in a single call
            if rows:
                try:
                    self.client.insert(
                        table=plugin,
                        data=rows,
                        column_names=column_names,
                    )
                except Exception as e:
                    logger.error(f"Error inserting data into ClickHouse table {plugin} ({e})")
                    return False

        return True

    def exit(self):
        """Close the ClickHouse export module."""
        # Close the ClickHouse client
        time.sleep(3)  # Wait a bit to ensure all data is written
        self.client.close()

        # Call the father method
        super().exit()

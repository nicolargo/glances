#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — DuckDB export module (P3-3, wave D).

Ported from the v4 module in this directory: same `[duckdb]` section, same
tables (one per plugin, named after it), same columns (`time`,
`hostname_id`, `key_id` for a collection, then one column per field, `key`
included) and the same DuckDB types, so an existing database keeps working.

Carries the fix for CVE-2026-32611 (SQL injection in the DuckDB DDL):

- every IDENTIFIER — the table (plugin name) and each column (field name) —
  goes through `quote_identifier()`: wrapped in double quotes with any
  embedded double quote doubled, DuckDB's own identifier quoting, so no
  name can end the identifier and start a statement;
- every VALUE — interface, process, mount point and container names, the
  hostname — is a `?` bound parameter, never part of the statement text;
- the column TYPE is chosen from a fixed map, never from the data.

`duckdb` is imported when the exporter starts, so this module stays
importable without it.
"""

from __future__ import annotations

import sys
from datetime import datetime
from platform import node
from typing import TYPE_CHECKING, Any

from glances.exports.export_base_v5 import GlancesExportBase
from glances.logger import logger

if TYPE_CHECKING:
    import argparse

    from glances.config_v5 import GlancesConfigV5
    from glances.plugins.plugin.base_v5 import GlancesPluginBase

# Python type name -> DuckDB column type (v4, verbatim).
# https://duckdb.org/docs/stable/clients/python/conversion
convert_types = {
    "bool": "BOOLEAN",
    "int": "BIGINT",
    "float": "DOUBLE",
    "str": "VARCHAR",
    "tuple": "VARCHAR",
    "list": "VARCHAR",
    "NoneType": "VARCHAR",
}

# v4: the field lists of these plugins vary between items.
_SKIPPED_PLUGINS = ("sensors", "fs")


def quote_identifier(name: str) -> str:
    """Quote a DuckDB identifier: `"…"`, embedded double quotes doubled."""
    return '"' + str(name).replace('"', '""') + '"'


def normalize(value: Any) -> Any:
    """v4, verbatim: a one-item `['True']`/`['False']` list is a boolean."""
    if isinstance(value, list) and len(value) == 1 and value[0] in ["True", "False"]:
        return bool(value[0])
    return value


def _column(name: str, value: Any) -> str:
    return f"{quote_identifier(name)} {convert_types[type(normalize(value)).__name__]}"


class Export(GlancesExportBase):
    """Write Glances stats to a DuckDB database, one table per plugin."""

    export_name = "duckdb"

    def __init__(self, config: GlancesConfigV5, args: argparse.Namespace | None = None) -> None:
        super().__init__(config, args)
        self.database: str | None = None
        self.user: str | None = None
        self.password: str | None = None
        self.hostname: str | None = None
        if not self.load_conf("duckdb", mandatories=("database",), options=("user", "password", "hostname")):
            logger.critical("Missing duckdb config")
            sys.exit(2)
        # Always stored, so the stats of several hosts can share a database.
        self.hostname = self.hostname or node().split(".")[0]
        self.client = self.init()

    def init(self) -> Any:
        try:
            import duckdb
        except ImportError as e:
            logger.critical("Export duckdb needs the duckdb library (%s)", e)
            sys.exit(2)
        try:
            client = duckdb.connect(database=self.database)
        except Exception as e:
            logger.critical("Cannot connect to DuckDB %s (%s)", self.database, e)
            sys.exit(2)
        logger.info("Stats will be exported to DuckDB: %s", self.database)
        return client

    # ------------------------------------------------------------ rows

    def _rows(self, payload: dict | list) -> tuple[list[str], list[list[Any]]] | None:
        """Build (column definitions, rows) in the v4 layout."""
        now = datetime.now().replace(microsecond=0)
        columns = [f"{quote_identifier('time')} TIMETZ", f"{quote_identifier('hostname_id')} VARCHAR"]
        if isinstance(payload, dict):
            columns += [_column(key, value) for key, value in payload.items()]
            return columns, [[now, self.hostname] + [normalize(v) for v in payload.values()]]
        if isinstance(payload, list) and payload and "key" in payload[0]:
            columns.append(f"{quote_identifier('key_id')} VARCHAR")
            columns += [_column(key, value) for key, value in payload[0].items()]
            rows = [
                [now, self.hostname, f"{item.get('key')}"] + [normalize(v) for v in item.values()] for item in payload
            ]
            return columns, rows
        return None

    # ---------------------------------------------------------- update

    def update(self, plugins: list[GlancesPluginBase]) -> None:
        """One row per scalar plugin, one row per item of a collection.

        Overrides the base: a SQL row needs the structured payload, not the
        flattened `<item>.<field>` columns `build_export()` produces. Holds
        `_lifecycle_lock` itself, since it never calls `super().update()`.
        """
        with self._lifecycle_lock:
            for plugin in plugins:
                if not getattr(plugin, "EXPORTABLE", True) or plugin.plugin_name in _SKIPPED_PLUGINS:
                    continue
                name = plugin.plugin_name
                try:
                    payload = plugin.get_export()
                    if not payload:
                        continue
                    built = self._rows(self._merge_limits(plugin, self._inject_key(plugin, payload)))
                    if built is not None:
                        self._write(name, *built)
                except Exception as e:
                    logger.warning("Cannot export %s stats to DuckDB (%s)", name, e)

    def export(self, name: str, columns: list[str], points: list[Any]) -> None:
        """Unused — rows are built from the structured payload in update()."""

    def _write(self, table: str, columns: list[str], rows: list[list[Any]]) -> None:
        quoted = quote_identifier(table)
        if table not in [t[0] for t in self.client.sql("SHOW TABLES").fetchall()]:
            self.client.execute(f"CREATE TABLE {quoted} ({', '.join(columns)});")
            self.client.commit()
        placeholders = ", ".join("?" for _ in rows[0])
        self.client.executemany(f"INSERT INTO {quoted} VALUES ({placeholders});", rows)
        self.client.commit()
        logger.debug("Export %s stats to DuckDB", table)

    def exit(self) -> None:
        super().exit()
        try:
            self.client.close()
        except Exception as e:
            logger.debug("Cannot close the DuckDB connection (%s)", e)

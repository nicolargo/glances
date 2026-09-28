#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — TimescaleDB export module (P3-3, wave D).

Ported from the v4 module in this directory: same `[timescaledb]` section,
same tables (one hypertable per plugin, named after it), same columns
(`time`, `hostname_id`, `key_id` for a collection, then one column per
field) and the same PostgreSQL types, so an existing database keeps working.

Carries the fix for CVE-2026-30930 (SQL injection through monitored data):

- every VALUE — process names, mount points, interface names, container
  names, the hostname — is a bound parameter (`%s` placeholders built with
  `psycopg.sql.Placeholder`), never part of the statement text;
- every IDENTIFIER — the table (plugin name) and each column (field name) —
  goes through `psycopg.sql.Identifier`, the driver's own quoting;
- the column TYPE is chosen from a fixed map and is the only raw SQL
  fragment. v4 kept each column as a `"name TYPE NULL"` string and split it
  on the first space, so a field name containing a space leaked its tail
  into `sql.SQL()` as raw SQL; v5 keeps the name and the type apart.

The connection is opened with keyword arguments instead of v4's
interpolated libpq conninfo string, so a password containing a space or a
quote can neither break nor extend the connection parameters.
`psycopg` is imported when the exporter starts, so this module stays
importable without it.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from platform import node
from typing import TYPE_CHECKING, Any

from glances.exports.export_base_v5 import GlancesExportBase
from glances.logger import logger

if TYPE_CHECKING:
    import argparse

    from glances.config_v5 import GlancesConfigV5
    from glances.plugins.plugin.base_v5 import GlancesPluginBase

# Python type name -> PostgreSQL column type (v4, verbatim).
# https://www.postgresql.org/docs/current/datatype.html
convert_types = {
    "bool": "BOOLEAN",
    "int": "BIGINT",
    "float": "DOUBLE PRECISION",
    "str": "TEXT",
    "tuple": "TEXT",
    "list": "TEXT",
    "NoneType": "DOUBLE PRECISION",
}

# v4: the field lists of these plugins vary between items.
_SKIPPED_PLUGINS = ("sensors", "fs", "diskio")


def normalize(value: Any) -> Any:
    """Turn a stat into a value psycopg binds natively (v4, verbatim)."""
    if isinstance(value, (list, tuple)):
        if len(value) == 1 and isinstance(value[0], bool):
            return value[0]
        return ", ".join(str(v) for v in value)
    return value


class Export(GlancesExportBase):
    """Write Glances stats to TimescaleDB hypertables, one per plugin."""

    export_name = "timescaledb"

    def __init__(self, config: GlancesConfigV5, args: argparse.Namespace | None = None) -> None:
        super().__init__(config, args)
        self.db: str | None = None
        self.user: str | None = None
        self.password: str | None = None
        self.hostname: str | None = None
        if not self.load_conf(
            "timescaledb", mandatories=("host", "port", "db"), options=("user", "password", "hostname")
        ):
            logger.critical("Missing timescaledb config")
            sys.exit(2)
        # Always stored, so the stats of several hosts can share a database.
        self.hostname = self.hostname or node().split(".")[0]
        self.client = self.init()

    def init(self) -> Any:
        try:
            import psycopg
            from psycopg import sql
        except ImportError as e:
            logger.critical("Export timescaledb needs the psycopg library (%s)", e)
            sys.exit(2)
        self.sql = sql
        try:
            client = psycopg.connect(
                host=self.host, port=self.port, dbname=self.db, user=self.user, password=self.password
            )
        except Exception as e:
            logger.critical("Cannot connect to TimescaleDB server %s:%s (%s)", self.host, self.port, e)
            sys.exit(2)
        logger.info("Stats will be exported to TimescaleDB server %s:%s", self.host, self.port)
        return client

    # ------------------------------------------------------------ rows

    def _rows(
        self, plugin: str, payload: dict | list
    ) -> tuple[list[tuple[str, str]], list[str], list[list[Any]]] | None:
        """Build (columns as (name, type), segment-by columns, rows), v4 layout."""
        now = datetime.now(timezone.utc)
        columns = [("time", "TIMESTAMPTZ NOT NULL"), ("hostname_id", "TEXT NOT NULL")]
        if isinstance(payload, dict):
            stats = self._rename_user(plugin, payload)
            columns += [(key, f"{convert_types[type(value).__name__]} NULL") for key, value in stats.items()]
            return columns, ["hostname_id"], [[now, self.hostname] + [normalize(v) for v in stats.values()]]
        if isinstance(payload, list) and payload and "key" in payload[0]:
            items = [self._rename_user(plugin, item) for item in payload]
            columns.append(("key_id", "TEXT NOT NULL"))
            columns += [
                (key, f"{convert_types[type(value).__name__]} NULL") for key, value in items[0].items() if key != "key"
            ]
            rows = [
                [now, self.hostname, item.get("key")] + [normalize(v) for k, v in item.items() if k != "key"]
                for item in items
            ]
            return columns, ["hostname_id", "key_id"], rows
        return None

    @staticmethod
    def _rename_user(plugin: str, stats: dict) -> dict:
        """`user` is a reserved word in PostgreSQL: v4 stores it as `user_<plugin>`."""
        if "user" not in stats:
            return stats
        stats = dict(stats)
        stats[f"user_{plugin}"] = stats.pop("user")
        return stats

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
                    payload = self._merge_limits(plugin, self._inject_key(plugin, payload))
                    built = self._rows(name, payload)
                    if built is not None:
                        self._write(name, *built)
                except Exception as e:
                    logger.warning("Cannot export %s stats to TimescaleDB (%s)", name, e)

    def export(self, name: str, columns: list[str], points: list[Any]) -> None:
        """Unused — rows are built from the structured payload in update()."""

    def _identifier(self, name: str) -> Any:
        """`sql.Identifier`, with `%` doubled.

        psycopg reads `%s` / `%(x)s` placeholders in the whole query text, a
        quoted identifier included (found in P3-7 on a real PostgreSQL). A
        field name carrying one could not inject -- the placeholder count
        would no longer match and the statement fails -- but it made that
        plugin's export fail every cycle. Every statement below is run WITH
        a parameter sequence, so psycopg turns `%%` back into `%`.
        """
        return self.sql.Identifier(name.replace("%", "%%"))

    def _write(self, table: str, columns: list[tuple[str, str]], segmented_by: list[str], rows: list[list]) -> None:
        sql = self.sql
        ident = self._identifier
        # The transaction commits on success and rolls back before the error
        # propagates, so a failure never leaves the connection aborted.
        with self.client.transaction(), self.client.cursor() as cur:
            cur.execute(
                "SELECT EXISTS(SELECT * FROM information_schema.tables WHERE table_name=%s)",
                [table],
            )
            if not cur.fetchone()[0]:
                # https://github.com/timescale/timescaledb/blob/main/README.md#create-a-hypertable
                # The column type comes from convert_types, never from the data.
                fields = sql.SQL(", ").join(
                    sql.SQL("{} {}").format(ident(column), sql.SQL(kind)) for column, kind in columns
                )
                cur.execute(
                    sql.SQL(
                        "CREATE TABLE {table} ({fields}) WITH ("
                        "timescaledb.hypertable, "
                        "timescaledb.partition_column='time', "
                        "timescaledb.segmentby = {segmentby});"
                    ).format(
                        table=ident(table),
                        fields=fields,
                        segmentby=sql.Literal(", ".join(segmented_by)),
                    ),
                    # Empty, not None: psycopg then undoubles `%%` here too.
                    (),
                )
            insert = sql.SQL("INSERT INTO {table} ({cols}) VALUES ({vals})").format(
                table=ident(table),
                cols=sql.SQL(", ").join(ident(column) for column, _ in columns),
                vals=sql.SQL(", ").join(sql.Placeholder() for _ in columns),
            )
            cur.executemany(insert, rows)
        logger.debug("Export %s stats to TimescaleDB", table)

    def exit(self) -> None:
        super().exit()
        try:
            self.client.close()
        except Exception as e:
            logger.debug("Cannot close the TimescaleDB connection (%s)", e)

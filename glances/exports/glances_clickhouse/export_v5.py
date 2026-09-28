#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — ClickHouse export module (P3-3, wave C).

Ported from the v4 module in this directory: same `[clickhouse]` section, one
MergeTree table per plugin (named after it, `ORDER BY time`) created on first
use and widened when a new field appears, columns `time`, `hostname_id`,
`key_id` (collections only) then one column per raw stat field, typed from
the values (String > Float64 > Int64 > Bool). Like v4, this exporter works
on the raw payload, not on `build_export()`'s flattened names, so it
overrides `update()`.

SQL safety: identifiers (table and column names) are checked, then quoted
with the driver's own `quote_identifier`; every value — an interface or
mount name included — travels as insert data, never inside a SQL string.
`clickhouse_connect` is imported when the exporter starts.
"""

from __future__ import annotations

import re
import sys
from collections.abc import Callable
from datetime import datetime, timezone
from platform import node
from typing import TYPE_CHECKING, Any

from glances.exports.export_base_v5 import GlancesExportBase
from glances.logger import logger

if TYPE_CHECKING:
    import argparse

    from glances.config_v5 import GlancesConfigV5
    from glances.plugins.plugin.base_v5 import GlancesPluginBase

# Columns every table has, with their fixed types.
_FIXED_COLUMNS = {"time": "DateTime", "hostname_id": "String", "key_id": "String"}

# A name holding a quote, a backslash or a control character is no field
# name: it is refused rather than trusted to the quoting alone.
_SAFE_IDENTIFIER = re.compile(r"[^`\"\\\x00-\x1f\x7f]+")


def _infer_ch_type(values: list[Any]) -> str:
    """The ClickHouse type for a column: String > Float64 > Int64 > Bool (v4)."""
    found: set[str] = set()
    for v in values:
        if v is None:
            continue
        if isinstance(v, bool):
            found.add("Bool")
        elif isinstance(v, float):
            found.add("Float64")
        elif isinstance(v, int):
            found.add("Int64")
        else:
            return "Nullable(String)"
    for ch_type in ("Float64", "Int64", "Bool"):
        if ch_type in found:
            return f"Nullable({ch_type})"
    return "Nullable(String)"


def _to_cell(value: Any) -> Any:
    """A value the driver can store: anything but a scalar becomes its string."""
    if value is None or isinstance(value, (bool, int, float, str, datetime)):
        return value
    return str(value)


class Export(GlancesExportBase):
    """Write Glances stats to a ClickHouse server."""

    export_name = "clickhouse"

    def __init__(self, config: GlancesConfigV5, args: argparse.Namespace | None = None) -> None:
        super().__init__(config, args)
        self.db: str | None = None
        self.user: str | None = None
        self.password: str | None = None
        if not self.load_conf(
            "clickhouse", mandatories=("host", "port", "db", "user", "password"), options=("hostname",)
        ):
            logger.critical("Missing clickhouse config")
            sys.exit(2)
        # Always stored, so the stats can be filtered by host.
        self.hostname = self.hostname or node().split(".")[0]
        self.quote_identifier: Callable[[str], str] = str
        self.client = self.init()

    def init(self) -> Any:
        try:
            import clickhouse_connect
            from clickhouse_connect.driver.binding import quote_identifier
        except ImportError as e:
            logger.critical("Export clickhouse needs the clickhouse_connect library (%s)", e)
            sys.exit(2)
        self.quote_identifier = quote_identifier
        try:
            client = clickhouse_connect.get_client(
                host=self.host, port=int(self.port), username=self.user, password=self.password, database=self.db
            )
        except Exception as e:
            logger.critical("Cannot connect to ClickHouse server %s:%s (%s)", self.host, self.port, self._redact(e))
            sys.exit(2)
        logger.info("Stats will be exported to ClickHouse server: %s:%s", self.host, self.port)
        return client

    def _redact(self, error: Exception) -> str:
        """The error text, with the configured credentials masked."""
        text = str(error)
        for secret in (self.password, self.user):
            if secret:
                text = text.replace(secret, "***")
        return text

    # ------------------------------------------------------------ rows

    def _table(self, payload: dict | list) -> tuple[list[str], list[list[Any]]] | None:
        """v4's rows for one plugin: (column names, rows), or None to skip it."""
        now = datetime.now(tz=timezone.utc)
        if isinstance(payload, dict):
            columns = ["time", "hostname_id", *payload]
            return columns, [[now, self.hostname, *payload.values()]]
        if payload and "key" in payload[0]:
            # Every key of every item: the items do not all carry the same fields.
            keys = list(dict.fromkeys(k for item in payload for k in item if k != "key"))
            columns = ["time", "hostname_id", "key_id", *keys]
            rows = [[now, self.hostname, item.get("key"), *(item.get(k) for k in keys)] for item in payload]
            return columns, rows
        return None

    def update(self, plugins: list[GlancesPluginBase]) -> None:
        """The base loop, with v4's per-plugin table rows instead of `build_export()`."""
        with self._lifecycle_lock:
            for plugin in plugins:
                if not getattr(plugin, "EXPORTABLE", True):
                    continue
                try:
                    payload = plugin.get_export()
                    if not payload:
                        continue
                    payload = self._merge_limits(plugin, self._inject_key(plugin, payload))
                    table = self._table(payload)
                    if table is not None:
                        self.export(plugin.plugin_name, *table)
                except Exception as e:
                    logger.warning("Export %s: plugin %s failed (%s)", self.export_name, plugin.plugin_name, e)

    def export(self, name: str, columns: list[str], points: list[Any]) -> None:
        """Create or widen the `name` table, then insert `points` (a list of rows)."""
        if not _SAFE_IDENTIFIER.fullmatch(name):
            logger.debug("ClickHouse: unsafe table name %r skipped", name)
            return
        keep = [i for i, column in enumerate(columns) if _SAFE_IDENTIFIER.fullmatch(column)]
        if len(keep) != len(columns):
            logger.debug("ClickHouse table %s: %d unsafe column name(s) skipped", name, len(columns) - len(keep))
        columns = [columns[i] for i in keep]
        rows = [[_to_cell(row[i]) for i in keep] for row in points]
        schema = {
            column: _FIXED_COLUMNS.get(column) or _infer_ch_type([row[i] for row in rows])
            for i, column in enumerate(columns)
        }

        quote = self.quote_identifier
        table = quote(name)
        definition = ", ".join(f"{quote(column)} {ch_type}" for column, ch_type in schema.items())
        try:
            self.client.command(
                f"CREATE TABLE IF NOT EXISTS {table} ({definition}) ENGINE = MergeTree() ORDER BY `time`"
            )
            # Schema evolution: add the missing columns, fix the changed types.
            existing = {row[0]: row[1] for row in self.client.query(f"DESCRIBE TABLE {table}").result_rows}
            for column, ch_type in schema.items():
                if column not in existing:
                    self.client.command(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {quote(column)} {ch_type}")
                elif existing[column] != ch_type and column not in _FIXED_COLUMNS:
                    logger.debug(
                        "ClickHouse table %s: changing column %s from %s to %s", name, column, existing[column], ch_type
                    )
                    self.client.command(f"ALTER TABLE {table} MODIFY COLUMN {quote(column)} {ch_type}")
            self.client.insert(table=name, data=rows, column_names=columns)
        except Exception as e:
            logger.warning("Cannot export %s stats to ClickHouse (%s)", name, self._redact(e))
        else:
            logger.debug("Export %s stats to ClickHouse", name)

    def exit(self) -> None:
        # The barrier first (see the base class), then close the HTTP client.
        super().exit()
        self.client.close()

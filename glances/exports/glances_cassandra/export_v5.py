#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — Cassandra/ScyllaDB export module (P3-3, wave D).

Ported from the v4 module in this directory: same `[cassandra]` section,
same keyspace (SimpleStrategy), same table
`(plugin text, time timeuuid, stat map<text,float>)` and the same rows —
one per plugin per tick, numbers only, as floats.

Carries the fix for CVE-2026-35588 (CQL injection through the config):

- `keyspace` and `table` must match `^[A-Za-z][A-Za-z0-9_]*$` and
  `replication_factor` must be a positive integer, checked at startup
  BEFORE the driver is even imported. These three are the only strings
  interpolated into CQL (identifiers and the DDL replication map cannot be
  bound); a value that fails is fatal, with a critical log naming the key.
  v4 only logged an error and left a half-built exporter behind, which
  then crashed in `exit()`;
- every VALUE — the plugin name, the timeuuid, and the stat map whose keys
  carry interface, process and container names — is bound to a prepared
  statement, never part of the statement text.

`table` defaults to `host`, as `conf/glances.conf` documents (v4 said so but
refused a missing `table`); a host that is not a valid identifier, like an
IP address, is refused the same way. `cassandra-driver` is imported when the
exporter starts, so this module stays importable without it.
"""

from __future__ import annotations

import re
import sys
from datetime import datetime
from numbers import Number
from typing import TYPE_CHECKING, Any

from glances.exports.export_base_v5 import GlancesExportBase
from glances.logger import logger

if TYPE_CHECKING:
    import argparse

    from glances.config_v5 import GlancesConfigV5

_CQL_IDENTIFIER_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
_POSITIVE_INT_RE = re.compile(r"^[1-9][0-9]*$")


class Export(GlancesExportBase):
    """Write Glances stats to a Cassandra or ScyllaDB cluster."""

    export_name = "cassandra"

    def __init__(self, config: GlancesConfigV5, args: argparse.Namespace | None = None) -> None:
        super().__init__(config, args)
        self.keyspace: str | None = None
        self.protocol_version: Any = 3
        self.replication_factor: Any = 2
        self.table: str | None = None
        self.username: str | None = None
        self.password: str | None = None
        if not self.load_conf(
            "cassandra",
            mandatories=("host", "port", "keyspace"),
            options=("protocol_version", "replication_factor", "table", "username", "password"),
        ):
            logger.critical("Missing cassandra config")
            sys.exit(2)
        self.table = self.table or self.host
        self._validate()
        self.cluster, self.session = self.init()

    def _validate(self) -> None:
        """Refuse any config value that would be interpolated into CQL unchecked."""
        # `fullmatch`, not `match`: `$` also matches before a trailing newline,
        # so `match` let `"glances\n"` through into the DDL.
        for key in ("keyspace", "table"):
            if not _CQL_IDENTIFIER_RE.fullmatch(str(getattr(self, key))):
                logger.critical(
                    "Invalid cassandra config: %s=%r must match %s", key, getattr(self, key), _CQL_IDENTIFIER_RE.pattern
                )
                sys.exit(2)
        for key in ("port", "replication_factor", "protocol_version"):
            if not _POSITIVE_INT_RE.fullmatch(str(getattr(self, key)).strip()):
                logger.critical("Invalid cassandra config: %s=%r must be a positive integer", key, getattr(self, key))
                sys.exit(2)
        self.replication_factor = int(self.replication_factor)
        self.protocol_version = int(self.protocol_version)
        self.port = int(self.port)

    def init(self) -> tuple[Any, Any]:
        try:
            from cassandra import InvalidRequest
            from cassandra.auth import PlainTextAuthProvider
            from cassandra.cluster import Cluster
            from cassandra.util import uuid_from_time
        except ImportError as e:
            logger.critical("Export cassandra needs the cassandra-driver library (%s)", e)
            sys.exit(2)
        self._uuid_from_time = uuid_from_time

        # Without username/password, the driver connects with no auth (v4).
        auth_provider = PlainTextAuthProvider(username=self.username, password=self.password)
        try:
            cluster = Cluster(
                [self.host], port=self.port, protocol_version=self.protocol_version, auth_provider=auth_provider
            )
            session = cluster.connect()
        except Exception as e:
            logger.critical("Cannot connect to Cassandra cluster %s:%s (%s)", self.host, self.port, e)
            sys.exit(2)

        # keyspace, table and replication_factor were validated in _validate().
        try:
            session.set_keyspace(self.keyspace)
        except InvalidRequest:
            logger.info("Create keyspace %s on the Cassandra cluster", self.keyspace)
            session.execute(
                f"CREATE KEYSPACE {self.keyspace} WITH "
                f"replication = {{ 'class': 'SimpleStrategy', 'replication_factor': '{self.replication_factor}' }}"
            )
            session.set_keyspace(self.keyspace)

        try:
            session.execute(
                f"CREATE TABLE {self.table} "
                "(plugin text, time timeuuid, stat map<text,float>, PRIMARY KEY (plugin, time)) "
                "WITH CLUSTERING ORDER BY (time DESC)"
            )
        except Exception:
            logger.debug("Cassandra table %s already exists", self.table)

        logger.info(
            "Stats will be exported to Cassandra cluster %s:%s in keyspace %s", self.host, self.port, self.keyspace
        )
        return cluster, session

    def export(self, name: str, columns: list[str], points: list[Any]) -> None:
        # Numbers only, as floats (v4). Booleans are already "true"/"false".
        data = {k: float(v) for k, v in zip(columns, points) if isinstance(v, Number)}
        try:
            query = self.session.prepare(f"INSERT INTO {self.table} (plugin, time, stat) VALUES (?, ?, ?)")
            self.session.execute(query, (name, self._uuid_from_time(datetime.now()), data))
        except Exception as e:
            logger.warning("Cannot export %s stats to Cassandra (%s)", name, e)
        else:
            logger.debug("Export %s stats to Cassandra", name)

    def exit(self) -> None:
        super().exit()
        for resource in (self.session, self.cluster):
            try:
                resource.shutdown()
            except Exception as e:
                logger.debug("Cannot shut the Cassandra connection down (%s)", e)

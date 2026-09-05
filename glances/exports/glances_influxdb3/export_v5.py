#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — InfluxDB 3.x export module.

Ported from the v4 module in this directory. Same measurement shape as the
1.x and 2.x exporters — `GlancesExportBase.normalize_for_influxdb()` is the
single implementation.
"""

from __future__ import annotations

import sys
from platform import node
from typing import TYPE_CHECKING, Any

from glances.exports.export_base_v5 import GlancesExportBase
from glances.logger import logger

if TYPE_CHECKING:
    import argparse

    from glances.config_v5 import GlancesConfigV5


class Export(GlancesExportBase):
    """Write Glances stats to an InfluxDB 3.x server."""

    export_name = "influxdb3"

    def __init__(self, config: GlancesConfigV5, args: argparse.Namespace | None = None) -> None:
        super().__init__(config, args)

        # Mandatory keys, in addition to host and port. load_conf() either
        # sets them all or returns False, so no fallback is needed below.
        self.org: str | None = None
        self.database: str | None = None
        self.token: str | None = None

        # Optional keys — the default has to be in place BEFORE load_conf(),
        # which leaves it untouched when the key is absent.
        self.prefix: str | None = None
        self.tags: str | None = None
        # 3.x takes a full URL as `host` ("http://localhost:8181"), so the port
        # is already in it and the client never receives self.port -- it only
        # reaches a log line. v4 listed it as mandatory anyway, harmlessly,
        # because its load_conf() merely left it None. In v5 a missing
        # mandatory is fatal, and the shipped conf/glances.conf declares no
        # port, so requiring it would make `--export influxdb3` unstartable.
        self.port: str | None = None

        if not self.load_conf(
            "influxdb3",
            mandatories=("host", "org", "database", "token"),
            options=("prefix", "tags", "port"),
        ):
            logger.critical("Missing influxdb3 config")
            sys.exit(2)

        # The hostname is always added as a tag. Set, like self.tags, before
        # the first export() — normalize_for_influxdb() reads both.
        self.hostname = node().split(".")[0]

        self.client = self.init()

    def init(self) -> Any:
        """Connect and verify the target database."""
        # Imported here, not at module level: the client library is an
        # optional dependency and must not be a cost for every Glances start.
        from influxdb_client_3 import InfluxDBClient3

        try:
            db = InfluxDBClient3(
                host=self.host,
                org=self.org,
                database=self.database,
                token=self.token,
            )
        except Exception as e:
            logger.critical("Cannot connect to InfluxDB database '%s' (%s)", self.database, e)
            sys.exit(2)

        target = f"{self.host}:{self.port}" if self.port else self.host
        logger.info("Stats will be exported to InfluxDB server %s in %s database", target, self.database)
        return db

    def export(self, name: str, columns: list[str], points: list[Any]) -> None:
        """Write one plugin's measurements."""
        if self.prefix is not None:
            name = self.prefix + "." + name
        if not points:
            logger.debug("Cannot export empty %s stats to InfluxDB", name)
            return
        try:
            self.client.write(
                record=self.normalize_for_influxdb(name, columns, points),
                time_precision="s",
            )
        except Exception as e:
            # Warning, not error (#1561).
            logger.warning("Cannot export %s stats to InfluxDB (%s)", name, e)
        else:
            logger.debug("Export %s stats to InfluxDB", name)

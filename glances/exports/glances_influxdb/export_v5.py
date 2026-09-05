#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — InfluxDB 1.x export module.

Ported from the v4 module in this directory. The measurement shape is
produced by `GlancesExportBase.normalize_for_influxdb()`, shared with the
2.x and 3.x exporters — the three differ only in their client library and
their write call.

`influxdb` is imported inside `init()`, never at module level: discovery
imports this file on every start-up and the library is optional.
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
    """Write Glances stats to an InfluxDB 1.x server."""

    export_name = "influxdb"

    def __init__(self, config: GlancesConfigV5, args: argparse.Namespace | None = None) -> None:
        super().__init__(config, args)

        # Mandatory keys, in addition to host and port. load_conf() either
        # sets them or returns False, so these are declarations, not defaults.
        self.user: str | None = None
        self.password: str | None = None
        self.db: str | None = None

        # Optional keys. Assigned BEFORE load_conf(): an absent optional key
        # leaves the value below in place (it is not reset to None).
        self.protocol: str = "http"
        self.prefix: str | None = None
        self.tags: str | None = None

        if not self.load_conf(
            "influxdb",
            mandatories=("host", "port", "user", "password", "db"),
            options=("protocol", "prefix", "tags"),
        ):
            logger.critical("Missing influxdb config")
            sys.exit(2)

        # The hostname is always added as a tag.
        self.hostname: str = node().split(".")[0]

        self.client = self.init()

    def init(self) -> Any:
        """Connect and verify the target database exists."""
        from influxdb import InfluxDBClient

        # Correct issue #1530
        ssl = self.protocol.lower() == "https"

        try:
            db = InfluxDBClient(
                host=self.host,
                port=self.port,
                ssl=ssl,
                verify_ssl=False,
                username=self.user,
                password=self.password,
                database=self.db,
            )
            get_all_db = [i["name"] for i in db.get_list_database()]
        except Exception as e:
            # v4 caught only InfluxDBClientError here. Measured: an unreachable
            # server raises requests.exceptions.ConnectionError -- the commonest
            # failure of all -- which escaped and killed the process with a
            # traceback instead of the clean exit design section 8 promises.
            # The 2.x and 3.x siblings already catch Exception.
            logger.critical("Cannot connect to InfluxDB database '%s' (%s)", self.db, e)
            sys.exit(2)

        if self.db not in get_all_db:
            logger.critical("InfluxDB database '%s' did not exist. Please create it", self.db)
            sys.exit(2)

        logger.info("Stats will be exported to InfluxDB server: %s", db._baseurl)
        return db

    def export(self, name: str, columns: list[str], points: list[Any]) -> None:
        """Write one plugin's measurements."""
        if self.prefix is not None:
            name = self.prefix + "." + name
        if not points:
            logger.debug("Cannot export empty %s stats to InfluxDB", name)
            return
        try:
            self.client.write_points(
                self.normalize_for_influxdb(name, columns, points),
                time_precision="s",
            )
        except Exception as e:
            # Warning, not error: a momentary outage must not read as a bug (#1561).
            logger.warning("Cannot export %s stats to InfluxDB (%s)", name, e)
        else:
            logger.debug("Export %s stats to InfluxDB", name)

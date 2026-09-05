#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — InfluxDB 2.x export module (InfluxDB 1.8+ to <3.0).

Ported from the v4 module in this directory. One behavioural change: the
client's write buffer is flushed on the EXPORT cadence.

v4 read `args.time` — the CLI refresh rate — whenever `[influxdb2] interval`
was 0 or unset. v5 has no such argument; `[export] refresh` is what drives
the export loop, so the buffer is sized from it via the same resolver the
scheduler uses. In the common case where both fall back to the global
refresh the resulting value is identical to v4's.

`influxdb_client` is imported inside the method that needs it, never at
module level: the module then stays importable (for tests, for
introspection) on an install without the client library.
"""

from __future__ import annotations

import sys
from platform import node
from typing import TYPE_CHECKING, Any

from glances.exports.export_base_v5 import GlancesExportBase, resolve_export_refresh
from glances.logger import logger

if TYPE_CHECKING:
    import argparse

    from glances.config_v5 import GlancesConfigV5


class Export(GlancesExportBase):
    """Write Glances stats to an InfluxDB 2.x server."""

    export_name = "influxdb2"

    def __init__(self, config: GlancesConfigV5, args: argparse.Namespace | None = None) -> None:
        super().__init__(config, args)

        # Mandatory keys, in addition to host and port. Set by load_conf(),
        # which is fatal when one is missing — unlike v4, which silently
        # continued with None. Hence no `is None` fallback below.
        self.org: str | None = None
        self.bucket: str | None = None
        self.token: str | None = None

        # Optional keys: load_conf() overwrites them only when the key is set,
        # so the defaults have to be in place before the call.
        self.protocol: str = "http"
        self.prefix: str | None = None
        self.tags: str | None = None
        self.interval: Any = 0

        if not self.load_conf(
            "influxdb2",
            # v4 also demanded "user" and "password" here, then never read
            # them -- 2.x authenticates with a token. Harmless in v4, whose
            # load_conf() only left them None; FATAL in v5, where a missing
            # mandatory aborts. Keeping them would make `--export influxdb2`
            # refuse to start on the shipped conf/glances.conf, which declares
            # neither. Dropped, not moved to options: nothing reads them.
            mandatories=("host", "port", "org", "bucket", "token"),
            options=("protocol", "prefix", "tags", "interval"),
        ):
            logger.critical("Missing influxdb2 config")
            sys.exit(2)

        # Flush interval, in seconds. 0 / unset / unparseable → export cadence.
        try:
            self.interval = int(self.interval)
        except ValueError:
            logger.warning("InfluxDB export interval is not an integer, use default value")
            self.interval = 0
        if self.interval <= 0:
            self.interval = int(resolve_export_refresh(self.config))
        logger.debug("InfluxDB export interval is set to %s seconds", self.interval)

        # The hostname is always added as a tag — read by normalize_for_influxdb().
        self.hostname: str | None = node().split(".")[0]

        self.client = self.init()

    def init(self) -> Any:
        """Connect and return a batched write API."""
        from influxdb_client import InfluxDBClient, WriteOptions

        url = f"{self.protocol}://{self.host}:{self.port}"
        try:
            # https://influxdb-client.readthedocs.io/en/stable/api.html#influxdbclient
            client = InfluxDBClient(
                url=url,
                enable_gzip=False,
                verify_ssl=False,
                org=self.org,
                token=self.token,
            )
        except Exception as e:
            logger.critical("Cannot connect to InfluxDB server '%s' (%s)", url, e)
            sys.exit(2)

        # health() does NOT raise on an unreachable server: it returns a
        # HealthCheck whose status is "fail". v4 logged its message under
        # "Connected to InfluxDB server version None (...)", which tells the
        # operator the opposite of the truth. The connection is not made fatal
        # -- WriteOptions below is configured to retry, so a server that is
        # merely slow to come up must not kill Glances -- only reported honestly.
        health = client.health()
        if health.status == "pass":
            logger.info("Connected to InfluxDB server version %s (%s)", health.version, health.message)
        else:
            logger.warning("InfluxDB server at %s is not healthy (%s) — will retry", url, health.message)

        return client.write_api(
            write_options=WriteOptions(
                batch_size=500,
                flush_interval=self.interval * 1000,
                jitter_interval=2000,
                retry_interval=5000,
                max_retries=5,
                max_retry_delay=30000,
                exponential_base=2,
            )
        )

    def export(self, name: str, columns: list[str], points: list[Any]) -> None:
        """Write one plugin's measurements."""
        if self.prefix is not None:
            name = self.prefix + "." + name
        if not points:
            logger.debug("Cannot export empty %s stats to InfluxDB", name)
            return
        try:
            self.client.write(
                self.bucket,
                self.org,
                self.normalize_for_influxdb(name, columns, points),
                time_precision="s",
            )
        except Exception as e:
            # Warning, not error: a momentary outage must not read as a bug (#1561).
            logger.warning("Cannot export %s stats to InfluxDB (%s)", name, e)
        else:
            logger.debug("Export %s stats to InfluxDB", name)

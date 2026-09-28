#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — StatsD export module (P3-3, wave A).

Ported from the v4 module in this directory: same `[statsd]` section, one
gauge per numeric field, named `<plugin>.<field>` under `prefix`, with v4's
character clean-up (#1068). `statsd` is imported when the exporter starts.
"""

from __future__ import annotations

import sys
from numbers import Number
from typing import TYPE_CHECKING, Any

from glances.exports.export_base_v5 import GlancesExportBase
from glances.logger import logger

if TYPE_CHECKING:
    import argparse

    from glances.config_v5 import GlancesConfigV5


def normalize(name: str) -> str:
    """No `:` or `%`, spaces as `_`: StatsD's line format (v4, issue #1068)."""
    return name.replace(":", "").replace("%", "").replace(" ", "_")


class Export(GlancesExportBase):
    """Send Glances stats to a StatsD server, as gauges."""

    export_name = "statsd"

    def __init__(self, config: GlancesConfigV5, args: argparse.Namespace | None = None) -> None:
        super().__init__(config, args)
        self.prefix: str | None = None
        if not self.load_conf("statsd", mandatories=("host", "port"), options=("prefix",)):
            logger.critical("Missing statsd config")
            sys.exit(2)
        self.prefix = self.prefix or "glances"
        self.client = self.init()

    def init(self) -> Any:
        try:
            from statsd import StatsClient
        except ImportError as e:
            logger.critical("Export statsd needs the statsd library (%s)", e)
            sys.exit(2)
        logger.info("Stats will be exported to the StatsD server %s:%s", self.host, self.port)
        return StatsClient(self.host, int(self.port), prefix=self.prefix)

    def export(self, name: str, columns: list[str], points: list[Any]) -> None:
        for column, value in zip(columns, points):
            if not isinstance(value, Number) or isinstance(value, bool):
                continue
            try:
                self.client.gauge(normalize(f"{name}.{column}"), value)
            except Exception as e:
                logger.warning("Cannot export %s stats to StatsD (%s)", name, e)
                return
        logger.debug("Export %s stats to StatsD", name)

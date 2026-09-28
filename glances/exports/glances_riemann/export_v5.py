#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — Riemann export module (P3-3, wave A).

Ported from the v4 module in this directory: same `[riemann]` section, one
event per numeric field, `{"host": <hostname>, "service": "<plugin> <field>",
"metric": <value>}`. `bernhard` is imported when the exporter starts.
"""

from __future__ import annotations

import socket
import sys
from numbers import Number
from typing import TYPE_CHECKING, Any

from glances.exports.export_base_v5 import GlancesExportBase
from glances.logger import logger

if TYPE_CHECKING:
    import argparse

    from glances.config_v5 import GlancesConfigV5


class Export(GlancesExportBase):
    """Send Glances stats to a Riemann server, as events."""

    export_name = "riemann"

    def __init__(self, config: GlancesConfigV5, args: argparse.Namespace | None = None) -> None:
        super().__init__(config, args)
        if not self.load_conf("riemann", mandatories=("host", "port")):
            logger.critical("Missing riemann config")
            sys.exit(2)
        self.hostname = socket.gethostname()
        self.client = self.init()

    def init(self) -> Any:
        try:
            import bernhard
        except ImportError as e:
            logger.critical("Export riemann needs the bernhard library (%s)", e)
            sys.exit(2)
        try:
            return bernhard.Client(host=self.host, port=int(self.port))
        except Exception as e:
            logger.error("Cannot connect to the Riemann server %s:%s (%s)", self.host, self.port, e)
            return None

    def export(self, name: str, columns: list[str], points: list[Any]) -> None:
        if self.client is None:
            return
        for column, value in zip(columns, points):
            if not isinstance(value, Number) or isinstance(value, bool):
                continue
            try:
                self.client.send({"host": self.hostname, "service": f"{name} {column}", "metric": value})
            except Exception as e:
                logger.warning("Cannot export %s stats to Riemann (%s)", name, e)
                return
        logger.debug("Export %s stats to Riemann", name)

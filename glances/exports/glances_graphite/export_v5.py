#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — Graphite export module (P3-3, wave A).

Ported from the v4 module in this directory: same `[graphite]` section, same
metric names (`<prefix>.<system_name>.<plugin>.<field>`, lowercased, spaces
as `_`), numbers only. `graphitesend` is imported when the exporter starts,
so this module stays importable without it.
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
    """A Graphite metric name has no space (v4)."""
    return name.replace(" ", "_")


class Export(GlancesExportBase):
    """Send Glances stats to a Graphite (carbon) server."""

    export_name = "graphite"

    def __init__(self, config: GlancesConfigV5, args: argparse.Namespace | None = None) -> None:
        super().__init__(config, args)
        self.prefix: str | None = None
        self.system_name: str | None = None
        if not self.load_conf("graphite", mandatories=("host", "port"), options=("prefix", "system_name")):
            logger.critical("Missing graphite config")
            sys.exit(2)
        self.prefix = self.prefix or "glances"
        self.port = int(self.port)
        self.client = self.init()

    def init(self) -> Any:
        try:
            from graphitesend import GraphiteClient
        except ImportError as e:
            logger.critical("Export graphite needs the graphitesend library (%s)", e)
            sys.exit(2)
        options: dict[str, Any] = {"prefix": self.prefix, "lowercase_metric_names": True}
        if self.system_name is not None:
            options["system_name"] = self.system_name
        try:
            client = GraphiteClient(graphite_server=self.host, graphite_port=self.port, **options)
        except Exception as e:
            # v4 went on without a client; so does v5, and says it once.
            logger.error("Cannot write to the Graphite server %s:%s (%s)", self.host, self.port, e)
            return None
        logger.info("Stats will be exported to the Graphite server %s:%s", self.host, self.port)
        return client

    def export(self, name: str, columns: list[str], points: list[Any]) -> None:
        if self.client is None:
            return
        metrics = {
            normalize(f"{name}.{column}"): value
            for column, value in zip(columns, points)
            if isinstance(value, Number) and not isinstance(value, bool)
        }
        try:
            self.client.send_dict(metrics)
        except Exception as e:
            logger.warning("Cannot export %s stats to Graphite (%s)", name, e)
        else:
            logger.debug("Export %s stats to Graphite", name)

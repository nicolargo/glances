#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — OpenTSDB export module (P3-3, wave A).

Ported from the v4 module in this directory: same `[opentsdb]` section, one
point per numeric field, named `<prefix>.<plugin>.<field>`, with the
configured `tags`. `potsdb` is imported when the exporter starts.
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


class Export(GlancesExportBase):
    """Send Glances stats to an OpenTSDB server."""

    export_name = "opentsdb"

    def __init__(self, config: GlancesConfigV5, args: argparse.Namespace | None = None) -> None:
        super().__init__(config, args)
        self.prefix: str | None = None
        self.tags: str | None = None
        if not self.load_conf("opentsdb", mandatories=("host", "port"), options=("prefix", "tags")):
            logger.critical("Missing opentsdb config")
            sys.exit(2)
        self.prefix = self.prefix or "glances"
        # Parsed once: the tags do not change between points.
        self._tags = self.parse_tags(self.tags)
        self.client = self.init()

    def init(self) -> Any:
        try:
            import potsdb
        except ImportError as e:
            logger.critical("Export opentsdb needs the potsdb library (%s)", e)
            sys.exit(2)
        try:
            return potsdb.Client(self.host, port=int(self.port), check_host=True)
        except Exception as e:
            logger.critical("Cannot connect to the OpenTSDB server %s:%s (%s)", self.host, self.port, e)
            sys.exit(2)

    def export(self, name: str, columns: list[str], points: list[Any]) -> None:
        for column, value in zip(columns, points):
            if not isinstance(value, Number) or isinstance(value, bool):
                continue
            try:
                self.client.send(f"{self.prefix}.{name}.{column}", value, **self._tags)
            except Exception as e:
                logger.warning("Cannot export %s stats to OpenTSDB (%s)", name, e)
                return
        logger.debug("Export %s stats to OpenTSDB", name)

    def exit(self) -> None:
        # The barrier first (see the base class), then drain potsdb's queue.
        super().exit()
        self.client.wait()

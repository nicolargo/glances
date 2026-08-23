#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — JSON export module.

Ported from the v4 module in this directory. The file holds ONE JSON
object describing the latest cycle and is rewritten — not appended — every
time, exactly as in v4. Consumers tail the file and re-read it whole.

v4 buffered per plugin and flushed when the first plugin of the list came
round again; that sentinel existed only because the parent class owned the
plugin loop. In v5 the exporter owns its own ``update()``, so the buffer is
assembled and written in one pass. Same output, no sentinel.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any

from glances.exports.export_base_v5 import GlancesExportBase
from glances.globals import json_dumps
from glances.logger import logger

if TYPE_CHECKING:
    import argparse

    from glances.config_v5 import GlancesConfigV5
    from glances.plugins.plugin.base_v5 import GlancesPluginBase


class Export(GlancesExportBase):
    """Write the whole cycle to a JSON file."""

    export_name = "json"

    def __init__(self, config: GlancesConfigV5, args: argparse.Namespace) -> None:
        super().__init__(config, args)

        self.json_filename = args.export_json_file

        # Fail fast on an unwritable path rather than at the first cycle.
        # Snap's strict confinement blocks at open(), so the open() call
        # itself must be inside the try — not just the write.
        try:
            with open(self.json_filename, "w"):
                pass
        except OSError as e:
            logger.critical("Cannot create the JSON file: %s", e)
            sys.exit(2)

        logger.info("Exporting stats to file: %s", self.json_filename)
        self.buffer: dict[str, Any] = {}

    def update(self, plugins: list[GlancesPluginBase]) -> None:
        """Fill the buffer from every exportable plugin, then flush once."""
        self.buffer = {}
        super().update(plugins)

        try:
            with open(self.json_filename, "wb") as json_file:
                json_file.write(json_dumps(self.buffer) + b"\n")
        except Exception as e:
            logger.error("Can not export data to JSON (%s)", e)

    def export(self, name: str, columns: list[str], points: list[Any]) -> None:
        """Buffer one plugin's flattened stats. Flushed by update()."""
        self.buffer[name] = dict(zip(columns, points))

    def exit(self) -> None:
        # Nothing to release — each flush opens and closes its own handle.
        # super().exit() is still called for the barrier, so the pattern is
        # uniform across exporters and a future resource added here is
        # protected by default.
        super().exit()

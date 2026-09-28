#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — RESTful export module (P3-3, wave E).

Ported from the v4 module in this directory: same `[restful]` section
(`host`, `port`, `protocol`, `path`, all mandatory), and the same body: ONE
POST per export cycle, `{"<plugin>": {"<field>": value, ...}, ...}`.

v4 detected the end of a cycle when the first plugin came round again, so
each POST carried the previous cycle and the last one was never sent. v5's
`update()` sees the whole cycle at once and posts it at its end.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any

import requests

from glances.exports.export_base_v5 import GlancesExportBase
from glances.logger import logger

if TYPE_CHECKING:
    import argparse

    from glances.config_v5 import GlancesConfigV5
    from glances.plugins.plugin.base_v5 import GlancesPluginBase

# v4's timeout for the POST.
TIMEOUT = 15


class Export(GlancesExportBase):
    """POST every plugin's stats to an HTTP endpoint, once per cycle."""

    export_name = "restful"

    def __init__(self, config: GlancesConfigV5, args: argparse.Namespace | None = None) -> None:
        super().__init__(config, args)
        self.protocol: str | None = None
        self.path: str | None = None
        if not self.load_conf("restful", mandatories=("host", "port", "protocol", "path")):
            logger.critical("Missing restful config")
            sys.exit(2)
        self.url = f"{self.protocol}://{self.host}:{self.port}{self.path}"
        self._buffer: dict[str, dict[str, Any]] = {}
        logger.info("Stats will be exported to the RESTful endpoint %s", self.url)

    def export(self, name: str, columns: list[str], points: list[Any]) -> None:
        # One plugin of the cycle: kept for the single POST `update()` sends.
        self._buffer[name] = dict(zip(columns, points))

    def update(self, plugins: list[GlancesPluginBase]) -> None:
        self._buffer = {}
        super().update(plugins)
        if not self._buffer:
            return
        try:
            response = requests.post(self.url, json=self._buffer, allow_redirects=True, timeout=TIMEOUT)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.warning("Cannot export stats to the RESTful endpoint %s (%s)", self.url, e)
        else:
            logger.debug("Export %d plugins to the RESTful endpoint %s", len(self._buffer), self.url)

#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — now (current date/time) plugin (scalar).

Migrated from `glances/plugins/now/__init__.py`. Writes ``iso`` (ISO-8601)
and ``custom`` (strftime, ``[global] strftime_format`` or a tz-aware
default). The TUI shows only ``custom`` (left-padded), v4 parity.
"""

from __future__ import annotations

import asyncio
import datetime
from time import strftime, tzname
from typing import Any, ClassVar

from glances.config_v5 import GlancesConfigV5
from glances.plugins.plugin.base_v5 import GlancesPluginBase
from glances.stats_store_v5 import StatsStoreV5


class PluginModel(GlancesPluginBase[dict]):
    """Current date/time plugin (scalar)."""

    plugin_name: ClassVar[str] = "now"
    IS_COLLECTION: ClassVar[bool] = False

    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "custom": {"description": "Current date in custom format.", "unit": "string"},
        "iso": {"description": "Current date in ISO 8601 format.", "unit": "string"},
    }

    def __init__(self, store: StatsStoreV5, config: GlancesConfigV5) -> None:
        super().__init__(store, config)
        self._strftime = self.config.get("global", "strftime_format", "")

    async def _grab_stats(self) -> dict:
        return await asyncio.to_thread(self._collect)

    def _collect(self) -> dict[str, Any]:
        iso = datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()
        if self._strftime:
            custom = strftime(self._strftime)
        elif len(tzname[1]) > 6:
            custom = strftime("%Y-%m-%d %H:%M:%S %z")
        else:
            custom = strftime("%Y-%m-%d %H:%M:%S %Z")
        return {"iso": iso, "custom": custom}

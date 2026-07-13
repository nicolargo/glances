#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — wifi plugin (collection, per-hotspot).

Migrated from `glances/plugins/wifi/__init__.py`. Stats are read from
`/proc/net/wireless` (Linux only). The v4 dead `_thread`/`exit()`
scaffolding (never actually populated) is not ported.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, ClassVar

from glances.plugins.plugin.base_v5 import GlancesPluginBase
from glances.plugins.plugin.thresholds_v5 import compute_level

logger = logging.getLogger(__name__)

# v4 parity defaults (dBm, negative): `[wifi]` careful/warning/critical.
_DEFAULT_CAREFUL = -65.0
_DEFAULT_WARNING = -75.0
_DEFAULT_CRITICAL = -85.0

# Use stats available in the /proc/net/wireless file.
# Note: it only gives signal information about the current hotspot.
WIRELESS_FILE = "/proc/net/wireless"


class PluginModel(GlancesPluginBase[list]):
    """Wifi plugin (collection)."""

    plugin_name: ClassVar[str] = "wifi"
    IS_COLLECTION: ClassVar[bool] = True
    EMITS_ALERTS: ClassVar[bool] = True

    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "ssid": {
            "description": "Wi-Fi network name (interface name).",
            "unit": "string",
            "primary_key": True,
        },
        "quality_link": {
            "description": "Signal quality level.",
            "unit": "dBm",
            "watched": False,
        },
        "quality_level": {
            "description": "Signal strength level.",
            "unit": "dBm",
            "watched": True,
            "watch_direction": "low",
            "prominent": False,
        },
    }

    async def _grab_stats(self) -> list:
        return await asyncio.to_thread(self._collect)

    @staticmethod
    def _collect() -> list:
        """Synchronous grab (runs in a worker thread).

        Existence is checked at grab time (not import time) — hardware
        can appear/disappear, and an empty collection is a valid startup
        state. The `open()` call itself is wrapped in try/except (Snap
        confinement blocks host file access at the open stage, not the
        read stage).
        """
        if not os.path.exists(WIRELESS_FILE):
            return []
        out: list[dict[str, Any]] = []
        try:
            with open(WIRELESS_FILE) as f:
                # The first two lines are a header.
                f.readline()
                f.readline()
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split()
                    out.append(
                        {
                            "ssid": parts[0][:-1],
                            "quality_link": float(parts[2]),
                            "quality_level": float(parts[3]),
                        }
                    )
        except (PermissionError, FileNotFoundError, IndexError, ValueError) as exc:
            logger.debug("wifi: grab failed: %s", exc)
        return out

    # -------------------------------------------------- transform: alert levels

    def _derived_parameters(self) -> None:
        """Compute per-interface alert levels with v4 `get_alert` parity.

        Signal strength is a negative dBm value where LOWER is worse, so
        the comparison is inverted (`direction="low"`): `value <= critical`
        alerts critical, etc. This bypasses the base `_derived_parameters` /
        `read_thresholds` path because `read_thresholds` treats a negative
        config value as "absent" (`thresholds_v5.py:146`), which would
        silently drop wifi's negative dBm thresholds.

        Result: `_levels = {ssid: {"quality_level": {"level", "prominent"}}}`.
        """
        self._levels = {}
        if not isinstance(self._stats, list):
            return
        prominent = bool(self.fields_description["quality_level"].get("prominent", False))
        try:
            careful, warning, critical = self._read_thresholds()
        except (TypeError, KeyError, ValueError):
            return
        thresholds = {"careful": careful, "warning": warning, "critical": critical}
        for row in self._stats:
            if not isinstance(row, dict):
                continue
            quality_level = row.get("quality_level")
            if not isinstance(quality_level, (int, float)):
                continue  # no numeric reading -> DEFAULT (no colour, no alert)
            level = compute_level(quality_level, thresholds, "low")
            self._levels[str(row.get("ssid", ""))] = {"quality_level": {"level": level, "prominent": prominent}}

    def _read_thresholds(self) -> tuple[float, float, float]:
        """Read `[wifi]` careful/warning/critical, defaulting to v4 parity values."""
        careful = float(self.config.get("wifi", "careful", _DEFAULT_CAREFUL))
        warning = float(self.config.get("wifi", "warning", _DEFAULT_WARNING))
        critical = float(self.config.get("wifi", "critical", _DEFAULT_CRITICAL))
        return careful, warning, critical

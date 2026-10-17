#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — wifi plugin (collection, per-hotspot).

Migrated from `glances/plugins/wifi/__init__.py`. Stats are read over
nl80211 (Linux only, see `nl80211.py`), falling back to
`/proc/net/wireless` when nl80211 is not available. The v4 dead
`_thread`/`exit()` scaffolding (never actually populated) is not ported.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, ClassVar

from glances.plugins.plugin.base import GlancesPluginBase
from glances.plugins.plugin.thresholds import compute_level
from glances.plugins.wifi import nl80211

logger = logging.getLogger(__name__)

# v4 parity defaults (dBm, negative): `[wifi]` careful/warning/critical.
_DEFAULT_CAREFUL = -65.0
_DEFAULT_WARNING = -75.0
_DEFAULT_CRITICAL = -85.0

# Fallback when nl80211 is unavailable: the /proc/net/wireless file. It goes
# through the legacy wireless extensions, which the kernel warns about (and
# which return nothing for Wi-Fi 7 hardware), hence nl80211 first.
# Note: both only give signal information about the current hotspot.
WIRELESS_FILE = "/proc/net/wireless"

# nl80211 has no link quality value: derive it like the cfg80211 wireless
# extensions did, so the field is unchanged: the signal clamped to
# [-110, -40] dBm, shifted to 0..70.
_QUALITY_MIN_DBM = -110
_QUALITY_MAX_DBM = -40


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
            # Column label, TUI header and WebUI alike (field_label, prefer_short).
            "short_name": "dBm",
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

        Reads nl80211 first. Only when nl80211 cannot be reached at all
        (no netlink, no cfg80211) does it fall back to `/proc/net/wireless`.
        A transient nl80211 failure yields an empty collection, a valid
        state like "no wireless hardware".
        """
        try:
            signals = nl80211.station_signals()
        except nl80211.Nl80211Unavailable as exc:
            logger.debug("wifi: nl80211 unavailable (%s), falling back to %s", exc, WIRELESS_FILE)
            return PluginModel._collect_proc()
        except OSError as exc:
            logger.debug("wifi: nl80211 grab failed: %s", exc)
            return []
        return [
            {
                "ssid": name,
                "quality_link": float(min(max(signal, _QUALITY_MIN_DBM), _QUALITY_MAX_DBM) - _QUALITY_MIN_DBM),
                "quality_level": float(signal),
            }
            for name, signal in signals.items()
        ]

    @staticmethod
    def _collect_proc() -> list:
        """Read `/proc/net/wireless` (legacy wireless extensions fallback).

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
        config value as "absent" (`thresholds.py:146`), which would
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

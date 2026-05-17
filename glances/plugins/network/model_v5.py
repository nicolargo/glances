#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — Network plugin (collection, per-interface).

Migrated from `glances/plugins/network/__init__.py` (v4). First collection
plugin in v5 — exercises:

- per-item counter→rate via `GlancesPluginBase._transform_gauge`
- `_levels` indexed by primary key (`interface_name`)
- generic show/hide filtering driven from `[network] show=` / `hide=`
- `normalize_by` against per-direction bandwidth capacity, with the
  divisor=0 skip semantics for interfaces whose link speed is unknown
  (loopback, virtual interfaces) — see base class `_compute_levels_for_item`.

V4-aligned watched fields:
- ``bytes_recv`` / ``bytes_sent`` — prominent True, thresholds expressed
  as a ratio against ``bytes_speed_rate_per_sec`` (per-direction
  full-duplex split capacity). Default ratios 0.7 / 0.8 / 0.9 mirror v4's
  bandwidth-percentage alerts.
- ``errors_in`` / ``errors_out`` — prominent True, absolute err/s
  thresholds. Any sustained error is anomalous.

`dropped_in` / `dropped_out` are rate-only (not watched) — they are noisy
on busy interfaces and would generate too many false positives.

SNMP support is **not ported to v5** (architecture §10).
"""

from __future__ import annotations

import asyncio
from typing import Any, ClassVar

import psutil

from glances.plugins.plugin.base_v5 import GlancesPluginBase

# Default thresholds for bytes_recv / bytes_sent are interpreted as a
# ratio of the per-direction bandwidth capacity (bytes_speed_rate_per_sec)
# — values in [0, 1]. Matches v4's "warn at 70 % of interface speed".
_DEFAULT_BANDWIDTH_THRESHOLDS = {"careful": 0.7, "warning": 0.8, "critical": 0.9}

# Errors per second: any sustained error rate is anomalous.
_DEFAULT_ERROR_THRESHOLDS = {"careful": 1.0, "warning": 5.0, "critical": 20.0}


class PluginModel(GlancesPluginBase[list]):
    """Per-network-interface plugin (collection)."""

    plugin_name: ClassVar[str] = "network"
    IS_COLLECTION: ClassVar[bool] = True

    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "interface_name": {
            "description": "Network interface name.",
            "unit": "string",
            "primary_key": True,
        },
        "bytes_recv": {
            "description": "Bytes received per second.",
            "unit": "bytespers",
            "rate": True,
            "watched": True,
            "watch_direction": "high",
            "prominent": False,
            "default_thresholds": _DEFAULT_BANDWIDTH_THRESHOLDS,
            "normalize_by": "bytes_speed_rate_per_sec",
        },
        "bytes_sent": {
            "description": "Bytes sent per second.",
            "unit": "bytespers",
            "rate": True,
            "watched": True,
            "watch_direction": "high",
            "prominent": False,
            "default_thresholds": _DEFAULT_BANDWIDTH_THRESHOLDS,
            "normalize_by": "bytes_speed_rate_per_sec",
        },
        "errors_in": {
            "description": "Receive errors per second.",
            "unit": "number",
            "rate": True,
            "watched": True,
            "watch_direction": "high",
            "prominent": False,
            "default_thresholds": _DEFAULT_ERROR_THRESHOLDS,
        },
        "errors_out": {
            "description": "Send errors per second.",
            "unit": "number",
            "rate": True,
            "watched": True,
            "watch_direction": "high",
            "prominent": False,
            "default_thresholds": _DEFAULT_ERROR_THRESHOLDS,
        },
        "dropped_in": {
            "description": "Receive packets dropped per second.",
            "unit": "number",
            "rate": True,
        },
        "dropped_out": {
            "description": "Send packets dropped per second.",
            "unit": "number",
            "rate": True,
        },
        "bytes_speed_rate_per_sec": {
            "description": (
                "Estimated per-direction bandwidth capacity in bytes/s. "
                "Computed from net_if_stats().speed (Mbit/s) under a "
                "full-duplex split assumption: speed_mbits * 1e6 / 8 / 2. "
                "Returns 0 when the OS does not report a link speed "
                "(loopback, virtual interfaces) — in which case threshold "
                "normalisation is skipped for bytes_recv / bytes_sent."
            ),
            "unit": "bytespers",
        },
        "is_up": {
            "description": "Whether the interface is up.",
            "unit": "bool",
        },
    }

    async def _grab_stats(self) -> list:
        # Two psutil calls coalesced under asyncio.gather. They are
        # independent so the underlying threads run in parallel.
        io_counters, if_stats = await asyncio.gather(
            asyncio.to_thread(psutil.net_io_counters, pernic=True),
            asyncio.to_thread(psutil.net_if_stats),
        )

        out: list[dict[str, Any]] = []
        for name, counters in io_counters.items():
            stats = if_stats.get(name)
            speed_mbits = float(getattr(stats, "speed", 0) or 0) if stats is not None else 0.0
            # Mbit/s → bytes/s, full-duplex per-direction split (see schema
            # description). 0 stays 0 — the base class skips level
            # computation when the divisor is 0.
            bytes_speed_per_dir = (speed_mbits * 1_000_000.0 / 8.0) / 2.0 if speed_mbits else 0.0
            out.append(
                {
                    "interface_name": name,
                    "bytes_recv": counters.bytes_recv,
                    "bytes_sent": counters.bytes_sent,
                    "errors_in": counters.errin,
                    "errors_out": counters.errout,
                    "dropped_in": counters.dropin,
                    "dropped_out": counters.dropout,
                    "bytes_speed_rate_per_sec": bytes_speed_per_dir,
                    "is_up": bool(getattr(stats, "isup", False)) if stats is not None else False,
                }
            )
        return out

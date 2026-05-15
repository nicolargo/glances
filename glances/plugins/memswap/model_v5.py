#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — memswap plugin (scalar, system-wide swap usage).

Migrated from `glances/plugins/memswap/__init__.py`. Sister of the v5
`mem` plugin.

V4-aligned watched fields:
- ``percent`` — prominent True; thresholds 50/70/90 (mirrors `mem`).
- ``sin``/``sout`` — cumulative counters in v4; v5 exposes them as
  per-second rates via ``rate: True``.

The plugin tolerates platforms without a swap file (Illumos, OpenBSD —
cf. issues #1767, #2719): psutil raises on ``swap_memory()`` and v5
returns an empty payload rather than crashing the scheduler tick.

SNMP support is **not ported to v5** (architecture §10).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, ClassVar

import psutil

from glances.plugins.plugin.base_v5 import GlancesPluginBase

logger = logging.getLogger(__name__)

# Swap thresholds are looser than `mem` (60/80/95 vs 50/70/90): a fairly
# full swap is normal on systems with active paging and only really
# concerning near saturation. Override in glances.conf under [memswap].
_DEFAULT_PERCENT_THRESHOLDS = {"careful": 60.0, "warning": 80.0, "critical": 95.0}


class PluginModel(GlancesPluginBase[dict]):
    """System-wide swap memory plugin (scalar)."""

    plugin_name: ClassVar[str] = "memswap"
    IS_COLLECTION: ClassVar[bool] = False

    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "total": {
            "description": "Total swap memory.",
            "unit": "bytes",
        },
        "used": {
            "description": "Used swap memory.",
            "unit": "bytes",
        },
        "free": {
            "description": "Free swap memory.",
            "unit": "bytes",
        },
        "percent": {
            "description": "Used swap memory as a percentage of total.",
            "unit": "percent",
            "watched": True,
            "watch_direction": "high",
            "prominent": True,
            "default_thresholds": _DEFAULT_PERCENT_THRESHOLDS,
        },
        "sin": {
            "description": (
                "Bytes the system has swapped in from disk (per second — v4 reports "
                "the cumulative counter; v5 converts it to a rate)."
            ),
            "unit": "bytespers",
            "rate": True,
        },
        "sout": {
            "description": (
                "Bytes the system has swapped out to disk (per second — v4 reports "
                "the cumulative counter; v5 converts it to a rate)."
            ),
            "unit": "bytespers",
            "rate": True,
        },
    }

    async def _grab_stats(self) -> dict:
        try:
            sm = await asyncio.to_thread(psutil.swap_memory)
        except (OSError, RuntimeError) as exc:
            # Illumos / OpenBSD without a swap file (issues #1767, #2719).
            # Returning an empty dict lets the scheduler keep ticking without
            # ever populating the store for this plugin.
            logger.debug("memswap: psutil.swap_memory() unavailable on this host: %s", exc)
            return {}
        return sm._asdict()

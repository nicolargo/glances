#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — load plugin (scalar).

Migrated from `glances/plugins/load/__init__.py`. The v4 module is left
untouched until the final `develop-v5 → develop` merge (architecture §10).

V4-aligned alert semantics:
- `min1`  is **not watched** — too volatile (transient bursts cause flapping).
- `min5`  is watched with `prominent: False` — informational, font-only render.
- `min15` is watched with `prominent: True`  — the sustained-load signal,
   background-highlighted and (in v4) the only one logged into events.

In v5, both `min5` and `min15` transitions feed `GlancesAlerts.history`
(architecture §3.3 / §3.4); the `prominent` tag is what distinguishes
the visual treatment and, downstream, lets consumers (LLM diagnostic
plugin, etc.) filter by severity.

Thresholds are interpreted **per core** via `normalize_by: "cpucore"`
(v4-compatible). With `careful=0.7, warning=1.0, critical=5.0` and 4
cores, alerts fire on `min<N>` at `min<N>=2.8 / 4.0 / 20.0` respectively.
"""

from __future__ import annotations

import asyncio
from typing import Any, ClassVar

import psutil

from glances.plugins.plugin.base_v5 import GlancesPluginBase


def _logical_cores() -> int:
    """Best-effort logical CPU count, defaulting to 1."""
    try:
        return psutil.cpu_count(logical=True) or 1
    except Exception:
        return 1


_DEFAULT_THRESHOLDS = {"careful": 0.7, "warning": 1.0, "critical": 5.0}


class PluginModel(GlancesPluginBase[dict]):
    """Load average plugin (scalar)."""

    plugin_name: ClassVar[str] = "load"
    IS_COLLECTION: ClassVar[bool] = False

    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "min1": {
            "description": (
                "Average number of processes waiting in the run-queue plus those currently executing, over 1 minute."
            ),
            "unit": "float",
        },
        "min5": {
            "description": (
                "Average number of processes waiting in the run-queue plus those currently executing, over 5 minutes."
            ),
            "unit": "float",
            "watched": True,
            "watch_direction": "high",
            "prominent": False,
            "default_thresholds": _DEFAULT_THRESHOLDS,
            "normalize_by": "cpucore",
        },
        "min15": {
            "description": (
                "Average number of processes waiting in the run-queue plus those currently executing, over 15 minutes."
            ),
            "unit": "float",
            "watched": True,
            "watch_direction": "high",
            "prominent": True,
            "default_thresholds": _DEFAULT_THRESHOLDS,
            "normalize_by": "cpucore",
        },
        "cpucore": {
            "description": "Total number of logical CPU cores.",
            "unit": "number",
            "internal": True,
        },
    }

    async def _grab_stats(self) -> dict:
        try:
            avg = await asyncio.to_thread(psutil.getloadavg)
        except (AttributeError, OSError):
            return {}
        return {
            "min1": float(avg[0]),
            "min5": float(avg[1]),
            "min15": float(avg[2]),
            "cpucore": _logical_cores(),
        }

#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — quicklook plugin (scalar composite).

Migrated from `glances/plugins/quicklook/__init__.py`. Re-collects the
CPU / MEM / SWAP / LOAD percentages plus per-core CPU usage and CPU
metadata (name, frequency, core counts) for the compact "quicklook"
top-of-screen block.

v5 differences vs v4 (see the G2 plan, scope decisions):
- **No GPU** section (deferred to G4A with the gpu plugin).
- **No sparkline** (no v5 history store yet) — bars only.
- **No ZFS** arc adjustment on `mem` — plain (total-available)/total.

Collection uses the v5-native shared sampler (`glances/cpu_sampler_v5.py`)
for CPU aggregate + per-core, exactly like the `cpu`/`percpu` plugins —
NO import from any v4 plugin module.

`percpu`, `cpu_name`, `cpu_hz*` and the core counts are declared
`internal: True, watched: False`: kept out of level computation and the
generic renderer, but still delivered in the payload to the custom
`render_curses_v5.render()`.
"""

from __future__ import annotations

import asyncio
import platform
from typing import Any, ClassVar

import psutil

from glances.cpu_sampler_v5 import sampler
from glances.plugins.plugin.base_v5 import GlancesPluginBase

# Standard Glances percent ladder (matches v4 quicklook cpu/mem/load alerts).
_PERCENT_THRESHOLDS = {"careful": 50.0, "warning": 70.0, "critical": 90.0}


def _cpu_name() -> str:
    """Best-effort human CPU name.

    Linux: first `model name` line of /proc/cpuinfo. Other OSes (or Snap
    confinement blocking the open): fall back to `platform.processor()`.
    The `open()` is inside try/except for Snap strict confinement.
    """
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if line.startswith("model name"):
                    return line.split(":", 1)[1].strip()
    except (OSError, IndexError):
        pass
    return platform.processor() or "CPU"


def _collect_sync() -> dict[str, Any]:
    """Synchronous psutil collection (runs in a worker thread).

    Each metric is independently guarded so one failing call never drops
    the others.
    """
    out: dict[str, Any] = {}

    try:
        vm = psutil.virtual_memory()
        if vm.total:
            out["mem"] = round((vm.total - vm.available) / vm.total * 100.0, 1)
    except (OSError, RuntimeError, AttributeError):
        pass

    try:
        out["swap"] = psutil.swap_memory().percent
    except (OSError, RuntimeError):
        # Illumos raises RuntimeError (v4 #1767).
        pass

    try:
        log_core = sampler.cpu_count  # shared, cached-forever logical core count
        out["cpu_log_core"] = log_core
        load15 = psutil.getloadavg()[2]
        out["load"] = round(load15 / log_core * 100.0, 1)
    except (AttributeError, OSError, IndexError):
        pass

    try:
        out["cpu_phys_core"] = psutil.cpu_count(logical=False)
    except (OSError, RuntimeError):
        pass

    try:
        freq = psutil.cpu_freq()
        if freq is not None:
            if freq.current:
                out["cpu_hz_current"] = int(freq.current * 1_000_000)
            if freq.max:
                out["cpu_hz"] = int(freq.max * 1_000_000)
    except (OSError, RuntimeError, AttributeError, NotImplementedError):
        pass

    out["cpu_name"] = _cpu_name()
    return out


class PluginModel(GlancesPluginBase[dict]):
    """Quicklook plugin (scalar composite)."""

    plugin_name: ClassVar[str] = "quicklook"
    IS_COLLECTION: ClassVar[bool] = False

    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "cpu": {
            "description": "CPU percent usage.",
            "unit": "percent",
            "watched": True,
            "watch_direction": "high",
            "prominent": True,
            "default_thresholds": _PERCENT_THRESHOLDS,
        },
        "mem": {
            "description": "MEM percent usage.",
            "unit": "percent",
            "watched": True,
            "watch_direction": "high",
            "prominent": True,
            "default_thresholds": _PERCENT_THRESHOLDS,
        },
        "swap": {
            "description": "SWAP percent usage.",
            "unit": "percent",
            "watched": True,
            "watch_direction": "high",
            "prominent": False,
            "default_thresholds": _PERCENT_THRESHOLDS,
        },
        "load": {
            "description": "LOAD percent usage (15 min, normalized by core count).",
            "unit": "percent",
            "watched": True,
            "watch_direction": "high",
            "prominent": True,
            "default_thresholds": _PERCENT_THRESHOLDS,
        },
        "percpu": {
            "description": "Per-core CPU usage (list of {cpu_number, total}).",
            "unit": "percent",
            "internal": True,
            "watched": False,
        },
        "cpu_log_core": {
            "description": "Number of logical CPU cores.",
            "unit": "number",
            "internal": True,
            "watched": False,
        },
        "cpu_phys_core": {
            "description": "Number of physical CPU cores.",
            "unit": "number",
            "internal": True,
            "watched": False,
        },
        "cpu_name": {
            "description": "CPU name.",
            "unit": "string",
            "internal": True,
            "watched": False,
        },
        "cpu_hz_current": {
            "description": "CPU current frequency (Hz).",
            "unit": "hertz",
            "internal": True,
            "watched": False,
        },
        "cpu_hz": {
            "description": "CPU max frequency (Hz).",
            "unit": "hertz",
            "internal": True,
            "watched": False,
        },
    }

    async def _grab_stats(self) -> dict:
        out: dict[str, Any] = {}

        try:
            agg = await sampler.get_aggregate()
            out["cpu"] = round(100.0 - float(agg.idle), 1)
        except (OSError, RuntimeError, AttributeError):
            pass

        try:
            cores = await sampler.get_per_core()
            out["percpu"] = [{"cpu_number": i, "total": round(100.0 - float(c.idle), 1)} for i, c in enumerate(cores)]
        except (OSError, RuntimeError, AttributeError):
            pass

        out.update(await asyncio.to_thread(_collect_sync))
        return out

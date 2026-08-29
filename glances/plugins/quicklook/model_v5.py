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
from glances.logger import logger
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
    EXPORTABLE = False
    # Quicklook re-exposes cpu/mem/swap/load with the standard percent ladder
    # so its bars colour like the dedicated plugins — but those signals are
    # ALREADY watched by the cpu/mem/memswap/load plugins. Ingesting quicklook
    # too would double every aggregate alert. Keep colouring, skip the alerts
    # pipeline. See ``GlancesPluginBase.EMITS_ALERTS``.
    EMITS_ALERTS: ClassVar[bool] = False

    # `[quicklook] list` — which bars the TUI draws, in the configured order.
    # v4 values verbatim (glances/plugins/quicklook/__init__.py:92-93). The list
    # is DISPLAY-only: collection stays unconditional, so the payload, the REST
    # API and the history are identical whatever the user selects. That is what
    # makes strict v4 display parity free here — v5 dropped v4's global
    # `gpu_stats.get_gpu_*` polling flags, so listing a GPU stat no longer turns
    # any hardware polling on, and omitting it no longer turns any off.
    AVAILABLE_STATS_LIST: ClassVar[list[str]] = ["cpu", "mem", "swap", "load", "gpu_mem", "gpu_proc"]
    DEFAULT_STATS_LIST: ClassVar[list[str]] = ["cpu", "mem", "load"]
    DEFAULT_BAR_CHAR: ClassVar[str] = "|"

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
        "gpu_mem": {
            "description": "Average GPU memory consumption.",
            "unit": "percent",
            "watched": True,
            "watch_direction": "high",
            "prominent": True,
            "default_thresholds": _PERCENT_THRESHOLDS,
        },
        "gpu_proc": {
            "description": "Average GPU processor consumption.",
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
        "stats_list": {
            "description": "Stats displayed as bars, in display order ([quicklook] list).",
            "unit": "string",
            "internal": True,
            "watched": False,
        },
        "bar_char": {
            "description": "Character used to fill the bars ([quicklook] bar_char).",
            "unit": "string",
            "internal": True,
            "watched": False,
        },
    }

    def __init__(self, store: Any, config: Any) -> None:
        super().__init__(store, config)
        self.stats_list = self._read_stats_list()
        self.bar_char = self._read_bar_char()

    def _read_stats_list(self) -> list[str]:
        """Parse `[quicklook] list=cpu,mem,load` (v4 `__init__.py:110-121`).

        `config.get()` coerces to the default's type, so the list arrives
        already split and stripped (`config_v5._coerce_list`).
        """
        stats_list = self.config.get("quicklook", "list", self.DEFAULT_STATS_LIST)
        unknown = [stat for stat in stats_list if stat not in self.AVAILABLE_STATS_LIST]
        if unknown or not stats_list:
            # A misconfigured list falls back to the DEFAULT, not to everything
            # available — answering a config mistake by displaying MORE than was
            # asked for is what v4 did until PR #3700.
            if unknown:
                logger.warning(
                    "Quicklook plugin: unknown stats in the list: %s (available: %s), falling back to %s",
                    unknown,
                    self.AVAILABLE_STATS_LIST,
                    self.DEFAULT_STATS_LIST,
                )
            return list(self.DEFAULT_STATS_LIST)
        return stats_list

    def _read_bar_char(self) -> str:
        """Parse `[quicklook] bar_char=|` (v4 `get_conf_value('bar_char', default=['|'])[0]`).

        v4 reads the value as a list and keeps its first ITEM, so `bar_char=#,@`
        yields '#'. A multi-character item is passed through unchanged, exactly
        as in v4 — `Bar` repeats it per cell, which overflows the bar width.
        """
        chars = self.config.get("quicklook", "bar_char", [self.DEFAULT_BAR_CHAR])
        return chars[0] if chars else self.DEFAULT_BAR_CHAR

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
        self._add_gpu_means(out)
        # Display settings ride along as internal fields — the custom
        # render_curses_v5.render() has no other way to reach the config.
        out["stats_list"] = self.stats_list
        out["bar_char"] = self.bar_char
        return out

    def _add_gpu_means(self, out: dict[str, Any]) -> None:
        """Average the gpu plugin's per-card proc/mem into gpu_proc/gpu_mem.

        Cross-plugin read via the stats store — the gpu plugin publishes
        its card list, quicklook averages it (replaces v4's global
        `glances.gpu_percent` mutable channel). Keys are omitted entirely
        when no GPU is present or every card reports None, so the renderer
        draws no GPU bar (auto-show only when a GPU is detected).
        """
        cards = self.store.get("gpu")
        if not isinstance(cards, list) or not cards:
            return
        for src, dst in (("mem", "gpu_mem"), ("proc", "gpu_proc")):
            vals = [c[src] for c in cards if isinstance(c, dict) and c.get(src) is not None]
            if vals:
                out[dst] = round(sum(vals) / len(vals), 1)

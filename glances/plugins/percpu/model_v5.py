#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — per-CPU plugin (collection).

Migrated from `glances/plugins/percpu/__init__.py`. Companion to the v5
`cpu` plugin (system-wide aggregate); both share psutil samples through
``glances.cpu_sampler_v5`` (architecture §3 — equivalent of v4's
``glances/cpu_percent.py`` shared singleton).

Stats shape: one entry per logical CPU core, keyed on ``cpu_number``.

Field-level alerts (`watched`/`prominent`) are **not enabled** on
`percpu` — per-core alerting would mostly amplify noise from individual
cores while the aggregate is calm. The system-wide ``cpu`` plugin is
the source of CPU alerts. This matches v4 behaviour (no `'log': True`
on percpu fields).

Per-item level computation in collections lands in Phase 1.3 alongside
the network plugin; until then `_levels` stays empty for this plugin
regardless.
"""

from __future__ import annotations

import sys
from typing import Any, ClassVar

from glances.cpu_sampler_v5 import sampler
from glances.plugins.plugin.base_v5 import GlancesPluginBase


def _os_headers() -> list[str]:
    """Return the OS-specific stat columns, in TUI order (v4
    ``define_headers_from_os``). Mirrors
    ``glances.outputs.curses_renderer_v5``'s copy of the same logic — kept
    here, not imported from there, so the model does not depend on the
    presentation layer for a fact the model itself is the authority on.
    """
    base = ["user", "system"]
    p = sys.platform
    if p.startswith("linux"):
        return base + ["iowait", "idle", "irq", "nice", "steal", "guest"]
    if p == "darwin":
        return base + ["idle", "nice"]
    if "bsd" in p:
        return base + ["idle", "irq", "nice"]
    if p in ("win32", "cygwin"):
        return base + ["dpc", "interrupt"]
    # Unknown OS — fall back to the Linux column set.
    return base + ["iowait", "idle", "irq", "nice", "steal", "guest"]


class PluginModel(GlancesPluginBase[list]):
    """Per-CPU plugin (collection)."""

    plugin_name: ClassVar[str] = "percpu"
    IS_COLLECTION: ClassVar[bool] = True

    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "cpu_number": {
            "description": "CPU core number (zero-based logical core index).",
            "unit": "number",
            "primary_key": True,
        },
        "total": {
            "description": "Sum of CPU percentages (except idle) for this core.",
            "unit": "percent",
        },
        "system": {
            "description": (
                "Percent time spent in kernel space on this core. System CPU time is "
                "the time spent running code in the operating system kernel."
            ),
            "unit": "percent",
        },
        "user": {
            "description": (
                "Percent time spent in user space on this core. User CPU time is the "
                "time spent on the processor running the program's code."
            ),
            "unit": "percent",
        },
        "idle": {
            "description": "Percent time this core was idle.",
            "unit": "percent",
        },
        "iowait": {
            "description": "(Linux) Percent time this core spent waiting for I/O operations to complete.",
            "unit": "percent",
        },
        "irq": {
            "description": "(Linux and BSD) Percent time this core spent servicing hardware/software interrupts.",
            "unit": "percent",
        },
        "softirq": {
            "description": "(Linux) Percent time this core spent handling software interrupts.",
            "unit": "percent",
        },
        "nice": {
            "description": "(UNIX) Percent time this core spent on niced user-level processes.",
            "unit": "percent",
        },
        "steal": {
            "description": (
                "(Linux) Percentage of time this virtual CPU waited for a real CPU "
                "while the hypervisor was servicing another virtual processor."
            ),
            "unit": "percent",
        },
        "guest": {
            "description": "(Linux) Percent of time this core spent running a virtual CPU for guest OSes.",
            "unit": "percent",
        },
        "guest_nice": {
            "description": "(Linux) Percent of time this core spent running a niced guest virtual CPU.",
            "unit": "percent",
        },
        "dpc": {
            "description": "(Windows) Percent of time this core spent handling deferred procedure calls.",
            "unit": "percent",
        },
        "interrupt": {
            "description": "(Windows) Percent of time this core spent handling software interrupts.",
            "unit": "percent",
        },
        # `[percpu] max_cpu_display` — the cap both this plugin and quicklook
        # honour. Declared `internal`: it is configuration the renderers need,
        # not a metric (the same shape quicklook uses for `stats_list`).
        "max_cpu_display": {
            "description": "Maximum number of CPU cores displayed before the mean row ([percpu] max_cpu_display).",
            "unit": "number",
            "internal": True,
            "watched": False,
        },
        # OS-resolved column order (`_os_headers()`), published so the WebUI
        # renders the SAME subset in the SAME order as the TUI: the browser
        # cannot resolve `sys.platform`, but the server can — the same fix
        # already applied to `max_cpu_display` (final review, Important 3).
        "stat_fields": {
            "description": "OS-specific stat columns, in the order the TUI renders them (define_headers_from_os).",
            "unit": "string",
            "internal": True,
            "watched": False,
        },
    }

    def __init__(self, store: Any, config: Any) -> None:
        super().__init__(store, config)
        self.max_cpu_display = self._read_max_cpu_display()
        self.stat_fields = _os_headers()

    def _read_max_cpu_display(self) -> int:
        """Parse `[percpu] max_cpu_display=4` (v4 `percpu/__init__.py:119`)."""
        return self.config.get("percpu", "max_cpu_display", 4)

    def _add_metadata(self) -> None:
        super()._add_metadata()
        self._metadata["max_cpu_display"] = self.max_cpu_display
        self._metadata["stat_fields"] = self.stat_fields

    async def _grab_stats(self) -> list:
        # The shared sampler guards against psutil's "no baseline yet"
        # first-call behaviour (cf. `cpu_sampler_v5._is_unsettled`).
        per_core = await sampler.get_per_core()
        out: list[dict[str, Any]] = []
        for cpu_number, cpu_times in enumerate(per_core):
            entry: dict[str, Any] = {"cpu_number": cpu_number}
            # `total` = 100 - idle, rounded as in v4 cpu_percent.py.
            idle = getattr(cpu_times, "idle", None)
            if idle is not None:
                entry["total"] = round(100.0 - float(idle), 1)
            for name in (
                "user",
                "system",
                "idle",
                "nice",
                "iowait",
                "irq",
                "softirq",
                "steal",
                "guest",
                "guest_nice",
                "dpc",
                "interrupt",
            ):
                if hasattr(cpu_times, name):
                    entry[name] = getattr(cpu_times, name)
            out.append(entry)
        return out

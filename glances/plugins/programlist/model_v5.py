#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — Program list plugin (collection, per-program).

Migrated from `glances/plugins/programlist/__init__.py` (v4, which subclasses
`ProcesslistPlugin`). The per-program view aggregates threads sharing the same
process ``name`` into a single row — the v4 ``j`` hotkey toggles between this
view and the per-thread ``processlist``.

Like ``processlist`` this plugin reads the already-populated, already-sorted
engine list: ``glances_processes.get_list(as_programs=True)`` runs
``glances.programs.processes_to_programs`` over the current ``processlist``
(populated by the ``processcount`` plugin earlier in the cycle). Primary key
is ``name`` (programs have no single pid — the engine sets ``pid='_'``).

Alerts: like ``processlist``, the watched CPU/MEM thresholds drive the TUI
colouring only — ``EMITS_ALERTS=False`` keeps the alerts pipeline out (v4
never paged on individual programs).

V5 scope (G5-hotkeys): aggregation reused as-is; no extended view, no filter
UI. The ``j`` hotkey lives in the curses TUI, which shows exactly one of
``processlist`` / ``programlist`` at a time.
"""

from __future__ import annotations

import logging
from typing import Any, ClassVar

from glances.plugins.plugin.base_v5 import GlancesPluginBase
from glances.processes import glances_processes

logger = logging.getLogger(__name__)

# Same ladder as processlist — a single program above 50% is noteworthy.
# Note: a program's cpu_percent / memory_percent is the SUM across its child
# threads, so it can exceed 100% (mirrors v4, which reuses the processlist
# thresholds for the program view).
_DEFAULT_CPU_THRESHOLDS = {"careful": 50.0, "warning": 70.0, "critical": 90.0}
_DEFAULT_MEM_THRESHOLDS = {"careful": 50.0, "warning": 70.0, "critical": 90.0}


class PluginModel(GlancesPluginBase[list]):
    """Per-program plugin (collection, keyed on ``name``)."""

    plugin_name: ClassVar[str] = "programlist"
    IS_COLLECTION: ClassVar[bool] = True
    # Same rationale as processlist: per-program thresholds colour cells but
    # must not page or pile up events. See ``GlancesPluginBase.EMITS_ALERTS``.
    EMITS_ALERTS: ClassVar[bool] = False

    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "name": {
            "description": "Program name (shared process name aggregating its threads).",
            "unit": "string",
            "primary_key": True,
        },
        "username": {
            "description": "Program owner (user name, '_' when children differ).",
            "unit": "string",
        },
        "nprocs": {
            "description": "Number of child processes aggregated into this program.",
            "unit": "number",
        },
        "status": {
            "description": "Program status ('_' when children differ).",
            "unit": "string",
            "watched": True,
            "threshold_type": "categorical",
            "prominent": False,
        },
        "nice": {
            "description": "Program nice value ('_' when children differ).",
            "unit": "number",
            "watched": True,
            "threshold_type": "categorical",
            "prominent": False,
        },
        "num_threads": {
            "description": "Total number of threads across the program's children.",
            "unit": "number",
        },
        "cpu_percent": {
            "description": "Program CPU consumption (sum across children — can exceed 100%).",
            "unit": "percent",
            "watched": True,
            "watch_direction": "high",
            "prominent": False,
            "default_thresholds": _DEFAULT_CPU_THRESHOLDS,
        },
        "memory_percent": {
            "description": "Program resident memory consumption (sum across children).",
            "unit": "percent",
            "watched": True,
            "watch_direction": "high",
            "prominent": False,
            "default_thresholds": _DEFAULT_MEM_THRESHOLDS,
        },
        "cmdline": {
            "description": "Command line (the program name, as a single-token list).",
            "unit": "list",
        },
        # ---------------- internal (kept for export, hidden from generic TUI)
        "memory_info": {
            "description": "Aggregated memory information (dict with rss/vms keys).",
            "unit": "byte",
            "internal": True,
        },
        "cpu_times": {
            "description": "Aggregated CPU times (dict with user/system keys).",
            "unit": "second",
            "internal": True,
        },
        "io_counters": {
            "description": "Aggregated I/O counters (concatenated per-child blocks).",
            "unit": "byte",
            "internal": True,
        },
        "time_since_update": {
            "description": "Wall-clock interval since the previous engine refresh (seconds).",
            "unit": "second",
            "internal": True,
        },
    }

    async def _grab_stats(self) -> list:
        try:
            raw = glances_processes.get_list(as_programs=True)
        except Exception as exc:  # noqa: BLE001 — engine is third-party-ish, guard widely
            logger.debug("programlist: engine.get_list(as_programs=True) failed: %s", exc)
            return []
        if not isinstance(raw, list):
            return []
        # Copy each entry so downstream consumers cannot mutate engine state.
        return [dict(p) for p in raw if isinstance(p, dict)]

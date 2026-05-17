#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — Process list plugin (collection, per-process).

Migrated from `glances/plugins/processlist/__init__.py` (v4). Collection
plugin keyed on ``pid``. The companion ``processcount`` plugin runs the
shared engine each cycle; this plugin reads the already-populated list.

V5 scope (G4-processlist):
- Top-level fields only — pid, name, username, status, nice, num_threads,
  cpu_percent (watched 50/70/90), memory_percent (watched 50/70/90),
  cmdline, cpu_num.
- Engine-internal fields (``memory_info``, ``cpu_times``, ``io_counters``,
  ``gids``, ``time_since_update``, ``key``) are flagged ``internal=True``
  so they are kept in the store for downstream consumers but excluded
  from the generic renderer's column set.
- No extended view, no programs aggregation, no filter UI (deferred).

Coupling note: depends on ``processcount`` running first in the cycle to
trigger ``engine.update()``. Mirrors v4 contract.
"""

from __future__ import annotations

import logging
from typing import Any, ClassVar

from glances.plugins.plugin.base_v5 import GlancesPluginBase
from glances.processes import glances_processes

logger = logging.getLogger(__name__)

# Match v4 mem ladder: anything above 50% is noteworthy on a single process.
_DEFAULT_CPU_THRESHOLDS = {"careful": 50.0, "warning": 70.0, "critical": 90.0}
_DEFAULT_MEM_THRESHOLDS = {"careful": 50.0, "warning": 70.0, "critical": 90.0}


class PluginModel(GlancesPluginBase[list]):
    """Per-process plugin (collection)."""

    plugin_name: ClassVar[str] = "processlist"
    IS_COLLECTION: ClassVar[bool] = True

    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "pid": {
            "description": "Process identifier (PID).",
            "unit": "number",
            "primary_key": True,
        },
        "name": {
            "description": "Process name.",
            "unit": "string",
        },
        "username": {
            "description": "Process owner (user name).",
            "unit": "string",
        },
        "status": {
            "description": "Process status (single letter — S sleeping, R running, etc.).",
            "unit": "string",
            "watched": True,
            "threshold_type": "categorical",
            "prominent": False,
            # No defaults — operators opt in via:
            #   [processlist]
            #   status_ok=R,W,P,I
            #   status_critical=Z,D
        },
        "nice": {
            "description": "Process nice value.",
            "unit": "number",
            "watched": True,
            "threshold_type": "categorical",
            "prominent": False,
            # Opt-in via comma-separated int lists, e.g.:
            #   [processlist]
            #   nice_warning=-20,-19,...,-1,1,2,...,19   (non-zero is warning)
            # or escalating buckets:
            #   nice_careful=1,2,3,4,5,6,7,8,9
            #   nice_warning=10,11,12,13,14
            #   nice_critical=15,16,17,18,19
        },
        "num_threads": {
            "description": "Number of threads spawned by the process.",
            "unit": "number",
        },
        "cpu_percent": {
            "description": (
                "Process CPU consumption (can exceed 100% on multi-threaded workloads spread across cores)."
            ),
            "unit": "percent",
            "watched": True,
            "watch_direction": "high",
            "prominent": False,
            "default_thresholds": _DEFAULT_CPU_THRESHOLDS,
        },
        "memory_percent": {
            "description": "Process resident memory consumption as a percentage of total RAM.",
            "unit": "percent",
            "watched": True,
            "watch_direction": "high",
            "prominent": False,
            "default_thresholds": _DEFAULT_MEM_THRESHOLDS,
        },
        "cmdline": {
            "description": "Command line of the process (list of argv tokens).",
            "unit": "list",
        },
        "cpu_num": {
            "description": "CPU core number where the process is currently running.",
            "unit": "number",
        },
        # ---------------- internal (kept for export, hidden from generic TUI)
        "memory_info": {
            "description": "Process memory information (psutil pmem namedtuple).",
            "unit": "byte",
            "internal": True,
        },
        "cpu_times": {
            "description": "Process CPU times (psutil pcputimes namedtuple).",
            "unit": "second",
            "internal": True,
        },
        "io_counters": {
            "description": "Process I/O counters (list [read_bytes, write_bytes, ..., io_tag]).",
            "unit": "byte",
            "internal": True,
        },
        "gids": {
            "description": "Process group IDs (psutil pgids namedtuple).",
            "unit": "number",
            "internal": True,
        },
        "time_since_update": {
            "description": "Wall-clock interval since the previous engine refresh (seconds).",
            "unit": "second",
            "internal": True,
        },
        "key": {
            "description": "Name of the primary key field (always ``pid``).",
            "unit": "string",
            "internal": True,
        },
    }

    async def _grab_stats(self) -> list:
        try:
            raw = glances_processes.get_list()
        except Exception as exc:  # noqa: BLE001 — engine is third-party-ish, guard widely
            logger.debug("processlist: engine.get_list() failed: %s", exc)
            return []
        if not isinstance(raw, list):
            return []
        # The engine returns the live list (and its dicts); copy each entry
        # so downstream consumers cannot mutate the engine's internal state.
        return [dict(p) for p in raw if isinstance(p, dict)]

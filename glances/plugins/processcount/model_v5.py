#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — Process count plugin (scalar aggregates).

Migrated from `glances/plugins/processcount/__init__.py` (v4). Drives the
shared ``glances.processes.glances_processes`` singleton: ``_grab_stats``
calls ``engine.update()`` once per cycle and surfaces the aggregate
counters (``total`` / ``running`` / ``sleeping`` / ``thread`` / ``pid_max``).

V5 scope (G4-processlist):
- Engine reused as-is — no rewrite of ``glances/processes.py``.
- Extended view, programs aggregation and the filter UI are NOT wired
  through v5 args yet; they default to off (the engine's ``disable_tag`` /
  ``disable_extended_tag`` stay False, ``process_filter`` stays None).
  Re-plumbing through ``GlancesConfigV5`` / v5 CLI is deferred to G5.

Coupling note: the companion ``processlist`` plugin calls
``glances_processes.get_list()`` and depends on this plugin having run
first in the cycle (so ``engine.update()`` has populated the list).
Mirrors v4's processcount-runs-the-engine contract.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, ClassVar

from glances.plugins.plugin.base_v5 import GlancesPluginBase
from glances.processes import glances_processes

logger = logging.getLogger(__name__)


class PluginModel(GlancesPluginBase[dict]):
    """Process aggregate counts (scalar)."""

    plugin_name: ClassVar[str] = "processcount"

    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "total": {
            "description": "Total number of processes.",
            "unit": "number",
            "history": True,
        },
        "running": {
            "description": "Number of running processes.",
            "unit": "number",
            "history": True,
        },
        "sleeping": {
            "description": "Number of sleeping processes.",
            "unit": "number",
            "history": True,
        },
        "thread": {
            "description": "Total number of threads across all processes.",
            "unit": "number",
            "history": True,
        },
        "pid_max": {
            "description": "Maximum PID value supported by the kernel (Linux) or None.",
            "unit": "number",
        },
        # The live process sort, published so the WebUI and a client TUI read
        # the key the engine sorted this cycle's list with (shared sort design,
        # 2026-09-30). `internal`: the API keeps it; `exportable: False`: a
        # string column in a time-series backend would be noise.
        "sort_key": {
            "description": "Key the processes, containers and VMs are sorted by.",
            "unit": "string",
            "internal": True,
            "exportable": False,
        },
        "auto_sort": {
            "description": "True when the sort key is chosen automatically (from the alerts).",
            "unit": "bool",
            "internal": True,
            "exportable": False,
        },
    }

    async def _grab_stats(self) -> dict[str, Any]:
        try:
            await asyncio.to_thread(glances_processes.update)
        except Exception as exc:  # noqa: BLE001 — engine is third-party-ish (psutil iter), guard widely
            logger.debug("processcount: engine.update() failed: %s", exc)
            return {}
        count = glances_processes.get_count()
        if not isinstance(count, dict):
            return {}
        # Engine returns a live dict ref — copy so downstream consumers
        # can't mutate the engine's state.
        return dict(count)

    def _add_metadata(self) -> None:
        # Read right after `engine.update()` (`_grab_stats`), which is what
        # sorts the list: the key published is the one this cycle used.
        super()._add_metadata()
        self._metadata["sort_key"] = glances_processes.sort_key
        self._metadata["auto_sort"] = bool(glances_processes.auto_sort)

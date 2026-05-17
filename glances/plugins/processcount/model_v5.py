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
        },
        "running": {
            "description": "Number of running processes.",
            "unit": "number",
        },
        "sleeping": {
            "description": "Number of sleeping processes.",
            "unit": "number",
        },
        "thread": {
            "description": "Total number of threads across all processes.",
            "unit": "number",
        },
        "pid_max": {
            "description": "Maximum PID value supported by the kernel (Linux) or None.",
            "unit": "number",
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

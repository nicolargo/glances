#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — core plugin (CPU core counts, REST-only).

Migrated from `glances/plugins/core/__init__.py`. v4 sets
``display_curse=False`` (the load plugin surfaces the core count), so v5
sets ``DISPLAY_IN_TUI=False``. The data is still served via REST and
consumable by exporters.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, ClassVar

import psutil

from glances.plugins.plugin.base_v5 import GlancesPluginBase

logger = logging.getLogger(__name__)


class PluginModel(GlancesPluginBase[dict]):
    """CPU core-count plugin (scalar, REST-only)."""

    plugin_name: ClassVar[str] = "core"
    IS_COLLECTION: ClassVar[bool] = False
    DISPLAY_IN_TUI: ClassVar[bool] = False

    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "phys": {
            "description": "Number of physical cores (hyper-thread CPUs excluded).",
            "unit": "number",
        },
        "log": {
            "description": "Number of logical CPU cores (physical cores × threads per core).",
            "unit": "number",
        },
    }

    async def _grab_stats(self) -> dict:
        try:
            phys, log = await asyncio.to_thread(self._counts)
        except (OSError, RuntimeError, NameError) as exc:
            logger.debug("core: psutil.cpu_count() unavailable: %s", exc)
            return {}
        return {"phys": phys, "log": log}

    @staticmethod
    def _counts() -> tuple[int | None, int | None]:
        return psutil.cpu_count(logical=False), psutil.cpu_count()

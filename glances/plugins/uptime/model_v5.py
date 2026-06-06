#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — uptime plugin (scalar).

Migrated from `glances/plugins/uptime/__init__.py`. v4 stored a formatted
string; v5 stores the canonical ``seconds`` since boot (matching v4's
``get_export`` contract ``{'seconds': N}``). The TUI renderer formats it
to ``3d04h`` style via the ``seconds`` unit formatter.

SNMP support is **not ported to v5** (architecture §10).
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, ClassVar

import psutil

from glances.plugins.plugin.base_v5 import GlancesPluginBase

logger = logging.getLogger(__name__)


class PluginModel(GlancesPluginBase[dict]):
    """System uptime plugin (scalar)."""

    plugin_name: ClassVar[str] = "uptime"
    IS_COLLECTION: ClassVar[bool] = False

    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "seconds": {
            "description": "Seconds elapsed since the system booted.",
            "unit": "seconds",
        },
    }

    async def _grab_stats(self) -> dict:
        try:
            boot = await asyncio.to_thread(psutil.boot_time)
        except (OSError, RuntimeError) as exc:
            logger.debug("uptime: psutil.boot_time() unavailable: %s", exc)
            return {}
        return {"seconds": int(max(0.0, time.time() - boot))}

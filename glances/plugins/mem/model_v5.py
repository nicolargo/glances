#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — memory plugin (scalar).

Migrated from `glances/plugins/mem/__init__.py`. The v4 module is left
untouched until the final `develop-v5 → develop` merge (architecture §10).
"""

from __future__ import annotations

import asyncio
from typing import Any, ClassVar

import psutil

from glances.plugins.plugin.base_v5 import GlancesPluginBase


class PluginModel(GlancesPluginBase[dict]):
    """Virtual memory plugin (scalar)."""

    plugin_name: ClassVar[str] = "mem"
    IS_COLLECTION: ClassVar[bool] = False

    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "total": {
            "description": "Total physical memory available.",
            "unit": "bytes",
        },
        "available": {
            "description": (
                "Actual amount of available memory that can be given instantly to "
                "processes that request more memory; calculated by summing different "
                "memory values depending on the platform (e.g. free + buffers + cached "
                "on Linux). Suitable for monitoring actual memory usage in a "
                "cross-platform fashion."
            ),
            "unit": "bytes",
            "short_name": "avail",
        },
        "percent": {
            "description": "Percentage usage calculated as (total - available) / total * 100.",
            "unit": "percent",
            "watched": True,
            "watch_direction": "high",
            "prominent": True,
            "default_thresholds": {"careful": 50.0, "warning": 70.0, "critical": 90.0},
        },
        "used": {
            "description": (
                "Memory used, calculated differently depending on the platform and "
                "designed for informational purposes only."
            ),
            "unit": "bytes",
        },
        "free": {
            "description": (
                "Memory not being used at all (zeroed) that is readily available; "
                "note that this does not reflect the actual memory available — use "
                "`available` instead."
            ),
            "unit": "bytes",
        },
        "active": {
            "description": "(UNIX) Memory currently in use or very recently used, resident in RAM.",
            "unit": "bytes",
        },
        "inactive": {
            "description": "(UNIX) Memory that is marked as not used.",
            "unit": "bytes",
            "short_name": "inacti",
        },
        "buffers": {
            "description": "(Linux, BSD) Cache for items like filesystem metadata.",
            "unit": "bytes",
            "short_name": "buffer",
        },
        "cached": {
            "description": "(Linux, BSD) Cache for various things (including ZFS cache).",
            "unit": "bytes",
        },
        "shared": {
            "description": "(BSD) Memory that may be simultaneously accessed by multiple processes.",
            "unit": "bytes",
        },
        "wired": {
            "description": "(BSD, macOS) Memory marked to always stay in RAM — never paged to disk.",
            "unit": "bytes",
        },
        "slab": {
            "description": "(Linux) In-kernel data structures cache.",
            "unit": "bytes",
        },
    }

    async def _grab_stats(self) -> dict:
        vm = await asyncio.to_thread(psutil.virtual_memory)
        # psutil returns a namedtuple — fields not declared in
        # fields_description are stripped by the base in _remove_parameters.
        return vm._asdict()

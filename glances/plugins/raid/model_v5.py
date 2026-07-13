#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — raid plugin (collection, per-array).

Migrated from `glances/plugins/raid/__init__.py`. The v4 grabber
(`pymdstat.MdStat().get_stats()['arrays']`) returns a dict keyed by array
name; the v5 collection needs a flat list, so each array's dict key is
injected as the `name` primary-key field.

Deliberate divergence from v4: `EMITS_ALERTS = True`. v4 coloured degraded
(warning) / inactive (critical) arrays but never raised an alert. A
degraded or inactive RAID array is a real incident, so v5 feeds the alert
history + action pipeline. There is no `careful` tier for RAID.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, ClassVar

from glances.plugins.plugin.base_v5 import GlancesPluginBase

logger = logging.getLogger(__name__)

# Import the optional v4 grabber; absence disables the plugin (empty list).
try:
    from pymdstat import MdStat
except ImportError:
    MdStat = None  # type: ignore[assignment]


class PluginModel(GlancesPluginBase[list]):
    """RAID plugin (collection)."""

    plugin_name: ClassVar[str] = "raid"
    IS_COLLECTION: ClassVar[bool] = True
    # Divergence from v4 (colour-only): degraded/inactive arrays alert.
    EMITS_ALERTS: ClassVar[bool] = True

    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "name": {
            "description": "RAID array name.",
            "unit": "string",
            "primary_key": True,
        },
        "type": {
            "description": "RAID level (e.g. raid1); None renders as UNKNOWN.",
            "unit": "string",
            "internal": True,
            "watched": False,
        },
        "status": {
            "description": "RAID array status (active/inactive).",
            "unit": "string",
            "internal": True,
            "watched": False,
        },
        "used": {
            "description": "Number of used disks.",
            "unit": "number",
            "watched": False,
        },
        "available": {
            "description": "Number of available disks.",
            "unit": "number",
            "watched": False,
        },
        "components": {
            "description": "Component disks (name -> role).",
            "unit": "string",
            "internal": True,
            "watched": False,
        },
        "config": {
            "description": "Array layout string (e.g. UU / U_).",
            "unit": "string",
            "internal": True,
            "watched": False,
        },
    }

    async def _grab_stats(self) -> list:
        return await asyncio.to_thread(self._collect)

    @staticmethod
    def _collect() -> list:
        """Synchronous grab (runs in a worker thread).

        Wraps the v4 pymdstat grabber. Guarded twice:
        - `MdStat is None` (import failed) -> empty collection.
        - any runtime failure (no /proc/mdstat, parse error) -> empty
          collection; the base class keeps the last good stats.

        The v4 grabber returns a dict keyed by array name; we inject that
        key as the `name` primary-key field and return a flat list.
        """
        if MdStat is None:
            return []
        try:
            arrays = MdStat().get_stats()["arrays"]
        except Exception as exc:  # noqa: BLE001 — any grab failure -> empty, keep last good
            logger.debug("raid: grab failed: %s", exc)
            return []
        out: list[dict[str, Any]] = []
        for name, array in arrays.items():
            if not isinstance(array, dict):
                continue
            row = dict(array)
            row["name"] = name
            out.append(row)
        return out

    def _derived_parameters(self) -> None:
        """Compute per-array alert levels (mirrors v4 `raid_alert`).

        Overrides the base watched-field walk entirely — RAID's level is a
        bespoke ladder keyed on the (non-watched) `status` field so the
        renderer and the alert engine share one index. `prominent: False`
        → coloured text, no background highlight (sensors parity).
        """
        self._levels = {}
        if not isinstance(self._stats, list):
            return
        for item in self._stats:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            if name is None:
                continue
            level = self._array_level(item)
            if level is None:
                continue
            self._levels[str(name)] = {"status": {"level": level, "prominent": False}}

    @staticmethod
    def _array_level(item: dict) -> str | None:
        """RAID alert ladder (v4 `raid_alert` parity).

        raid0 (no redundancy) -> ok; inactive -> critical; missing disk
        counts -> None (DEFAULT, no colour/alert); fewer used than
        available disks -> warning (degraded); else ok.
        """
        array_type = item.get("type")
        status = item.get("status")
        used = item.get("used")
        available = item.get("available")
        if array_type == "raid0":
            return "ok"
        if status == "inactive":
            return "critical"
        if used is None or available is None:
            return None
        if used < available:
            return "warning"
        return "ok"

#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — smart plugin (collection, per-device).

Ported from `glances/plugins/smart/__init__.py`. Reuses the v4 module-level
grabber `get_smart_data(hide_attributes)` (pySMART) verbatim, wrapped in
`asyncio.to_thread` and gated on root (`is_admin()`) + the pySMART import.

v4 keys each device dict by NUMERIC attribute ids, which the flat v5 field
filter would strip. Each device is therefore RESHAPED into
`{"name": DeviceName, "attributes": [attr, …]}` (attrs sorted by the v4
numeric order); `_remove_parameters` filters only top-level item keys, so the
nested `attributes` list passes through intact.

No levels, no alerts (EMITS_ALERTS = False) — v4 smart is display-only.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, ClassVar

import glances.plugins.smart as smart_v4
from glances.globals import is_admin
from glances.plugins.plugin.base_v5 import GlancesPluginBase

logger = logging.getLogger(__name__)


class PluginModel(GlancesPluginBase[list]):
    """SMART disk attributes plugin (collection)."""

    plugin_name: ClassVar[str] = "smart"
    IS_COLLECTION: ClassVar[bool] = True
    # v4 smart is display-only: no watched fields, no colouring, no alerts.
    EMITS_ALERTS: ClassVar[bool] = False

    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "name": {
            "description": "Device identification string (e.g. '/dev/sda Samsung SSD 850').",
            "unit": "string",
            "primary_key": True,
        },
        "attributes": {
            "description": "List of SMART attribute dicts (name, key, raw, value, worst, threshold, ...).",
            "unit": "list",
            "internal": True,
            "watched": False,
        },
    }

    def __init__(self, store: Any, config: Any) -> None:
        super().__init__(store, config)
        self._hide_attributes = self._parse_hide_attributes()

    def _parse_hide_attributes(self) -> list[str]:
        """Parse `[smart] hide_attributes=a,b,c` into a list (v4 parity)."""
        raw = self.config.get("smart", "hide_attributes", "")
        if not raw:
            return []
        logger.info("Following SMART attributes will not be displayed: %s", raw)
        return str(raw).split(",")

    async def _grab_stats(self) -> list:
        """Grab SMART data (root-gated, pySMART-guarded) and reshape.

        Mirrors v4 `update()`: non-root disables the plugin (→ empty), a
        missing pySMART import disables it (→ empty). Otherwise the v4 helper
        runs in a worker thread and each device is reshaped for v5.
        """
        if not is_admin():
            # v4 calls `disable(args, "smart")` when not admin; here we simply
            # yield an empty collection (base keeps it valid).
            return []
        if smart_v4.import_error_tag:
            return []
        devices = await asyncio.to_thread(smart_v4.get_smart_data, self._hide_attributes)
        return [self._reshape(dev) for dev in devices if isinstance(dev, dict)]

    @staticmethod
    def _reshape(device: dict) -> dict:
        """Flatten a v4 numeric-keyed device dict into the v5 shape.

        `{'DeviceName': str, <num>: attr, …}` -> `{"name": str, "attributes": [attr, …]}`.
        Attribute keys are sorted by their v4 numeric id (`sorted(key=int)`);
        non-numeric keys (#2904) keep insertion order.
        """
        name = device.get("DeviceName", "")
        keys = [k for k in device if k != "DeviceName"]
        try:
            keys = sorted(keys, key=int)
        except (TypeError, ValueError):
            pass  # #2904 — some keys are not numeric; keep insertion order.
        return {"name": name, "attributes": [device[k] for k in keys]}

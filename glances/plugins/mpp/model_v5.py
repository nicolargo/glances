#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — MPP plugin (collection, per media engine).

Migrated from `glances/plugins/mpp/__init__.py`. Reuses the v4 hardware
card `glances/plugins/mpp/cards/rockchip_mpp.py` as a pure collector,
the same way `npu/model_v5.py` reuses `npu/cards/*`.

**Glances does not write to `/proc`.** The Rockchip kernel driver only
reports engine load once `/proc/mpp_service/load_interval` is non-zero.
v4 silently wrote that setting; v5 does not, because a monitoring tool
must not mutate a global kernel setting. Until the operator sets it, the
card reports no engines — so this plugin logs one WARNING naming the
exact command, then stays quiet. See `docs/aoa/mpp.rst`.

**Default-disabled**: v4 ships `[mpp] disable=True`.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, ClassVar

from glances.plugins.mpp.cards.rockchip_mpp import RockchipMPP
from glances.plugins.plugin.base_v5 import GlancesPluginBase

logger = logging.getLogger(__name__)

_PERCENT_THRESHOLDS = {"careful": 50.0, "warning": 70.0, "critical": 90.0}

_NO_LOAD_HINT = (
    "mpp: the MPP service is present but reports no engine load. The kernel "
    "only publishes load once /proc/mpp_service/load_interval is non-zero, and "
    "Glances does not set it. Run as root, once per boot: "
    "echo 1000 > /proc/mpp_service/load_interval — see docs/aoa/mpp.rst"
)


class PluginModel(GlancesPluginBase[list]):
    """Per-MPP-engine plugin (collection)."""

    plugin_name: ClassVar[str] = "mpp"
    IS_COLLECTION: ClassVar[bool] = True
    EMITS_ALERTS: ClassVar[bool] = True
    # Mirrors v4 `[mpp] disable=True`.
    DISABLED_BY_DEFAULT: ClassVar[bool] = True

    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "engine_id": {
            "description": "Engine identification (e.g. rockchip_rkvenc).",
            "unit": "string",
            "primary_key": True,
        },
        "name": {"description": "Engine name (RKVENC, RKVDEC, RKJPEGD).", "unit": "string"},
        "type": {"description": "Engine type (enc, dec, jpeg).", "unit": "string"},
        "load": {
            "description": "Engine load.",
            "unit": "percent",
            "watched": True,
            "watch_direction": "high",
            "prominent": True,
            "default_thresholds": _PERCENT_THRESHOLDS,
        },
        "utilization": {"description": "Engine utilization.", "unit": "percent"},
        "sessions": {"description": "Number of active sessions.", "unit": "number"},
    }

    def __init__(self, store: Any, config: Any) -> None:
        super().__init__(store, config)
        self._card = RockchipMPP()
        self._warned_no_load = False

    def _collect(self) -> list:
        if not self._card.is_available():
            # No Rockchip MPP hardware here. Not an operator mistake — the
            # plugin simply has nothing to report.
            return []
        try:
            stats = self._card.get_stats()
        except Exception as exc:  # noqa: BLE001 — a faulty card must not kill the loop
            logger.debug("mpp: collection failed, disabling the card: %s", exc)
            self._card.disable()
            return []

        if not stats and not self._warned_no_load:
            # The service exists but publishes nothing: almost always the
            # unset load_interval. Say so once, with the fix.
            self._warned_no_load = True
            logger.warning(_NO_LOAD_HINT)
        return stats

    async def _grab_stats(self) -> list:
        return await asyncio.to_thread(self._collect)

    def stop(self) -> None:
        self._card.exit()

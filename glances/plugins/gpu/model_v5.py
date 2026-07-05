#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — GPU plugin (collection, per-card).

Migrated from `glances/plugins/gpu/__init__.py`. Reuses the v4 hardware
card backends (`glances/plugins/gpu/cards/{nvidia,amd,intel,arm}.py`) as
pure collectors — each is instantiated once (guarded; a backend whose
init raises is simply left out) and polled every cycle inside
`asyncio.to_thread`. One backend failing never drops the others.

The v4 `__init__.py` side effect of writing GPU means into the global
`glances.gpu_percent` module is intentionally NOT ported — the v5
quicklook reads this plugin's published cards from the stats store
instead (see quicklook/model_v5.py).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, ClassVar

from glances.plugins.plugin.base_v5 import GlancesPluginBase

logger = logging.getLogger(__name__)

_PERCENT_THRESHOLDS = {"careful": 70.0, "warning": 80.0, "critical": 90.0}
# GPU temperature ladder — exact v4 conf/glances.conf [gpu] defaults.
_TEMP_THRESHOLDS = {"careful": 60.0, "warning": 70.0, "critical": 80.0}


def _build_backends() -> list:
    """Instantiate every available v4 GPU card backend, guarded.

    A backend whose constructor raises (driver/library absent) is skipped.
    Import is local so a missing optional dependency (e.g. pynvml) cannot
    break module import for machines without that vendor.
    """
    backends: list = []
    from glances.plugins.gpu.cards.amd import AmdGPU
    from glances.plugins.gpu.cards.arm import ArmGPU
    from glances.plugins.gpu.cards.intel import IntelGPU
    from glances.plugins.gpu.cards.nvidia import NvidiaGPU

    for cls in (NvidiaGPU, AmdGPU, IntelGPU, ArmGPU):
        try:
            backends.append(cls())
        except Exception as exc:  # noqa: BLE001 — any driver/lib error → skip vendor
            logger.debug("gpu: %s init failed: %s", cls.__name__, exc)
    return backends


class PluginModel(GlancesPluginBase[list]):
    """Per-GPU plugin (collection)."""

    plugin_name: ClassVar[str] = "gpu"
    IS_COLLECTION: ClassVar[bool] = True

    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "gpu_id": {
            "description": "GPU identifier (e.g. nvidia0).",
            "unit": "string",
            "primary_key": True,
        },
        "name": {
            "description": "GPU product name.",
            "unit": "string",
            "internal": True,
        },
        "proc": {
            "description": "GPU processor consumption.",
            "unit": "percent",
            "watched": True,
            "watch_direction": "high",
            "prominent": True,
            "default_thresholds": _PERCENT_THRESHOLDS,
        },
        "mem": {
            "description": "GPU memory consumption.",
            "unit": "percent",
            "watched": True,
            "watch_direction": "high",
            "prominent": True,
            "default_thresholds": _PERCENT_THRESHOLDS,
        },
        "temperature": {
            "description": "GPU temperature.",
            "unit": "celsius",
            "watched": True,
            "watch_direction": "high",
            "prominent": False,
            "default_thresholds": _TEMP_THRESHOLDS,
        },
        "fan_speed": {
            "description": "GPU fan speed.",
            "unit": "percent",
            "internal": True,
            "watched": False,
        },
    }

    def __init__(self, store: Any, config: Any) -> None:
        super().__init__(store, config)
        self._backends = _build_backends()

    def _collect(self) -> list:
        out: list[dict[str, Any]] = []
        for backend in self._backends:
            try:
                cards = backend.get_device_stats()
            except Exception as exc:  # noqa: BLE001 — one bad GPU must not drop others
                logger.debug("gpu: %s collect failed: %s", type(backend).__name__, exc)
                continue
            if cards:
                out.extend(cards)
        return out

    async def _grab_stats(self) -> list:
        return await asyncio.to_thread(self._collect)

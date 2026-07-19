#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — NPU plugin (collection, per-card).

Migrated from `glances/plugins/npu/__init__.py`. Reuses the v4 hardware
card backends (`glances/plugins/npu/cards/{amd,intel,rockchip}.py`) as
pure collectors. Each card exposes an availability model
(`is_available()`, `get_device_stats()`, `disable()`); a card that
raises during collection is disabled for the rest of the run (v4 parity).

**Default-disabled**: v4 ships `[npu] disable=True`. This plugin mirrors
that via `DISABLED_BY_DEFAULT = True` — without an explicit
`[npu] disable=False` it is not even instantiated by
`main_v5.discover_plugins()`. The class stays discoverable, so it can be
enabled without code changes.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, ClassVar

from glances.plugins.plugin.base_v5 import GlancesPluginBase

logger = logging.getLogger(__name__)

_PERCENT_THRESHOLDS = {"careful": 50.0, "warning": 70.0, "critical": 90.0}


def _build_backends() -> list:
    backends: list = []
    from glances.plugins.npu.cards.amd import AmdNPU
    from glances.plugins.npu.cards.intel import IntelNPU
    from glances.plugins.npu.cards.rockchip import RockchipNPU

    for cls in (AmdNPU, IntelNPU, RockchipNPU):
        try:
            backends.append(cls())
        except Exception as exc:  # noqa: BLE001
            logger.debug("npu: %s init failed: %s", cls.__name__, exc)
    return backends


class PluginModel(GlancesPluginBase[list]):
    """Per-NPU plugin (collection)."""

    plugin_name: ClassVar[str] = "npu"
    IS_COLLECTION: ClassVar[bool] = True
    # Mirrors v4 `[npu] disable=True`: off unless the operator opts in.
    DISABLED_BY_DEFAULT: ClassVar[bool] = True

    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "npu_id": {
            "description": "NPU identifier (e.g. intel_1).",
            "unit": "string",
            "primary_key": True,
        },
        "name": {"description": "NPU product name.", "unit": "string", "internal": True},
        "load": {
            "description": "NPU load.",
            "unit": "percent",
            "watched": True,
            "watch_direction": "high",
            "prominent": True,
            "default_thresholds": _PERCENT_THRESHOLDS,
        },
        "freq": {
            "description": "NPU frequency (current/max).",
            "unit": "percent",
            "watched": True,
            "watch_direction": "high",
            "prominent": False,
            "default_thresholds": _PERCENT_THRESHOLDS,
        },
        "mem": {
            "description": "NPU memory consumption.",
            "unit": "percent",
            "watched": True,
            "watch_direction": "high",
            "prominent": False,
            "default_thresholds": _PERCENT_THRESHOLDS,
        },
        "freq_current": {"description": "NPU current frequency (Hz).", "unit": "hertz", "internal": True},
        "freq_max": {"description": "NPU maximum frequency (Hz).", "unit": "hertz", "internal": True},
        "temperature": {"description": "NPU temperature.", "unit": "celsius", "internal": True},
        "power": {"description": "NPU power draw.", "unit": "watt", "internal": True},
    }

    def __init__(self, store: Any, config: Any) -> None:
        super().__init__(store, config)
        self._backends = _build_backends()

    def _collect(self) -> list:
        out: list[dict[str, Any]] = []
        for backend in self._backends:
            if not backend.is_available():
                continue
            try:
                stats = backend.get_device_stats()
            except Exception as exc:  # noqa: BLE001 — disable the faulty card, keep others
                logger.debug("npu: %s collect failed, disabling: %s", type(backend).__name__, exc)
                backend.disable()
                continue
            if stats:
                out.append(stats)
        return out

    async def _grab_stats(self) -> list:
        return await asyncio.to_thread(self._collect)

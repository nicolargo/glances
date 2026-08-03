#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — AMPs plugin (collection, one item per configured AMP).

Port of `glances/plugins/amps/__init__.py` (v4). All the orchestration —
dynamic loading, per-AMP cadence, bounded execution — lives in
`glances/amps_list_v5.py`; this model only projects the AMP objects into the
store and computes the level of each AMP's process count.

`SCHEDULE_AT_GLOBAL_REFRESH = True`: every AMP owns its cadence through its
own `Timer`, so `[amps] refresh` would only throttle the PUBLICATION of
results the AMPs have already produced. Same reasoning as `ports`.

See docs/superpowers/specs/2026-08-02-glances-v5-g6c-amps-design.md.
"""

from __future__ import annotations

from typing import Any, ClassVar

from glances.amps_list_v5 import AmpsListV5
from glances.plugins.plugin.base_v5 import GlancesPluginBase


class PluginModel(GlancesPluginBase[list]):
    """Application Monitoring Processes (collection, primary key ``name``)."""

    plugin_name: ClassVar[str] = "amps"
    IS_COLLECTION: ClassVar[bool] = True
    # v4 calls its own `get_alert()`, not `get_alert_log()`: the level colours
    # the TUI cell and is never written to the event history nor dispatched to
    # an action. Same family as `ports` and `processlist`.
    EMITS_ALERTS: ClassVar[bool] = False
    # Each AMP fires on its own `[amp_<name>] refresh`; the plugin's job is to
    # publish what they produced, promptly. See the module docstring.
    SCHEDULE_AT_GLOBAL_REFRESH: ClassVar[bool] = True

    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        # `Amp.NAME`, not the config-section suffix: the default AMP
        # capitalises it (`[amp_dropbox]` -> `Dropbox`). v4 parity.
        "name": {"description": "AMP name.", "unit": "string", "primary_key": True},
        "result": {"description": "AMP result (a string, possibly multi-line).", "unit": "string"},
        "refresh": {"description": "AMP refresh interval.", "unit": "second"},
        "timer": {"description": "Time until next refresh.", "unit": "second"},
        "count": {"description": "Number of matching processes.", "unit": "number"},
        "countmin": {"description": "Minimum number of matching processes.", "unit": "number"},
        "countmax": {"description": "Maximum number of matching processes.", "unit": "number"},
        "regex": {"description": "True when a regex is configured for this AMP.", "unit": "bool"},
    }

    def __init__(self, store, config) -> None:
        super().__init__(store, config)
        self._amps_list = AmpsListV5(config)

    async def _grab_stats(self) -> list:
        amps = await self._amps_list.update()
        return [
            {
                "name": amp.NAME,
                "result": amp.result(),
                "refresh": amp.refresh(),
                "timer": amp.time_until_refresh(),
                "count": amp.count(),
                "countmin": amp.count_min(),
                "countmax": amp.count_max(),
                "regex": amp.regex() is not None,
            }
            for amp in amps
        ]

    # ------------------------------------------------------------- levels
    #
    # BESPOKE, on purpose: the level of `count` depends on two OTHER fields
    # (`countmin` / `countmax`), which neither the base's numeric ladder nor
    # its categorical mapping can express. Same precedent as `ports`;
    # `base_v5.py` is deliberately NOT modified.

    @staticmethod
    def _count_level(count: Any, count_min: Any, count_max: Any) -> str | None:
        """Transposition of v4 `AmpsPlugin.get_alert`.

        An unconfigured AMP defaults both bounds to the observed count, which
        is what makes it always `ok`.
        """
        if count is None:
            return None
        if count_min is None:
            count_min = count
        if count_max is None:
            count_max = count
        try:
            count = int(count)
            count_min = int(count_min)
            count_max = int(count_max)
        except (TypeError, ValueError):
            return None
        if count > 0:
            return "ok" if count_min <= count <= count_max else "warning"
        return "ok" if count_min == 0 else "critical"

    def _derived_parameters(self) -> None:
        """Compute `_levels` from the process count of each AMP.

        REPLACES the base implementation: `count` is the only field that ever
        gets a level. Adding a `watched: True` field to `fields_description`
        would therefore be silently ineffective — wire it in here as well.

        Shape: `{<Amp.NAME>: {"count": {"level": …, "prominent": False}}}`.
        `prominent = False`: v4 colours the AMP name text, never a background.
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
            level = self._count_level(item.get("count"), item.get("countmin"), item.get("countmax"))
            if level is None:
                continue
            self._levels[name] = {"count": {"level": level, "prominent": False}}

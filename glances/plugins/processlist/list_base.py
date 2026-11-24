#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Shared base for the ``processlist`` and ``programlist`` plugin models."""

# Both plugins read the list the process engine already built this cycle and
# share the `[processlist]` config section: the export filter (issue #794),
# `disable_virtual_memory` and the core count published for Irix mode. Only
# the engine call differs (per process or per program).

from __future__ import annotations

import logging
import re
from typing import Any

import psutil

from glances.config import GlancesConfig
from glances.plugins.plugin.base import GlancesPluginBase
from glances.stats_store import StatsStore

logger = logging.getLogger(__name__)

# The Irix-mode divisor (v4 `nb_log_core`). Read once: the core count of a
# running host does not change under Glances.
_LOGICAL_CORES: int = psutil.cpu_count(logical=True) or 1


class ProcessListModelBase(GlancesPluginBase[list]):
    """Collection plugin over the process engine's current list."""

    def __init__(self, store: StatsStore, config: GlancesConfig) -> None:
        """Read the `[processlist]` options shared by both views."""
        super().__init__(store, config)
        # v4 parity (issue #794): by default NOTHING is exported — a process
        # list can carry hundreds of columns and blow up flat-schema
        # exporters (CSV/InfluxDB). Only items matching an operator-set
        # filter are exported. Both views use the `[processlist] export` key,
        # as v4 has one filter for the per-process and per-program views.
        self._export_patterns: list[re.Pattern[str]] = self._compile_filter("export", section="processlist")
        # Read once: both views use the `[processlist]` section.
        self._disable_virtual_memory: bool = bool(self.config.get("processlist", "disable_virtual_memory", False))

    def _add_metadata(self) -> None:
        super()._add_metadata()
        self._metadata["cpucore"] = _LOGICAL_CORES
        self._metadata["disable_virtual_memory"] = self._disable_virtual_memory

    def get_export(self) -> list[dict[str, Any]]:
        """
        Filtered export view (v4 parity, issue #794).

        Empty (no columns at all) unless `[processlist] export` (or
        `--export-process-filter`) is configured, in which case only items
        whose `name` or `cmdline` matches one of the patterns are exported.
        Never affects `get_stats()` / the REST API / the TUI.
        """
        if not self._export_patterns:
            return []
        return [item for item in super().get_export() if self._matches_export(item)]  # type: ignore[return-value]

    def _matches_export(self, item: dict[str, Any]) -> bool:
        name = str(item.get("name", ""))
        cmdline = item.get("cmdline")
        cmdline_str = " ".join(cmdline) if isinstance(cmdline, list) else str(cmdline or "")
        return any(p.search(name) or p.search(cmdline_str) for p in self._export_patterns)

    def _get_engine_list(self) -> Any:
        """The engine's current list for this view."""
        raise NotImplementedError

    async def _grab_stats(self) -> list:
        try:
            raw = self._get_engine_list()
        except Exception as exc:  # noqa: BLE001 — engine is third-party-ish, guard widely
            logger.debug("%s: engine list failed: %s", self.plugin_name, exc)
            return []
        if not isinstance(raw, list):
            return []
        # The engine returns the live list (and its dicts); copy each entry
        # so downstream consumers cannot mutate the engine's internal state.
        return [dict(p) for p in raw if isinstance(p, dict)]

#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — VMs plugin (collection, per-VM).

Migrated from `glances/plugins/vms/__init__.py`. Reuses the v4 engines
(`glances/plugins/vms/engines/{multipass,virsh}.py`) VERBATIM as
synchronous CLI collectors; ``_grab_stats`` wraps the blocking CLI work
in ``asyncio.to_thread``. Both engines are constructed unconditionally
(v4 parity) — each self-guards on its ``import_*_error_tag`` inside
``update()``, returning ``('', [])`` when its binary is absent.

**Default-disabled**: v4 ships `[vms] disable=True`. This plugin mirrors
that — with no explicit `[vms] disable=False` in the user config it
collects and publishes nothing. The plugin is still discovered so it can
be enabled without code changes.

No alerts: ``EMITS_ALERTS = False`` — no field is declared ``watched``.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, ClassVar

from glances.plugins.plugin.base_v5 import GlancesPluginBase
from glances.plugins.vms.engines import VmsExtension
from glances.plugins.vms.engines.multipass import VmExtension as MultipassVmExtension
from glances.plugins.vms.engines.virsh import VmExtension as VirshVmExtension
from glances.processes import glances_processes
from glances.processes import sort_stats as sort_stats_processes

logger = logging.getLogger(__name__)

_DEFAULT_MAX_NAME_SIZE = 20


def sort_vm_stats(stats: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    """Port of v4 `glances/plugins/vms/__init__.py::sort_vm_stats`.

    Makes VM sort follow the process sort (processlist-aligned). ``glances_processes
    .sort_key`` is read fresh every call — the dynamic ``auto`` resolution
    (cpu/mem depending on load) is preserved, never hardcoded.

    DELIBERATE v4 divergence: v4's `sort_vm_stats` calls `sort_stats_processes`
    WITHOUT capturing its return value. Since `sort_stats` returns a NEW sorted
    list (it does not mutate in place — see glances/processes.py:816), v4's VM
    sort is a silent no-op. We capture the return so the sort actually applies,
    matching `containers` (`sort_docker_stats`, which does capture) and the
    maintainer's processlist-alignment requirement.
    """
    if glances_processes.sort_key == "memory_percent":
        sort_by, sort_by_secondary = "memory_usage", "cpu_time"
    elif glances_processes.sort_key == "name":
        sort_by, sort_by_secondary = "name", "cpu_time"
    else:
        sort_by, sort_by_secondary = "cpu_time", "memory_usage"
    stats = sort_stats_processes(
        stats,
        sorted_by=sort_by,
        sorted_by_secondary=sort_by_secondary,
        reverse=glances_processes.sort_key != "name",
    )
    return sort_by, stats


class PluginModel(GlancesPluginBase[list]):
    """Per-VM plugin (collection)."""

    plugin_name: ClassVar[str] = "vms"
    IS_COLLECTION: ClassVar[bool] = True
    EMITS_ALERTS: ClassVar[bool] = False

    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "name": {"description": "VM name.", "unit": "string", "primary_key": True},
        "id": {"description": "VM ID.", "unit": "string"},
        "release": {"description": "VM release.", "unit": "string"},
        "status": {"description": "VM status.", "unit": "string"},
        "cpu_count": {"description": "VM CPU count.", "unit": "number"},
        "cpu_time": {"description": "VM CPU time (per-second rate).", "unit": "percent", "rate": True},
        "memory_usage": {"description": "VM memory usage.", "unit": "byte"},
        "memory_total": {"description": "VM memory total.", "unit": "byte"},
        "load_1min": {"description": "VM load, last 1 min (None if unsupported by the engine).", "unit": "float"},
        "load_5min": {"description": "VM load, last 5 min (None if unsupported by the engine).", "unit": "float"},
        "load_15min": {"description": "VM load, last 15 min (None if unsupported by the engine).", "unit": "float"},
        "ipv4": {"description": "VM IPv4 address.", "unit": "string"},
        "engine": {"description": "VM engine name.", "unit": "string"},
        "engine_version": {"description": "VM engine version.", "unit": "string"},
    }

    def __init__(self, store: Any, config: Any) -> None:
        super().__init__(store, config)
        # Mirror v4: build both engines unconditionally; each self-guards on
        # its import_*_error_tag inside update() (returns ('', []) when the
        # binary is absent). No construction gating — matches v4 __init__.
        self.watchers: dict[str, VmsExtension] = {
            "multipass": MultipassVmExtension(),
            "virsh": VirshVmExtension(),
        }
        self._max_name_size = int(self.config.get("vms", "max_name_size", _DEFAULT_MAX_NAME_SIZE))

    def _is_enabled(self) -> bool:
        # Mirror v4 [vms] disable=True default (see npu/model_v5.py).
        raw = self.config.get("vms", "disable", "True")
        return str(raw).strip().lower() in ("false", "0", "no")

    def _all_tag(self) -> bool:
        raw = self.config.get("vms", "all", "False")
        return str(raw).strip().lower() in ("true", "1", "yes")

    def _collect(self) -> list:
        stats: list[dict[str, Any]] = []
        all_tag = self._all_tag()
        for engine, watcher in self.watchers.items():
            try:
                version, vms = watcher.update(all_tag=all_tag)
            except Exception as exc:  # noqa: BLE001 — one bad engine must not kill the others
                logger.debug("vms: engine %s update failed: %s", engine, exc)
                continue
            for vm in vms:
                vm["engine"] = engine
                vm["engine_version"] = version
            stats.extend(vms)
        # Pre-sort the list to follow the dynamic process sort key (v4
        # parity). The returned key is not exposed — the renderer underlines
        # from the global view["sort_key"], processlist-aligned.
        _, stats = sort_vm_stats(stats)
        return stats

    async def _grab_stats(self) -> list:
        if not self._is_enabled():
            return []
        return await asyncio.to_thread(self._collect)

    def _add_metadata(self) -> None:
        super()._add_metadata()
        self._metadata["max_name_size"] = self._max_name_size

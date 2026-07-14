#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — Containers plugin (collection, per-container).

Port of ``glances/plugins/containers/__init__.py`` (v4). Reuses the v4
Docker/Podman/LXD engine machinery VERBATIM (streaming threads +
ThreadPoolExecutor); ``_grab_stats`` only wraps the v4 flatten/merge/sort
pipeline in ``asyncio.to_thread``. CPU/IO/net rates stay computed inside the
engines' ``StatsFetcher`` classes. See design doc
docs/superpowers/specs/2026-07-14-glances-v5-g6a-design.md.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, ClassVar

from glances.plugins.containers.engines import ContainersExtension
from glances.plugins.containers.engines.docker import DockerExtension, disable_plugin_docker
from glances.plugins.containers.engines.lxd import LxdExtension, disable_plugin_lxd
from glances.plugins.containers.engines.podman import PodmanExtension, disable_plugin_podman
from glances.plugins.plugin.base_v5 import GlancesPluginBase
from glances.processes import glances_processes
from glances.processes import sort_stats as sort_stats_processes

logger = logging.getLogger(__name__)

_DEFAULT_PODMAN_SOCK = "unix:///run/user/1000/podman/podman.sock"


class PluginModel(GlancesPluginBase[list]):
    """Per-container plugin (collection)."""

    plugin_name: ClassVar[str] = "containers"
    IS_COLLECTION: ClassVar[bool] = True
    EMITS_ALERTS: ClassVar[bool] = True

    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "name": {"description": "Container name.", "unit": "string", "primary_key": True},
        "id": {"description": "Container ID.", "unit": "string"},
        "image": {"description": "Container image.", "unit": "string"},
        "status": {"description": "Container status.", "unit": "string"},
        "created": {"description": "Container creation date.", "unit": "string"},
        "command": {"description": "Container command.", "unit": "string"},
        "cpu_percent": {
            "description": "Container CPU consumption.",
            "unit": "percent",
            "watched": True,
            "watch_direction": "high",
            "prominent": False,
            "threshold_field": "cpu",
        },
        "cpu_limit": {"description": "Container CPU limit.", "unit": "number"},
        "memory_usage": {
            "description": "Container memory usage (v4 export value: usage − cache when present). Feeds export/REST.",
            "unit": "byte",
        },
        "memory_usage_no_cache": {
            "description": "Container memory usage minus inactive_file. TUI display value.",
            "unit": "byte",
        },
        "memory_inactive_file": {"description": "Container memory inactive file.", "unit": "byte"},
        "memory_limit": {"description": "Container memory limit.", "unit": "byte"},
        "memory_percent": {
            "description": "Container memory usage as a percentage of its limit.",
            "unit": "percent",
            "watched": True,
            "watch_direction": "high",
            "prominent": False,
            "threshold_field": "mem",
        },
        "io_rx": {"description": "Container IO bytes read rate.", "unit": "bytepersecond"},
        "io_wx": {"description": "Container IO bytes write rate.", "unit": "bytepersecond"},
        "network_rx": {"description": "Container network RX bitrate.", "unit": "bitpersecond"},
        "network_tx": {"description": "Container network TX bitrate.", "unit": "bitpersecond"},
        "ports": {"description": "Container ports.", "unit": "string"},
        "uptime": {"description": "Container uptime.", "unit": "string"},
        "engine": {"description": "Container engine (Docker, Podman, LXD).", "unit": "string"},
        "pod_name": {"description": "Pod name (Podman only).", "unit": "string"},
        "pod_id": {"description": "Pod ID (Podman only).", "unit": "string"},
    }

    def __init__(self, store, config) -> None:
        super().__init__(store, config)

        # Reuse the v4 engines verbatim (Option A). Each construction is
        # guarded so a broken engine leaves the others (and an empty plugin)
        # valid.
        self.watchers: dict[str, ContainersExtension] = {}
        if not disable_plugin_docker:
            self._try_add_watcher("docker", lambda: DockerExtension())
        if not disable_plugin_podman:
            self._try_add_watcher("podman", lambda: PodmanExtension(podman_sock=self._podman_sock()))
        if not disable_plugin_lxd:
            self._try_add_watcher("lxd", lambda: LxdExtension(poll_interval=self._poll_interval()))

        # Static config surfaced to the renderer via metadata each cycle.
        raw_disable = self.config.get(self.plugin_name, "disable_stats", "")
        self._disable_stats: list[str] = (
            [s.strip() for s in raw_disable.split(",") if s.strip()]
            if isinstance(raw_disable, str)
            else list(raw_disable or [])
        )
        try:
            self._max_name_size = int(self.config.get(self.plugin_name, "max_name_size", 20))
        except (TypeError, ValueError):
            self._max_name_size = 20

    def _try_add_watcher(self, engine: str, factory) -> None:
        try:
            self.watchers[engine] = factory()
        except Exception as e:
            logger.warning("containers: engine %s unavailable (%s) — skipped", engine, e)

    def _podman_sock(self) -> str:
        sock = self.config.get(self.plugin_name, "podman_sock", "")
        if isinstance(sock, (list, tuple)):
            sock = sock[0] if sock else ""
        return str(sock) if sock else _DEFAULT_PODMAN_SOCK

    def _poll_interval(self) -> float:
        val = self.config.get(self.plugin_name, "refresh", -1.0)
        try:
            val = float(val)
        except (TypeError, ValueError):
            val = -1.0
        return val if val > 0 else 2.0

    def _all_tag(self) -> bool:
        val = self.config.get(self.plugin_name, "all", False)
        return str(val).lower() == "true"

    def _update_watchers(self) -> list:
        """v4 flatten/merge/inject-engine/reconcile-memory/sort pipeline.

        Blocking (reads engine snapshots); always called via to_thread.
        show/hide filtering is left to the base ``_filter_collection`` on the
        ``name`` primary key — not re-implemented here.
        """
        all_tag = self._all_tag()
        items: list[dict[str, Any]] = []
        for engine, watcher in self.watchers.items():
            try:
                _version, containers = watcher.update(all_tag=all_tag)
            except Exception as e:
                logger.warning("containers: engine %s update failed: %s", engine, e)
                continue
            for c in containers:
                c["engine"] = engine
                self._reconcile_memory(c)
                items.append(c)
        return self._sort(items)

    @staticmethod
    def _reconcile_memory(container: dict[str, Any]) -> None:
        """Compute the three memory surfaces from the engine's nested
        ``memory`` dict (design §6.1, three-surface decision):

        - ``memory_usage``          — LEFT UNTOUCHED (v4 export value set by
          the engine's ``generate_stats``). Feeds export / REST.
        - ``memory_usage_no_cache`` — ``usage − inactive_file``. Feeds the
          TUI MEM column (display).
        - ``memory_percent``        — ``memory_usage_no_cache / limit * 100``.
          Feeds alerting (thresholds, ``threshold_field="mem"``).
        """
        mem = container.get("memory") or {}
        if "usage" not in mem:
            return
        usage_no_cache = mem["usage"] - mem.get("inactive_file", 0)
        container["memory_usage_no_cache"] = usage_no_cache
        container["memory_inactive_file"] = mem.get("inactive_file")
        limit = mem.get("limit")
        container["memory_percent"] = (usage_no_cache / limit * 100.0) if limit else None

    @staticmethod
    def _sort(stats: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Faithful reimplementation of v4 ``sort_docker_stats`` — sort by the
        process engine's active sort key so containers track the process sort.

        ``glances_processes.sort_key`` is read fresh every cycle (dynamic
        default preserved: ``auto`` resolves to cpu/mem per load before the
        getter returns — never hardcode a static key). The map resolves the
        dynamically-selected key to a container column; the fallback tuple is
        only the column mapping for genuinely unmapped keys, not a static
        sort key."""
        sort_by, sort_by_secondary = {
            "memory_percent": ("memory_usage", "cpu_percent"),
            "name": ("name", "cpu_percent"),
        }.get(glances_processes.sort_key, ("cpu_percent", "memory_usage"))
        try:
            return sort_stats_processes(
                stats,
                sorted_by=sort_by,
                sorted_by_secondary=sort_by_secondary,
                reverse=glances_processes.sort_key != "name",
            )
        except Exception as e:
            logger.debug("containers: sort failed: %s", e)
            return stats

    async def _grab_stats(self) -> list:
        if not self.watchers:
            return []
        try:
            return await asyncio.to_thread(self._update_watchers)
        except Exception as e:
            logger.warning("containers: grab failed: %s", e)
            return []

    def _add_metadata(self) -> None:
        super()._add_metadata()
        # Static [containers] config the renderer needs (it has no config access).
        self._metadata["disable_stats"] = self._disable_stats
        self._metadata["max_name_size"] = self._max_name_size

    def stop(self) -> None:
        for engine, watcher in self.watchers.items():
            try:
                watcher.stop()
            except Exception as e:
                logger.warning("containers: stop(%s) failed: %s", engine, e)

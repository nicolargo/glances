#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 asyncio scheduler.

Architecture references:
- §1.2  Async plugin update loop
- §1.3  StatsStore (consumer)
- §3.1  GlancesPluginBase (consumer)

The scheduler is the first component in v5 that actively *consumes*
`GlancesPluginBase`. It owns one `asyncio.Task` per registered plugin and
runs each plugin's `update()` at its configured `refresh_time`. A failure
in any single plugin must never crash the gather loop — `update()` already
swallows exceptions, this scheduler adds a second safety net.

Concrete plugin auto-discovery is **not** wired here — Phase 0.6 only
exposes manual `register()`. Auto-discovery lands when concrete plugins do
(Phase 1+).
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from glances.alerts_v5 import GlancesAlerts
    from glances.config_v5 import GlancesConfigV5
    from glances.plugins.plugin.base_v5 import GlancesPluginBase
    from glances.stats_store_v5 import StatsStoreV5

logger = logging.getLogger(__name__)

# Hard-coded fallback used only if `[global] refresh_time` is absent from
# the config. Matches the v4 default.
_DEFAULT_REFRESH_TIME = 2.0


class AsyncScheduler:
    """Run registered plugins concurrently via `asyncio.gather`.

    Lifecycle:
        scheduler = AsyncScheduler(store, config)
        scheduler.register(plugin_a)
        scheduler.register(plugin_b, refresh_time=5.0)
        await scheduler.run_forever()         # blocks until cancelled
        # in another coroutine: await scheduler.stop()
    """

    def __init__(
        self,
        store: StatsStoreV5,
        config: GlancesConfigV5,
        alerts: GlancesAlerts | None = None,
    ) -> None:
        self.store = store
        self.config = config
        # Optional alerts hook — when set, the scheduler calls
        # `alerts.ingest_plugin(plugin)` after each plugin update so the
        # alert state machine sees every `_levels` payload. Absent → no
        # alerts ingestion (back-compatible with the Phase 0.6 contract).
        self.alerts = alerts

        self._entries: list[_PluginEntry] = []
        self._tasks: list[asyncio.Task[None]] = []
        self._running: bool = False

    # ------------------------------------------------------------ register

    def register(
        self,
        plugin: GlancesPluginBase,
        refresh_time: float | None = None,
    ) -> None:
        """Register `plugin` with its refresh interval.

        Precedence for `refresh_time`:
        1. Explicit `refresh_time=` argument
        2. `[<plugin_name>] refresh` (v4 key) or `refresh_time` (alias)
        3. `[global] refresh` (v4 key) or `refresh_time` (alias)
        4. `_DEFAULT_REFRESH_TIME` (2.0s)
        """
        if self._running:
            raise RuntimeError("Cannot register a plugin while the scheduler is running")

        if any(entry.plugin is plugin for entry in self._entries):
            raise ValueError(f"Plugin {plugin.plugin_name!r} is already registered")

        rt = self._resolve_refresh_time(plugin.plugin_name, refresh_time)
        if rt <= 0:
            raise ValueError(f"refresh_time for {plugin.plugin_name!r} must be > 0, got {rt}")

        self._entries.append(_PluginEntry(plugin=plugin, refresh_time=rt))

    def _resolve_refresh_time(self, plugin_name: str, explicit: float | None) -> float:
        if explicit is not None:
            return float(explicit)
        # Per-plugin section then global, each honouring the documented v4
        # key `refresh` first and the `refresh_time` alias second. A
        # sentinel of -1.0 (unset) falls through to the next source rather
        # than latching. Historically the scheduler read only `refresh_time`,
        # so every shipped `[<plugin>] refresh=N` (e.g. `[sensors] refresh=10`)
        # was silently ignored and expensive plugins polled at the global
        # rate — a real CPU regression. See config's `refresh` docs.
        per_plugin = self._config_refresh(plugin_name)
        if per_plugin > 0:
            return per_plugin
        glob = self._config_refresh("global")
        if glob > 0:
            return glob
        return _DEFAULT_REFRESH_TIME

    def _config_refresh(self, section: str) -> float:
        """Return the refresh interval from `[section] refresh|refresh_time`, else -1.0."""
        for key in ("refresh", "refresh_time"):
            raw = self.config.get(section, key, -1.0)
            try:
                value = float(raw)
            except (TypeError, ValueError):
                continue
            if value > 0:
                return value
        return -1.0

    # ------------------------------------------------------------ run/stop

    async def run_forever(self) -> None:
        """Start one task per registered plugin and block until cancelled.

        Returns cleanly when `stop()` is called from another coroutine.
        Raises only on programmer error (e.g. running with zero plugins
        registered).
        """
        if self._running:
            raise RuntimeError("Scheduler is already running")
        if not self._entries:
            raise RuntimeError("Cannot run scheduler with no registered plugins")

        self._running = True
        self._tasks = [asyncio.create_task(self._plugin_loop(entry)) for entry in self._entries]
        try:
            # return_exceptions=True so a single task raising does not
            # propagate out of gather and tear the rest down.
            await asyncio.gather(*self._tasks, return_exceptions=True)
        finally:
            self._running = False
            self._tasks = []

    async def stop(self) -> None:
        """Cancel every plugin loop, then let each plugin release resources."""
        for task in self._tasks:
            task.cancel()
        # Drain cancellations. `return_exceptions=True` swallows the
        # `CancelledError` we just raised on each task.
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        # Teardown hook: let each plugin release long-lived resources
        # (e.g. containers' engine streaming threads). Run in a thread so a
        # blocking join cannot stall the event loop, and guard each so one
        # failing teardown cannot block the others.
        for entry in self._entries:
            try:
                await asyncio.to_thread(entry.plugin.stop)
            except Exception as e:
                logger.warning("Scheduler: stop() of %s failed: %s", entry.plugin.plugin_name, e)

    # ------------------------------------------------------------ internals

    async def _plugin_loop(self, entry: _PluginEntry) -> None:
        """Per-plugin loop: `update()` → optional alerts ingest → `sleep`, forever."""
        plugin_name = entry.plugin.plugin_name
        while True:
            try:
                await entry.plugin.update()
            except Exception as e:
                # Defensive: GlancesPluginBase.update() already swallows.
                # This catches anything a future plugin override might leak.
                logger.warning("Scheduler caught exception from %s: %s", plugin_name, e)
            if self.alerts is not None:
                try:
                    await self.alerts.ingest_plugin(entry.plugin)
                except Exception as e:
                    # Defensive: alerts must never tear down the loop either.
                    logger.warning("Alerts ingest failed for %s: %s", plugin_name, e)
            await asyncio.sleep(entry.refresh_time)


class _PluginEntry:
    """Internal record holding a plugin and its resolved refresh interval."""

    __slots__ = ("plugin", "refresh_time")

    def __init__(self, plugin: GlancesPluginBase, refresh_time: float) -> None:
        self.plugin = plugin
        self.refresh_time = refresh_time

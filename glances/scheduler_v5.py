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

    def __init__(self, store: StatsStoreV5, config: GlancesConfigV5) -> None:
        self.store = store
        self.config = config

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
        2. `[<plugin_name>] refresh_time` from config
        3. `[global] refresh_time` from config
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
        # Per-plugin section: `[<plugin_name>] refresh_time`. We pass a
        # sentinel default of -1.0 so an unset value falls through to the
        # global section instead of latching the float fallback.
        per_plugin = self.config.get(plugin_name, "refresh_time", -1.0)
        if per_plugin > 0:
            return float(per_plugin)
        return float(self.config.get("global", "refresh_time", _DEFAULT_REFRESH_TIME))

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
        """Cancel every plugin loop and wait for clean termination."""
        for task in self._tasks:
            task.cancel()
        # Drain cancellations. `return_exceptions=True` swallows the
        # `CancelledError` we just raised on each task.
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

    # ------------------------------------------------------------ internals

    async def _plugin_loop(self, entry: _PluginEntry) -> None:
        """Per-plugin loop: `update()` then `sleep(refresh_time)`, forever."""
        plugin_name = entry.plugin.plugin_name
        while True:
            try:
                await entry.plugin.update()
            except Exception as e:
                # Defensive: GlancesPluginBase.update() already swallows.
                # This catches anything a future plugin override might leak.
                logger.warning("Scheduler caught exception from %s: %s", plugin_name, e)
            await asyncio.sleep(entry.refresh_time)


class _PluginEntry:
    """Internal record holding a plugin and its resolved refresh interval."""

    __slots__ = ("plugin", "refresh_time")

    def __init__(self, plugin: GlancesPluginBase, refresh_time: float) -> None:
        self.plugin = plugin
        self.refresh_time = refresh_time

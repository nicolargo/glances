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
    from glances.exports.export_base_v5 import GlancesExportBase
    from glances.plugins.plugin.base_v5 import GlancesPluginBase
    from glances.stats_store_v5 import StatsStoreV5

logger = logging.getLogger(__name__)

# Hard-coded fallback used only if `[global] refresh_time` is absent from
# the config. Matches the v4 default. A copy of this constant also lives in
# glances.exports.export_base_v5 — kept as a separate copy on purpose, not
# for import cost (main_v5.py now imports glances.exports and
# glances.exports.export_base_v5 unconditionally in every mode, ~0.5ms
# total, so that's no longer a reason not to import here). The real reason:
# layering. This scheduler is core/lower-level and the export subsystem
# already depends on IT (`resolve_export_refresh()` takes the scheduler's
# resolved global refresh as a parameter) — a module-top import the other
# way, just to fetch a literal `2.0`, would add a static dependency in the
# wrong direction for no benefit. `_export_refresh_time()` below still does
# a local, function-scoped import of `resolve_export_refresh` itself,
# because that one is an actual cross-module call, not a bare constant.
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
        self._exporters: list[GlancesExportBase] = []

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
        3. `plugin.DEFAULT_REFRESH_TIME` (the plugin's own intended cadence)
        4. `[global] refresh` (v4 key) or `refresh_time` (alias)
        5. `_DEFAULT_REFRESH_TIME` (2.0s)
        """
        if self._running:
            raise RuntimeError("Cannot register a plugin while the scheduler is running")

        if any(entry.plugin is plugin for entry in self._entries):
            raise ValueError(f"Plugin {plugin.plugin_name!r} is already registered")

        if refresh_time is None and plugin.SCHEDULE_AT_GLOBAL_REFRESH:
            # This plugin's `[<plugin>] refresh` throttles its own background
            # source poll, NOT its publication cadence (e.g. `ports`, whose
            # ThreadScanner fills the scan list asynchronously). It must be
            # published at the fast global cadence so the TUI reflects the
            # scan's progress promptly. See GlancesPluginBase.SCHEDULE_AT_GLOBAL_REFRESH.
            rt = self._global_refresh_time()
        else:
            # getattr: test rigs register duck-typed fakes that do not derive
            # from GlancesPluginBase (mirrors alerts_v5's EMITS_ALERTS read).
            rt = self._resolve_refresh_time(
                plugin.plugin_name,
                refresh_time,
                getattr(plugin, "DEFAULT_REFRESH_TIME", None),
            )
        if rt <= 0:
            raise ValueError(f"refresh_time for {plugin.plugin_name!r} must be > 0, got {rt}")

        self._entries.append(_PluginEntry(plugin=plugin, refresh_time=rt))

    def register_exporter(self, exporter: GlancesExportBase) -> None:
        """Register an export module. Its loop starts with `run_forever()`.

        Unlike plugins, exporters share ONE loop and ONE cadence
        (`[export] refresh`): a backend write is a batch operation, and
        staggering it per plugin would multiply round-trips for no gain.
        """
        if self._running:
            raise RuntimeError("Cannot register an exporter while the scheduler is running")
        self._exporters.append(exporter)

    def _resolve_refresh_time(
        self,
        plugin_name: str,
        explicit: float | None,
        plugin_default: float | None = None,
    ) -> float:
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
        # The plugin's own intended cadence, ahead of the global fallback.
        # Keeps an expensive plugin (sensors: 145ms/cycle) off the 2s global
        # rate for a user whose config has no `[<plugin>] refresh` key,
        # without a central list of per-plugin values to maintain.
        # See GlancesPluginBase.DEFAULT_REFRESH_TIME.
        if plugin_default is not None and plugin_default > 0:
            return float(plugin_default)
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

    def _global_refresh_time(self) -> float:
        """Resolve `[global] refresh|refresh_time`, falling back to the default.

        Reuses `_config_refresh` so this is the same source of truth used at
        registration time — no second place defines the global cadence.
        """
        glob = self._config_refresh("global")
        return glob if glob > 0 else _DEFAULT_REFRESH_TIME

    def _export_refresh_time(self) -> float:
        """Cadence of the export loop. Delegates to the export layer so the
        exporters and the loop never read `[export] refresh` differently."""
        from glances.exports.export_base_v5 import resolve_export_refresh

        return resolve_export_refresh(self.config, self._global_refresh_time())

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
        if self._exporters:
            self._tasks.append(asyncio.create_task(self._export_loop()))
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
        for exporter in self._exporters:
            try:
                await asyncio.to_thread(exporter.exit)
            except Exception as e:
                logger.warning(
                    "Scheduler: exit() of export %s failed: %s",
                    exporter.export_name or type(exporter).__name__,
                    e,
                )

    # ------------------------------------------------------------ internals

    async def _plugin_loop(self, entry: _PluginEntry) -> None:
        """Per-plugin loop: `update()` → optional alerts ingest → `sleep`, forever.

        The *first* sleep of each loop uses `min(global_refresh,
        entry.refresh_time)` instead of `entry.refresh_time`; every
        subsequent sleep uses the plugin's own `refresh_time` as before.
        Symptom this fixes: plugins that launch a background scan from
        `update()` (e.g. `ports`) publish a placeholder payload on their
        first call (every status still `None`, "Scanning"...) and only fill
        in real values on the *next* call. With a long per-plugin `refresh`
        (`[ports] refresh=30`, `60`...) that next call — and the first
        useful publication — was delayed by the whole interval, so the UI
        showed nothing for up to a minute. v4 avoided this by
        continuously re-publishing from a single global loop. Using the
        global cadence for just the first sleep gets real values on screen
        within a couple of seconds again, while `min(...)` guarantees a
        plugin configured *faster* than the global refresh is never slowed
        down by this.
        """
        plugin_name = entry.plugin.plugin_name
        first_cycle = True
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
            if first_cycle:
                sleep_time = min(self._global_refresh_time(), entry.refresh_time)
                first_cycle = False
            else:
                sleep_time = entry.refresh_time
            await asyncio.sleep(sleep_time)

    async def _export_loop(self) -> None:
        """Single loop driving every registered exporter, forever.

        One `to_thread` handoff per exporter per tick — never per plugin.
        Every exporter here is blocking (file IO, HTTP clients), and a
        handoff costs ~307 µs, so 34 plugins × N exporters per tick would
        dominate the cycle.

        An exporter that raises is logged and kept: a backend that is
        momentarily down must not cost the operator their other exports,
        nor silently stop exporting once it comes back.

        The export interval is resolved ONCE, here, before the loop starts
        — not on every tick. `_export_refresh_time()` reaches
        `resolve_export_refresh()`, which logs a WARNING whenever
        `[export] refresh` is clamped up to the global refresh; resolving
        it every tick would repeat that warning on every export cycle
        (e.g. ~43000 times a day at `[export] refresh=1` / `[global]
        refresh=2`). Mirrors `_plugin_loop()`, which resolves its interval
        once at `register()` rather than on every iteration.
        """
        sleep_time = self._export_refresh_time()
        while True:
            plugins = [entry.plugin for entry in self._entries]
            for exporter in self._exporters:
                try:
                    await asyncio.to_thread(exporter.update, plugins)
                except Exception as e:
                    logger.warning("Export %s failed: %s", exporter.export_name or type(exporter).__name__, e)
            await asyncio.sleep(sleep_time)


class _PluginEntry:
    """Internal record holding a plugin and its resolved refresh interval."""

    __slots__ = ("plugin", "refresh_time")

    def __init__(self, plugin: GlancesPluginBase, refresh_time: float) -> None:
        self.plugin = plugin
        self.refresh_time = refresh_time

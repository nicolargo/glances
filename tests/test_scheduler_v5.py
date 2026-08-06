#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — unit + smoke tests for AsyncScheduler.

Test stack: pytest + pytest-asyncio (auto mode). See architecture decisions §9.

Coverage:
- refresh_time precedence (explicit > plugin section > global > default)
- run_forever calls plugin.update() at least once per plugin
- stop() cancels loops cleanly
- A plugin raising in its loop does NOT kill the others
- register() rejects duplicate plugin and rejects calls during run
- Smoke: 2 plugins → both end up in the StatsStore
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import pytest

from glances.config_v5 import GlancesConfigV5
from glances.plugins.plugin.base_v5 import GlancesPluginBase
from glances.scheduler_v5 import _DEFAULT_REFRESH_TIME, AsyncScheduler
from glances.stats_store_v5 import StatsStoreV5

# ---------------------------------------------------------- fake plugins


class FastPlugin(GlancesPluginBase[dict]):
    plugin_name = "fast"
    IS_COLLECTION = False
    fields_description = {"value": {"description": "v", "unit": "number"}}

    def __init__(self, store, config):
        super().__init__(store, config)
        self.calls = 0

    async def _grab_stats(self) -> dict:
        self.calls += 1
        return {"value": self.calls}


class SlowPlugin(GlancesPluginBase[dict]):
    plugin_name = "slow"
    IS_COLLECTION = False
    fields_description = {"value": {"description": "v", "unit": "number"}}

    def __init__(self, store, config):
        super().__init__(store, config)
        self.calls = 0

    async def _grab_stats(self) -> dict:
        self.calls += 1
        return {"value": self.calls * 10}


# A plugin whose update() bypasses the base-class swallow and re-raises,
# to exercise the scheduler's defensive try/except.
class RaisingPlugin(GlancesPluginBase[dict]):
    plugin_name = "raising"
    IS_COLLECTION = False
    fields_description = {"value": {"description": "v", "unit": "number"}}

    def __init__(self, store, config):
        super().__init__(store, config)
        self.calls = 0

    async def _grab_stats(self) -> dict:
        return {"value": 0}

    async def update(self) -> None:  # type: ignore[override]
        self.calls += 1
        raise RuntimeError("boom from update override")


# ---------------------------------------------------------- fixtures


@pytest.fixture
def store() -> StatsStoreV5:
    return StatsStoreV5()


@pytest.fixture
def config(tmp_path: Path, monkeypatch) -> GlancesConfigV5:
    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    return GlancesConfigV5()


def _config_with_ini(tmp_path: Path, monkeypatch, ini_body: str) -> GlancesConfigV5:
    """Helper: build a config with the given INI content as the user file."""
    user_dir = tmp_path / "xdg" / "glances"
    user_dir.mkdir(parents=True)
    (user_dir / "glances.conf").write_text(ini_body)
    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    return GlancesConfigV5()


# ---------------------------------------------------------- refresh_time


def test_register_uses_explicit_refresh_time(store, config):
    scheduler = AsyncScheduler(store, config)
    plugin = FastPlugin(store, config)

    scheduler.register(plugin, refresh_time=7.5)

    assert scheduler._entries[0].refresh_time == 7.5


def test_register_uses_plugin_section_refresh_time(store, tmp_path, monkeypatch):
    config = _config_with_ini(
        tmp_path,
        monkeypatch,
        "[fast]\nrefresh_time = 4.5\n",
    )
    scheduler = AsyncScheduler(store, config)
    plugin = FastPlugin(store, config)

    scheduler.register(plugin)

    assert scheduler._entries[0].refresh_time == 4.5


def test_register_falls_back_to_global(store, tmp_path, monkeypatch):
    config = _config_with_ini(
        tmp_path,
        monkeypatch,
        "[global]\nrefresh_time = 6.0\n",
    )
    scheduler = AsyncScheduler(store, config)
    plugin = FastPlugin(store, config)

    scheduler.register(plugin)

    assert scheduler._entries[0].refresh_time == 6.0


def test_register_uses_plugin_section_refresh_v4_key(store, tmp_path, monkeypatch):
    """The documented v4 key `[<plugin>] refresh` must be honoured (not only
    the `refresh_time` alias) — every shipped conf uses `refresh`."""
    config = _config_with_ini(tmp_path, monkeypatch, "[fast]\nrefresh = 10\n")
    scheduler = AsyncScheduler(store, config)
    scheduler.register(FastPlugin(store, config))
    assert scheduler._entries[0].refresh_time == 10.0


def test_register_uses_global_refresh_v4_key(store, tmp_path, monkeypatch):
    config = _config_with_ini(tmp_path, monkeypatch, "[global]\nrefresh = 8\n")
    scheduler = AsyncScheduler(store, config)
    scheduler.register(FastPlugin(store, config))
    assert scheduler._entries[0].refresh_time == 8.0


def test_plugin_refresh_beats_global(store, tmp_path, monkeypatch):
    config = _config_with_ini(tmp_path, monkeypatch, "[global]\nrefresh = 2\n[fast]\nrefresh = 10\n")
    scheduler = AsyncScheduler(store, config)
    scheduler.register(FastPlugin(store, config))
    assert scheduler._entries[0].refresh_time == 10.0


class GlobalCadencePlugin(FastPlugin):
    """A plugin whose `[<plugin>] refresh` throttles its own background source,
    so it must be POLLED at the global cadence (e.g. `ports`)."""

    plugin_name = "fast"  # reuse the `[fast]` section
    SCHEDULE_AT_GLOBAL_REFRESH = True


def test_schedule_at_global_refresh_ignores_plugin_refresh(store, tmp_path, monkeypatch):
    # `[fast] refresh = 30` would normally win, but the flag forces the global.
    config = _config_with_ini(tmp_path, monkeypatch, "[global]\nrefresh = 3\n[fast]\nrefresh = 30\n")
    scheduler = AsyncScheduler(store, config)
    scheduler.register(GlobalCadencePlugin(store, config))
    assert scheduler._entries[0].refresh_time == 3.0


def test_schedule_at_global_refresh_still_honours_explicit_arg(store, tmp_path, monkeypatch):
    # An explicit refresh_time= must still win over the flag (test-rig escape hatch).
    config = _config_with_ini(tmp_path, monkeypatch, "[global]\nrefresh = 3\n")
    scheduler = AsyncScheduler(store, config)
    scheduler.register(GlobalCadencePlugin(store, config), refresh_time=9.0)
    assert scheduler._entries[0].refresh_time == 9.0


# ------------------------------------------------- DEFAULT_REFRESH_TIME


class SlowByDefaultPlugin(GlancesPluginBase[dict]):
    """A plugin declaring its own intended cadence, like `sensors` (30s)."""

    plugin_name = "fast"  # reuse the `[fast]` section in the ini helpers
    IS_COLLECTION = False
    DEFAULT_REFRESH_TIME = 30.0
    fields_description = {"value": {"description": "v", "unit": "number"}}

    async def _grab_stats(self) -> dict:
        return {"value": 1}


def test_plugin_default_refresh_time_beats_global(store, tmp_path, monkeypatch):
    """A plugin declaring DEFAULT_REFRESH_TIME must not collapse to the global
    cadence. This is the whole point of the attribute: an expensive plugin
    keeps its intended cadence for a user whose personal config has no
    `[<plugin>] refresh` key (sensors costs 145ms/cycle — at the 2s global
    rate that is 7.2% of a core instead of 0.48%)."""
    config = _config_with_ini(tmp_path, monkeypatch, "[global]\nrefresh = 2\n")
    scheduler = AsyncScheduler(store, config)
    scheduler.register(SlowByDefaultPlugin(store, config))
    assert scheduler._entries[0].refresh_time == 30.0


def test_plugin_default_refresh_time_used_with_no_config_file(store, config):
    """No config file at all — the class attribute still applies."""
    scheduler = AsyncScheduler(store, config)
    scheduler.register(SlowByDefaultPlugin(store, config))
    assert scheduler._entries[0].refresh_time == 30.0


def test_config_section_beats_plugin_default_refresh_time(store, tmp_path, monkeypatch):
    """The user's explicit `[<plugin>] refresh` always wins over the class
    default — that is what makes this a non-breaking change."""
    config = _config_with_ini(tmp_path, monkeypatch, "[fast]\nrefresh = 5\n")
    scheduler = AsyncScheduler(store, config)
    scheduler.register(SlowByDefaultPlugin(store, config))
    assert scheduler._entries[0].refresh_time == 5.0


def test_explicit_arg_beats_plugin_default_refresh_time(store, config):
    scheduler = AsyncScheduler(store, config)
    scheduler.register(SlowByDefaultPlugin(store, config), refresh_time=1.5)
    assert scheduler._entries[0].refresh_time == 1.5


def test_schedule_at_global_refresh_beats_plugin_default_refresh_time(store, tmp_path, monkeypatch):
    """`ports` declares DEFAULT_REFRESH_TIME=30 for its own scan throttle, but
    must still be POLLED at the global cadence — the flag wins."""

    class GlobalCadenceWithDefault(SlowByDefaultPlugin):
        SCHEDULE_AT_GLOBAL_REFRESH = True

    config = _config_with_ini(tmp_path, monkeypatch, "[global]\nrefresh = 3\n")
    scheduler = AsyncScheduler(store, config)
    scheduler.register(GlobalCadenceWithDefault(store, config))
    assert scheduler._entries[0].refresh_time == 3.0


def test_shipped_plugin_default_refresh_times():
    """Guard the actual values against silent drift. These are the cadences
    the shipped conf documents; they now live on the plugin classes."""
    from glances.main_v5 import discover_plugin_classes

    expected = {
        "sensors": 30.0,
        "fs": 30.0,
        "folders": 60.0,
        "ip": 60.0,
        "cloud": 120.0,
        "connections": 10.0,
        "system": 60.0,
        "core": 60.0,
        "ports": 30.0,
    }
    found = {
        cls.plugin_name: cls.DEFAULT_REFRESH_TIME
        for _, cls in discover_plugin_classes()
        if cls.DEFAULT_REFRESH_TIME is not None
    }
    assert found == expected


def test_register_falls_back_to_default(store, config):
    scheduler = AsyncScheduler(store, config)
    plugin = FastPlugin(store, config)

    scheduler.register(plugin)

    assert scheduler._entries[0].refresh_time == _DEFAULT_REFRESH_TIME


def test_register_rejects_non_positive_refresh_time(store, config):
    scheduler = AsyncScheduler(store, config)
    plugin = FastPlugin(store, config)

    with pytest.raises(ValueError, match="must be > 0"):
        scheduler.register(plugin, refresh_time=0)


# ---------------------------------------------------------- registration guards


def test_register_same_plugin_twice_raises(store, config):
    scheduler = AsyncScheduler(store, config)
    plugin = FastPlugin(store, config)
    scheduler.register(plugin, refresh_time=1.0)

    with pytest.raises(ValueError, match="already registered"):
        scheduler.register(plugin, refresh_time=1.0)


async def test_register_after_run_raises(store, config):
    scheduler = AsyncScheduler(store, config)
    p1 = FastPlugin(store, config)
    p2 = SlowPlugin(store, config)
    scheduler.register(p1, refresh_time=0.05)

    run_task = asyncio.create_task(scheduler.run_forever())
    await asyncio.sleep(0.01)  # let the loop start

    try:
        with pytest.raises(RuntimeError, match="while the scheduler is running"):
            scheduler.register(p2, refresh_time=0.05)
    finally:
        await scheduler.stop()
        await run_task


async def test_run_forever_with_no_plugins_raises(store, config):
    scheduler = AsyncScheduler(store, config)
    with pytest.raises(RuntimeError, match="no registered plugins"):
        await scheduler.run_forever()


async def test_run_forever_when_already_running_raises(store, config):
    scheduler = AsyncScheduler(store, config)
    plugin = FastPlugin(store, config)
    scheduler.register(plugin, refresh_time=0.05)

    run_task = asyncio.create_task(scheduler.run_forever())
    await asyncio.sleep(0.01)

    try:
        with pytest.raises(RuntimeError, match="already running"):
            await scheduler.run_forever()
    finally:
        await scheduler.stop()
        await run_task


# ---------------------------------------------------------- run / stop


async def test_run_forever_calls_plugin_update(store, config):
    scheduler = AsyncScheduler(store, config)
    plugin = FastPlugin(store, config)
    scheduler.register(plugin, refresh_time=0.01)

    run_task = asyncio.create_task(scheduler.run_forever())
    await asyncio.sleep(0.05)
    await scheduler.stop()
    await run_task

    assert plugin.calls >= 1


async def test_stop_cancels_loops_cleanly(store, config):
    scheduler = AsyncScheduler(store, config)
    plugin = FastPlugin(store, config)
    scheduler.register(plugin, refresh_time=0.01)

    run_task = asyncio.create_task(scheduler.run_forever())
    await asyncio.sleep(0.03)
    await scheduler.stop()

    # run_forever must return cleanly (no unraised exception).
    await run_task
    assert scheduler._running is False
    assert scheduler._tasks == []


async def test_stop_calls_plugin_stop_on_every_plugin(store, config):
    calls = []

    class _P:
        plugin_name = "p_ok"

        def __init__(self, name):
            self.plugin_name = name

        async def update(self):
            return None

        def stop(self):
            calls.append(self.plugin_name)

    class _PRaises(_P):
        def stop(self):
            calls.append(self.plugin_name)
            raise RuntimeError("boom")

    scheduler = AsyncScheduler(store, config)
    scheduler.register(_PRaises("p_bad"), refresh_time=1.0)
    scheduler.register(_P("p_ok"), refresh_time=1.0)

    # stop() before run: no tasks, but must still call each plugin.stop().
    await scheduler.stop()

    # Both plugins torn down; the raising one did not block the other.
    assert set(calls) == {"p_bad", "p_ok"}


async def test_one_plugin_crash_does_not_kill_others(store, config, caplog):
    scheduler = AsyncScheduler(store, config)
    raiser = RaisingPlugin(store, config)
    healthy = FastPlugin(store, config)
    scheduler.register(raiser, refresh_time=0.01)
    scheduler.register(healthy, refresh_time=0.01)

    with caplog.at_level(logging.WARNING):
        run_task = asyncio.create_task(scheduler.run_forever())
        await asyncio.sleep(0.05)
        await scheduler.stop()
        await run_task

    assert raiser.calls >= 1
    assert healthy.calls >= 1
    assert "Scheduler caught exception from raising" in caplog.text


# ---------------------------------------------------------- smoke


async def test_smoke_two_plugins_write_to_store(store, config):
    """End-to-end: register 2 plugins, run, assert both reach the store."""
    scheduler = AsyncScheduler(store, config)
    fast = FastPlugin(store, config)
    slow = SlowPlugin(store, config)
    scheduler.register(fast, refresh_time=0.01)
    scheduler.register(slow, refresh_time=0.01)

    run_task = asyncio.create_task(scheduler.run_forever())
    await asyncio.sleep(0.05)
    await scheduler.stop()
    await run_task

    fast_payload = store.get("fast")
    slow_payload = store.get("slow")
    assert fast_payload is not None
    assert slow_payload is not None
    assert fast_payload["value"] >= 1
    assert slow_payload["value"] >= 10
    assert "time_since_update" in fast_payload
    assert "time_since_update" in slow_payload


# ---------------------------------------------------------- alerts integration


class _RecordingAlerts:
    """Minimal alerts stand-in — records every ingest call."""

    def __init__(self) -> None:
        self.ingested: list[str] = []

    async def ingest_plugin(self, plugin) -> None:
        self.ingested.append(plugin.plugin_name)


class _BoomAlerts:
    """Alerts stand-in whose ingest always raises (resilience test)."""

    async def ingest_plugin(self, plugin) -> None:
        raise RuntimeError("alerts blew up")


async def test_alerts_ingest_is_called_after_each_plugin_update(store, config):
    alerts = _RecordingAlerts()
    scheduler = AsyncScheduler(store, config, alerts=alerts)  # type: ignore[arg-type]
    fast = FastPlugin(store, config)
    scheduler.register(fast, refresh_time=0.01)

    run_task = asyncio.create_task(scheduler.run_forever())
    await asyncio.sleep(0.05)
    await scheduler.stop()
    await run_task

    # At least one ingest per cycle. Multiple cycles run during the 50 ms window.
    assert alerts.ingested.count("fast") >= 1


async def test_alerts_ingest_exception_does_not_crash_scheduler(store, config, caplog):
    """A failing alerts.ingest_plugin must never tear down the plugin loop."""
    scheduler = AsyncScheduler(store, config, alerts=_BoomAlerts())  # type: ignore[arg-type]
    fast = FastPlugin(store, config)
    scheduler.register(fast, refresh_time=0.01)

    run_task = asyncio.create_task(scheduler.run_forever())
    with caplog.at_level(logging.WARNING):
        await asyncio.sleep(0.05)
        await scheduler.stop()
        await run_task

    # Plugin still produced stats despite alerts raising every cycle.
    assert store.get("fast") is not None
    assert "Alerts ingest failed" in caplog.text


async def test_scheduler_without_alerts_does_not_call_anything(store, config):
    """Back-compat: omitting `alerts=` behaves exactly like Phase 0.6."""
    scheduler = AsyncScheduler(store, config)
    assert scheduler.alerts is None
    fast = FastPlugin(store, config)
    scheduler.register(fast, refresh_time=0.01)

    run_task = asyncio.create_task(scheduler.run_forever())
    await asyncio.sleep(0.03)
    await scheduler.stop()
    await run_task

    assert store.get("fast") is not None


# ---------------------------------------------------------- first-cycle sleep

# Captured once, at import time, before any test monkeypatches
# `glances.scheduler_v5.asyncio.sleep` — that patch targets the *shared*
# `asyncio` module object (scheduler_v5's `asyncio` import is not a copy),
# so anything that re-read `asyncio.sleep` after patching would pick up the
# fake instead of a real sleep.
_real_sleep = asyncio.sleep


def _record_sleeps(monkeypatch) -> list[float]:
    """Patch `asyncio.sleep` as seen by scheduler_v5 to record durations
    instead of actually waiting for them, so the plugin loop advances
    through many cycles almost instantly. Returns the list that gets
    appended to on every call, in call order."""
    recorded: list[float] = []

    async def fake_sleep(delay: float) -> None:
        recorded.append(delay)
        await _real_sleep(0)  # yield to the loop without actually waiting

    monkeypatch.setattr("glances.scheduler_v5.asyncio.sleep", fake_sleep)
    return recorded


async def _run_until(scheduler: AsyncScheduler, recorded: list[float], minimum: int) -> None:
    """Start `scheduler`, poll (via the real sleep) until at least
    `minimum` fake-sleep calls have been recorded, then stop it."""
    run_task = asyncio.create_task(scheduler.run_forever())
    for _ in range(200):
        if len(recorded) >= minimum:
            break
        await _real_sleep(0.001)
    await scheduler.stop()
    await run_task


async def test_first_sleep_is_global_refresh_then_plugin_refresh(store, tmp_path, monkeypatch):
    """Timeline from the bug report: [global] refresh=2, [slow] refresh=60.
    The first sleep must be the global cadence (2s) so the plugin's second
    `update()` — the first with real values — happens quickly; every sleep
    after that reverts to the plugin's own `refresh` (60s)."""
    config = _config_with_ini(tmp_path, monkeypatch, "[global]\nrefresh = 2\n[slow]\nrefresh = 60\n")
    scheduler = AsyncScheduler(store, config)
    plugin = SlowPlugin(store, config)
    scheduler.register(plugin)
    assert scheduler._entries[0].refresh_time == 60.0  # registration order untouched

    recorded = _record_sleeps(monkeypatch)
    await _run_until(scheduler, recorded, minimum=3)

    assert recorded[0] == 2.0  # first sleep: min(global=2, plugin=60)
    assert recorded[1] == 60.0  # steady state: back to the plugin's own refresh
    assert recorded[2] == 60.0


async def test_first_sleep_not_slowed_when_plugin_faster_than_global(store, tmp_path, monkeypatch):
    """A plugin configured FASTER than the global cadence must never be
    slowed down by the first-cycle rule: min(global=10, plugin=1) == 1."""
    config = _config_with_ini(tmp_path, monkeypatch, "[global]\nrefresh = 10\n[fast]\nrefresh = 1\n")
    scheduler = AsyncScheduler(store, config)
    plugin = FastPlugin(store, config)
    scheduler.register(plugin)
    assert scheduler._entries[0].refresh_time == 1.0

    recorded = _record_sleeps(monkeypatch)
    await _run_until(scheduler, recorded, minimum=2)

    assert recorded[0] == 1.0
    assert recorded[1] == 1.0


async def test_steady_state_sleep_still_equals_plugin_refresh_time(store, config, monkeypatch):
    """Existing behaviour preserved: with no per-plugin/global config at
    play (explicit `refresh_time=`), every sleep — including repeated
    cycles well past the first — still equals the plugin's own
    `refresh_time`, exactly as before this fix."""
    scheduler = AsyncScheduler(store, config)
    plugin = SlowPlugin(store, config)
    scheduler.register(plugin, refresh_time=0.01)

    recorded = _record_sleeps(monkeypatch)
    await _run_until(scheduler, recorded, minimum=5)

    assert all(delay == 0.01 for delay in recorded)

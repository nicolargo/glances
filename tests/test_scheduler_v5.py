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

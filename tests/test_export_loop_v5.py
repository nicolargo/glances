#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — unit tests for the scheduler's export loop (design §7)."""

from __future__ import annotations

import asyncio
import threading
import time

import pytest

from glances.config_v5 import GlancesConfigV5
from glances.exports.export_base_v5 import GlancesExportBase
from glances.plugins.plugin.base_v5 import GlancesPluginBase
from glances.scheduler_v5 import AsyncScheduler
from glances.stats_store_v5 import StatsStoreV5


class TinyPlugin(GlancesPluginBase[dict]):
    plugin_name = "tiny"
    IS_COLLECTION = False
    fields_description = {"percent": {"description": "p", "unit": "percent"}}

    async def _grab_stats(self) -> dict:
        return {"percent": 1.0}


class RecordingExport(GlancesExportBase):
    export_name = "recording"

    def __init__(self, config, args=None):
        super().__init__(config, args)
        self.ticks = 0
        self.exited = False

    def update(self, plugins):
        self.ticks += 1

    def export(self, name, columns, points):
        pass

    def exit(self):
        self.exited = True


def make_config(sections: dict) -> GlancesConfigV5:
    config = GlancesConfigV5()
    config._merged = {s: dict(opts) for s, opts in sections.items()}
    return config


@pytest.mark.asyncio
async def test_export_loop_ticks_while_the_scheduler_runs():
    config = make_config({"global": {"refresh": "0.05"}, "export": {"refresh": "0.05"}})
    store = StatsStoreV5()
    scheduler = AsyncScheduler(store, config)
    scheduler.register(TinyPlugin(store, config))
    exporter = RecordingExport(config)
    scheduler.register_exporter(exporter)

    task = asyncio.create_task(scheduler.run_forever())
    await asyncio.sleep(0.2)
    await scheduler.stop()
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)

    assert exporter.ticks >= 2


@pytest.mark.asyncio
async def test_no_export_loop_when_no_exporter_registered():
    config = make_config({"global": {"refresh": "0.05"}})
    store = StatsStoreV5()
    scheduler = AsyncScheduler(store, config)
    scheduler.register(TinyPlugin(store, config))

    task = asyncio.create_task(scheduler.run_forever())
    await asyncio.sleep(0.1)
    running = len(scheduler._tasks)
    await scheduler.stop()
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)

    assert running == 1  # the plugin loop only


def test_export_refresh_defaults_to_the_global_refresh():
    config = make_config({"global": {"refresh": "3"}})
    scheduler = AsyncScheduler(StatsStoreV5(), config)
    assert scheduler._export_refresh_time() == 3.0


def test_export_refresh_is_clamped_up_to_the_global_refresh(caplog):
    config = make_config({"global": {"refresh": "5"}, "export": {"refresh": "1"}})
    scheduler = AsyncScheduler(StatsStoreV5(), config)
    with caplog.at_level("WARNING"):
        value = scheduler._export_refresh_time()
    assert value == 5.0
    assert "clamped" in caplog.text.lower()


def test_export_refresh_honours_a_slower_setting():
    config = make_config({"global": {"refresh": "2"}, "export": {"refresh": "30"}})
    scheduler = AsyncScheduler(StatsStoreV5(), config)
    assert scheduler._export_refresh_time() == 30.0


@pytest.mark.asyncio
async def test_stop_calls_exit_on_every_exporter():
    config = make_config({"global": {"refresh": "0.05"}})
    store = StatsStoreV5()
    scheduler = AsyncScheduler(store, config)
    scheduler.register(TinyPlugin(store, config))
    exporter = RecordingExport(config)
    scheduler.register_exporter(exporter)

    await scheduler.stop()

    assert exporter.exited is True


@pytest.mark.asyncio
async def test_a_failing_exporter_does_not_stop_the_loop(caplog):
    class Boom(RecordingExport):
        export_name = "boom"

        def update(self, plugins):
            super().update(plugins)
            raise RuntimeError("nope")

    config = make_config({"global": {"refresh": "0.05"}, "export": {"refresh": "0.05"}})
    store = StatsStoreV5()
    scheduler = AsyncScheduler(store, config)
    scheduler.register(TinyPlugin(store, config))
    boom = Boom(config)
    good = RecordingExport(config)
    scheduler.register_exporter(boom)
    scheduler.register_exporter(good)

    task = asyncio.create_task(scheduler.run_forever())
    with caplog.at_level("WARNING"):
        await asyncio.sleep(0.2)
    await scheduler.stop()
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)

    assert boom.ticks >= 2
    assert good.ticks >= 2
    assert "nope" in caplog.text


@pytest.mark.asyncio
async def test_exit_waits_for_an_in_flight_update():
    """Regression test for Important 3.

    Cancelling the export task while it is suspended at `await
    asyncio.to_thread(exporter.update, plugins)` raises CancelledError at
    the await point but leaves the worker thread running `update()`.
    `stop()` then calls `exporter.exit()` — from a second `to_thread` call
    — concurrently. Without `GlancesExportBase._lifecycle_lock` held by
    both `update()` and `exit()`, a real exporter could release backend
    resources (e.g. close a file) while `update()` is still writing to
    them. This test fails if `self._lifecycle_lock` is removed from
    `update()` (verified manually — see the final review report).
    """
    events: list[tuple[str, str]] = []

    class SlowExport(GlancesExportBase):
        export_name = "slow"

        def export(self, name, columns, points):
            events.append(("update-start", threading.current_thread().name))
            time.sleep(0.3)
            events.append(("update-end", threading.current_thread().name))

        def exit(self):
            super().exit()
            events.append(("exit", threading.current_thread().name))

    config = make_config({"global": {"refresh": "0.05"}, "export": {"refresh": "0.05"}})
    store = StatsStoreV5()
    scheduler = AsyncScheduler(store, config)
    plugin = TinyPlugin(store, config)
    await plugin.update()  # payload ready before the loop starts, so export() runs on tick 0
    scheduler.register(plugin)
    exporter = SlowExport(config)
    scheduler.register_exporter(exporter)

    task = asyncio.create_task(scheduler.run_forever())
    await asyncio.sleep(0.1)  # let the export tick reach export()'s sleep
    await scheduler.stop()
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)

    assert [name for name, _ in events] == ["update-start", "update-end", "exit"]


def test_export_flag_sets_per_exporter_booleans():
    from glances.main_v5 import build_parser

    args = build_parser().parse_args(["--export", "csv,influxdb2"])
    from glances.main_v5 import apply_export_flags

    apply_export_flags(args)

    assert args.export_csv is True
    assert args.export_influxdb2 is True
    assert getattr(args, "export_json", False) is False


def test_discover_exporters_returns_nothing_without_the_flag():
    from glances.main_v5 import apply_export_flags, build_parser, discover_exporters

    args = build_parser().parse_args([])
    apply_export_flags(args)

    assert discover_exporters(make_config({}), args) == []


def test_csv_and_json_file_flags_have_v4_defaults():
    from glances.main_v5 import build_parser

    args = build_parser().parse_args([])

    assert args.export_csv_file == "./glances.csv"
    assert args.export_json_file == "./glances.json"
    assert args.export_csv_overwrite is False

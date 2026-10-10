"""Scheduler idle mode: slow down without client, wake on the first request."""

import asyncio
import time

from glances.scheduler_v5 import AsyncScheduler


class _Config:
    def __init__(self, **glob):
        self.glob = glob

    def get(self, section, key, default=None):
        return self.glob.get(key, default) if section == "global" else default


def _scheduler(**glob):
    return AsyncScheduler(store=None, config=_Config(**glob))


def test_disabled_by_default():
    sch = _scheduler()
    sch._last_activity -= 1000
    assert not sch._is_idle()


def test_idle_after_delay_and_touch_resets():
    sch = _scheduler()
    sch.enable_idle_mode()
    assert not sch._is_idle()
    sch._last_activity = time.monotonic() - 1000
    assert sch._is_idle()
    sch.touch()
    assert not sch._is_idle()


def test_factor_one_disables():
    sch = _scheduler(idle_refresh_factor=1)
    sch.enable_idle_mode()
    sch._last_activity = time.monotonic() - 1000
    assert not sch._is_idle()


def test_touch_wakes_idle_sleep():
    async def run():
        sch = _scheduler(idle_refresh_factor=100)
        sch.enable_idle_mode()
        sch._last_activity = time.monotonic() - 1000
        sleeper = asyncio.create_task(sch._sleep(1.0))  # idle: would sleep 100 s
        await asyncio.sleep(0.05)
        assert not sleeper.done()
        sch.touch()
        await asyncio.wait_for(sleeper, 1.0)

    asyncio.run(run())


def test_requests_touch_but_probes_do_not():
    from fastapi.testclient import TestClient

    from glances.config_v5 import GlancesConfigV5
    from glances.stats_store_v5 import StatsStoreV5
    from glances.webserver_v5 import build_app

    app = build_app(config=GlancesConfigV5(), store=StatsStoreV5())
    hits = []
    app.state.on_activity = lambda: hits.append(1)
    client = TestClient(app)
    client.get("/status")
    client.get("/healthz")
    assert hits == []
    client.get("/api/5/pluginslist")
    assert hits == [1]

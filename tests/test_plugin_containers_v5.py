#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the Glances v5 containers plugin model."""

from __future__ import annotations

import pytest

from glances.plugins.containers.model_v5 import PluginModel


def _mk(store_with, config_with, section=None):
    return PluginModel(store_with(), config_with({"containers": section or {}}))


def test_identity(store_with, config_with):
    p = _mk(store_with, config_with)
    assert p.plugin_name == "containers"
    assert p.IS_COLLECTION is True
    assert p.EMITS_ALERTS is True
    assert p._primary_key == "name"


def test_fields_present(store_with, config_with):
    p = _mk(store_with, config_with)
    fd = p.fields_description
    for key in (
        "name",
        "id",
        "image",
        "status",
        "created",
        "command",
        "cpu_percent",
        "cpu_limit",
        "memory_usage",
        "memory_usage_no_cache",
        "memory_limit",
        "memory_percent",
        "io_rx",
        "io_wx",
        "network_rx",
        "network_tx",
        "ports",
        "uptime",
        "engine",
        "pod_name",
        "pod_id",
    ):
        assert key in fd, key
    assert fd["name"].get("primary_key") is True
    # Threshold aliases (design §5.2).
    assert fd["cpu_percent"]["threshold_field"] == "cpu"
    assert fd["memory_percent"]["threshold_field"] == "mem"


def test_cpu_level_uses_cpu_prefix_thresholds(store_with, config_with):
    p = _mk(store_with, config_with, {"cpu_warning": "70", "cpu_critical": "90"})
    p._stats = [{"name": "web", "cpu_percent": 95.0, "memory_percent": None}]
    p._derived_parameters()
    assert p._levels["web"]["cpu_percent"]["level"] == "critical"


def test_mem_level_uses_mem_prefix_thresholds(store_with, config_with):
    p = _mk(store_with, config_with, {"mem_careful": "20", "mem_warning": "50"})
    p._stats = [{"name": "web", "cpu_percent": None, "memory_percent": 60.0}]
    p._derived_parameters()
    assert p._levels["web"]["memory_percent"]["level"] == "warning"


def test_per_container_cpu_override(store_with, config_with):
    p = _mk(store_with, config_with, {"cpu_warning": "70", "web_cpu_warning": "10"})
    p._stats = [{"name": "web", "cpu_percent": 15.0}]
    p._derived_parameters()
    assert p._levels["web"]["cpu_percent"]["level"] == "warning"


class _FakeWatcher:
    def __init__(self, containers, raises=False):
        self._containers = containers
        self._raises = raises
        self.stopped = False

    def update(self, all_tag):
        if self._raises:
            raise RuntimeError("engine down")
        return {}, [dict(c) for c in self._containers]

    def stop(self):
        self.stopped = True


def _model_with_watchers(store_with, config_with, watchers, section=None):
    p = PluginModel(store_with(), config_with({"containers": section or {}}))
    p.watchers = watchers
    return p


@pytest.mark.asyncio
async def test_grab_merges_engines_and_injects_engine_field(store_with, config_with):
    # memory_usage=250 simulates the engine's v4 export value (usage−cache);
    # the nested memory dict drives the no-cache + percent surfaces.
    d = {
        "name": "web",
        "key": "name",
        "memory_usage": 250,
        "memory": {"usage": 300, "inactive_file": 100, "limit": 1000},
    }
    p = _model_with_watchers(store_with, config_with, {"docker": _FakeWatcher([d])})
    out = await p._grab_stats()
    assert len(out) == 1
    assert out[0]["engine"] == "docker"
    # Three memory surfaces:
    assert out[0]["memory_usage"] == 250  # export (v4 value, untouched)
    assert out[0]["memory_usage_no_cache"] == 200  # display (usage − inactive_file)
    assert out[0]["memory_percent"] == 20.0  # alert  (200 / 1000 * 100)


@pytest.mark.asyncio
async def test_grab_partial_failure_keeps_other_engine(store_with, config_with):
    ok = {"name": "web", "memory": {}}
    p = _model_with_watchers(
        store_with,
        config_with,
        {"bad": _FakeWatcher([], raises=True), "docker": _FakeWatcher([ok])},
    )
    out = await p._grab_stats()
    assert [c["name"] for c in out] == ["web"]


@pytest.mark.asyncio
async def test_grab_empty_when_no_watcher(store_with, config_with):
    p = _model_with_watchers(store_with, config_with, {})
    assert await p._grab_stats() == []


@pytest.mark.asyncio
async def test_grab_memory_percent_none_when_limit_zero(store_with, config_with):
    # limit=0 → no meaningful percent, no divide-by-zero: memory_percent is None.
    d = {"name": "web", "memory": {"usage": 300, "inactive_file": 100, "limit": 0}}
    p = _model_with_watchers(store_with, config_with, {"docker": _FakeWatcher([d])})
    out = await p._grab_stats()
    assert out[0]["memory_usage_no_cache"] == 200
    assert out[0]["memory_percent"] is None


@pytest.mark.asyncio
async def test_grab_memory_percent_none_when_limit_missing(store_with, config_with):
    # No limit key → memory_percent is None (guarded), no exception.
    d = {"name": "web", "memory": {"usage": 300, "inactive_file": 100}}
    p = _model_with_watchers(store_with, config_with, {"docker": _FakeWatcher([d])})
    out = await p._grab_stats()
    assert out[0]["memory_usage_no_cache"] == 200
    assert out[0]["memory_percent"] is None


@pytest.mark.asyncio
async def test_grab_all_tag_forwarded_to_watcher(store_with, config_with):
    seen = {}

    class _Capturing(_FakeWatcher):
        def update(self, all_tag):
            seen["all_tag"] = all_tag
            return {}, []

    p = _model_with_watchers(store_with, config_with, {"docker": _Capturing([])}, section={"all": "True"})
    await p._grab_stats()
    assert seen["all_tag"] is True


@pytest.mark.asyncio
async def test_grab_sort_follows_glances_processes_sort_key(store_with, config_with):
    from glances.processes import glances_processes

    cs = [
        {"name": "a", "cpu_percent": 1.0, "memory": {}},
        {"name": "b", "cpu_percent": 9.0, "memory": {}},
    ]
    p = _model_with_watchers(store_with, config_with, {"docker": _FakeWatcher(cs)})
    saved = glances_processes.sort_key
    try:
        glances_processes.set_sort_key("cpu_percent", auto=False)
        out = await p._grab_stats()
        # cpu_percent sort is reverse (highest first).
        assert [c["name"] for c in out] == ["b", "a"]

        glances_processes.set_sort_key("name", auto=False)
        out = await p._grab_stats()
        # name sort is ascending.
        assert [c["name"] for c in out] == ["a", "b"]
    finally:
        glances_processes.set_sort_key(saved, auto=False)


def test_stop_calls_each_watcher(store_with, config_with):
    w1, w2 = _FakeWatcher([]), _FakeWatcher([])
    p = _model_with_watchers(store_with, config_with, {"docker": w1, "podman": w2})
    p.stop()
    assert w1.stopped and w2.stopped


def test_stop_one_raising_watcher_does_not_block_others(store_with, config_with):
    class _Boom(_FakeWatcher):
        def stop(self):
            raise RuntimeError("boom")

    good = _FakeWatcher([])
    p = _model_with_watchers(store_with, config_with, {"bad": _Boom([]), "docker": good})
    p.stop()  # must not raise
    assert good.stopped


def test_metadata_carries_disable_stats_and_max_name_size(store_with, config_with):
    p = PluginModel(store_with(), config_with({"containers": {"disable_stats": "command", "max_name_size": "12"}}))
    p._add_metadata()
    assert "command" in p._metadata["disable_stats"]
    assert p._metadata["max_name_size"] == 12

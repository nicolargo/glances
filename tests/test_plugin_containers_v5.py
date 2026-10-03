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

from unittest.mock import call, patch

import pytest

import glances.plugins.containers.model_v5 as model_mod
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
        "engine_url",
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


def test_mem_cell_coloured_by_memory_percent_level():
    from glances.outputs.curses_renderer_v5 import ColorRole
    from glances.plugins.containers.render_curses_v5 import _cpu_mem_cells

    c = {"name": "web", "cpu_percent": 5.0, "memory_usage_no_cache": 900, "memory_percent": 95.0}
    levels = {"memory_percent": {"level": "critical", "prominent": False}}
    cpu_cell, mem_cell = _cpu_mem_cells(c, set(), levels, show_mem_max=False)
    assert mem_cell.color == ColorRole.CRITICAL
    assert cpu_cell.color == ColorRole.DEFAULT


def test_container_without_cpu_or_memory_stats(store_with, config_with):
    # A restarting container: no cpu_percent / memory_percent, memory={}.
    from glances.plugins.containers.render_curses_v5 import render

    p = _mk(store_with, config_with, {"cpu_critical": "90", "mem_critical": "90"})
    c = {"name": "web", "engine": "docker", "status": "restarting", "memory": {}}
    PluginModel._reconcile_memory(c)
    p._stats = [c]
    p._derived_parameters()
    item_levels = p._levels.get("web", {})
    assert "cpu_percent" not in item_levels
    assert "memory_percent" not in item_levels
    rows = render({"data": [c], "_levels": p._levels, "disable_stats": [], "max_name_size": 20}, None, {})
    assert len(rows) == 2  # header + the container row


class _FakeMonitor:
    def __init__(self, containers, engine="docker", engine_url=None, raises=False):
        self._containers = containers
        self.ENGINE = engine
        self.engine_url = engine_url
        self._raises = raises
        self.stopped = False

    def update(self, all_tag):
        if self._raises:
            raise RuntimeError("engine down")
        return {}, [dict(c) for c in self._containers]

    def stop(self):
        self.stopped = True


def _model_with_monitors(store_with, config_with, monitors, section=None):
    p = PluginModel(store_with(), config_with({"containers": section or {}}))
    p.monitors = monitors
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
    p = _model_with_monitors(store_with, config_with, [_FakeMonitor([d], engine="docker")])
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
    p = _model_with_monitors(
        store_with,
        config_with,
        [_FakeMonitor([], raises=True), _FakeMonitor([ok])],
    )
    out = await p._grab_stats()
    assert [c["name"] for c in out] == ["web"]


@pytest.mark.asyncio
async def test_grab_empty_when_no_monitors(store_with, config_with):
    p = _model_with_monitors(store_with, config_with, [])
    assert await p._grab_stats() == []


@pytest.mark.asyncio
async def test_grab_memory_percent_none_when_limit_zero(store_with, config_with):
    # limit=0 → no meaningful percent, no divide-by-zero: memory_percent is None.
    d = {"name": "web", "memory": {"usage": 300, "inactive_file": 100, "limit": 0}}
    p = _model_with_monitors(store_with, config_with, [_FakeMonitor([d])])
    out = await p._grab_stats()
    assert out[0]["memory_usage_no_cache"] == 200
    assert out[0]["memory_percent"] is None


@pytest.mark.asyncio
async def test_grab_memory_percent_none_when_limit_missing(store_with, config_with):
    # No limit key → memory_percent is None (guarded), no exception.
    d = {"name": "web", "memory": {"usage": 300, "inactive_file": 100}}
    p = _model_with_monitors(store_with, config_with, [_FakeMonitor([d])])
    out = await p._grab_stats()
    assert out[0]["memory_usage_no_cache"] == 200
    assert out[0]["memory_percent"] is None


@pytest.mark.asyncio
async def test_grab_all_tag_forwarded_to_monitor(store_with, config_with):
    seen = {}

    class _Capturing(_FakeMonitor):
        def update(self, all_tag):
            seen["all_tag"] = all_tag
            return {}, []

    p = _model_with_monitors(store_with, config_with, [_Capturing([])], section={"all": "True"})
    await p._grab_stats()
    assert seen["all_tag"] is True


@pytest.mark.asyncio
async def test_grab_sort_follows_glances_processes_sort_key(store_with, config_with):
    from glances.processes import glances_processes

    cs = [
        {"name": "a", "cpu_percent": 1.0, "memory": {}},
        {"name": "b", "cpu_percent": 9.0, "memory": {}},
    ]
    p = _model_with_monitors(store_with, config_with, [_FakeMonitor(cs)])
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


def test_stop_calls_each_monitor(store_with, config_with):
    m1, m2 = _FakeMonitor([]), _FakeMonitor([])
    p = _model_with_monitors(store_with, config_with, [m1, m2])
    p.stop()
    assert m1.stopped and m2.stopped


def test_stop_one_raising_monitor_does_not_block_others(store_with, config_with):
    class _Boom(_FakeMonitor):
        def stop(self):
            raise RuntimeError("boom")

    good = _FakeMonitor([])
    p = _model_with_monitors(store_with, config_with, [_Boom([]), good])
    p.stop()  # must not raise
    assert good.stopped


def test_metadata_carries_disable_stats_and_max_name_size(store_with, config_with):
    p = PluginModel(store_with(), config_with({"containers": {"disable_stats": "command", "max_name_size": "12"}}))
    p._add_metadata()
    assert "command" in p._metadata["disable_stats"]
    assert p._metadata["max_name_size"] == 12


@pytest.mark.parametrize(
    ("conf_value", "expected"),
    [
        (None, None),
        ("", []),
        ("unix:///var/run/docker.sock", ["unix:///var/run/docker.sock"]),
        (
            '"unix:///var/run/docker.sock", tcp://remote:2375',
            ["unix:///var/run/docker.sock", "tcp://remote:2375"],
        ),
        (
            "'unix:///var/run/docker.sock', '', \"tcp://remote:2375\"",
            ["unix:///var/run/docker.sock", "tcp://remote:2375"],
        ),
    ],
)
def test_parse_urls_from_config(store_with, config_with, conf_value, expected):
    cfg = config_with({"containers": {"docker_urls": conf_value}} if conf_value is not None else {})
    p = PluginModel(store_with(), cfg)
    assert p._parse_urls("docker_urls") == expected


def test_parse_urls_from_list(store_with, config_with):
    p = PluginModel(store_with(), config_with({}))
    p.config = type("MockConfig", (), {"get_value": lambda self, sec, key, default=None: ['"unix:///d1.sock"', '', "'unix:///d2.sock'"]})()
    assert p._parse_urls("docker_urls") == ["unix:///d1.sock", "unix:///d2.sock"]


def test_init_monitors_with_custom_urls(store_with, config_with):
    with (
        patch.object(model_mod, "DockerEngineMonitor") as mock_docker,
        patch.object(model_mod, "PodmanEngineMonitor") as mock_podman,
        patch.object(model_mod, "LxdEngineMonitor") as mock_lxd,
        patch.object(model_mod, "disable_plugin_docker", False),
        patch.object(model_mod, "disable_plugin_podman", False),
        patch.object(model_mod, "disable_plugin_lxd", False),
    ):
        cfg = config_with(
            {
                "containers": {
                    "docker_urls": "unix:///d1.sock, unix:///d2.sock",
                    "podman_urls": "unix:///p1.sock",
                    "lxd_urls": "",
                }
            }
        )
        p = PluginModel(store_with(), cfg)

        assert mock_docker.call_args_list == [call(url="unix:///d1.sock"), call(url="unix:///d2.sock")]
        assert mock_podman.call_args_list == [call(url="unix:///p1.sock")]
        assert mock_lxd.call_count == 0
        assert len(p.monitors) == 3


def test_init_monitors_all_disabled(store_with, config_with):
    with (
        patch.object(model_mod, "DockerEngineMonitor") as mock_docker,
        patch.object(model_mod, "PodmanEngineMonitor") as mock_podman,
        patch.object(model_mod, "LxdEngineMonitor") as mock_lxd,
        patch.object(model_mod, "disable_plugin_docker", False),
        patch.object(model_mod, "disable_plugin_podman", False),
        patch.object(model_mod, "disable_plugin_lxd", False),
    ):
        cfg = config_with(
            {
                "containers": {
                    "docker_urls": "",
                    "podman_urls": "",
                    "lxd_urls": "",
                }
            }
        )
        p = PluginModel(store_with(), cfg)

        assert mock_docker.call_count == 0
        assert mock_podman.call_count == 0
        assert mock_lxd.call_count == 0
        assert len(p.monitors) == 0


@pytest.mark.asyncio
async def test_grab_aggregates_multiple_monitors_for_same_engine(store_with, config_with):
    c1 = {"name": "c1", "key": "name", "engine": "docker", "engine_url": "unix:///d1.sock", "memory": {}}
    c2 = {"name": "c2", "key": "name", "engine": "docker", "engine_url": "unix:///d2.sock", "memory": {}}
    m1 = _FakeMonitor([c1])
    m2 = _FakeMonitor([c2])

    p = PluginModel(store_with(), config_with({}))
    p.monitors = [m1, m2]

    out = await p._grab_stats()
    assert len(out) == 2
    names = {c["name"] for c in out}
    assert names == {"c1", "c2"}
    urls = {c["engine_url"] for c in out}
    assert urls == {"unix:///d1.sock", "unix:///d2.sock"}

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

import time
from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

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
        "started_at",
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
    p.config = type(
        "MockConfig",
        (),
        {"get_value": lambda self, sec, key, default=None: ['"unix:///d1.sock"', '', "'unix:///d2.sock'"]},
    )()
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


# started_at: the engines publish the container start time (Unix seconds). 2026-10-06T08:00:00Z == 1791273600.
_STARTED_AT = 1791273600
_ACTIVITY = {"cpu": {"total": 1.0}, "memory": {"usage": 100}, "io": {}, "network": {}}


def _docker_monitor():
    m = model_mod.DockerEngineMonitor.__new__(model_mod.DockerEngineMonitor)
    m.engine_url = None
    m.image_cache = {}
    m.stats_fetchers = {"c1": SimpleNamespace(activity_stats=_ACTIVITY)}
    return m


def _docker_container(status):
    c = MagicMock()
    c.id, c.name, c.ports = "c1", "web", {}
    c.attrs = {
        "State": {"Status": status, "StartedAt": "2026-10-06T08:00:00.123456789Z"},
        "Created": "2026-10-01T00:00:00Z",
        "Config": {"Cmd": ["sh"]},
    }
    c.image.tags = ["web:latest"]
    return c


def _podman_monitor():
    m = model_mod.PodmanEngineMonitor.__new__(model_mod.PodmanEngineMonitor)
    m.engine_url = None
    m.image_cache = {}
    m.container_stats_fetchers = {"c1": SimpleNamespace(activity_stats=_ACTIVITY)}
    return m


def _podman_container(state):
    c = MagicMock()
    c.id, c.name, c.ports = "c1", "web", {}
    c.attrs = {"State": state, "StartedAt": _STARTED_AT, "Created": 1791000000, "Command": ["sh"]}
    c.image.tags = ["web:latest"]
    return c


def _lxd_monitor():
    m = model_mod.LxdEngineMonitor.__new__(model_mod.LxdEngineMonitor)
    m.ext_name = "containers (LXD)"
    m.engine_url = None
    m.stats_fetchers = {"web": SimpleNamespace(activity_stats=_ACTIVITY)}
    return m


def _lxd_instance(status, last_used_at="2026-10-06T08:00:00Z"):
    i = MagicMock()
    i.name, i.status, i.last_used_at = "web", status, last_used_at
    i.config, i.expanded_devices = {}, {}
    return i


def test_docker_started_at_is_the_start_timestamp():
    stats = _docker_monitor().generate_stats(_docker_container("running"))
    assert stats["started_at"] == _STARTED_AT


def test_docker_started_at_is_none_when_not_running():
    stats = _docker_monitor().generate_stats(_docker_container("exited"))
    assert stats["started_at"] is None


def test_podman_started_at_is_the_start_timestamp():
    stats = _podman_monitor().generate_stats(_podman_container("running"))
    assert stats["started_at"] == _STARTED_AT


def test_podman_started_at_is_none_when_not_running():
    # Podman keeps StartedAt after the container stops.
    stats = _podman_monitor().generate_stats(_podman_container("exited"))
    assert stats["started_at"] is None


@pytest.mark.parametrize("tz", ["UTC0", "JST-9", "EST5EDT"])
def test_lxd_started_at_is_last_used_at_in_utc(monkeypatch, tz):
    # last_used_at is UTC: the timestamp must not move with the local zone.
    monkeypatch.setenv("TZ", tz)
    time.tzset()
    try:
        stats = _lxd_monitor().generate_stats(_lxd_instance("Running"))
    finally:
        monkeypatch.undo()
        time.tzset()
    assert stats["started_at"] == _STARTED_AT


@pytest.mark.parametrize(
    ("status", "last_used_at"), [("Stopped", "2026-10-06T08:00:00Z"), ("Running", "1970-01-01T00:00:00Z")]
)
def test_lxd_started_at_is_none_without_a_start(status, last_used_at):
    stats = _lxd_monitor().generate_stats(_lxd_instance(status, last_used_at))
    assert stats["started_at"] is None


@pytest.mark.asyncio
async def test_grab_publishes_started_at_and_no_uptime(store_with, config_with):
    m = _docker_monitor()
    m.update = lambda all_tag: ({}, [m.generate_stats(_docker_container("running"))])
    m.stop = lambda: None
    p = _model_with_monitors(store_with, config_with, [m])
    await p.update()
    item = p.get_stats()["data"][0]
    assert item["started_at"] == _STARTED_AT
    assert "uptime" not in item

#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — unit tests for the ``processlist`` plugin (collection)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from glances.config_v5 import GlancesConfigV5
from glances.plugins.processlist.model_v5 import PluginModel
from glances.stats_store_v5 import StatsStoreV5


@pytest.fixture
def store() -> StatsStoreV5:
    return StatsStoreV5()


@pytest.fixture
def config(tmp_path, monkeypatch) -> GlancesConfigV5:
    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    return GlancesConfigV5()


def _config_with(tmp_path, monkeypatch, body: str) -> GlancesConfigV5:
    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    xdg = tmp_path / "xdg"
    cfg_dir = xdg / "glances"
    cfg_dir.mkdir(parents=True)
    (cfg_dir / "glances.conf").write_text(body)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    return GlancesConfigV5()


def _proc(**overrides):
    """Build a representative engine process dict."""
    base = {
        "pid": 1234,
        "name": "python3",
        "username": "alice",
        "status": "S",
        "nice": 0,
        "num_threads": 4,
        "cpu_percent": 12.5,
        "memory_percent": 3.1,
        "cmdline": ["python3", "myscript.py"],
        "cpu_num": 2,
        "memory_info": (1024, 2048, 0, 0, 0, 0, 0),
        "cpu_times": (1.0, 0.5),
        "io_counters": [0, 0, 0, 0, 0],
        "time_since_update": 1.0,
        "key": "pid",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------- contract


def test_plugin_identity(store, config):
    plugin = PluginModel(store, config)
    assert plugin.plugin_name == "processlist"
    assert plugin.IS_COLLECTION is True
    assert plugin._primary_key == "pid"


def test_pid_is_primary_key(store, config):
    fields = PluginModel(store, config)._fields
    assert fields["pid"].get("primary_key") is True


def test_cpu_and_mem_percent_are_watched_not_prominent(store, config):
    fields = PluginModel(store, config)._fields
    for name in ("cpu_percent", "memory_percent"):
        assert fields[name].get("watched") is True, name
        assert fields[name].get("prominent") is False, name
        assert fields[name].get("default_thresholds") == {
            "careful": 50.0,
            "warning": 70.0,
            "critical": 90.0,
        }, name


def test_internal_fields_flagged(store, config):
    fields = PluginModel(store, config)._fields
    for name in ("memory_info", "cpu_times", "io_counters", "gids", "time_since_update", "key"):
        assert fields[name].get("internal") is True, name


# ---------------------------------------------------------- update pipeline


async def test_update_surfaces_engine_list(store, config):
    plugin = PluginModel(store, config)
    procs = [_proc(pid=1, name="systemd"), _proc(pid=42, name="bash")]
    with patch("glances.plugins.processlist.model_v5.glances_processes.get_list", return_value=procs):
        await plugin.update()
    data = store.get("processlist")["data"]
    pids = sorted(p["pid"] for p in data)
    assert pids == [1, 42]


async def test_update_filters_undeclared_fields(store, config):
    plugin = PluginModel(store, config)
    procs = [_proc(pid=1, name="x", fancy_extra="surprise")]
    with patch("glances.plugins.processlist.model_v5.glances_processes.get_list", return_value=procs):
        await plugin.update()
    item = store.get("processlist")["data"][0]
    assert "fancy_extra" not in item


async def test_update_returns_copy_so_engine_state_isolated(store, config):
    plugin = PluginModel(store, config)
    engine_list = [_proc(pid=1, name="x")]
    with patch("glances.plugins.processlist.model_v5.glances_processes.get_list", return_value=engine_list):
        await plugin.update()
    stored = store.get("processlist")["data"][0]
    stored["name"] = "MUTATED"
    # Engine's source dict must be untouched.
    assert engine_list[0]["name"] == "x"


async def test_update_handles_engine_failure(store, config):
    plugin = PluginModel(store, config)
    with patch(
        "glances.plugins.processlist.model_v5.glances_processes.get_list",
        side_effect=RuntimeError("engine boom"),
    ):
        await plugin.update()
    assert store.get("processlist")["data"] == []


async def test_update_handles_non_list_return(store, config):
    plugin = PluginModel(store, config)
    with patch(
        "glances.plugins.processlist.model_v5.glances_processes.get_list",
        return_value=None,
    ):
        await plugin.update()
    assert store.get("processlist")["data"] == []


async def test_update_skips_non_dict_entries(store, config):
    plugin = PluginModel(store, config)
    procs = [_proc(pid=1, name="x"), "garbage", None, _proc(pid=2, name="y")]
    with patch("glances.plugins.processlist.model_v5.glances_processes.get_list", return_value=procs):
        await plugin.update()
    pids = sorted(p["pid"] for p in store.get("processlist")["data"])
    assert pids == [1, 2]


# ---------------------------------------------------------- thresholds


async def test_cpu_percent_default_thresholds_trigger_level(store, config):
    plugin = PluginModel(store, config)
    procs = [_proc(pid=1, cpu_percent=75.0)]  # > warning (70)
    with patch("glances.plugins.processlist.model_v5.glances_processes.get_list", return_value=procs):
        await plugin.update()
    levels = store.get("processlist")["_levels"]
    assert levels[1]["cpu_percent"]["level"] == "warning"
    assert levels[1]["cpu_percent"]["prominent"] is False


async def test_memory_percent_default_thresholds_trigger_level(store, config):
    plugin = PluginModel(store, config)
    procs = [_proc(pid=1, memory_percent=95.0)]  # > critical (90)
    with patch("glances.plugins.processlist.model_v5.glances_processes.get_list", return_value=procs):
        await plugin.update()
    levels = store.get("processlist")["_levels"]
    assert levels[1]["memory_percent"]["level"] == "critical"


async def test_user_can_override_cpu_percent_threshold(tmp_path, monkeypatch, store):
    config = _config_with(
        tmp_path,
        monkeypatch,
        "[processlist]\ncpu_percent_careful=20\ncpu_percent_warning=40\ncpu_percent_critical=60\n",
    )
    plugin = PluginModel(store, config)
    procs = [_proc(pid=1, cpu_percent=45.0)]  # > 40 → warning under override
    with patch("glances.plugins.processlist.model_v5.glances_processes.get_list", return_value=procs):
        await plugin.update()
    levels = store.get("processlist")["_levels"]
    assert levels[1]["cpu_percent"]["level"] == "warning"


# ---------------------------------------------------------- categorical thresholds


async def test_status_categorical_threshold_from_config(tmp_path, monkeypatch, store):
    """`status_critical=Z,D` should mark zombies as critical."""
    config = _config_with(
        tmp_path,
        monkeypatch,
        "[processlist]\nstatus_ok=R,W,P,I\nstatus_critical=Z,D\n",
    )
    plugin = PluginModel(store, config)
    procs = [
        _proc(pid=1, status="R"),
        _proc(pid=2, status="Z"),
        _proc(pid=3, status="S"),  # not in any bucket → ok
    ]
    with patch("glances.plugins.processlist.model_v5.glances_processes.get_list", return_value=procs):
        await plugin.update()
    levels = store.get("processlist")["_levels"]
    assert levels[1]["status"]["level"] == "ok"
    assert levels[2]["status"]["level"] == "critical"
    assert levels[3]["status"]["level"] == "ok"


async def test_status_without_config_emits_no_level_entry(store, config):
    """No `status_*=` in conf → status is watched but no level computed."""
    plugin = PluginModel(store, config)
    procs = [_proc(pid=1, status="Z")]
    with patch("glances.plugins.processlist.model_v5.glances_processes.get_list", return_value=procs):
        await plugin.update()
    levels = store.get("processlist")["_levels"]
    # status not configured → no entry under levels[1].
    assert "status" not in levels.get(1, {})


async def test_nice_categorical_threshold_from_config(tmp_path, monkeypatch, store):
    """`nice_warning=-1,1,...` flags non-zero nice values as warning."""
    config = _config_with(
        tmp_path,
        monkeypatch,
        "[processlist]\nnice_warning=-1,1,2,3,4,5\n",
    )
    plugin = PluginModel(store, config)
    procs = [
        _proc(pid=1, nice=0),  # not in list → ok
        _proc(pid=2, nice=3),  # in list → warning
        _proc(pid=3, nice=-1),  # in list → warning
    ]
    with patch("glances.plugins.processlist.model_v5.glances_processes.get_list", return_value=procs):
        await plugin.update()
    levels = store.get("processlist")["_levels"]
    assert levels[1]["nice"]["level"] == "ok"
    assert levels[2]["nice"]["level"] == "warning"
    assert levels[3]["nice"]["level"] == "warning"


async def test_nice_escalating_categorical_thresholds(tmp_path, monkeypatch, store):
    """Buckets careful / warning / critical escalate by membership."""
    config = _config_with(
        tmp_path,
        monkeypatch,
        "[processlist]\nnice_careful=1,2,3,4,5,6,7,8,9\nnice_warning=10,11,12,13,14\nnice_critical=15,16,17,18,19\n",
    )
    plugin = PluginModel(store, config)
    procs = [
        _proc(pid=1, nice=5),
        _proc(pid=2, nice=12),
        _proc(pid=3, nice=18),
    ]
    with patch("glances.plugins.processlist.model_v5.glances_processes.get_list", return_value=procs):
        await plugin.update()
    levels = store.get("processlist")["_levels"]
    assert levels[1]["nice"]["level"] == "careful"
    assert levels[2]["nice"]["level"] == "warning"
    assert levels[3]["nice"]["level"] == "critical"

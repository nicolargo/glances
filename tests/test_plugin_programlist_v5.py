#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — unit tests for the ``programlist`` plugin (collection)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from glances.config_v5 import GlancesConfigV5
from glances.plugins.programlist.model_v5 import PluginModel
from glances.stats_store_v5 import StatsStoreV5


@pytest.fixture
def store() -> StatsStoreV5:
    return StatsStoreV5()


@pytest.fixture
def config(tmp_path, monkeypatch) -> GlancesConfigV5:
    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    return GlancesConfigV5()


def _program(**overrides):
    """Build a representative engine program dict (processes_to_programs output)."""
    base = {
        "name": "python3",
        "username": "alice",
        "nprocs": 3,
        "num_threads": 12,
        "cpu_percent": 42.5,
        "memory_percent": 9.3,
        "cmdline": ["python3"],
        "memory_info": {"rss": 96 * 1024**2, "vms": 360 * 1024**2},
        "cpu_times": {"user": 3.0, "system": 1.5},
        "io_counters": [0, 0, 0, 0, 1],
        "status": "S",
        "nice": 0,
        "time_since_update": 1.0,
        "pid": "_",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------- contract


def test_plugin_identity(store, config):
    plugin = PluginModel(store, config)
    assert plugin.plugin_name == "programlist"
    assert plugin.IS_COLLECTION is True
    assert plugin._primary_key == "name"


def test_programlist_opts_out_of_alerts(store, config):
    """Like processlist, programlist colours cells but never pages."""
    assert PluginModel.EMITS_ALERTS is False


def test_name_is_primary_key(store, config):
    fields = PluginModel(store, config)._fields
    assert fields["name"].get("primary_key") is True


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
    for name in ("memory_info", "cpu_times", "io_counters", "time_since_update"):
        assert fields[name].get("internal") is True, name


# ---------------------------------------------------------- update pipeline


async def test_update_surfaces_engine_programs(store, config):
    plugin = PluginModel(store, config)
    progs = [_program(name="python3"), _program(name="bash", nprocs=1)]
    with patch(
        "glances.plugins.programlist.model_v5.glances_processes.get_list",
        return_value=progs,
    ) as mocked:
        await plugin.update()
    names = sorted(p["name"] for p in store.get("programlist")["data"])
    assert names == ["bash", "python3"]
    # The engine must be asked for the aggregated programs view.
    mocked.assert_called_once_with(as_programs=True)


async def test_update_returns_copy_so_engine_state_isolated(store, config):
    plugin = PluginModel(store, config)
    engine_list = [_program(name="python3")]
    with patch(
        "glances.plugins.programlist.model_v5.glances_processes.get_list",
        return_value=engine_list,
    ):
        await plugin.update()
    store.get("programlist")["data"][0]["name"] = "MUTATED"
    assert engine_list[0]["name"] == "python3"


async def test_update_handles_engine_failure(store, config):
    plugin = PluginModel(store, config)
    with patch(
        "glances.plugins.programlist.model_v5.glances_processes.get_list",
        side_effect=RuntimeError("engine boom"),
    ):
        await plugin.update()
    assert store.get("programlist")["data"] == []


async def test_update_handles_non_list_return(store, config):
    plugin = PluginModel(store, config)
    with patch(
        "glances.plugins.programlist.model_v5.glances_processes.get_list",
        return_value=None,
    ):
        await plugin.update()
    assert store.get("programlist")["data"] == []


# ---------------------------------------------------------- thresholds


async def test_cpu_percent_threshold_triggers_level(store, config):
    plugin = PluginModel(store, config)
    progs = [_program(name="hog", cpu_percent=95.0)]  # > critical (90)
    with patch(
        "glances.plugins.programlist.model_v5.glances_processes.get_list",
        return_value=progs,
    ):
        await plugin.update()
    levels = store.get("programlist")["_levels"]
    assert levels["hog"]["cpu_percent"]["level"] == "critical"
    assert levels["hog"]["cpu_percent"]["prominent"] is False

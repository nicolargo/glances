#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — unit tests for ``ProcessListModelBase`` (processlist / programlist)."""

from __future__ import annotations

import re
from unittest.mock import patch

import psutil
import pytest

from glances.config import GlancesConfig
from glances.plugins.processlist.list_base import ProcessListModelBase
from glances.plugins.processlist.model import PluginModel as ProcessModel
from glances.plugins.programlist.model import PluginModel as ProgramModel
from glances.stats_store import StatsStore

GET_LIST = "glances.processes.glances_processes.get_list"
MODELS = [ProcessModel, ProgramModel]


@pytest.fixture
def store() -> StatsStore:
    return StatsStore()


@pytest.fixture
def config(tmp_path, monkeypatch) -> GlancesConfig:
    monkeypatch.setattr(GlancesConfig, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    return GlancesConfig()


def _config_with(tmp_path, monkeypatch, body: str) -> GlancesConfig:
    monkeypatch.setattr(GlancesConfig, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    cfg_dir = tmp_path / "xdg" / "glances"
    cfg_dir.mkdir(parents=True)
    (cfg_dir / "glances.conf").write_text(body)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    return GlancesConfig()


# ---------------------------------------------------------- hierarchy


@pytest.mark.parametrize("model", MODELS)
def test_both_plugins_share_the_base(model):
    assert issubclass(model, ProcessListModelBase)


def test_base_requires_the_engine_hook(store, config):
    plugin = ProcessModel(store, config)
    with pytest.raises(NotImplementedError):
        ProcessListModelBase._get_engine_list(plugin)


def test_each_plugin_asks_the_engine_for_its_own_view(store, config):
    with patch(GET_LIST, return_value=[]) as mocked:
        ProcessModel(store, config)._get_engine_list()
        mocked.assert_called_once_with()
    with patch(GET_LIST, return_value=[]) as mocked:
        ProgramModel(store, config)._get_engine_list()
        mocked.assert_called_once_with(as_programs=True)


# ---------------------------------------------------------- _grab_stats


@pytest.mark.parametrize("model", MODELS)
async def test_grab_stats_copies_each_entry(model, store, config):
    rows = [{"name": "a"}, {"name": "b"}]
    with patch(GET_LIST, return_value=rows):
        out = await model(store, config)._grab_stats()
    assert out == rows
    out[0]["name"] = "MUTATED"
    assert rows[0]["name"] == "a"


@pytest.mark.parametrize("model", MODELS)
async def test_grab_stats_drops_non_dict_entries(model, store, config):
    with patch(GET_LIST, return_value=[{"name": "a"}, None, "x", 3]):
        out = await model(store, config)._grab_stats()
    assert out == [{"name": "a"}]


@pytest.mark.parametrize("model", MODELS)
@pytest.mark.parametrize("value", [None, {"name": "a"}, "text"])
async def test_grab_stats_non_list_gives_empty(model, value, store, config):
    with patch(GET_LIST, return_value=value):
        assert await model(store, config)._grab_stats() == []


@pytest.mark.parametrize("model", MODELS)
async def test_grab_stats_engine_error_gives_empty(model, store, config):
    with patch(GET_LIST, side_effect=RuntimeError("boom")):
        assert await model(store, config)._grab_stats() == []


# ---------------------------------------------------------- [processlist] options


@pytest.mark.parametrize("model", MODELS)
def test_no_export_patterns_by_default(model, store, config):
    plugin = model(store, config)
    assert plugin._export_patterns == []
    assert plugin.get_export() == []


@pytest.mark.parametrize("model", MODELS)
def test_both_plugins_read_the_processlist_section(model, tmp_path, monkeypatch, store):
    cfg = _config_with(tmp_path, monkeypatch, "[processlist]\nexport=python.*\ndisable_virtual_memory=True\n")
    plugin = model(store, cfg)
    assert [p.pattern for p in plugin._export_patterns] == ["python.*"]
    assert plugin._disable_virtual_memory is True


@pytest.mark.parametrize("model", MODELS)
def test_metadata_carries_core_count_and_virt_flag(model, store, config):
    plugin = model(store, config)
    plugin._add_metadata()
    assert plugin._metadata["cpucore"] == (psutil.cpu_count(logical=True) or 1)
    assert plugin._metadata["disable_virtual_memory"] is False


# ---------------------------------------------------------- _matches_export


@pytest.mark.parametrize(
    ("item", "expected"),
    [
        ({"name": "python3"}, True),
        ({"name": "bash", "cmdline": ["/usr/bin/python3", "app.py"]}, True),
        ({"name": "bash", "cmdline": "python3 app.py"}, True),
        ({"name": "bash", "cmdline": None}, False),
        ({"name": "bash", "cmdline": ["bash"]}, False),
        ({}, False),
    ],
)
def test_matches_export_checks_name_and_cmdline(item, expected, store, config):
    plugin = ProcessModel(store, config)
    plugin._export_patterns = [re.compile("python")]
    assert plugin._matches_export(item) is expected

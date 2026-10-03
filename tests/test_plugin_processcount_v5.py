#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — unit tests for the ``processcount`` plugin (scalar)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from glances.config_v5 import GlancesConfigV5
from glances.plugins.processcount.model_v5 import PluginModel
from glances.stats_store_v5 import StatsStoreV5


@pytest.fixture
def store() -> StatsStoreV5:
    return StatsStoreV5()


@pytest.fixture
def config(tmp_path, monkeypatch) -> GlancesConfigV5:
    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    return GlancesConfigV5()


# ---------------------------------------------------------- contract


def test_plugin_identity(store, config):
    plugin = PluginModel(store, config)
    assert plugin.plugin_name == "processcount"
    assert plugin.IS_COLLECTION is False


def test_schema_fields(store, config):
    fields = PluginModel(store, config)._fields
    for name in ("total", "running", "sleeping", "thread", "pid_max"):
        assert name in fields, name
        # None of them are watched — pure aggregate counts.
        assert fields[name].get("watched", False) is False, name


# ---------------------------------------------------------- update pipeline


async def test_update_calls_engine_and_surfaces_count(store, config):
    """``_grab_stats`` triggers ``engine.update()`` and returns the aggregate."""
    plugin = PluginModel(store, config)
    fake_count = {"total": 42, "running": 5, "sleeping": 30, "thread": 100, "pid_max": 32768}
    with (
        patch("glances.plugins.processcount.model_v5.glances_processes.update") as upd,
        patch(
            "glances.plugins.processcount.model_v5.glances_processes.get_count",
            return_value=fake_count,
        ),
    ):
        await plugin.update()
        assert upd.called
    payload = store.get("processcount")
    assert payload["total"] == 42
    assert payload["running"] == 5
    assert payload["sleeping"] == 30
    assert payload["thread"] == 100
    assert payload["pid_max"] == 32768


async def test_update_returns_copy_of_engine_dict(store, config):
    """Mutating the stored payload must not affect the engine's internal state."""
    plugin = PluginModel(store, config)
    engine_dict = {"total": 1, "running": 0, "sleeping": 1, "thread": 1, "pid_max": 32768}
    with (
        patch("glances.plugins.processcount.model_v5.glances_processes.update"),
        patch(
            "glances.plugins.processcount.model_v5.glances_processes.get_count",
            return_value=engine_dict,
        ),
    ):
        await plugin.update()
    stored = store.get("processcount")
    stored["total"] = 999
    # The engine's source dict must be untouched.
    assert engine_dict["total"] == 1


async def test_update_handles_engine_failure(store, config):
    """If the engine raises, the plugin yields an empty payload (no crash)."""
    plugin = PluginModel(store, config)
    with patch(
        "glances.plugins.processcount.model_v5.glances_processes.update",
        side_effect=RuntimeError("psutil fault"),
    ):
        await plugin.update()
    payload = store.get("processcount")
    # Empty dict from grab_stats → no declared fields surface (filter strips them).
    for name in ("total", "running", "sleeping", "thread", "pid_max"):
        assert name not in payload, name


async def test_update_handles_get_count_non_dict(store, config):
    """Defensive: if engine.get_count() returns junk, fall back to empty."""
    plugin = PluginModel(store, config)
    with (
        patch("glances.plugins.processcount.model_v5.glances_processes.update"),
        patch(
            "glances.plugins.processcount.model_v5.glances_processes.get_count",
            return_value=None,
        ),
    ):
        await plugin.update()
    payload = store.get("processcount")
    for name in ("total", "running", "sleeping", "thread", "pid_max"):
        assert name not in payload, name


# ------------------------------------------ the live sort key (shared sort)


async def _update_with_sort(plugin, key, auto):
    count = {"total": 1, "running": 0, "sleeping": 1, "thread": 1, "pid_max": 32768}
    with (
        patch("glances.plugins.processcount.model_v5.glances_processes.update"),
        patch("glances.plugins.processcount.model_v5.glances_processes.get_count", return_value=count),
        patch("glances.plugins.processcount.model_v5.glances_processes._sort_key", key),
        patch("glances.plugins.processcount.model_v5.glances_processes.auto_sort", auto),
    ):
        await plugin.update()


async def test_the_live_sort_key_is_published(store, config):
    """The key this cycle's list was sorted with -- what the WebUI underlines
    and what a client TUI follows."""
    plugin = PluginModel(store, config)
    await _update_with_sort(plugin, "memory_percent", False)
    payload = plugin.get_api_payload()
    assert payload["sort_key"] == "memory_percent"
    assert payload["auto_sort"] is False


async def test_the_auto_sort_flag_is_published(store, config):
    plugin = PluginModel(store, config)
    await _update_with_sort(plugin, "cpu_percent", True)
    payload = plugin.get_api_payload()
    assert payload["sort_key"] == "cpu_percent"
    assert payload["auto_sort"] is True


async def test_the_sort_key_is_not_exported(store, config):
    """A string column in InfluxDB/CSV would be noise: API yes, export no."""
    plugin = PluginModel(store, config)
    await _update_with_sort(plugin, "name", False)
    export = plugin.get_export()
    assert "sort_key" not in export
    assert "auto_sort" not in export
    assert export["total"] == 1


# ---------------------------------------------------------- real-host cycle


async def test_real_host_counts_are_consistent(store, config):
    """One unpatched update on the real machine: the counts must hold together."""
    await PluginModel(store, config).update()
    payload = store.get("processcount")
    assert payload["total"] > 0
    for name in ("total", "running", "sleeping", "thread"):
        assert payload[name] >= 0, name
    assert payload["running"] + payload["sleeping"] <= payload["total"]
    assert payload["thread"] >= payload["total"]

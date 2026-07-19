#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — unit tests for the `connections` plugin."""

from __future__ import annotations

from collections import namedtuple
from unittest.mock import patch

import psutil
import pytest

from glances.config_v5 import GlancesConfigV5
from glances.plugins.connections.model_v5 import PluginModel
from glances.stats_store_v5 import StatsStoreV5

FakeConn = namedtuple("FakeConn", ["status"])


# ---------------------------------------------------------- fixtures


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


# ---------------------------------------------------------- identity / schema


def test_plugin_identity(store, config):
    plugin = PluginModel(store, config)
    assert plugin.plugin_name == "connections"
    assert plugin.IS_COLLECTION is False
    assert plugin.EMITS_ALERTS is True


def test_fields_description_keys():
    assert set(PluginModel.fields_description.keys()) == {
        "net_connections_enabled",
        "nf_conntrack_enabled",
        "LISTEN",
        "ESTABLISHED",
        "initiated",
        "terminated",
        "nf_conntrack_count",
        "nf_conntrack_max",
        "nf_conntrack_percent",
    }


def test_only_nf_conntrack_percent_is_watched():
    assert [k for k, v in PluginModel.fields_description.items() if v.get("watched")] == ["nf_conntrack_percent"]


def test_nf_conntrack_percent_default_thresholds():
    assert PluginModel.fields_description["nf_conntrack_percent"]["default_thresholds"] == {
        "careful": 70.0,
        "warning": 80.0,
        "critical": 90.0,
    }


# ---------------------------------------------------------- approved bug fix


def test_initiated_and_terminated_states_are_distinct():
    assert PluginModel.initiated_states != PluginModel.terminated_states
    assert set(PluginModel.initiated_states).isdisjoint(set(PluginModel.terminated_states))


async def test_terminated_computed_from_terminated_states_not_initiated(store, config, monkeypatch):
    plugin = PluginModel(store, config)
    monkeypatch.setattr(plugin, "_is_enabled", lambda: True)
    conns = [
        FakeConn(psutil.CONN_LISTEN),
        FakeConn(psutil.CONN_LISTEN),
        FakeConn(psutil.CONN_ESTABLISHED),
        FakeConn(psutil.CONN_SYN_SENT),
        FakeConn(psutil.CONN_TIME_WAIT),
        FakeConn(psutil.CONN_TIME_WAIT),
        FakeConn(psutil.CONN_CLOSE_WAIT),
    ]
    with patch("glances.plugins.connections.model_v5.psutil.net_connections", return_value=conns):
        stats = await plugin._grab_stats()
    assert stats["LISTEN"] == 2
    assert stats["ESTABLISHED"] == 1
    assert stats["initiated"] == 1  # one SYN_SENT
    assert stats["terminated"] == 3  # two TIME_WAIT + one CLOSE_WAIT
    assert stats["terminated"] != stats["initiated"]


# ---------------------------------------------------------- disabled by default


async def test_disabled_by_default_returns_empty(store, config):
    plugin = PluginModel(store, config)
    with patch("glances.plugins.connections.model_v5.psutil.net_connections") as mock_nc:
        assert await plugin._grab_stats() == {}
    mock_nc.assert_not_called()


async def test_enabled_via_config_collects(tmp_path, monkeypatch, store):
    config = _config_with(tmp_path, monkeypatch, "[connections]\ndisable=False\n")
    plugin = PluginModel(store, config)
    with patch("glances.plugins.connections.model_v5.psutil.net_connections", return_value=[]):
        stats = await plugin._grab_stats()
    assert stats["net_connections_enabled"] is True
    assert stats["LISTEN"] == 0


# ---------------------------------------------------------- per-cycle retry


async def test_net_connections_failure_is_retried_next_cycle(tmp_path, monkeypatch, store):
    config = _config_with(tmp_path, monkeypatch, "[connections]\ndisable=False\n")
    plugin = PluginModel(store, config)

    with patch("glances.plugins.connections.model_v5.psutil.net_connections", side_effect=OSError("boom")) as mock_nc:
        stats1 = await plugin._grab_stats()
    assert stats1["net_connections_enabled"] is False
    assert "LISTEN" not in stats1
    assert mock_nc.call_count == 1

    # Second cycle: the call must be retried and, now that it works, the
    # plugin must fully recover. A latched flag would fail all three
    # assertions below.
    with patch(
        "glances.plugins.connections.model_v5.psutil.net_connections",
        return_value=[FakeConn(psutil.CONN_LISTEN)],
    ) as mock_nc2:
        stats2 = await plugin._grab_stats()
    assert mock_nc2.call_count == 1
    assert stats2["net_connections_enabled"] is True
    assert stats2["LISTEN"] == 1


async def test_nf_conntrack_failure_is_retried_next_cycle(tmp_path, monkeypatch, store):
    """The real-world case: the nf_conntrack module is loaded AFTER
    Glances starts. v4 recovers; v5 must too."""
    config = _config_with(tmp_path, monkeypatch, "[connections]\ndisable=False\n")
    plugin = PluginModel(store, config)
    count_file = tmp_path / "count"
    max_file = tmp_path / "max"
    plugin.conntrack_paths = {"nf_conntrack_count": str(count_file), "nf_conntrack_max": str(max_file)}

    with patch("glances.plugins.connections.model_v5.psutil.net_connections", return_value=[]):
        stats1 = await plugin._grab_stats()
    assert stats1["nf_conntrack_enabled"] is False
    assert "nf_conntrack_count" not in stats1

    # The conntrack counters appear (module loaded) — next cycle must
    # pick them up.
    count_file.write_text("10\n")
    max_file.write_text("100\n")
    with patch("glances.plugins.connections.model_v5.psutil.net_connections", return_value=[]):
        stats2 = await plugin._grab_stats()
    assert stats2["nf_conntrack_enabled"] is True
    assert stats2["nf_conntrack_count"] == 10.0
    assert stats2["nf_conntrack_percent"] == 10.0


async def test_enabled_flags_are_not_instance_state(tmp_path, monkeypatch, store):
    """Structural guard: the flags must live only in the payload, never on
    the instance — an attribute is how a latch would creep back in.

    This must run a real collection cycle FIRST: a regression that hoists
    the flags onto `self` lazily (only on/after the first `_collect()`)
    would pass a check performed before any cycle ran. Compare the
    instance's attribute set before and after to catch that.
    """
    config = _config_with(tmp_path, monkeypatch, "[connections]\ndisable=False\n")
    plugin = PluginModel(store, config)
    before = set(vars(plugin))

    with patch(
        "glances.plugins.connections.model_v5.psutil.net_connections",
        return_value=[FakeConn(psutil.CONN_LISTEN)],
    ):
        await plugin._grab_stats()

    after = set(vars(plugin))
    assert after == before, f"collection cycle hoisted new instance attributes: {after - before}"
    assert not hasattr(plugin, "_net_connections_enabled")
    assert not hasattr(plugin, "_nf_conntrack_enabled")


# ---------------------------------------------------------- conntrack edge cases


async def test_absent_conntrack_files_yield_valid_payload(tmp_path, monkeypatch, store):
    config = _config_with(tmp_path, monkeypatch, "[connections]\ndisable=False\n")
    plugin = PluginModel(store, config)
    plugin.conntrack_paths = {
        "nf_conntrack_count": str(tmp_path / "nope_count"),
        "nf_conntrack_max": str(tmp_path / "nope_max"),
    }
    with patch("glances.plugins.connections.model_v5.psutil.net_connections", return_value=[]):
        stats = await plugin._grab_stats()  # must not raise
    assert stats["nf_conntrack_enabled"] is False
    assert "nf_conntrack_percent" not in stats


async def test_nf_conntrack_max_zero_no_crash_no_percent(tmp_path, monkeypatch, store):
    config = _config_with(tmp_path, monkeypatch, "[connections]\ndisable=False\n")
    plugin = PluginModel(store, config)
    count_file = tmp_path / "count"
    max_file = tmp_path / "max"
    count_file.write_text("10\n")
    max_file.write_text("0\n")
    plugin.conntrack_paths = {"nf_conntrack_count": str(count_file), "nf_conntrack_max": str(max_file)}
    with patch("glances.plugins.connections.model_v5.psutil.net_connections", return_value=[]):
        stats = await plugin._grab_stats()  # must not raise ZeroDivisionError
    assert stats["nf_conntrack_enabled"] is True
    assert stats["nf_conntrack_max"] == 0.0
    assert "nf_conntrack_percent" not in stats


# ---------------------------------------------------------- thresholds / _levels


@pytest.mark.parametrize(
    "count, max_, expected_level",
    [
        (10, 100, "ok"),
        (70, 100, "careful"),
        (80, 100, "warning"),
        (90, 100, "critical"),
        (99, 100, "critical"),
    ],
)
async def test_nf_conntrack_percent_default_thresholds_drive_level(
    tmp_path, monkeypatch, store, count, max_, expected_level
):
    config = _config_with(tmp_path, monkeypatch, "[connections]\ndisable=False\n")
    plugin = PluginModel(store, config)
    count_file = tmp_path / "count"
    max_file = tmp_path / "max"
    count_file.write_text(f"{count}\n")
    max_file.write_text(f"{max_}\n")
    plugin.conntrack_paths = {"nf_conntrack_count": str(count_file), "nf_conntrack_max": str(max_file)}
    with patch("glances.plugins.connections.model_v5.psutil.net_connections", return_value=[]):
        await plugin.update()
    entry = store.get("connections")["_levels"]["nf_conntrack_percent"]
    assert entry["level"] == expected_level
    assert entry["prominent"] is False


async def test_only_nf_conntrack_percent_is_levelled(tmp_path, monkeypatch, store):
    config = _config_with(tmp_path, monkeypatch, "[connections]\ndisable=False\n")
    plugin = PluginModel(store, config)
    count_file = tmp_path / "count"
    max_file = tmp_path / "max"
    count_file.write_text("10\n")
    max_file.write_text("100\n")
    plugin.conntrack_paths = {"nf_conntrack_count": str(count_file), "nf_conntrack_max": str(max_file)}
    with patch(
        "glances.plugins.connections.model_v5.psutil.net_connections",
        return_value=[FakeConn(psutil.CONN_LISTEN)],
    ):
        await plugin.update()
    levels = store.get("connections")["_levels"]
    assert list(levels.keys()) == ["nf_conntrack_percent"]


# ---------------------------------------------------------- export


async def test_get_export_strips_internals(tmp_path, monkeypatch, store):
    config = _config_with(tmp_path, monkeypatch, "[connections]\ndisable=False\n")
    plugin = PluginModel(store, config)
    with patch(
        "glances.plugins.connections.model_v5.psutil.net_connections",
        return_value=[FakeConn(psutil.CONN_LISTEN)],
    ):
        await plugin.update()
    exported = plugin.get_export()
    assert "_levels" not in exported
    assert "time_since_update" not in exported
    assert exported["LISTEN"] == 1

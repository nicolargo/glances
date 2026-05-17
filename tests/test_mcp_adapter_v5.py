#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Unit tests for the v5 → MCP duck-typed adapter (G3-MCP Task 1).

The adapter exposes the v4-``GlancesStats``-style surface that
``GlancesMcpServer`` consumes (``getPluginsList``, ``get_plugin(name)``,
``getAllAsDict``, ``getAllLimitsAsDict``) on top of v5's
``StatsStoreV5`` + plugin registry + ``GlancesAlerts``. The MCP class
itself remains untouched.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, ClassVar

import pytest

from glances.alerts_v5 import GlancesAlerts
from glances.config_v5 import GlancesConfigV5
from glances.outputs import mcp_adapter_v5
from glances.outputs.mcp_adapter_v5 import McpPluginView, McpStatsAdapter
from glances.plugins.plugin.base_v5 import GlancesPluginBase
from glances.stats_store_v5 import StatsStoreV5


@pytest.fixture(autouse=True)
def _reset_history_warn_throttle():
    """The history-WARN throttle is module-global — reset between tests
    so per-test WARN-once assertions are deterministic."""
    mcp_adapter_v5._HISTORY_WARN_SEEN.clear()
    yield
    mcp_adapter_v5._HISTORY_WARN_SEEN.clear()


# ---------------------------------------------------------------- helpers


class _CpuStub(GlancesPluginBase[dict]):
    """Minimal scalar plugin used as a registry fixture."""

    plugin_name: ClassVar[str] = "cpu"
    IS_COLLECTION: ClassVar[bool] = False

    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "total": {
            "unit": "percent",
            "watched": True,
            "prominent": True,
            "default_thresholds": {"careful": 50.0, "warning": 70.0, "critical": 90.0},
        },
        "user": {"unit": "percent"},
    }

    async def _grab_stats(self) -> dict:  # not used in these tests
        return {}


class _NetStub(GlancesPluginBase[list]):
    """Minimal collection plugin (primary_key = interface_name)."""

    plugin_name: ClassVar[str] = "network"
    IS_COLLECTION: ClassVar[bool] = True

    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "interface_name": {"unit": "string", "primary_key": True},
        "bytes_recv": {
            "unit": "bytespers",
            "rate": True,
            "watched": True,
            "prominent": True,
            "default_thresholds": {"careful": 0.7, "warning": 0.8, "critical": 0.9},
        },
    }

    async def _grab_stats(self) -> list:
        return []


@pytest.fixture
def config(tmp_path, monkeypatch) -> GlancesConfigV5:
    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "no-system.conf")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    return GlancesConfigV5()


@pytest.fixture
def store_with_data(config) -> StatsStoreV5:
    store = StatsStoreV5()
    asyncio.run(store.set("cpu", {"total": 12.5, "user": 8.0}))
    asyncio.run(store.set("network", [{"interface_name": "eth0", "bytes_recv": 100.0}]))
    return store


@pytest.fixture
def plugins(config, store_with_data) -> list[GlancesPluginBase]:
    return [_CpuStub(store_with_data, config), _NetStub(store_with_data, config)]


@pytest.fixture
def alerts(config) -> GlancesAlerts:
    return GlancesAlerts(config)


@pytest.fixture
def adapter(store_with_data, plugins, alerts) -> McpStatsAdapter:
    return McpStatsAdapter(store=store_with_data, plugins=plugins, alerts=alerts)


# ---------------------------------------------------------------- plugin enumeration


def test_get_plugins_list_returns_registered_names(adapter):
    """getPluginsList covers the v5 plugin registry — synthetic 'alert' included."""
    names = adapter.getPluginsList()
    assert "cpu" in names
    assert "network" in names
    # 'alert' is synthetic — exposed even though it is not a real plugin.
    assert "alert" in names


def test_get_all_as_dict_returns_store_snapshot(adapter, store_with_data):
    """getAllAsDict mirrors StatsStoreV5.as_dict()."""
    all_stats = adapter.getAllAsDict()
    assert all_stats["cpu"] == store_with_data.get("cpu")
    assert all_stats["network"] == store_with_data.get("network")


# ---------------------------------------------------------------- get_plugin / get_raw


def test_get_plugin_returns_view_for_known_plugin(adapter):
    view = adapter.get_plugin("cpu")
    assert view is not None
    assert isinstance(view, McpPluginView)


def test_get_plugin_returns_none_for_unknown(adapter):
    """Plugin not in v5 registry → None (MCP raises 'Plugin not found').

    Use a synthetic name here — every real v4 plugin is ported as of
    G4-processlist, so we can no longer pick a "definitely unported"
    name from the v4 catalogue. The adapter must still return ``None``
    for anything outside the registry.
    """
    assert adapter.get_plugin("no_such_plugin") is None
    assert adapter.get_plugin("") is None


def test_plugin_view_get_raw_returns_store_value(adapter, store_with_data):
    view = adapter.get_plugin("cpu")
    raw = view.get_raw()
    assert raw == store_with_data.get("cpu")


def test_collection_plugin_view_get_raw_returns_list(adapter, store_with_data):
    view = adapter.get_plugin("network")
    raw = view.get_raw()
    assert raw == store_with_data.get("network")
    assert isinstance(raw, list)


# ---------------------------------------------------------------- limits


def test_plugin_view_get_limits_aggregates_default_thresholds(adapter):
    """get_limits walks fields_description for `default_thresholds`."""
    limits = adapter.get_plugin("cpu").get_limits()
    # `total` has thresholds; `user` does not. Only `total` keys present.
    assert "total" in limits
    assert limits["total"] == {"careful": 50.0, "warning": 70.0, "critical": 90.0}
    assert "user" not in limits


def test_get_all_limits_as_dict_covers_every_plugin(adapter):
    """getAllLimitsAsDict returns one entry per real plugin (alert excluded)."""
    all_limits = adapter.getAllLimitsAsDict()
    assert "cpu" in all_limits
    assert "network" in all_limits
    # The synthetic 'alert' plugin has no thresholds — not reported.
    assert "alert" not in all_limits
    assert all_limits["cpu"]["total"]["warning"] == 70.0


# ---------------------------------------------------------------- history (deferred)


def test_plugin_view_get_raw_history_returns_empty_for_scalar(adapter):
    """v5 has no history yet — adapter returns {} per the design contract."""
    view = adapter.get_plugin("cpu")
    assert view.get_raw_history() == {}


def test_plugin_view_get_raw_history_emits_warn_once(adapter, caplog):
    """Each plugin emits the WARN once to avoid log spam on repeated MCP polls."""
    view = adapter.get_plugin("cpu")
    with caplog.at_level(logging.WARNING):
        view.get_raw_history()
        view.get_raw_history()
        view.get_raw_history()
    warns = [r for r in caplog.records if r.levelno == logging.WARNING and "history" in r.message]
    assert len(warns) == 1
    assert "cpu" in warns[0].message


def test_plugin_view_history_warn_is_per_plugin(adapter, caplog):
    """Per-plugin throttling: cpu's WARN does not silence network's."""
    with caplog.at_level(logging.WARNING):
        adapter.get_plugin("cpu").get_raw_history()
        adapter.get_plugin("network").get_raw_history()
    targets = [r.message for r in caplog.records if r.levelno == logging.WARNING and "history" in r.message]
    assert any("cpu" in m for m in targets)
    assert any("network" in m for m in targets)


# ---------------------------------------------------------------- synthetic 'alert' plugin


def test_get_plugin_alert_returns_view_even_without_registry_entry(adapter):
    """'alert' is synthetic — must yield a non-None view even though it is not
    in the plugin registry."""
    view = adapter.get_plugin("alert")
    assert view is not None


def test_alert_view_get_raw_returns_alerts_history_list(adapter, alerts):
    """alert.get_raw() forwards GlancesAlerts.get_history() — v5-native schema."""
    raw = adapter.get_plugin("alert").get_raw()
    assert raw == alerts.get_history()
    assert isinstance(raw, list)


def test_alert_view_get_limits_is_empty(adapter):
    """The synthetic alert view carries no thresholds."""
    assert adapter.get_plugin("alert").get_limits() == {}


# ---------------------------------------------------------------- defensive


def test_get_plugin_none_when_name_is_empty_string(adapter):
    assert adapter.get_plugin("") is None

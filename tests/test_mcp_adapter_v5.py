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
import json
import logging
from typing import Any, ClassVar

import pytest

from glances.alerts_v5 import GlancesAlerts
from glances.config_v5 import GlancesConfigV5
from glances.history_v5 import HistoryStoreV5
from glances.outputs.mcp_adapter_v5 import McpPluginView, McpStatsAdapter
from glances.plugins.plugin.base_v5 import GlancesPluginBase
from glances.stats_store_v5 import StatsStoreV5

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
            "history": True,
            "watched": True,
            "prominent": True,
            "default_thresholds": {"careful": 0.7, "warning": 0.8, "critical": 0.9},
        },
        "secret": {"unit": "string", "exportable": False},
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
    # Envelope shape, as written by GlancesPluginBase._build_store_payload():
    # a collection plugin stores {"data": [...], "_levels": {...}, metadata}.
    # It never stores a bare list -- verified against the real plugin set.
    asyncio.run(
        store.set(
            "network",
            {
                "data": [{"interface_name": "eth0", "bytes_recv": 100.0, "secret": "hunter2"}],
                "time_since_update": 2.0,
                "_levels": {},
            },
        )
    )
    return store


@pytest.fixture
def plugins(config, store_with_data) -> list[GlancesPluginBase]:
    return [_CpuStub(store_with_data, config), _NetStub(store_with_data, config)]


@pytest.fixture
def alerts(config) -> GlancesAlerts:
    return GlancesAlerts(config)


@pytest.fixture
def adapter(store_with_data, plugins, alerts) -> McpStatsAdapter:
    return McpStatsAdapter(plugins=plugins, alerts=alerts)


# ---------------------------------------------------------------- plugin enumeration


def test_get_plugins_list_returns_registered_names(adapter):
    """getPluginsList covers the v5 plugin registry — synthetic 'alert' included."""
    names = adapter.getPluginsList()
    assert "cpu" in names
    assert "network" in names
    # 'alert' is synthetic — exposed even though it is not a real plugin.
    assert "alert" in names


def test_get_all_as_dict_returns_every_plugin_payload(adapter, store_with_data):
    """getAllAsDict serves each plugin's filtered view (issue #3211), keyed by
    plugin name. It used to mirror StatsStoreV5.as_dict(), which handed MCP
    clients the raw payload including fields the exporters withhold."""
    all_stats = adapter.getAllAsDict()

    assert all_stats["cpu"] == store_with_data.get("cpu")
    assert all_stats["network"]["data"] == [{"interface_name": "eth0", "bytes_recv": 100.0}]


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


def test_collection_plugin_view_get_raw_returns_the_envelope(adapter, store_with_data):
    """A collection plugin's payload is the `{"data": [...]}` envelope, not a
    bare list: that is what _build_store_payload() writes and what the REST API
    serves. This test previously asserted a list, which the fixture produced by
    writing the store directly -- a shape no plugin can actually publish."""
    view = adapter.get_plugin("network")

    raw = view.get_raw()

    assert isinstance(raw, dict)
    assert raw["data"] == [{"interface_name": "eth0", "bytes_recv": 100.0}]
    assert "_levels" in raw


# ---------------------------------------------------------------- limits


def test_plugin_view_get_limits_aggregates_default_thresholds(adapter):
    """get_limits delegates to GlancesPluginBase.get_limits(), which layers
    config over each field's `default_thresholds`."""
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


# ---------------------------------------------------------------- history


def test_plugin_view_history_is_empty_without_a_store(adapter, caplog):
    """History disabled (no store attached): an empty columnar payload, and
    no WARNING -- the gap the adapter used to log is closed."""
    with caplog.at_level(logging.WARNING):
        assert adapter.get_plugin("cpu").get_raw_history() == {"timestamps": [], "series": {}}
    assert not [r for r in caplog.records if r.levelno >= logging.WARNING]


def test_plugin_view_history_is_the_rest_payload(adapter, plugins):
    """Same shape as /api/5/<plugin>/history: one helper serves both."""
    net = plugins[1]
    net.history = HistoryStoreV5(10)
    net.history.record(
        "network", [{"interface_name": "eth0", "bytes_recv": 5.0}], ["bytes_recv"], "interface_name", now=1.0
    )
    expected = {"timestamps": [1.0], "series": {"bytes_recv": {"eth0": [5.0]}}}
    assert adapter.get_plugin("network").get_raw_history() == expected == net.get_history()


def test_plugin_view_history_unknown_item_is_empty(adapter, plugins):
    net = plugins[1]
    net.history = HistoryStoreV5(10)
    net.history.record(
        "network", [{"interface_name": "eth0", "bytes_recv": 5.0}], ["bytes_recv"], "interface_name", now=1.0
    )
    assert adapter.get_plugin("network").get_raw_history(item="nope") == {"timestamps": [], "series": {}}


def test_synthetic_alert_plugin_history_is_empty(adapter):
    assert adapter.get_plugin("alert").get_raw_history() == {"timestamps": [], "series": {}}


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


# ---------------------------------------------------------------- limits


class _ConfigurableStub(GlancesPluginBase[dict]):
    """Scalar plugin whose thresholds can be overridden from config."""

    plugin_name: ClassVar[str] = "configurable"
    IS_COLLECTION: ClassVar[bool] = False

    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "total": {
            "unit": "percent",
            "watched": True,
            "watch_direction": "high",
            "default_thresholds": {"careful": 50.0, "warning": 70.0, "critical": 90.0},
        },
    }

    async def _grab_stats(self) -> dict:
        return {"total": 1.0}


def test_get_all_limits_reflects_a_config_override(store_with, config_with):
    """Regression guard: the adapter used to aggregate `default_thresholds`
    straight from the schema, so `glances://limits` reported the shipped
    default even when the operator had overridden it."""
    config = config_with({"configurable": {"total_warning": "42"}})
    store = store_with()
    plugin = _ConfigurableStub(store, config)
    adapter = McpStatsAdapter(plugins=[plugin])
    assert adapter.getAllLimitsAsDict()["configurable"]["total"]["warning"] == 42.0


def test_get_plugin_limits_reflects_a_config_override(store_with, config_with):
    config = config_with({"configurable": {"total_critical": "99"}})
    store = store_with()
    plugin = _ConfigurableStub(store, config)
    adapter = McpStatsAdapter(plugins=[plugin])
    view = adapter.get_plugin("configurable")
    assert view is not None
    assert view.get_limits()["total"]["critical"] == 99.0


def test_synthetic_alert_plugin_has_no_limits():
    adapter = McpStatsAdapter(plugins=[])
    view = adapter.get_plugin("alert")
    assert view is not None
    assert view.get_limits() == {}


# ------------------------------------------------- export filter (issue #3211)


def test_mcp_plugin_view_drops_non_exportable_fields(adapter, store_with_data):
    """An MCP client is a consumer like any other: leaving it on the raw store
    payload recreated exactly the inconsistency #3211 is about."""
    assert any("secret" in i for i in store_with_data.get("network")["data"]), "guard: the fixture must publish it"

    raw = adapter.get_plugin("network").get_raw()

    assert all("secret" not in item for item in raw["data"])
    assert "_levels" in raw


def test_mcp_all_drops_non_exportable_fields(adapter):
    payload = adapter.getAllAsDict()

    assert all("secret" not in item for item in payload["network"]["data"])


def test_mcp_synthetic_plugin_still_bypasses_the_filter(adapter):
    """`alert` has no real plugin behind it — it must keep working."""
    payload = adapter.get_plugin("alert").get_raw()

    assert isinstance(payload, list)


def test_mcp_no_longer_reads_the_store(adapter):
    """Structural guard for #3211: the facade holds no store reference at all,
    so no future edit can quietly reintroduce a raw read."""
    assert not hasattr(adapter, "_store")
    assert not hasattr(adapter.get_plugin("network"), "_store")


# ------------------------------------------------- v4 MCP server on the v5 facade


class _ProcStub(GlancesPluginBase[list]):
    """Minimal processlist collection plugin (primary_key = pid)."""

    plugin_name: ClassVar[str] = "processlist"
    IS_COLLECTION: ClassVar[bool] = True

    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "pid": {"unit": "number", "primary_key": True},
        "name": {"unit": "string"},
        "cpu_percent": {"unit": "percent"},
    }

    async def _grab_stats(self) -> list:
        return [
            {"pid": 1, "name": "idle", "cpu_percent": 0.5},
            {"pid": 2, "name": "busy", "cpu_percent": 90.0},
            {"pid": 3, "name": "mid", "cpu_percent": 40.0},
        ]


def test_top_processes_prompt_accepts_the_collection_envelope(config):
    """`top_processes_report` sorts get_raw() as a process list; the v5 facade
    serves the `{"data": [...]}` envelope, which crashed the prompt with
    `'str' object has no attribute 'get'` once processlist had published."""
    pytest.importorskip("mcp")
    from glances.outputs.glances_mcp import GlancesMcpServer

    store = StatsStoreV5()
    proc = _ProcStub(store, config)
    asyncio.run(proc.update())
    server = GlancesMcpServer(stats=McpStatsAdapter(plugins=[proc]), args=None, config=config)

    result = asyncio.run(server._mcp.get_prompt("top_processes_report", {"nb": "2"}))

    text = result.messages[0].content.text
    top = text[text.index("[") :]
    assert [p["name"] for p in json.loads(top)] == ["busy", "mid"]

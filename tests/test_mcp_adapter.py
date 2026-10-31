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
``StatsStore`` + plugin registry + ``GlancesAlerts``. The MCP class
itself remains untouched.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, ClassVar

import pytest

from glances.alerts import GlancesAlerts
from glances.config import GlancesConfig
from glances.history import HistoryStore
from glances.outputs.mcp_adapter import McpPluginView, McpStatsAdapter
from glances.plugins.plugin.base import GlancesPluginBase
from glances.stats_store import StatsStore

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
def config(tmp_path, monkeypatch) -> GlancesConfig:
    monkeypatch.setattr(GlancesConfig, "SYSTEM_CONFIG_PATH", tmp_path / "no-system.conf")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    return GlancesConfig()


@pytest.fixture
def store_with_data(config) -> StatsStore:
    store = StatsStore()
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
    plugin name. It used to mirror StatsStore.as_dict(), which handed MCP
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
    net.history = HistoryStore(10)
    net.history.record(
        "network", [{"interface_name": "eth0", "bytes_recv": 5.0}], ["bytes_recv"], "interface_name", now=1.0
    )
    expected = {"timestamps": [1.0], "series": {"bytes_recv": {"eth0": [5.0]}}}
    assert adapter.get_plugin("network").get_raw_history() == expected == net.get_history()


def test_plugin_view_history_unknown_item_is_an_error(adapter, plugins):
    """An unknown item is a KeyError, as REST answers 404: an empty payload
    hid a typo in the item name. Only the history tool passes an item."""
    net = plugins[1]
    net.history = HistoryStore(10)
    net.history.record(
        "network", [{"interface_name": "eth0", "bytes_recv": 5.0}], ["bytes_recv"], "interface_name", now=1.0
    )
    with pytest.raises(KeyError):
        adapter.get_plugin("network").get_raw_history(item="nope")


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

    store = StatsStore()
    proc = _ProcStub(store, config)
    asyncio.run(proc.update())
    server = GlancesMcpServer(stats=McpStatsAdapter(plugins=[proc]), args=None, config=config)

    result = asyncio.run(server._mcp.get_prompt("top_processes_report", {"nb": "2"}))

    text = result.messages[0].content.text
    top = text[text.index("[") :]
    assert [p["name"] for p in json.loads(top)] == ["busy", "mid"]


@pytest.fixture
def mcp_server(adapter, config):
    pytest.importorskip("mcp")
    from glances.outputs.glances_mcp import GlancesMcpServer

    return GlancesMcpServer(stats=adapter, args=None, config=config)


def test_mcp_lists_the_resources_and_templates(mcp_server):
    """v4 `test_mcp` 010/011, over the v5 facade instead of a live server."""
    uris = [str(r.uri) for r in asyncio.run(mcp_server._mcp.list_resources())]
    # Wire (camelCase) names: MCP SDK >= 2 renamed the attributes to snake_case.
    raw_templates = asyncio.run(mcp_server._mcp.list_resource_templates())
    templates = {t.model_dump(by_alias=True)["uriTemplate"] for t in raw_templates}
    assert {"glances://plugins", "glances://stats", "glances://limits"} <= set(uris)
    assert {"glances://stats/{plugin}", "glances://stats/{plugin}/history", "glances://limits/{plugin}"} <= templates


def test_mcp_lists_the_four_prompts(mcp_server):
    names = [p.name for p in asyncio.run(mcp_server._mcp.list_prompts())]
    assert {"system_health_summary", "alert_analysis", "top_processes_report", "storage_health"} <= set(names)


def test_system_health_prompt_carries_the_payloads(mcp_server):
    result = asyncio.run(mcp_server._mcp.get_prompt("system_health_summary"))
    text = result.messages[0].content.text
    assert "Glances" in text
    assert '"cpu"' in text and "12.5" in text


class _HotCpu(_CpuStub):
    async def _grab_stats(self) -> dict:
        return {"total": 95.0, "user": 90.0}


def test_alert_analysis_prompt_takes_the_level_over_alerts(config, monkeypatch):
    """v4 `test_mcp::test_022`: a real critical alert from the v5 engine."""
    pytest.importorskip("mcp")
    from glances.outputs.glances_mcp import GlancesMcpServer

    monkeypatch.setenv("GLANCES_ALERTS__WARMUP_CYCLES", "0")
    monkeypatch.setenv("GLANCES_ALERTS__MIN_DURATION_SECONDS", "0")
    config = GlancesConfig()
    cpu = _HotCpu(StatsStore(), config)
    alerts = GlancesAlerts(config)

    async def one_cycle():
        await cpu.update()
        await alerts.ingest_plugin(cpu)

    asyncio.run(one_cycle())
    server = GlancesMcpServer(stats=McpStatsAdapter(plugins=[cpu], alerts=alerts), args=None, config=config)

    result = asyncio.run(server._mcp.get_prompt("alert_analysis", {"level": "critical"}))

    text = result.messages[0].content.text
    assert "severity filter: 'critical'" in text
    payload = json.loads(text[text.index("{") :])
    [incident] = payload["incidents"]
    assert (incident["plugin"], incident["field"], incident["level"]) == ("cpu", "total", "critical")
    assert incident["ongoing"] is True


def _root_message(exc: BaseException) -> str:
    """The handler's own message: the MCP SDK wraps it in a generic error."""
    while exc.__cause__ is not None:
        exc = exc.__cause__
    return str(exc)


def _hot_cpu_server(config_factory, monkeypatch, *, history_size=None):
    """A v5 MCP server whose engine holds one ongoing critical cpu.total alert."""
    from glances.outputs.glances_mcp import GlancesMcpServer

    monkeypatch.setenv("GLANCES_ALERTS__WARMUP_CYCLES", "0")
    monkeypatch.setenv("GLANCES_ALERTS__MIN_DURATION_SECONDS", "0")
    config = config_factory()
    cpu = _HotCpu(StatsStore(), config)
    alerts = GlancesAlerts(config)

    async def one_cycle():
        await cpu.update()
        await alerts.ingest_plugin(cpu)

    asyncio.run(one_cycle())
    return GlancesMcpServer(stats=McpStatsAdapter(plugins=[cpu], alerts=alerts), args=None, config=config), alerts


def test_alert_analysis_reports_an_alert_the_history_has_evicted(monkeypatch):
    """F1: the prompt used to feed the bounded transition log as "active alerts".
    Once the opening event aged out of the ring buffer, an ongoing alert
    vanished from the prompt and the LLM was told the system was healthy."""
    pytest.importorskip("mcp")
    server, alerts = _hot_cpu_server(GlancesConfig, monkeypatch)
    alerts._history.clear()  # the opening transition has been evicted
    assert alerts.get_ongoing(), "guard: the engine must still hold the alert"

    result = asyncio.run(server._mcp.get_prompt("alert_analysis", {}))

    text = result.messages[0].content.text
    payload = json.loads(text[text.index("{") :])
    assert [(i["plugin"], i["level"], i["ongoing"]) for i in payload["incidents"]] == [("cpu", "critical", True)]


def test_alert_analysis_level_filter_is_applied(monkeypatch):
    """F1: `level` used to be interpolated in the text and never applied."""
    pytest.importorskip("mcp")
    server, _ = _hot_cpu_server(GlancesConfig, monkeypatch)

    result = asyncio.run(server._mcp.get_prompt("alert_analysis", {"level": "warning"}))

    text = result.messages[0].content.text
    assert json.loads(text[text.index("{") :])["incidents"] == []


def test_alert_analysis_rejects_an_unknown_level(monkeypatch):
    pytest.importorskip("mcp")
    server, _ = _hot_cpu_server(GlancesConfig, monkeypatch)

    with pytest.raises(Exception) as exc_info:
        asyncio.run(server._mcp.get_prompt("alert_analysis", {"level": "bogus"}))
    assert "level" in _root_message(exc_info.value)


def test_alert_incidents_resource_matches_the_rest_route(monkeypatch):
    """`glances://alerts/incidents` serves the `/api/5/alert/incidents` envelope."""
    pytest.importorskip("mcp")
    from glances.alerts_incidents import incidents_payload

    server, alerts = _hot_cpu_server(GlancesConfig, monkeypatch)

    [content] = asyncio.run(server._mcp.read_resource("glances://alerts/incidents"))

    assert json.loads(content.content) == json.loads(json.dumps(incidents_payload(alerts)))


def test_alert_incidents_without_an_alerts_pipeline_is_an_error(config):
    """No alerts pipeline: an explicit error, as REST answers 404. An empty
    envelope would read as an all-clear."""
    pytest.importorskip("mcp")
    from glances.outputs.glances_mcp import GlancesMcpServer

    assert McpStatsAdapter(plugins=[]).get_alert_incidents() is None
    server = GlancesMcpServer(stats=McpStatsAdapter(plugins=[]), args=None, config=config)
    with pytest.raises(Exception) as exc_info:
        asyncio.run(server._mcp.read_resource("glances://alerts/incidents"))
    assert "disabled" in _root_message(exc_info.value)
    with pytest.raises(Exception) as exc_info:
        asyncio.run(server._mcp.get_prompt("alert_analysis", {}))
    assert "disabled" in _root_message(exc_info.value)


# ------------------------------------------------- F2: field schema (/info)


def test_plugin_view_info_is_the_rest_schema(adapter, plugins):
    """Same source as /api/5/<plugin>/info: the plugin's fields_description."""
    assert adapter.get_plugin("network").get_info() == plugins[1].fields_description


def test_synthetic_alert_view_has_no_schema(adapter):
    assert adapter.get_plugin("alert").get_info() == {}


def test_all_info_covers_every_real_plugin(adapter, plugins):
    """Same as /api/5/all/info: every registered plugin, published or not."""
    assert adapter.getAllInfoAsDict() == {p.plugin_name: p.fields_description for p in plugins}


def test_mcp_serves_the_info_resources(mcp_server, plugins):
    [content] = asyncio.run(mcp_server._mcp.read_resource("glances://info/cpu"))
    assert json.loads(content.content) == json.loads(json.dumps(plugins[0].fields_description))

    [content] = asyncio.run(mcp_server._mcp.read_resource("glances://info"))
    assert set(json.loads(content.content)) == {"cpu", "network"}


def test_mcp_info_unknown_plugin_is_an_error(mcp_server):
    with pytest.raises(Exception) as exc_info:
        asyncio.run(mcp_server._mcp.read_resource("glances://info/nope"))
    assert "not found" in _root_message(exc_info.value)


# ------------------------------------------------- F4: /all contract


def test_get_all_as_dict_skips_unpublished_plugins(config, store_with_data):
    """Same contract as /api/5/all: a registered plugin with no payload yet
    (scheduler cycle 0) is absent, not present with an empty body."""
    unpublished = _ConfigurableStub(store_with_data, config)  # nothing in the store
    adapter = McpStatsAdapter(plugins=[_CpuStub(store_with_data, config), unpublished])

    assert set(adapter.getAllAsDict()) == {"cpu"}


# ------------------------------------------------- F3 / F5: tools


def _call_tool(server, name, arguments):
    """Call an MCP tool; return (is_error, text)."""
    result = asyncio.run(server._mcp.call_tool(name, arguments))
    # SDK >= 2 returns a CallToolResult, 1.x a (content, structured) tuple.
    if isinstance(result, tuple):
        return False, result[0][0].text
    return bool(result.is_error), result.content[0].text


def _call_tool_json(server, name, arguments):
    is_error, text = _call_tool(server, name, arguments)
    assert not is_error, text
    return json.loads(text)


def _tool_error(server, name, arguments) -> str:
    """The error a tool raises, as the MCP client sees it."""
    try:
        is_error, text = _call_tool(server, name, arguments)
    except Exception as exc:  # SDK 1.x raises ToolError
        return str(exc)
    assert is_error, text
    return text


def test_mcp_lists_the_tools(mcp_server):
    names = {t.name for t in asyncio.run(mcp_server._mcp.list_tools())}
    assert names == {"get_plugin_history", "get_plugin_field", "get_plugin_top", "get_plugin_items_by_value"}


@pytest.fixture
def net_history(plugins):
    net = plugins[1]
    net.history = HistoryStore(10)
    for ts, value in ((1.0, 5.0), (2.0, 6.0)):
        net.history.record(
            "network", [{"interface_name": "eth0", "bytes_recv": value}], ["bytes_recv"], "interface_name", now=ts
        )
    return net


def test_history_tool_applies_nb_field_and_item(mcp_server, net_history):
    """F3: the resource serves everything; the tool takes the REST filters."""
    payload = _call_tool_json(mcp_server, "get_plugin_history", {"plugin": "network", "nb": 1, "item": "eth0"})
    assert (
        payload
        == net_history.get_history(nb=1, item="eth0")
        == {
            "timestamps": [2.0],
            "series": {"bytes_recv": {"eth0": [6.0]}},
        }
    )
    payload = _call_tool_json(mcp_server, "get_plugin_history", {"plugin": "network", "field": "bytes_recv"})
    assert payload["timestamps"] == [1.0, 2.0]


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        ({"plugin": "nope"}, "not found"),
        ({"plugin": "network", "field": "secret"}, "secret"),
        ({"plugin": "network", "item": "wlan9"}, "wlan9"),
        ({"plugin": "network", "nb": -1}, "nb"),
    ],
)
def test_history_tool_errors_are_explicit(mcp_server, net_history, arguments, message):
    assert message in _tool_error(mcp_server, "get_plugin_history", arguments)


def test_field_tool_matches_the_rest_routes(mcp_server):
    """F5: `/<plugin>/<field>` and `/<plugin>/<field>/<pk>`."""
    assert _call_tool_json(mcp_server, "get_plugin_field", {"plugin": "cpu", "field": "total"}) == {"total": 12.5}
    assert _call_tool_json(mcp_server, "get_plugin_field", {"plugin": "network", "field": "bytes_recv"}) == {
        "bytes_recv": [100.0]
    }
    assert _call_tool_json(
        mcp_server, "get_plugin_field", {"plugin": "network", "field": "bytes_recv", "item": "eth0"}
    ) == {"bytes_recv": 100.0}


def test_top_and_value_tools_match_the_rest_routes(mcp_server):
    """F5: `/<plugin>/top/<n>` and `/<plugin>/<field>/value/<v>`."""
    row = {"interface_name": "eth0", "bytes_recv": 100.0}
    assert _call_tool_json(mcp_server, "get_plugin_top", {"plugin": "network", "n": 1}) == [row]
    assert _call_tool_json(
        mcp_server, "get_plugin_items_by_value", {"plugin": "network", "field": "interface_name", "value": "eth0"}
    ) == {"eth0": [row]}


@pytest.mark.parametrize(
    ("name", "arguments", "message"),
    [
        ("get_plugin_field", {"plugin": "cpu", "field": "nope"}, "not found"),
        ("get_plugin_field", {"plugin": "network", "field": "secret"}, "not found"),
        ("get_plugin_field", {"plugin": "network", "field": "bytes_recv", "item": "wlan9"}, "wlan9"),
        ("get_plugin_top", {"plugin": "cpu", "n": 1}, "has no items"),
        ("get_plugin_top", {"plugin": "network", "n": 0}, "n must be"),
        ("get_plugin_top", {"plugin": "alert", "n": 1}, "has no items"),
        ("get_plugin_items_by_value", {"plugin": "nope", "field": "a", "value": "b"}, "not found"),
    ],
)
def test_query_tool_errors_are_explicit(mcp_server, name, arguments, message):
    assert message in _tool_error(mcp_server, name, arguments)


def test_query_tools_return_null_before_the_first_cycle(config):
    """Cycle 0: `null`, as the REST field routes answer."""
    pytest.importorskip("mcp")
    from glances.outputs.glances_mcp import GlancesMcpServer

    proc = _ProcStub(StatsStore(), config)  # never updated
    server = GlancesMcpServer(stats=McpStatsAdapter(plugins=[proc]), args=None, config=config)
    assert _call_tool_json(server, "get_plugin_top", {"plugin": "processlist", "n": 1}) is None

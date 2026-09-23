#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — unit tests for the ``processlist`` plugin (collection)."""

from __future__ import annotations

import asyncio
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


def test_processlist_opts_out_of_alerts(store, config):
    """processlist colours cells but must NOT emit alerts events / actions.

    v4 never paged on individual processes; v5 mirrors this — `_levels` is
    computed for the renderer only. See base ``EMITS_ALERTS`` doc."""
    assert PluginModel.EMITS_ALERTS is False


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
    """`status_critical=Z,D` should mark zombies as critical.

    Values explicitly listed in ``status_ok`` get a level=ok entry. Values
    in NO bucket (here: 'S') get **no** entry — the renderer keeps the
    default colour. Mirrors v4 ``get_alert`` returning ``'DEFAULT'`` for
    unmatched categorical values.
    """
    config = _config_with(
        tmp_path,
        monkeypatch,
        "[processlist]\nstatus_ok=R,W,P,I\nstatus_critical=Z,D\n",
    )
    plugin = PluginModel(store, config)
    procs = [
        _proc(pid=1, status="R"),
        _proc(pid=2, status="Z"),
        _proc(pid=3, status="S"),  # not in any bucket → no level entry
    ]
    with patch("glances.plugins.processlist.model_v5.glances_processes.get_list", return_value=procs):
        await plugin.update()
    levels = store.get("processlist")["_levels"]
    assert levels[1]["status"]["level"] == "ok"
    assert levels[2]["status"]["level"] == "critical"
    # pid 3 has no status entry (or no entry at all if no other watched
    # field fired) — the renderer falls back to DEFAULT colour.
    assert "status" not in levels.get(3, {})


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
    """`nice_warning=-1,1,...` flags non-zero nice values as warning.

    nice=0 stays default-coloured (no level entry) — listing it in
    ``nice_ok=0`` would be the way to force an explicit OK.
    """
    config = _config_with(
        tmp_path,
        monkeypatch,
        "[processlist]\nnice_warning=-1,1,2,3,4,5\n",
    )
    plugin = PluginModel(store, config)
    procs = [
        _proc(pid=1, nice=0),  # not in any list → no level entry
        _proc(pid=2, nice=3),  # in list → warning
        _proc(pid=3, nice=-1),  # in list → warning
    ]
    with patch("glances.plugins.processlist.model_v5.glances_processes.get_list", return_value=procs):
        await plugin.update()
    levels = store.get("processlist")["_levels"]
    assert "nice" not in levels.get(1, {})
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


# ---------------------------------------------------------- export gate (issue #794)


async def test_get_export_empty_by_default(store, config):
    """v4 parity: nothing is exported unless `[processlist] export` is set."""
    plugin = PluginModel(store, config)
    procs = [_proc(pid=1, name="python3"), _proc(pid=2, name="bash")]
    with patch("glances.plugins.processlist.model_v5.glances_processes.get_list", return_value=procs):
        await plugin.update()
    assert plugin.get_export() == []


async def test_get_export_does_not_affect_get_stats(store, config):
    """The gate only touches get_export() — get_stats()/the TUI stay full."""
    plugin = PluginModel(store, config)
    procs = [_proc(pid=1, name="python3"), _proc(pid=2, name="bash")]
    with patch("glances.plugins.processlist.model_v5.glances_processes.get_list", return_value=procs):
        await plugin.update()
    assert plugin.get_export() == []
    assert len(plugin.get_stats()["data"]) == 2


async def test_get_export_filters_by_name_when_configured(tmp_path, monkeypatch, store):
    config = _config_with(tmp_path, monkeypatch, "[processlist]\nexport=python.*\n")
    plugin = PluginModel(store, config)
    procs = [_proc(pid=1, name="python3"), _proc(pid=2, name="bash", cmdline=["bash"])]
    with patch("glances.plugins.processlist.model_v5.glances_processes.get_list", return_value=procs):
        await plugin.update()
    exported = plugin.get_export()
    assert [p["pid"] for p in exported] == [1]


async def test_get_export_filters_by_cmdline_when_configured(tmp_path, monkeypatch, store):
    config = _config_with(tmp_path, monkeypatch, "[processlist]\nexport=.*myscript.*\n")
    plugin = PluginModel(store, config)
    procs = [
        _proc(pid=1, name="python3", cmdline=["python3", "myscript.py"]),
        _proc(pid=2, name="bash", cmdline=["bash"]),
    ]
    with patch("glances.plugins.processlist.model_v5.glances_processes.get_list", return_value=procs):
        await plugin.update()
    exported = plugin.get_export()
    assert [p["pid"] for p in exported] == [1]


async def test_get_export_invalid_regex_ignored_with_warning(tmp_path, monkeypatch, store, caplog):
    config = _config_with(tmp_path, monkeypatch, "[processlist]\nexport=[invalid(\n")
    with caplog.at_level("WARNING"):
        plugin = PluginModel(store, config)
    assert any("invalid" in rec.message.lower() for rec in caplog.records)
    procs = [_proc(pid=1, name="python3")]
    with patch("glances.plugins.processlist.model_v5.glances_processes.get_list", return_value=procs):
        await plugin.update()
    # No usable pattern survived compilation → export stays empty (v4-safe default).
    assert plugin.get_export() == []


# ------------------------- the pinned process, as payload metadata (b3-web)


@pytest.fixture
def pin(monkeypatch):
    from glances.processes import glances_processes

    monkeypatch.setattr(glances_processes, "extended_pid", None, raising=False)
    monkeypatch.setattr(glances_processes, "extended_process", None, raising=False)
    return glances_processes


def _extended(pid=42, **over):
    base = {
        "pid": pid,
        "name": "hot",
        "extended_stats": True,
        "cpu_min": 1.0,
        "cpu_max": 9.0,
        "cpu_mean": 4.0,
        "memory_min": 1.0,
        "memory_max": 2.0,
        "memory_mean": 1.5,
        "cpu_affinity": [0, 1],
        "ionice": {"ioclass": 2, "value": 4},
        "memory_info": {"rss": 1024, "vms": 2048},
        "memory_swap": 0,
        "num_threads": 3,
        "num_fds": 7,
        "tcp": 1,
        "udp": 0,
        # Fields already in `data[]` for the same pid: must NOT be duplicated.
        "username": "alice",
        "cpu_percent": 4.0,
        "status": "S",
    }
    base.update(over)
    return base


@pytest.fixture
def plugin_and_store(store, config):
    """A processlist plugin whose engine grab returns one stable process.

    Patched at the engine boundary so these tests are about what the plugin
    PUBLISHES, not about what psutil happens to see."""
    with patch(
        "glances.plugins.processlist.model_v5.glances_processes.get_list",
        return_value=[_proc(pid=42), _proc(pid=7)],
    ):
        yield PluginModel(store, config), store


def _metadata_of(plugin, store):
    asyncio.run(plugin.update())
    return store.get("processlist", {})


def test_no_pin_publishes_no_extended_key(pin, plugin_and_store):
    """The key's PRESENCE is the signal, so it must be absent by default."""
    plugin, store = plugin_and_store
    assert "extended" not in _metadata_of(plugin, store)


def test_a_pinned_process_publishes_its_extended_stats(pin, plugin_and_store):
    plugin, store = plugin_and_store
    pin.extended_pid = 42
    pin.extended_process = _extended(42)

    extended = _metadata_of(plugin, store)["extended"]

    assert extended["pid"] == 42
    assert extended["name"] == "hot"
    assert extended["cpu_max"] == 9.0
    assert extended["ionice"] == {"ioclass": 2, "value": 4}


def test_only_the_extended_keys_are_published(pin, plugin_and_store):
    """The engine accumulates extended stats INTO the whole process dict.
    Publishing it whole would duplicate a dozen fields already in `data[]`."""
    plugin, store = plugin_and_store
    pin.extended_pid = 42
    pin.extended_process = _extended(42)

    extended = _metadata_of(plugin, store)["extended"]

    assert "username" not in extended
    assert "status" not in extended
    assert "cpu_percent" not in extended
    # And `cmdline` is not even offered: the engine has not added it yet when
    # it captures the accumulator. Measured against the live engine.
    assert "cmdline" not in PluginModel._EXTENDED_KEYS


def test_a_stale_accumulation_is_not_published(pin, plugin_and_store):
    """The cycle right after a pin still holds the PREVIOUS process' numbers.
    Publishing those under the new name is worse than publishing nothing."""
    plugin, store = plugin_and_store
    pin.extended_pid = 42
    pin.extended_process = _extended(7)  # the previous pin

    assert "extended" not in _metadata_of(plugin, store)


def test_unpinning_removes_the_key_from_the_payload(pin, plugin_and_store):
    """`_metadata` persists across cycles, so the key has to be actively
    removed — leaving it would freeze the block on screen forever."""
    plugin, store = plugin_and_store
    pin.extended_pid = 42
    pin.extended_process = _extended(42)
    assert "extended" in _metadata_of(plugin, store)

    pin.extended_pid = None
    pin.extended_process = None

    assert "extended" not in _metadata_of(plugin, store)


def test_exporters_never_see_it(pin, plugin_and_store):
    """`get_export()` returns the items, not the envelope — a time-series
    backend has no use for a UI pin."""
    plugin, store = plugin_and_store
    pin.extended_pid = 42
    pin.extended_process = _extended(42)
    asyncio.run(plugin.update())

    for item in plugin.get_export():
        assert "extended" not in item


def test_the_api_payload_carries_it(pin, plugin_and_store):
    """It has to survive `get_api_payload()`'s projection, or the browser
    would never see it — the same route `fs` publishes `free_space` by."""
    plugin, store = plugin_and_store
    pin.extended_pid = 42
    pin.extended_process = _extended(42)
    asyncio.run(plugin.update())

    assert plugin.get_api_payload()["extended"]["pid"] == 42


def test_the_published_payload_is_json_serialisable(pin, plugin_and_store):
    """`ionice.ioclass` is a psutil IntEnum in the live engine, not a plain
    int — and this payload goes out over the REST API."""
    import json

    import psutil

    plugin, store = plugin_and_store
    ioclass = getattr(psutil, "IOPRIO_CLASS_BE", 2)
    pin.extended_pid = 42
    pin.extended_process = _extended(42, ionice={"ioclass": ioclass, "value": 4})

    json.dumps(_metadata_of(plugin, store)["extended"])

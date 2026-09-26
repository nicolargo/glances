#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — the stats history store (design 2026-09-26, commit 1).

Covers the store alone (§5.3), the plugin feed (§5.2), the `history: True`
declarations (§4) and the configuration (§5.4).
"""

from __future__ import annotations

import ast
import importlib
import inspect
import logging
import textwrap

import pytest

from glances.config_v5 import GlancesConfigV5
from glances.history_v5 import DEFAULT_HISTORY_SIZE, HistoryStoreV5, resolve_history_size
from glances.plugins.plugin.base_v5 import GlancesPluginBase
from glances.stats_store_v5 import StatsStoreV5

# ------------------------------------------------------------------ the store


def _rec(h, stats, fields=("rx",), pk="name", now=0.0, plugin="p"):
    h.record(plugin, stats, list(fields), pk, now=now)


def test_scalar_plugin_series_is_a_flat_list():
    h = HistoryStoreV5(10)
    h.record("mem", {"percent": 41.2, "total": 8}, ["percent"], now=1.0)
    h.record("mem", {"percent": 41.5, "total": 8}, ["percent"], now=3.0)
    assert h.get("mem") == {"timestamps": [1.0, 3.0], "series": {"percent": [41.2, 41.5]}}


def test_collection_series_nest_by_field_then_raw_item():
    """No `<item>_<field>` flattening: `/home` and `sda1_read` stay addressable."""
    h = HistoryStoreV5(10)
    h.record(
        "fs",
        [{"mnt_point": "/home", "percent": 50.0}, {"mnt_point": "/", "percent": 10.0}],
        ["percent"],
        "mnt_point",
        now=1.0,
    )
    assert h.get("fs")["series"] == {"percent": {"/home": [50.0], "/": [10.0]}}


def test_a_late_series_is_left_padded_to_stay_aligned():
    h = HistoryStoreV5(10)
    _rec(h, [{"name": "eth0", "rx": 1.0}], now=1.0)
    _rec(h, [{"name": "eth0", "rx": 2.0}, {"name": "wlan0", "rx": 5.0}], now=2.0)
    out = h.get("p")
    assert out["timestamps"] == [1.0, 2.0]
    assert out["series"]["rx"] == {"eth0": [1.0, 2.0], "wlan0": [None, 5.0]}


def test_an_absent_series_gets_none_for_that_cycle():
    h = HistoryStoreV5(10)
    _rec(h, [{"name": "eth0", "rx": 1.0}, {"name": "wlan0", "rx": 5.0}], now=1.0)
    _rec(h, [{"name": "eth0", "rx": 2.0}], now=2.0)
    assert h.get("p")["series"]["rx"]["wlan0"] == [5.0, None]


def test_a_series_expires_once_every_point_is_none_and_not_a_cycle_earlier():
    h = HistoryStoreV5(3)
    _rec(h, [{"name": "eth0", "rx": 1.0}, {"name": "gone", "rx": 9.0}], now=0.0)
    for t in (1.0, 2.0):
        _rec(h, [{"name": "eth0", "rx": 1.0}], now=t)
    # Two idle cycles out of three: its first point is still in the window.
    assert h.get("p")["series"]["rx"]["gone"] == [9.0, None, None]
    _rec(h, [{"name": "eth0", "rx": 1.0}], now=3.0)
    assert "gone" not in h.get("p")["series"]["rx"]


def test_a_returning_item_starts_a_new_padded_series():
    h = HistoryStoreV5(2)
    _rec(h, [{"name": "a", "rx": 1.0}, {"name": "b", "rx": 1.0}], now=0.0)
    for t in (1.0, 2.0):
        _rec(h, [{"name": "a", "rx": 1.0}], now=t)
    _rec(h, [{"name": "a", "rx": 1.0}, {"name": "b", "rx": 7.0}], now=3.0)
    assert h.get("p")["series"]["rx"]["b"] == [None, 7.0]


def test_the_oldest_point_is_evicted_at_maxlen():
    h = HistoryStoreV5(3)
    for t in range(5):
        h.record("mem", {"percent": float(t)}, ["percent"], now=float(t))
    assert h.get("mem") == {"timestamps": [2.0, 3.0, 4.0], "series": {"percent": [2.0, 3.0, 4.0]}}


def test_nb_slices_the_axis_and_every_series_together():
    h = HistoryStoreV5(10)
    for t in range(4):
        _rec(h, [{"name": "eth0", "rx": float(t)}], now=float(t))
    out = h.get("p", nb=2)
    assert out == {"timestamps": [2.0, 3.0], "series": {"rx": {"eth0": [2.0, 3.0]}}}
    assert h.get("p", nb=0) == h.get("p", nb=99) == h.get("p")


def test_only_numbers_are_recorded():
    """A list (v4's quicklook.percpu) or a bool is not a measurement."""
    h = HistoryStoreV5(10)
    h.record(
        "q",
        {"cpu": 5.0, "percpu": [{"total": 1}], "flag": True, "n": 3, "none": None},
        ["cpu", "percpu", "flag", "n", "none"],
        now=1.0,
    )
    assert h.get("q")["series"] == {"cpu": [5.0], "n": [3]}


def test_a_series_starting_with_none_is_created_on_its_first_value():
    """Cycle 1 of a rate field is None: no series yet, and no misalignment later."""
    h = HistoryStoreV5(10)
    _rec(h, [{"name": "eth0", "rx": None}], now=1.0)
    assert h.get("p")["series"] == {}
    _rec(h, [{"name": "eth0", "rx": 3.0}], now=2.0)
    assert h.get("p") == {"timestamps": [1.0, 2.0], "series": {"rx": {"eth0": [None, 3.0]}}}


def test_get_returns_copies():
    h = HistoryStoreV5(10)
    h.record("mem", {"percent": 1.0}, ["percent"], now=1.0)
    h.get("mem")["series"]["percent"].append(99)
    assert h.get("mem")["series"]["percent"] == [1.0]


def test_an_unknown_plugin_is_empty_not_an_error():
    assert HistoryStoreV5(10).get("nope") == {"timestamps": [], "series": {}}


def test_a_disabled_history_is_no_store_at_all():
    with pytest.raises(ValueError):
        HistoryStoreV5(0)


def test_record_never_awaits():
    """Synchronous by design: a reader on the same event loop can never see
    half a cycle (§5.2)."""
    source = textwrap.dedent(inspect.getsource(HistoryStoreV5.record))
    tree = ast.parse(source)
    assert isinstance(tree.body[0], ast.FunctionDef)
    assert not any(isinstance(node, ast.Await) for node in ast.walk(tree))


# ------------------------------------------------------------- configuration


@pytest.fixture
def config_with(tmp_path, monkeypatch):
    def make(body: str = "") -> GlancesConfigV5:
        monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
        cfg_dir = tmp_path / "xdg" / "glances"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        (cfg_dir / "glances.conf").write_text(body)
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
        return GlancesConfigV5()

    return make


def test_history_size_defaults_to_1200(config_with):
    assert DEFAULT_HISTORY_SIZE == 1200
    assert resolve_history_size(config_with()) == 1200


def test_history_size_is_read_from_global(config_with):
    assert resolve_history_size(config_with("[global]\nhistory_size=60\n")) == 60


def test_history_size_zero_or_the_flag_disables(config_with):
    assert resolve_history_size(config_with("[global]\nhistory_size=0\n")) == 0
    assert resolve_history_size(config_with("[global]\nhistory_size=60\n"), disable_history=True) == 0


@pytest.mark.parametrize("value", ["-5", "lots"])
def test_an_invalid_history_size_warns_and_falls_back(value, config_with, caplog):
    with caplog.at_level(logging.WARNING, logger="glances.history_v5"):
        assert resolve_history_size(config_with(f"[global]\nhistory_size={value}\n")) == 1200
    assert "history_size" in caplog.text


def test_alerts_history_size_is_not_read(config_with):
    """`[alerts] history_size` sizes the alert ring buffer, not this."""
    assert resolve_history_size(config_with("[alerts]\nhistory_size=5\n")) == 1200


# ----------------------------------------------------------- the plugin feed


class _FakeCollection(GlancesPluginBase[list]):
    plugin_name = "fakehist"
    IS_COLLECTION = True
    fields_description = {
        "name": {"description": "n", "unit": "string", "primary_key": True},
        "rx": {"description": "r", "unit": "bytespers", "history": True},
        "size": {"description": "s", "unit": "bytes"},
    }

    def __init__(self, store, config, payload=None, fail=False):
        super().__init__(store, config)
        self.payload = payload or [{"name": "eth0", "rx": 10.0, "size": 1}]
        self.fail = fail

    async def _grab_stats(self) -> list:
        if self.fail:
            raise RuntimeError("psutil exploded")
        return [dict(item) for item in self.payload]


@pytest.fixture
def config(config_with):
    return config_with()


async def test_a_cycle_records_what_rest_serves(config):
    plugin = _FakeCollection(StatsStoreV5(), config)
    plugin.history = HistoryStoreV5(10)
    await plugin.update()
    served = plugin.get_api_payload()["data"]
    assert plugin.history.get("fakehist")["series"] == {"rx": {"eth0": [served[0]["rx"]]}}


async def test_only_history_fields_are_recorded(config):
    plugin = _FakeCollection(StatsStoreV5(), config)
    plugin.history = HistoryStoreV5(10)
    await plugin.update()
    assert list(plugin.history.get("fakehist")["series"]) == ["rx"]


async def test_a_failed_cycle_records_nothing(config):
    plugin = _FakeCollection(StatsStoreV5(), config, fail=True)
    plugin.history = HistoryStoreV5(10)
    await plugin.update()  # swallowed by update(), as ever
    assert plugin.history.get("fakehist") == {"timestamps": [], "series": {}}


async def test_no_store_records_nothing_and_raises_nothing(config):
    plugin = _FakeCollection(StatsStoreV5(), config)
    assert plugin.history is None
    await plugin.update()
    assert plugin.get_api_payload()["data"]


# --------------------------------------------------- the §4 declarations

# v4's `items_history_list`, mapped to v5 names (design §4). Pinned: a flag
# added or dropped later is a deliberate edit of this table.
_HISTORISED = {
    "cpu": ["system", "user"],
    "percpu": ["system", "user"],
    "load": ["min1", "min15", "min5"],
    "mem": ["percent"],
    "memswap": ["percent"],
    "processcount": ["running", "sleeping", "thread", "total"],
    "quicklook": ["cpu", "gpu_mem", "gpu_proc", "load", "mem", "swap"],
    "network": ["bytes_recv", "bytes_sent"],
    "diskio": ["read_bytes", "write_bytes"],
    "fs": ["percent"],
    "gpu": ["mem", "proc"],
    "npu": ["freq", "load", "mem"],
    "mpp": ["load"],
    "containers": ["cpu_percent"],
    "vms": ["memory_usage"],
}


def _all_plugin_models():
    from glances.main_v5 import discover_plugin_classes

    return {cls.plugin_name: cls for _name, cls in discover_plugin_classes()}


def test_the_historised_fields_are_v4s_items_history_list():
    declared = {
        name: sorted(f for f, spec in cls.fields_description.items() if spec.get("history"))
        for name, cls in _all_plugin_models().items()
    }
    assert {name: fields for name, fields in declared.items() if fields} == _HISTORISED


def test_no_historised_field_is_a_string():
    for name, fields in _HISTORISED.items():
        schema = _all_plugin_models()[name].fields_description
        for field in fields:
            assert schema[field].get("unit") != "string", f"{name}.{field}"


_LOCAL = ["cpu", "percpu", "load", "mem", "memswap", "processcount", "quicklook", "network", "diskio", "fs"]


@pytest.mark.parametrize("plugin_name", _LOCAL)
async def test_a_real_cycle_publishes_numbers_for_every_historised_field(plugin_name, config):
    """Against this host's real psutil payload: a declared field that turns
    out not to be a number would be silently dropped by the store."""
    module = importlib.import_module(f"glances.plugins.{plugin_name}.model_v5")
    plugin = module.PluginModel(StatsStoreV5(), config)
    await plugin.update()
    await plugin.update()
    payload = plugin.get_api_payload()
    rows = payload.get("data", []) if plugin.IS_COLLECTION else [payload]
    for row in rows:
        for field in _HISTORISED[plugin_name]:
            if field in row:
                value = row[field]
                assert value is None or (isinstance(value, (int, float)) and not isinstance(value, bool)), (
                    f"{plugin_name}.{field} = {value!r}"
                )

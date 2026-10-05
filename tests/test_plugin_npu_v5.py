#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — unit tests for the `npu` plugin (collection)."""

from __future__ import annotations

from pathlib import Path

import pytest

from glances.config_v5 import GlancesConfigV5
from glances.plugins.npu.cards.amd import AmdNPU
from glances.plugins.npu.cards.intel import IntelNPU
from glances.plugins.npu.cards.rockchip import RockchipNPU
from glances.plugins.npu.model_v5 import PluginModel
from glances.stats_store_v5 import StatsStoreV5


@pytest.fixture
def store() -> StatsStoreV5:
    return StatsStoreV5()


@pytest.fixture
def config(tmp_path, monkeypatch) -> GlancesConfigV5:
    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    return GlancesConfigV5()


class _FakeCard:
    def __init__(self, stats, available=True):
        self._stats = stats
        self._available = available
        self.disabled = False

    def is_available(self):
        return self._available

    def get_device_stats(self):
        return self._stats

    def disable(self):
        self.disabled = True
        self._available = False

    def exit(self):
        pass


class _BoomCard(_FakeCard):
    def get_device_stats(self):
        raise OSError("boom")


def _npu(npu_id="intel_1", name="NPU", load=45, freq=50):
    return {"npu_id": npu_id, "name": name, "load": load, "freq": freq, "mem": None}


def test_plugin_identity(store, config):
    p = PluginModel(store, config)
    assert p.plugin_name == "npu"
    assert p.IS_COLLECTION is True
    assert p._primary_key == "npu_id"


def test_fields_watched():
    fd = PluginModel.fields_description
    for key in ("load", "freq", "mem"):
        assert fd[key]["watched"] is True
    assert fd["npu_id"].get("primary_key") is True
    for key in ("freq_current", "freq_max", "power", "name"):
        assert fd[key].get("internal") is True


def test_npu_temperature_thresholds_mirror_v4():
    # v4 20555568: the temperature both interfaces already ask for must be
    # watched, with the same 60/70/80 ladder as [gpu].
    fd = PluginModel.fields_description["temperature"]
    assert fd["watched"] is True
    assert fd.get("internal") is not True
    assert fd["default_thresholds"] == {"careful": 60.0, "warning": 70.0, "critical": 80.0}


def test_temperature_level_warning_at_75(store, config):
    p = PluginModel(store, config)
    p._stats = [{"npu_id": "intel_1", "temperature": 75}]
    p._derived_parameters()
    assert p._levels["intel_1"]["temperature"]["level"] == "warning"


def test_temperature_level_ok_at_50(store, config):
    p = PluginModel(store, config)
    p._stats = [{"npu_id": "intel_1", "temperature": 50}]
    p._derived_parameters()
    assert p._levels["intel_1"]["temperature"]["level"] == "ok"


def test_temperature_critical_config_override_wins_over_default(store_with, config_with):
    config = config_with({"npu": {"temperature_critical": "50"}})
    p = PluginModel(store_with(), config)
    p._stats = [{"npu_id": "intel_1", "temperature": 55}]
    p._derived_parameters()
    assert p._levels["intel_1"]["temperature"]["level"] == "critical"


def test_temperature_none_gets_no_temperature_level(store, config):
    # AMD/Rockchip cards report no temperature: no decoration for that field.
    p = PluginModel(store, config)
    p._stats = [{"npu_id": "amd_1", "load": 20, "temperature": None}]
    p._derived_parameters()
    assert "temperature" not in p._levels.get("amd_1", {})


def test_load_freq_and_temperature_levels_in_one_pass(store, config):
    p = PluginModel(store, config)
    p._stats = [{"npu_id": "intel_1", "load": 95, "freq": 10, "temperature": 20}]
    p._derived_parameters()
    lv = p._levels["intel_1"]
    assert lv["load"]["level"] == "critical"
    assert lv["freq"]["level"] == "ok"
    assert lv["temperature"]["level"] == "ok"


@pytest.mark.asyncio
async def test_grab_stats_collects_available_cards(store, config, monkeypatch):
    p = PluginModel(store, config)
    p._backends = [_FakeCard(_npu("intel_1")), _FakeCard(_npu("amd_1"), available=False)]
    out = await p._grab_stats()
    assert [c["npu_id"] for c in out] == ["intel_1"]


@pytest.mark.asyncio
async def test_grab_stats_disables_card_on_error(store, config, monkeypatch):
    p = PluginModel(store, config)
    boom = _BoomCard(_npu("rockship_1"))
    p._backends = [boom]
    out = await p._grab_stats()
    assert out == []
    assert boom.disabled is True


def test_stop_calls_every_card_exit_even_if_one_raises(store, config):
    """v4 `exit()` closes each card on shutdown; one failing must not leave
    the others open."""
    calls = []

    class _Spy(_FakeCard):
        def __init__(self, error=None):
            super().__init__(None)
            self._error = error

        def exit(self):
            calls.append(self)
            if self._error:
                raise self._error

    p = PluginModel(store, config)
    p._backends = [_Spy(OSError("boom")), _Spy()]
    p.stop()
    assert calls == p._backends


def test_npu_disabled_by_default(config):
    # Mirror v4 [npu] disable=True — no user config present here. The gate
    # is generic: `main_v5.discover_plugins()` does not even instantiate a
    # plugin whose `is_disabled()` is True.
    assert PluginModel.DISABLED_BY_DEFAULT is True
    assert PluginModel.is_disabled(config) is True


# ---------------------------------------------------------- shared card drivers on tests-data
_NPU_DATA = Path(__file__).resolve().parent.parent / "tests-data" / "plugins" / "npu"


def _npu_expected(**kw):
    base = dict.fromkeys(
        ("load", "freq", "freq_current", "freq_max", "mem", "memory_used", "memory_total", "temperature", "power")
    )
    return {**base, **kw}


@pytest.mark.parametrize(
    ("vendor", "card_cls", "expected"),
    [
        (
            "amd",
            AmdNPU,
            _npu_expected(
                npu_id="amd_1", name="AMD NPU (Strix Point)", freq=53, freq_current=800000000, freq_max=1500000000
            ),
        ),
        (
            "intel",
            IntelNPU,
            _npu_expected(
                npu_id="intel_1",
                name="Intel NPU (Meteor Lake)",
                freq=57,
                freq_current=800000000,
                freq_max=1400000000,
                temperature=45.0,
                power=2.5,
            ),
        ),
        (
            "rockchip",
            RockchipNPU,
            _npu_expected(
                npu_id="rockship_1",
                name="Orange Pi 5 Plus",
                load=25,
                freq=60,
                freq_current=600000000,
                freq_max=1000000000,
            ),
        ),
    ],
)
@pytest.mark.asyncio
async def test_card_drivers_parse_tests_data(store, config, vendor, card_cls, expected):
    # Same expectations as v4 tests/test_core.py::test_025_npu, read through
    # the v5 collection path.
    card = card_cls(npu_root_folder=str(_NPU_DATA / vendor))
    p = PluginModel(store, config)
    p._backends = [card]
    out = await p._grab_stats()
    assert out[0] == expected

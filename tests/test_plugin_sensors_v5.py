#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the v5 sensors plugin model."""

from __future__ import annotations

import pytest

from glances.config_v5 import GlancesConfigV5
from glances.plugins.sensors.model_v5 import PluginModel
from glances.stats_store_v5 import StatsStoreV5


@pytest.fixture
def store() -> StatsStoreV5:
    return StatsStoreV5()


@pytest.fixture
def config(tmp_path, monkeypatch) -> GlancesConfigV5:
    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    return GlancesConfigV5()


def test_plugin_identity(store, config):
    p = PluginModel(store, config)
    assert p.plugin_name == "sensors"
    assert p.IS_COLLECTION is True
    assert p._primary_key == "label"


def test_fields_description_flags():
    fd = PluginModel.fields_description
    assert fd["label"]["primary_key"] is True
    assert fd["value"]["watched"] is True
    # Sensors alerts are coloured text only — no background highlight.
    assert fd["value"].get("prominent") is False
    assert "default_thresholds" not in fd["value"]
    for key in ("type", "unit", "warning", "critical", "status"):
        assert fd[key].get("internal") is True
        assert fd[key].get("watched", False) is False


class _FakeGrabber:
    """Stand-in for every sub-grabber: records its construction, collects nothing."""

    built: list = []

    def __init__(self, *args, **kwargs):
        type(self).built.append(args)

    def update(self):
        return []

    def get(self):
        return []


@pytest.fixture
def fake_grabbers(monkeypatch):
    from glances.plugins.sensors import model_v5

    _FakeGrabber.built = []
    for name in ("GlancesGrabSensors", "GlancesGrabHDDTemp", "GlancesGrabBat"):
        monkeypatch.setattr(model_v5, name, _FakeGrabber)
    return _FakeGrabber


def test_grabbers_are_not_built_at_init(store, config, fake_grabbers):
    """Constructing the plugin must not probe the hardware. `__init__` runs on
    the synchronous startup path, before the TUI paints its first frame, and
    building the temperature grabber alone calls `psutil.sensors_temperatures()`
    (~230 ms on a laptop). That cost belongs in `_collect()`, which already runs
    in a worker thread."""
    PluginModel(store, config)
    assert fake_grabbers.built == []


def test_grabbers_are_built_on_first_collect(store, config, fake_grabbers):
    p = PluginModel(store, config)
    p._collect()
    assert len(fake_grabbers.built) == 4  # cpu temp, fan, hddtemp, battery


def test_grabbers_are_built_only_once(store, config, fake_grabbers):
    p = PluginModel(store, config)
    p._collect()
    p._collect()
    assert len(fake_grabbers.built) == 4


@pytest.mark.asyncio
async def test_grab_stats_merges_all_types(store, config, monkeypatch):
    p = PluginModel(store, config)
    p._build_grabbers()  # lazily built on first collect — realise them to patch
    monkeypatch.setattr(
        p._grab_temp_core,
        "update",
        lambda: [{"label": "Core 0", "unit": "C", "value": 42, "warning": 80, "critical": 90}],
    )
    monkeypatch.setattr(p._grab_fan, "update", lambda: [{"label": "fan1", "unit": "R", "value": 1200}])
    monkeypatch.setattr(p._grab_hdd, "get", lambda: [{"label": "sda", "unit": "C", "value": 35}])

    def _bat():
        return [{"label": "Battery", "unit": "%", "value": 80, "status": "Charging"}]

    monkeypatch.setattr(p, "_grab_battery", _bat)

    rows = await p._grab_stats()
    by_label = {r["label"]: r for r in rows}
    assert by_label["Core 0"]["type"] == "temperature_core"
    assert by_label["Core 0"]["warning"] == 80
    assert by_label["fan1"]["type"] == "fan_speed"
    assert by_label["fan1"]["warning"] is None  # defaulted
    assert by_label["sda"]["type"] == "temperature_hdd"
    assert by_label["Battery"]["type"] == "battery"
    assert by_label["Battery"]["status"] == "Charging"


@pytest.mark.asyncio
async def test_grab_stats_survives_one_grabber_failure(store, config, monkeypatch):
    p = PluginModel(store, config)
    p._build_grabbers()  # lazily built on first collect — realise them to patch

    def _boom():
        raise OSError("boom")

    monkeypatch.setattr(p._grab_temp_core, "update", _boom)
    monkeypatch.setattr(p._grab_fan, "update", lambda: [{"label": "fan1", "unit": "R", "value": 1200}])
    monkeypatch.setattr(p._grab_hdd, "get", lambda: [])
    monkeypatch.setattr(p, "_grab_battery", lambda: [])

    rows = await p._grab_stats()
    assert [r["label"] for r in rows] == ["fan1"]  # temp core failed, fan survived


def _expand(p, rows):
    """Drive _expand_parameters against a given stats list."""
    p._stats = rows
    p._expand_parameters()
    return p._stats


def _cfg_with(tmp_path, monkeypatch, body: str) -> GlancesConfigV5:
    # Mirror tests/test_plugin_network_v5.py::_config_with — load a
    # [sensors] body via an XDG-discovered glances.conf.
    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    xdg = tmp_path / "xdg"
    cfg_dir = xdg / "glances"
    cfg_dir.mkdir(parents=True)
    (cfg_dir / "glances.conf").write_text(body)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    return GlancesConfigV5()


def test_alias_relabels(tmp_path, monkeypatch, store):
    config = _cfg_with(tmp_path, monkeypatch, "[sensors]\nalias=core 0:CPU Package\n")
    p = PluginModel(store, config)
    out = _expand(
        p,
        [{"label": "Core 0", "unit": "C", "value": 42, "warning": None, "critical": None, "type": "temperature_core"}],
    )
    assert out[0]["label"] == "CPU Package"


def _rows_core(*values):
    return [
        {"label": f"Core {i}", "unit": "C", "value": v, "warning": 80, "critical": 90, "type": "temperature_core"}
        for i, v in enumerate(values)
    ]


def test_fold_enabled_collapses_group(tmp_path, monkeypatch, store):
    config = _cfg_with(tmp_path, monkeypatch, "[sensors]\ntemperature_core_mean=true\n")
    p = PluginModel(store, config)
    out = _expand(p, _rows_core(40, 42, 44))
    assert len(out) == 1
    assert out[0]["label"] == "Core (mean)"
    assert out[0]["value"] == 42  # int(126/3 + 0.5)
    assert out[0]["warning"] == 80  # copied from first


def test_fold_disabled_keeps_rows(tmp_path, monkeypatch, store):
    config = _cfg_with(tmp_path, monkeypatch, "[sensors]\n")  # no mean key
    p = PluginModel(store, config)
    out = _expand(p, _rows_core(40, 42, 44))
    assert len(out) == 3
    assert {r["label"] for r in out} == {"Core 0", "Core 1", "Core 2"}


def test_fold_singleton_unchanged(tmp_path, monkeypatch, store):
    config = _cfg_with(tmp_path, monkeypatch, "[sensors]\ntemperature_core_mean=true\n")
    p = PluginModel(store, config)
    out = _expand(p, _rows_core(40))  # only Core 0
    assert len(out) == 1
    assert out[0]["label"] == "Core 0"  # not folded


def test_fold_excludes_non_numeric(tmp_path, monkeypatch, store):
    """A shared-prefix group with one ERR member: the numeric members fold,
    the non-numeric one is excluded from the mean and passes through."""
    config = _cfg_with(tmp_path, monkeypatch, "[sensors]\ntemperature_hdd_mean=true\n")
    p = PluginModel(store, config)
    rows = [
        {"label": "disk 0", "unit": "C", "value": 40, "warning": None, "critical": None, "type": "temperature_hdd"},
        {"label": "disk 1", "unit": "C", "value": 44, "warning": None, "critical": None, "type": "temperature_hdd"},
        {"label": "disk 2", "unit": "C", "value": "ERR", "warning": None, "critical": None, "type": "temperature_hdd"},
    ]
    out = _expand(p, rows)
    by_label = {r["label"]: r for r in out}
    # disk 0/1 (numeric) fold to one mean row; disk 2 (ERR) is excluded from
    # the mean and passes through unchanged.
    assert "disk (mean)" in by_label
    assert by_label["disk (mean)"]["value"] == 42  # int((40+44)/2 + 0.5)
    assert by_label["disk 2"]["value"] == "ERR"
    assert len(out) == 2  # one mean row + the ERR passthrough


def test_alias_runs_before_fold(tmp_path, monkeypatch, store):
    """Aliases that introduce a shared prefix must be applied before the
    fold, so the renamed rows collapse into one `<prefix> (mean)` row."""
    config = _cfg_with(
        tmp_path,
        monkeypatch,
        "[sensors]\nalias=temp1:CPU 0,temp2:CPU 1\ntemperature_core_mean=true\n",
    )
    p = PluginModel(store, config)
    rows = [
        {"label": "temp1", "unit": "C", "value": 40, "warning": None, "critical": None, "type": "temperature_core"},
        {"label": "temp2", "unit": "C", "value": 44, "warning": None, "critical": None, "type": "temperature_core"},
    ]
    out = _expand(p, rows)
    assert len(out) == 1
    assert out[0]["label"] == "CPU (mean)"  # only possible if alias ran first
    assert out[0]["value"] == 42


def _rows_fan(*values):
    return [
        {"label": f"fan {i}", "unit": "R", "value": v, "warning": None, "critical": None, "type": "fan_speed"}
        for i, v in enumerate(values)
    ]


def test_global_mean_folds_all_types(tmp_path, monkeypatch, store):
    """[sensors] mean=true folds every type with a >= 2-member prefix group,
    even types that carry no per-type <type>_mean key."""
    config = _cfg_with(tmp_path, monkeypatch, "[sensors]\nmean=true\n")
    p = PluginModel(store, config)
    out = _expand(p, _rows_core(40, 42, 44) + _rows_fan(1000, 1200))
    by_label = {r["label"]: r for r in out}
    assert "Core (mean)" in by_label
    assert "fan (mean)" in by_label
    assert len(out) == 2


def test_per_type_false_overrides_global_true(tmp_path, monkeypatch, store):
    """An explicit <type>_mean=false opts a type OUT even when the global
    mean=true is set (global default + per-type override)."""
    config = _cfg_with(tmp_path, monkeypatch, "[sensors]\nmean=true\ntemperature_core_mean=false\n")
    p = PluginModel(store, config)
    out = _expand(p, _rows_core(40, 42, 44) + _rows_fan(1000, 1200))
    by_label = {r["label"]: r for r in out}
    # Core NOT folded (explicit opt-out); fan folded (inherits global true).
    assert {"Core 0", "Core 1", "Core 2"} <= set(by_label)
    assert "fan (mean)" in by_label


def test_per_type_true_overrides_global_false(tmp_path, monkeypatch, store):
    """An explicit <type>_mean=true still folds that type when the global
    mean is false — backward compatibility with per-type-only configs."""
    config = _cfg_with(tmp_path, monkeypatch, "[sensors]\nmean=false\ntemperature_core_mean=true\n")
    p = PluginModel(store, config)
    out = _expand(p, _rows_core(40, 42, 44) + _rows_fan(1000, 1200))
    by_label = {r["label"]: r for r in out}
    assert "Core (mean)" in by_label  # per-type true wins over global false
    assert {"fan 0", "fan 1"} <= set(by_label)  # fan inherits global false -> not folded


def _levels(p, rows):
    p._stats = rows
    p._derived_parameters()
    return p._levels


def _temp_row(label, value, warning=None, critical=None):
    return {
        "label": label,
        "unit": "C",
        "value": value,
        "warning": warning,
        "critical": critical,
        "type": "temperature_core",
    }


def test_level_from_hardware_threshold(store, config):
    p = PluginModel(store, config)
    lv = _levels(p, [_temp_row("Core 0", 95, warning=80, critical=90)])
    assert lv["Core 0"]["value"]["level"] == "critical"
    # prominent mirrors the `value` field schema (False = coloured text, no
    # background highlight); it is NOT hardcoded.
    assert lv["Core 0"]["value"]["prominent"] is PluginModel.fields_description["value"]["prominent"]


def test_prominent_follows_field_schema(store, config, monkeypatch):
    """Flipping the schema `prominent` flag flows through to `_levels`."""
    p = PluginModel(store, config)
    monkeypatch.setitem(PluginModel.fields_description["value"], "prominent", True)
    assert _levels(p, [_temp_row("Core 0", 95, warning=80, critical=90)])["Core 0"]["value"]["prominent"] is True
    monkeypatch.setitem(PluginModel.fields_description["value"], "prominent", False)
    assert _levels(p, [_temp_row("Core 0", 95, warning=80, critical=90)])["Core 0"]["value"]["prominent"] is False


def test_level_hardware_warning(store, config):
    p = PluginModel(store, config)
    lv = _levels(p, [_temp_row("Core 0", 85, warning=80, critical=90)])
    assert lv["Core 0"]["value"]["level"] == "warning"


def test_level_none_when_no_critical(store, config):
    p = PluginModel(store, config)
    lv = _levels(p, [_temp_row("Core 0", 85, warning=80, critical=None)])
    assert "Core 0" not in lv  # no threshold source -> no level entry


def test_per_type_config_beats_hardware(tmp_path, monkeypatch, store):
    config = _cfg_with(tmp_path, monkeypatch, "[sensors]\ntemperature_core_critical=70\n")
    p = PluginModel(store, config)
    lv = _levels(p, [_temp_row("Core 0", 75, warning=80, critical=90)])
    # config critical 70 < value 75 -> critical, even though hardware critical is 90.
    assert lv["Core 0"]["value"]["level"] == "critical"


def test_per_sensor_config_beats_per_type(tmp_path, monkeypatch, store):
    config = _cfg_with(
        tmp_path,
        monkeypatch,
        "[sensors]\ntemperature_core_critical=70\ntemperature_core_core 0_critical=99\n",
    )
    p = PluginModel(store, config)
    lv = _levels(p, [_temp_row("Core 0", 75, warning=80, critical=90)])
    # per-sensor critical 99 > value 75 -> not critical; warning unset -> ok.
    assert lv["Core 0"]["value"]["level"] == "ok"


def test_battery_alerts_on_inverse(tmp_path, monkeypatch, store):
    config = _cfg_with(tmp_path, monkeypatch, "[sensors]\nbattery_critical=80\n")
    p = PluginModel(store, config)
    row = {
        "label": "Battery",
        "unit": "%",
        "value": 10,
        "warning": None,
        "critical": None,
        "type": "battery",
        "status": "Discharging",
    }
    lv = _levels(p, [row])
    # 100 - 10 = 90 >= config critical 80 -> critical (low battery).
    assert lv["Battery"]["value"]["level"] == "critical"


def test_thresholds_resolved_from_single_coherent_tier(tmp_path, monkeypatch, store):
    """v4 parity: the tier that wins on `critical` also supplies `warning`;
    config critical must NOT be mixed with a hardware warning."""
    config = _cfg_with(tmp_path, monkeypatch, "[sensors]\ntemperature_core_critical=90\n")
    p = PluginModel(store, config)
    # config critical=90 (per-type tier wins), no config warning; hardware
    # warning=80 must be IGNORED because the config tier owns both levels.
    lv = _levels(p, [_temp_row("Core 0", 85, warning=80, critical=95)])
    assert "Core 0" not in lv or lv["Core 0"]["value"]["level"] == "ok"  # not "warning"


def test_per_sensor_warning_from_same_tier(tmp_path, monkeypatch, store):
    """A per-sensor tier supplies its own warning (not the hardware one)."""
    config = _cfg_with(
        tmp_path,
        monkeypatch,
        "[sensors]\ntemperature_core_core 0_critical=95\ntemperature_core_core 0_warning=70\n",
    )
    p = PluginModel(store, config)
    lv = _levels(p, [_temp_row("Core 0", 75, warning=80, critical=90)])
    # per-sensor warning 70 <= value 75 < per-sensor critical 95 -> warning.
    assert lv["Core 0"]["value"]["level"] == "warning"


def test_config_critical_zero_is_honoured(tmp_path, monkeypatch, store):
    """A config threshold of 0 is a real limit, not 'unset'."""
    config = _cfg_with(tmp_path, monkeypatch, "[sensors]\ntemperature_core_critical=0\n")
    p = PluginModel(store, config)
    lv = _levels(p, [_temp_row("Core 0", 5, warning=None, critical=None)])
    assert lv["Core 0"]["value"]["level"] == "critical"  # 5 >= 0


def test_careful_tier_from_config(tmp_path, monkeypatch, store):
    """The shipped default `[sensors] temperature_core_careful` must be
    honoured (v4 parity: careful/warning/critical ladder)."""
    config = _cfg_with(
        tmp_path,
        monkeypatch,
        "[sensors]\ntemperature_core_careful=45\ntemperature_core_warning=65\ntemperature_core_critical=80\n",
    )
    p = PluginModel(store, config)
    assert _levels(p, [_temp_row("Core 0", 50)])["Core 0"]["value"]["level"] == "careful"
    assert _levels(p, [_temp_row("Core 0", 70)])["Core 0"]["value"]["level"] == "warning"
    assert _levels(p, [_temp_row("Core 0", 85)])["Core 0"]["value"]["level"] == "critical"
    assert _levels(p, [_temp_row("Core 0", 40)])["Core 0"]["value"]["level"] == "ok"


def test_per_type_config_warning_only_is_honoured(tmp_path, monkeypatch, store):
    """#3627: a config tier is selected as soon as ANY level is defined — the
    user is free to set a warning without a critical."""
    config = _cfg_with(tmp_path, monkeypatch, "[sensors]\ntemperature_core_warning=60\n")
    p = PluginModel(store, config)
    assert _levels(p, [_temp_row("Core 0", 65)])["Core 0"]["value"]["level"] == "warning"
    assert _levels(p, [_temp_row("Core 0", 55)])["Core 0"]["value"]["level"] == "ok"


def test_per_sensor_config_careful_only_is_honoured(tmp_path, monkeypatch, store):
    """#3627: same for a per-sensor tier holding only a careful level."""
    config = _cfg_with(tmp_path, monkeypatch, "[sensors]\ntemperature_core_core 0_careful=40\n")
    p = PluginModel(store, config)
    assert _levels(p, [_temp_row("Core 0", 50)])["Core 0"]["value"]["level"] == "careful"


def test_config_warning_only_does_not_borrow_the_hardware_critical(tmp_path, monkeypatch, store):
    """#3627 must not break the coherent-tier rule: a config tier that wins on
    `warning` owns EVERY level — the hardware critical must stay ignored."""
    config = _cfg_with(tmp_path, monkeypatch, "[sensors]\ntemperature_core_warning=60\n")
    p = PluginModel(store, config)
    lv = _levels(p, [_temp_row("Core 0", 95, warning=80, critical=90)])
    assert lv["Core 0"]["value"]["level"] == "warning"  # not "critical"


def test_hardware_tier_has_no_careful(store, config):
    """Hardware thresholds carry only warning/critical — no careful tier."""
    lv = _levels(p=PluginModel(store, config), rows=[_temp_row("Core 0", 55, warning=80, critical=90)])
    # 55 < warning 80, and hardware has no careful -> ok, never careful.
    assert lv["Core 0"]["value"]["level"] == "ok"


def test_emits_alerts_default_true():
    assert PluginModel.EMITS_ALERTS is True

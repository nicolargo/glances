#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the v5 wifi plugin model."""

from __future__ import annotations

import pytest

from glances.config import GlancesConfig
from glances.plugins.wifi import model as wifi_mod
from glances.plugins.wifi import nl80211
from glances.plugins.wifi.model import PluginModel
from glances.stats_store import StatsStore


@pytest.fixture
def store() -> StatsStore:
    return StatsStore()


@pytest.fixture
def config(tmp_path, monkeypatch) -> GlancesConfig:
    monkeypatch.setattr(GlancesConfig, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    return GlancesConfig()


def test_plugin_identity(store, config):
    p = PluginModel(store, config)
    assert p.plugin_name == "wifi"
    assert p.IS_COLLECTION is True
    assert p._primary_key == "ssid"


def test_fields_description_flags():
    fd = PluginModel.fields_description
    assert fd["ssid"]["primary_key"] is True
    assert fd["quality_level"]["watched"] is True
    assert fd["quality_level"]["watch_direction"] == "low"
    assert fd["quality_level"].get("prominent") is False
    assert fd["quality_link"].get("watched", False) is False


def _nl80211_unavailable(monkeypatch) -> None:
    """Force the /proc/net/wireless fallback, whatever hardware the tests run on."""

    def _raise():
        raise nl80211.Nl80211Unavailable("test")

    monkeypatch.setattr(nl80211, "station_signals", _raise)


_WIRELESS_CONTENT = """Inter-| sta-|   Quality        |   Discarded packets               | Missed | WE
 face | tus | link level noise |  nwid  crypt   frag  retry   misc | beacon | 22
wlp2s0: 0000   51.  -59.  -256        0      0      0      0   5881        0
wlan1: 0000   60.  -50.  -256        0      0      0      0      0        0
"""


@pytest.mark.asyncio
async def test_grab_parses_and_skips_two_header_lines(store, config, monkeypatch, tmp_path):
    _nl80211_unavailable(monkeypatch)
    wireless_file = tmp_path / "wireless"
    wireless_file.write_text(_WIRELESS_CONTENT)
    monkeypatch.setattr(wifi_mod, "WIRELESS_FILE", str(wireless_file))
    p = PluginModel(store, config)
    rows = await p._grab_stats()
    assert len(rows) == 2
    by_ssid = {r["ssid"]: r for r in rows}
    assert set(by_ssid) == {"wlp2s0", "wlan1"}
    assert by_ssid["wlp2s0"]["quality_link"] == 51.0
    assert by_ssid["wlp2s0"]["quality_level"] == -59.0


@pytest.mark.asyncio
async def test_grab_missing_file_returns_empty(store, config, monkeypatch, tmp_path):
    _nl80211_unavailable(monkeypatch)
    monkeypatch.setattr(wifi_mod, "WIRELESS_FILE", str(tmp_path / "does-not-exist"))
    p = PluginModel(store, config)
    assert await p._grab_stats() == []


# ------------------------------------------------------------ nl80211 source


@pytest.mark.asyncio
async def test_grab_uses_nl80211(store, config, monkeypatch, tmp_path):
    """nl80211 is the primary source: /proc/net/wireless is not touched."""
    monkeypatch.setattr(nl80211, "station_signals", lambda: {"wlp2s0": -59, "wlan1": -50})
    monkeypatch.setattr(wifi_mod, "WIRELESS_FILE", str(tmp_path / "must-not-be-read"))
    (tmp_path / "must-not-be-read").write_text(_WIRELESS_CONTENT.replace("wlp2s0", "stale0"))
    rows = await PluginModel(store, config)._grab_stats()
    by_ssid = {r["ssid"]: r for r in rows}
    assert set(by_ssid) == {"wlp2s0", "wlan1"}
    assert by_ssid["wlp2s0"] == {"ssid": "wlp2s0", "quality_link": 51.0, "quality_level": -59.0}
    assert by_ssid["wlan1"]["quality_link"] == 60.0


@pytest.mark.parametrize(
    ("signal", "quality_link"),
    [(-30, 70.0), (-40, 70.0), (-75, 35.0), (-110, 0.0), (-120, 0.0)],
)
@pytest.mark.asyncio
async def test_nl80211_quality_link_matches_wext(store, config, monkeypatch, signal, quality_link):
    """quality_link is derived exactly like cfg80211's wext: signal clamped to [-110, -40] then +110."""
    monkeypatch.setattr(nl80211, "station_signals", lambda: {"wlan0": signal})
    rows = await PluginModel(store, config)._grab_stats()
    assert rows == [{"ssid": "wlan0", "quality_link": quality_link, "quality_level": float(signal)}]


@pytest.mark.asyncio
async def test_nl80211_no_associated_interface_is_empty(store, config, monkeypatch):
    monkeypatch.setattr(nl80211, "station_signals", lambda: {})
    assert await PluginModel(store, config)._grab_stats() == []


@pytest.mark.asyncio
async def test_nl80211_transient_failure_is_empty_not_fallback(store, config, monkeypatch, tmp_path):
    """A transient nl80211 error must not re-open /proc/net/wireless (it would log the wext warning)."""

    def _fail():
        raise TimeoutError("netlink timeout")

    monkeypatch.setattr(nl80211, "station_signals", _fail)
    wireless_file = tmp_path / "wireless"
    wireless_file.write_text(_WIRELESS_CONTENT)
    monkeypatch.setattr(wifi_mod, "WIRELESS_FILE", str(wireless_file))
    assert await PluginModel(store, config)._grab_stats() == []


# -------------------------------------------------------- alert levels (Task 2)


def _cfg_with(tmp_path, monkeypatch, body: str) -> GlancesConfig:
    # Mirror tests/test_plugin_sensors.py::_cfg_with - load a [wifi] body
    # via an XDG-discovered glances.conf.
    monkeypatch.setattr(GlancesConfig, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    xdg = tmp_path / "xdg"
    cfg_dir = xdg / "glances"
    cfg_dir.mkdir(parents=True)
    (cfg_dir / "glances.conf").write_text(body)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    return GlancesConfig()


def _levels(p, rows):
    p._stats = rows
    p._derived_parameters()
    return p._levels


def _wifi_row(ssid, quality_level):
    return {"ssid": ssid, "quality_link": 50.0, "quality_level": quality_level}


def test_level_critical(store, config):
    p = PluginModel(store, config)
    lv = _levels(p, [_wifi_row("wlp2s0", -90)])
    assert lv["wlp2s0"]["quality_level"]["level"] == "critical"


def test_level_warning(store, config):
    p = PluginModel(store, config)
    lv = _levels(p, [_wifi_row("wlp2s0", -80)])
    assert lv["wlp2s0"]["quality_level"]["level"] == "warning"


def test_level_careful(store, config):
    p = PluginModel(store, config)
    lv = _levels(p, [_wifi_row("wlp2s0", -70)])
    assert lv["wlp2s0"]["quality_level"]["level"] == "careful"


def test_level_ok(store, config):
    p = PluginModel(store, config)
    lv = _levels(p, [_wifi_row("wlp2s0", -50)])
    assert lv["wlp2s0"]["quality_level"]["level"] == "ok"


def test_level_prominent_false(store, config):
    p = PluginModel(store, config)
    lv = _levels(p, [_wifi_row("wlp2s0", -90)])
    assert lv["wlp2s0"]["quality_level"]["prominent"] is False


def test_level_from_config_overrides_defaults(tmp_path, monkeypatch, store):
    config = _cfg_with(tmp_path, monkeypatch, "[wifi]\ncareful=-60\nwarning=-70\ncritical=-80\n")
    p = PluginModel(store, config)
    lv = _levels(p, [_wifi_row("wlp2s0", -75), _wifi_row("wlan1", -55), _wifi_row("wlan2", -82)])
    assert lv["wlp2s0"]["quality_level"]["level"] == "warning"  # -75 <= -70 (config), not <= -80
    assert lv["wlan1"]["quality_level"]["level"] == "ok"  # -55 > -60 (config)
    # Discriminator: -82 is "critical" under the -80 config band, but would only
    # be "warning" under the default -85 critical band. Proves the NEGATIVE
    # config values are actually read (the whole reason the override exists),
    # not silently ignored in favour of the -65/-75/-85 defaults.
    assert lv["wlan2"]["quality_level"]["level"] == "critical"  # -82 <= -80 (config); default would give warning


def test_level_boundary_is_inclusive(store, config):
    """A value sitting exactly on a threshold falls INTO that band — proves the
    engine uses `<=` (inclusive), not `<`. Uses the default -65/-75/-85 bands."""
    p = PluginModel(store, config)
    lv = _levels(
        p,
        [_wifi_row("careful0", -65), _wifi_row("warn0", -75), _wifi_row("crit0", -85)],
    )
    assert lv["careful0"]["quality_level"]["level"] == "careful"  # -65 <= -65
    assert lv["warn0"]["quality_level"]["level"] == "warning"  # -75 <= -75
    assert lv["crit0"]["quality_level"]["level"] == "critical"  # -85 <= -85


def test_level_none_skipped(store, config):
    p = PluginModel(store, config)
    lv = _levels(p, [_wifi_row("wlp2s0", None)])
    assert "wlp2s0" not in lv


def test_careful_is_colour_only(store, config):
    # The alert engine collapses careful -> ok (warning+ rule, v4 parity);
    # the level value computed here is exactly "careful" - the colouring
    # concern is decided downstream, not here.
    assert PluginModel.EMITS_ALERTS is True
    lv = _levels(p=PluginModel(store, config), rows=[_wifi_row("wlp2s0", -70)])
    assert lv["wlp2s0"]["quality_level"]["level"] == "careful"


def test_emits_alerts_true():
    assert PluginModel.EMITS_ALERTS is True

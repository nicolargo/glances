#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the Wifi plugin."""

from unittest.mock import MagicMock

import pytest

from glances.plugins import wifi as wifi_mod
from glances.plugins.wifi import WifiPlugin, nl80211

# Signal quality is reported in dBm, so the thresholds are negative and lower is worse.
ALL_LEVELS = {'wifi_careful': -65, 'wifi_warning': -75, 'wifi_critical': -85}


def decoration(limits, value):
    plugin = WifiPlugin(args=MagicMock(), config=None)
    plugin._limits = dict(limits)
    return plugin.get_alert(value)


class TestWifiAlertThresholds:
    """get_alert must honour whichever levels the config defines."""

    @pytest.mark.parametrize(
        ('value', 'expected'),
        [(-50, 'OK'), (-70, 'CAREFUL'), (-80, 'WARNING'), (-90, 'CRITICAL')],
    )
    def test_all_levels_configured(self, value, expected):
        assert decoration(ALL_LEVELS, value) == expected

    def test_only_careful_still_alerts(self):
        # Chaining the comparisons meant the undefined 'critical' level was compared
        # against None first, raising TypeError and dropping the result to DEFAULT —
        # so a config defining only 'careful' never produced an alert at all.
        assert decoration({'wifi_careful': -65}, -70) == 'CAREFUL'

    def test_only_warning_still_alerts(self):
        assert decoration({'wifi_warning': -75}, -80) == 'WARNING'

    def test_only_critical_still_alerts(self):
        assert decoration({'wifi_critical': -85}, -90) == 'CRITICAL'

    @pytest.mark.parametrize(
        'limits',
        [{'wifi_careful': -65}, {'wifi_warning': -75}, {'wifi_critical': -85}],
    )
    def test_a_good_signal_is_ok_under_any_partial_config(self, limits):
        # A signal above every defined threshold is OK, not undecorated.
        assert decoration(limits, -50) == 'OK'

    def test_the_most_severe_level_wins(self):
        assert decoration(ALL_LEVELS, -90) == 'CRITICAL'
        assert decoration({'wifi_warning': -75, 'wifi_critical': -85}, -90) == 'CRITICAL'

    def test_no_threshold_at_all_is_not_decorated(self):
        assert decoration({}, -90) == 'DEFAULT'

    def test_a_non_numeric_level_is_not_decorated(self):
        # Regression guard for issue #1373: an unparsed signal level is not comparable.
        assert decoration(ALL_LEVELS, None) == 'DEFAULT'
        assert decoration(ALL_LEVELS, 'n/a') == 'DEFAULT'


def _plugin():
    return WifiPlugin(args=MagicMock(disable_wifi=False), config=None)


def _nl80211_returns(monkeypatch, signals):
    monkeypatch.setattr(nl80211, 'station_signals', lambda: signals)


def _nl80211_raises(monkeypatch, exc):
    def _raise():
        raise exc

    monkeypatch.setattr(nl80211, 'station_signals', _raise)


_WIRELESS_CONTENT = """Inter-| sta-|   Quality        |   Discarded packets               | Missed | WE
 face | tus | link level noise |  nwid  crypt   frag  retry   misc | beacon | 22
wlp2s0: 0000   51.  -59.  -256        0      0      0      0   5881        0
"""


class TestWifiNl80211Source:
    """nl80211 is the primary source; /proc/net/wireless is only a fallback."""

    def test_uses_nl80211_and_ignores_proc_file(self, monkeypatch, tmp_path):
        proc = tmp_path / 'wireless'
        proc.write_text(_WIRELESS_CONTENT.replace('wlp2s0', 'stale0'))
        monkeypatch.setattr(wifi_mod, 'WIRELESS_FILE', str(proc))
        _nl80211_returns(monkeypatch, {'wlp2s0': -59, 'wlan1': -50})
        stats = _plugin()._get_wireless_stats()
        assert stats == [
            {'key': 'ssid', 'ssid': 'wlp2s0', 'quality_link': 51.0, 'quality_level': -59.0},
            {'key': 'ssid', 'ssid': 'wlan1', 'quality_link': 60.0, 'quality_level': -50.0},
        ]

    @pytest.mark.parametrize(
        ('signal', 'quality_link'),
        [(-30, 70.0), (-40, 70.0), (-75, 35.0), (-110, 0.0), (-120, 0.0)],
    )
    def test_quality_link_matches_wext(self, monkeypatch, signal, quality_link):
        # Derived like cfg80211's wext: signal clamped to [-110, -40] then +110
        _nl80211_returns(monkeypatch, {'wlan0': signal})
        assert _plugin()._get_wireless_stats()[0]['quality_link'] == quality_link

    def test_works_without_proc_net_wireless(self, monkeypatch):
        # Kernels built without the wext compat layer have no /proc/net/wireless but nl80211 works
        monkeypatch.setattr(wifi_mod, 'wireless_file_exists', False)
        _nl80211_returns(monkeypatch, {'wlan0': -60})
        plugin = _plugin()
        plugin.update()
        assert [s['ssid'] for s in plugin.stats] == ['wlan0']

    def test_falls_back_to_proc_file_when_nl80211_unavailable(self, monkeypatch, tmp_path):
        proc = tmp_path / 'wireless'
        proc.write_text(_WIRELESS_CONTENT)
        monkeypatch.setattr(wifi_mod, 'WIRELESS_FILE', str(proc))
        monkeypatch.setattr(wifi_mod, 'wireless_file_exists', True)
        _nl80211_raises(monkeypatch, nl80211.Nl80211Unavailable('test'))
        stats = _plugin()._get_wireless_stats()
        assert [(s['ssid'], s['quality_link'], s['quality_level']) for s in stats] == [('wlp2s0', 51.0, -59.0)]

    def test_no_fallback_and_no_proc_file_without_nl80211_or_file(self, monkeypatch, tmp_path):
        monkeypatch.setattr(wifi_mod, 'wireless_file_exists', False)
        _nl80211_raises(monkeypatch, nl80211.Nl80211Unavailable('test'))
        assert _plugin()._get_wireless_stats() == []

    def test_transient_nl80211_error_does_not_read_proc_file(self, monkeypatch, tmp_path):
        # Reading /proc/net/wireless is what logs the kernel warning: never do it on a mere hiccup
        proc = tmp_path / 'wireless'
        proc.write_text(_WIRELESS_CONTENT)
        monkeypatch.setattr(wifi_mod, 'WIRELESS_FILE', str(proc))
        monkeypatch.setattr(wifi_mod, 'wireless_file_exists', True)
        _nl80211_raises(monkeypatch, TimeoutError('netlink timeout'))
        assert _plugin()._get_wireless_stats() == []

    def test_no_associated_interface_is_empty(self, monkeypatch):
        _nl80211_returns(monkeypatch, {})
        assert _plugin()._get_wireless_stats() == []

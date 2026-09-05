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

from glances.plugins.wifi import WifiPlugin

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

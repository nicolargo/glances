#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the Ports plugin."""

import pytest

from glances.plugins.ports import PortsPlugin


@pytest.fixture
def ports_plugin():
    """Return a Ports plugin instance without running its full init."""
    return PortsPlugin.__new__(PortsPlugin)


def web_scan(status, elapsed=0, rtt_warning=1):
    """Return a web scan result as stored by the ports plugin."""
    return {'status': status, 'elapsed': elapsed, 'rtt_warning': rtt_warning}


class TestPortsPluginAlertLevel:
    """Test that the alert level is resolved by severity, not by dict ordering."""

    @pytest.mark.parametrize(
        ('conds', 'expected'),
        [
            ({'CAREFUL': True, 'CRITICAL': True, 'WARNING': True}, 'CRITICAL'),
            ({'CAREFUL': True, 'CRITICAL': False, 'WARNING': True}, 'WARNING'),
            ({'CAREFUL': True, 'CRITICAL': False, 'WARNING': False}, 'CAREFUL'),
            ({'CAREFUL': False, 'CRITICAL': False, 'WARNING': False}, 'OK'),
        ],
    )
    def test_most_severe_condition_wins(self, ports_plugin, conds, expected):
        """Test that the most severe matching condition is returned."""
        assert ports_plugin.get_default_ret_value(conds) == expected

    def test_web_not_scanned_yet_is_careful(self, ports_plugin):
        """Test that a URL whose first scan did not complete is not CRITICAL."""
        conds = ports_plugin.get_conds_if_url(web_scan(None))
        assert ports_plugin.get_default_ret_value(conds) == 'CAREFUL'

    def test_web_failing_and_slow_is_critical(self, ports_plugin):
        """Test that a failing URL stays CRITICAL even when it is also slow."""
        conds = ports_plugin.get_conds_if_url(web_scan(404, elapsed=5))
        assert ports_plugin.get_default_ret_value(conds) == 'CRITICAL'

    def test_web_failing_and_fast_is_critical(self, ports_plugin):
        """Test that a failing URL is CRITICAL."""
        conds = ports_plugin.get_conds_if_url(web_scan(404))
        assert ports_plugin.get_default_ret_value(conds) == 'CRITICAL'

    def test_web_ok_but_slow_is_warning(self, ports_plugin):
        """Test that a reachable but slow URL is WARNING."""
        conds = ports_plugin.get_conds_if_url(web_scan(200, elapsed=5))
        assert ports_plugin.get_default_ret_value(conds) == 'WARNING'

    def test_web_ok_and_fast_is_ok(self, ports_plugin):
        """Test that a reachable and fast URL is OK."""
        conds = ports_plugin.get_conds_if_url(web_scan(200))
        assert ports_plugin.get_default_ret_value(conds) == 'OK'

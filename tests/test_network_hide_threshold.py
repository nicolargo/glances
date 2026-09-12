#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""The network plugin honours the hide_threshold_bytes it documents.

Both the reference configuration and docs/aoa/network.rst offer the option
under [network]:

    [network]
    hide_zero=True
    hide_threshold_bytes=0

Nothing reports an option a plugin does not read -- the value simply stays at
the base class default of 0 and every interface with any traffic at all is
shown. These tests read the boundary back out of the views dict, so they fail
if the option stops being wired up again.
"""

import os

import pytest

from glances.config import Config
from glances.plugins.network import NetworkPlugin

RECV = 'bytes_recv_rate_per_sec'
SENT = 'bytes_sent_rate_per_sec'

THRESHOLD = 1024


def make_plugin(tmp_path, extra=''):
    config_file = tmp_path / 'glances.conf'
    config_file.write_text(f'[network]\nhide_zero=True\n{extra}', encoding='utf-8')
    return NetworkPlugin(args=None, config=Config(config_dir=os.fspath(config_file)))


@pytest.fixture
def plugin(tmp_path):
    return make_plugin(tmp_path, f'hide_threshold_bytes={THRESHOLD}\n')


def interface(recv_rate, sent_rate, name='eth0'):
    return {
        'interface_name': name,
        'key': 'interface_name',
        'alias': None,
        'is_up': True,
        'speed': 0,
        'time_since_update': 1.0,
        'bytes_recv': 0,
        'bytes_sent': 0,
        'bytes_all': 0,
        RECV: recv_rate,
        SENT: sent_rate,
        'bytes_all_rate_per_sec': recv_rate + sent_rate,
    }


def sample(plugin, stats):
    """Feed one refresh and return the views for the single interface."""
    plugin.stats = [stats]
    plugin.update_views()
    return plugin.views[stats['interface_name']]


class TestNetworkHideThresholdBytes:
    def test_the_option_reaches_the_plugin(self, plugin):
        assert plugin.hide_threshold_bytes == THRESHOLD

    def test_it_defaults_to_zero_when_not_configured(self, tmp_path):
        assert make_plugin(tmp_path).hide_threshold_bytes == 0

    def test_traffic_below_the_threshold_leaves_the_interface_hidden(self, plugin):
        sample(plugin, interface(0, 0))
        views = sample(plugin, interface(THRESHOLD - 500, THRESHOLD - 500))
        assert views[RECV]['hidden'] is True
        assert views[SENT]['hidden'] is True

    def test_traffic_above_the_threshold_reveals_the_interface(self, plugin):
        sample(plugin, interface(0, 0))
        views = sample(plugin, interface(THRESHOLD * 2, 0))
        assert views[RECV]['hidden'] is False

    def test_without_a_threshold_any_traffic_reveals_the_interface(self, tmp_path):
        # The default of 0 must keep behaving as it always did: a trickle that a
        # configured threshold would swallow is still traffic.
        no_threshold = make_plugin(tmp_path)
        sample(no_threshold, interface(0, 0))
        assert sample(no_threshold, interface(THRESHOLD - 500, 0))[RECV]['hidden'] is False

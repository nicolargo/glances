#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""hide_zero hides a stat that has never moved.

The reference configuration states the boundary for both plugins that use the
feature: "Set hide_threshold_bytes to an integer value to automatically hide
interface with traffic less or equal than this value". With the documented
default of 0, a rate of exactly 0 is therefore hidden.

This is invisible when it breaks: the views dict still has every key, the rows
just come back. So the tests below pin the boundary itself rather than any
message drawn from it.
"""

import os

import pytest

from glances.config import Config
from glances.plugins.diskio import DiskioPlugin
from glances.plugins.network import NetworkPlugin

RECV = 'bytes_recv_rate_per_sec'
SENT = 'bytes_sent_rate_per_sec'
READ = 'read_bytes_rate_per_sec'
WRITE = 'write_bytes_rate_per_sec'


def make_config(tmp_path, section, extra=''):
    config_file = tmp_path / 'glances.conf'
    config_file.write_text(f'[{section}]\nhide_zero=True\n{extra}', encoding='utf-8')
    return Config(config_dir=os.fspath(config_file))


@pytest.fixture
def network(tmp_path):
    return NetworkPlugin(args=None, config=make_config(tmp_path, 'network'))


@pytest.fixture
def diskio(tmp_path):
    return DiskioPlugin(args=None, config=make_config(tmp_path, 'diskio'))


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


def disk(read_rate, write_rate, name='sda'):
    return {
        'disk_name': name,
        'key': 'disk_name',
        'time_since_update': 1.0,
        'read_count': 0,
        'write_count': 0,
        'read_bytes': 0,
        'write_bytes': 0,
        READ: read_rate,
        WRITE: write_rate,
        'read_count_rate_per_sec': 0,
        'write_count_rate_per_sec': 0,
        'read_latency': 0,
        'write_latency': 0,
    }


def sample(plugin, stats):
    """Feed one refresh and return the views for the single row."""
    plugin.stats = [stats]
    plugin.update_views()
    return plugin.views[stats[plugin.get_key()]]


class TestHideZeroStaysHidden:
    """A stat that has never been different from 0 keeps hiding."""

    def test_an_idle_interface_stays_hidden_across_refreshes(self, network):
        # The first refresh has no previous view to carry forward and hides by
        # construction; the regression only shows from the second one on.
        assert sample(network, interface(0, 0))[RECV]['hidden'] is True

        for refresh in range(2, 5):
            views = sample(network, interface(0, 0))
            assert views[RECV]['hidden'] is True, f'recv came back on refresh {refresh}'
            assert views[SENT]['hidden'] is True, f'sent came back on refresh {refresh}'

    def test_an_idle_disk_stays_hidden_across_refreshes(self, diskio):
        assert sample(diskio, disk(0, 0))[READ]['hidden'] is True

        for refresh in range(2, 5):
            views = sample(diskio, disk(0, 0))
            assert views[READ]['hidden'] is True, f'read came back on refresh {refresh}'
            assert views[WRITE]['hidden'] is True, f'write came back on refresh {refresh}'


class TestHideZeroRevealsTraffic:
    """...and any traffic at all reveals it, permanently."""

    def test_traffic_reveals_the_field_and_it_does_not_hide_again(self, network):
        sample(network, interface(0, 0))
        views = sample(network, interface(0, 51200))
        assert views[SENT]['hidden'] is False, 'a transmitting interface must be shown'

        # "never been != 0" is a memory, not a snapshot: going quiet again does
        # not re-hide the field.
        views = sample(network, interface(0, 0))
        assert views[SENT]['hidden'] is False, 'an interface that has transmitted must stay shown'

    def test_one_byte_per_second_is_traffic(self, network):
        sample(network, interface(0, 0))
        assert sample(network, interface(1, 0))[RECV]['hidden'] is False


class TestHideThresholdBytes:
    """The threshold is the boundary the configuration file documents."""

    def test_a_rate_equal_to_the_threshold_is_hidden(self, tmp_path):
        plugin = DiskioPlugin(args=None, config=make_config(tmp_path, 'diskio', 'hide_threshold_bytes=1024\n'))
        assert plugin.hide_threshold_bytes == 1024

        sample(plugin, disk(0, 0))
        views = sample(plugin, disk(1024, 1024))
        assert views[READ]['hidden'] is True, 'a rate equal to the threshold is "less or equal than"'
        assert views[WRITE]['hidden'] is True

    def test_a_rate_above_the_threshold_is_shown(self, tmp_path):
        plugin = DiskioPlugin(args=None, config=make_config(tmp_path, 'diskio', 'hide_threshold_bytes=1024\n'))

        sample(plugin, disk(0, 0))
        assert sample(plugin, disk(1025, 0))[READ]['hidden'] is False


class TestHideZeroDisabled:
    """Nothing is hidden when the feature is off, whatever the rates are."""

    def test_hide_zero_false_never_hides(self, tmp_path):
        config_file = tmp_path / 'glances.conf'
        config_file.write_text('[network]\nhide_zero=False\n', encoding='utf-8')
        plugin = NetworkPlugin(args=None, config=Config(config_dir=os.fspath(config_file)))

        for _ in range(3):
            views = sample(plugin, interface(0, 0))
            assert views[RECV]['hidden'] is False
            assert views[SENT]['hidden'] is False

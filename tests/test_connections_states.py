"""Tests for the connections plugin state counters."""

from unittest import mock

import psutil
import pytest

from glances.plugins.connections import ConnectionsPlugin


def make_connection(status):
    return mock.Mock(status=status)


@pytest.fixture
def plugin():
    return ConnectionsPlugin(args=mock.Mock(time=2), config=None)


@pytest.fixture
def stats(plugin):
    connections = [
        make_connection(psutil.CONN_LISTEN),
        make_connection(psutil.CONN_ESTABLISHED),
        make_connection(psutil.CONN_ESTABLISHED),
        make_connection(psutil.CONN_SYN_SENT),
        make_connection(psutil.CONN_TIME_WAIT),
        make_connection(psutil.CONN_TIME_WAIT),
        make_connection(psutil.CONN_CLOSE_WAIT),
    ]
    with mock.patch('psutil.net_connections', return_value=connections):
        return plugin.update_for_net_connections_method({})


def test_terminated_states_are_counted(stats):
    assert stats['terminated'] == 3  # 2 TIME_WAIT + 1 CLOSE_WAIT
    assert stats[psutil.CONN_TIME_WAIT] == 2
    assert stats[psutil.CONN_CLOSE_WAIT] == 1


def test_initiated_states_are_counted(stats):
    assert stats['initiated'] == 1
    assert stats[psutil.CONN_SYN_SENT] == 1


def test_every_terminated_state_is_reported(plugin, stats):
    for state in plugin.terminated_states:
        assert state in stats


def test_listen_and_established_are_counted(stats):
    assert stats[psutil.CONN_LISTEN] == 1
    assert stats[psutil.CONN_ESTABLISHED] == 2


@pytest.fixture
def conntrack_plugin(plugin):
    """A plugin whose nf_conntrack limits match the ones conf/glances.conf ships."""
    plugin._limits.update(
        {
            'connections_nf_conntrack_percent_careful': 70,
            'connections_nf_conntrack_percent_warning': 80,
            'connections_nf_conntrack_percent_critical': 90,
        }
    )
    return plugin


def conntrack_decoration(plugin, percent):
    """Run update_views over a conntrack table filled to *percent* and read the decoration."""
    count = int(65536 * percent / 100)
    plugin.stats = {
        'net_connections_enabled': False,
        'nf_conntrack_enabled': True,
        'nf_conntrack_count': count,
        'nf_conntrack_max': 65536,
        'nf_conntrack_percent': percent,
    }
    plugin.update_views()
    return plugin.views['nf_conntrack_percent']['decoration']


def test_conntrack_alert_reads_the_tracked_percentage(conntrack_plugin):
    """A conntrack table this full drops connections; the thresholds exist to say so."""
    assert conntrack_decoration(conntrack_plugin, 95) == 'CRITICAL'
    assert conntrack_decoration(conntrack_plugin, 85) == 'WARNING'
    assert conntrack_decoration(conntrack_plugin, 75) == 'CAREFUL'


def test_conntrack_alert_stays_ok_below_the_first_threshold(conntrack_plugin):
    assert conntrack_decoration(conntrack_plugin, 10) == 'OK'

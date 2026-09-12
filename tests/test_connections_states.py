"""Tests for the connections plugin state counters."""

from time import time
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


@pytest.fixture
def enabled_plugin(plugin):
    """A plugin the refresh decorator will actually let run."""
    plugin.args = mock.Mock(time=2, disable_connections=False, disable_history=True)
    plugin.input_method = 'local'
    return plugin


def refresh(plugin, times):
    """Call update() as the main loop does, with the refresh delay behind us."""
    for _ in range(times):
        plugin.refresh_timer.target = time() - 1
        plugin.update()


@pytest.fixture
def conntrack_reads(enabled_plugin, tmp_path, monkeypatch):
    """Point the conntrack file at a path that does not exist, and count the reads."""
    reads = []
    missing = str(tmp_path / 'nf_conntrack_count')
    monkeypatch.setattr(enabled_plugin, 'conntrack', {'nf_conntrack_count': missing})
    real_open = open

    def counting_open(path, *args, **kwargs):
        if path == missing:
            reads.append(path)
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr('builtins.open', counting_open)
    return reads


# update() starts each refresh from a copy of stats_init_value, so a plugin that gave up
# on a probe used to forget it: the missing /proc file was read, and the warning logged,
# on every single refresh.
def test_failed_conntrack_probe_is_not_retried(enabled_plugin, conntrack_reads):
    with mock.patch('psutil.net_connections', return_value=[]):
        refresh(enabled_plugin, 3)

    assert len(conntrack_reads) == 1
    assert enabled_plugin.get_raw()['nf_conntrack_enabled'] is False


def test_failed_net_connections_probe_is_not_retried(enabled_plugin, conntrack_reads):
    with mock.patch('psutil.net_connections', side_effect=OSError('nope')) as net_connections:
        refresh(enabled_plugin, 3)

    assert net_connections.call_count == 1
    assert enabled_plugin.get_raw()['net_connections_enabled'] is False


def test_working_probes_keep_running(enabled_plugin, tmp_path, monkeypatch):
    count = tmp_path / 'nf_conntrack_count'
    count.write_text('42' + chr(10))
    maximum = tmp_path / 'nf_conntrack_max'
    maximum.write_text('100' + chr(10))
    monkeypatch.setattr(
        enabled_plugin,
        'conntrack',
        {'nf_conntrack_count': str(count), 'nf_conntrack_max': str(maximum)},
    )

    with mock.patch('psutil.net_connections', return_value=[]) as net_connections:
        refresh(enabled_plugin, 3)

    assert net_connections.call_count == 3
    stats = enabled_plugin.get_raw()
    assert stats['nf_conntrack_enabled'] is True
    assert stats['nf_conntrack_percent'] == 42.0

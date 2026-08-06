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

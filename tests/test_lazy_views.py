"""Tests for the lazily built process views."""

import json
from unittest import mock

import pytest

from glances.plugins.processlist import ProcesslistPlugin


def make_process(pid):
    return {
        'pid': pid,
        'key': 'pid',
        'name': f'proc{pid}',
        'cmdline': [f'proc{pid}'],
        'username': 'someone',
        'status': 'S',
        'nice': 0,
        'num_threads': 1,
        'cpu_percent': 0.0,
        'memory_percent': 0.1,
        'memory_info': {'rss': 1024, 'vms': 2048},
        'cpu_times': {'user': 1.0, 'system': 1.0},
        'io_counters': [0, 0, 0, 0, 0],
        'time_since_update': 1.0,
    }


@pytest.fixture
def plugin():
    p = ProcesslistPlugin(args=mock.Mock(time=2), config=None)
    p.stats = [make_process(pid) for pid in range(10)]
    return p


def test_refresh_builds_nothing(plugin):
    plugin.update_views()
    assert plugin.views == {}


def test_first_read_builds_the_views(plugin):
    plugin.update_views()
    views = plugin.get_views()
    assert views[4]['cpu_percent']['decoration'] is not None
    assert len(views) == 10


def test_unknown_key_raises(plugin):
    plugin.update_views()
    with pytest.raises(KeyError):
        plugin.get_views(item=999999)


def test_second_read_reuses_the_built_views(plugin):
    plugin.update_views()
    first = plugin.get_views()
    assert plugin.get_views() is first


def test_json_contains_every_process(plugin):
    plugin.update_views()
    assert len(json.loads(plugin.get_json_views())) == 10


def test_hide_zero_builds_eagerly(plugin):
    """hide_zero carries the hidden flag over from the previous views, which a deferred
    build no longer has."""
    plugin.hide_zero = True
    plugin.hide_zero_fields = ['cpu_percent']
    plugin.update_views()
    assert len(plugin.views) == 10

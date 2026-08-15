"""Tests for the lazily built process views."""

import json

import pytest


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
def plugin(glances_stats):
    """The shared processlist plugin, fed a fixed list and put back afterwards.

    Building a plugin here instead would write Mock attributes into the glances_processes
    singleton and break every later test that reads it.
    """
    p = glances_stats.get_plugin('processlist')
    saved = (p.stats, p.views, getattr(p, '_views_pending', False))
    p.stats = [make_process(pid) for pid in range(10)]
    yield p
    p.stats, p.views, pending = saved
    p._views_pending = pending


def test_refresh_builds_nothing(plugin):
    plugin.update_views()
    assert plugin.views == {}


def test_first_read_builds_the_views(plugin):
    plugin.update_views()
    views = plugin.get_views()
    assert views[4]['cpu_percent']['decoration'] is not None
    assert len(views) == 10


def test_second_read_reuses_the_built_views(plugin):
    plugin.update_views()
    first = plugin.get_views()
    assert plugin.get_views() is first


def test_json_contains_every_process(plugin):
    plugin.update_views()
    assert len(json.loads(plugin.get_json_views())) == 10


def test_reset_stays_reset(plugin):
    """Without clearing the pending flag the next read would rebuild what was reset."""
    plugin.update_views()
    plugin.reset_views()
    assert plugin.get_views() == {}


def test_set_views_is_not_overwritten(plugin):
    plugin.update_views()
    plugin.set_views({'given': 'by the server'})
    assert plugin.get_views() == {'given': 'by the server'}

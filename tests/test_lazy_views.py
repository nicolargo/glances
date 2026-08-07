"""Tests for the lazily built process views."""

import json
from unittest import mock

import pytest

from glances.plugins.plugin.model import LazyViews
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


def built_count(views):
    """How many entries exist without asking the lazy container to build more."""
    return dict.__len__(views)


def test_views_are_lazy_by_default(plugin):
    plugin.update_views()
    assert isinstance(plugin.views, LazyViews)
    assert built_count(plugin.views) == 0


def test_reading_one_key_builds_only_that_key(plugin):
    plugin.update_views()
    view = plugin.views[4]
    assert view['cpu_percent']['decoration'] is not None
    assert built_count(plugin.views) == 1


def test_unknown_key_raises(plugin):
    plugin.update_views()
    with pytest.raises(KeyError):
        plugin.views[999999]


def test_get_views_materializes_everything(plugin):
    plugin.update_views()
    views = plugin.get_views()
    assert len(views) == 10
    assert built_count(views) == 10


def test_json_contains_every_process(plugin):
    plugin.update_views()
    assert len(json.loads(plugin.get_json_views())) == 10


def test_hide_zero_falls_back_to_eager_views(plugin):
    """hide_zero reads the previous view of a key, which a lazy container cannot provide."""
    plugin.hide_zero = True
    plugin.hide_zero_fields = ['cpu_percent']
    plugin.update_views()
    assert not isinstance(plugin.views, LazyViews)
    assert len(plugin.views) == 10

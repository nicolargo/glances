#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""The container CPU and MEM views carry the decoration both front ends read.

The curses view reads these through get_views(item=..., key='cpu'|'mem',
option='decoration'), and plugin-containers.vue reads the same two entries. A
missing decoration is silent in both: get_views() answers 'DEFAULT' for a key it
cannot find, so an over-threshold container simply renders in plain text.
"""

import os

import pytest

from glances.config import Config
from glances.plugins.containers import ContainersPlugin


def container(name, cpu_total, memory_usage, limit=1000):
    return {
        'name': name,
        'id': name,
        'engine': 'docker',
        'status': 'running',
        'cpu': {'total': cpu_total},
        'memory': {'usage': memory_usage, 'limit': limit},
    }


@pytest.fixture
def plugin(tmp_path):
    """A plugin with explicit container thresholds, so the alerts are predictable."""
    config_file = tmp_path / 'glances.conf'
    config_file.write_text(
        # Keys are section-relative: [containers] cpu_careful becomes the
        # containers_cpu_careful limit.
        '[containers]\n'
        'cpu_careful=50\n'
        'cpu_warning=70\n'
        'cpu_critical=90\n'
        'mem_careful=50\n'
        'mem_warning=70\n'
        'mem_critical=90\n',
        encoding='utf-8',
    )
    return ContainersPlugin(args=None, config=Config(config_dir=os.fspath(config_file)))


class TestContainerDecorationViews:
    def test_cpu_and_mem_views_exist_for_each_container(self, plugin):
        plugin.stats = [container('quiet', 5.0, 50), container('busy', 95.0, 950)]
        plugin.update_views()

        for name in ('quiet', 'busy'):
            assert name in plugin.views, f'{name} has no view entry'
            for field in ('cpu', 'mem'):
                assert field in plugin.views[name], f'{name} has no {field} view'
                assert 'decoration' in plugin.views[name][field]

    def test_a_container_over_its_threshold_is_not_left_plain(self, plugin):
        plugin.stats = [container('quiet', 5.0, 50), container('busy', 95.0, 950)]
        plugin.update_views()

        # The point of the pair: something above the critical threshold must not
        # come out as DEFAULT, which is what both front ends render as no colour.
        assert plugin.views['busy']['cpu']['decoration'] != 'DEFAULT'
        assert plugin.views['busy']['mem']['decoration'] != 'DEFAULT'
        assert plugin.views['quiet']['cpu']['decoration'] == 'OK'

    def test_the_view_is_keyed_by_container_name(self, plugin):
        # Both readers index by name: curses passes item=container['name'], and
        # the WebUI does this.views[container.name]. get_key() says 'name'; this
        # pins that the views dict actually agrees.
        assert plugin.get_key() == 'name'
        plugin.stats = [container('named-thing', 10.0, 100)]
        plugin.update_views()
        assert 'named-thing' in plugin.views

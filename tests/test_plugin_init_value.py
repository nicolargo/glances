#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests that plugins exposing a list of stats initialise them as a list."""

import pytest

LIST_PLUGINS = (
    'alert',
    'amps',
    'containers',
    'diskio',
    'folders',
    'fs',
    'gpu',
    'irq',
    'mpp',
    'network',
    'npu',
    'percpu',
    'ports',
    'processlist',
    'programlist',
    'sensors',
    'smart',
    'vms',
    'wifi',
)


@pytest.mark.parametrize('plugin_name', LIST_PLUGINS)
def test_init_value_is_a_list(glances_stats, plugin_name):
    """get_init_value is what update() returns when it has nothing to report."""
    plugin = glances_stats.get_plugin(plugin_name)

    assert isinstance(plugin.get_init_value(), list)


@pytest.mark.parametrize('plugin_name', LIST_PLUGINS)
def test_reset_leaves_the_stats_a_list(glances_stats, plugin_name):
    """reset() must not swap the stats to a dict behind the API's back."""
    plugin = glances_stats.get_plugin(plugin_name)
    plugin.reset()

    assert isinstance(plugin.stats, list)

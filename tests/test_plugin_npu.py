#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the NPU plugin views."""

import os

import pytest

from glances.config import Config
from glances.plugins.npu import NpuPlugin


@pytest.fixture
def plugin_for(tmp_path):
    """Build an NPU plugin from a `[npu]` config body, with one card's stats set."""

    def build(config_body, stats):
        config_file = tmp_path / f'glances-npu-{abs(hash(tuple(config_body)))}.conf'
        config_file.write_text('\n'.join(['[npu]', *config_body]), encoding='utf-8')
        plugin = NpuPlugin(args=None, config=Config(config_dir=os.fspath(config_file)))
        plugin.stats = [{'key': 'npu_id', 'npu_id': 'npu0', **stats}]
        plugin.update_views()
        return plugin

    return build


DEFAULT_LIMITS = [
    'load_careful=50',
    'load_warning=70',
    'load_critical=90',
    'freq_careful=50',
    'freq_warning=70',
    'freq_critical=90',
    'temperature_careful=60',
    'temperature_warning=70',
    'temperature_critical=80',
]


class TestNpuTemperatureAlert:
    """`msg_curse` and the WebUI both read a temperature decoration that was never set.

    `update_views` replaced the base class's per-field views with a dict naming only
    load, freq and mem, so `views[npu_id]['temperature']` did not exist. The curses
    line fell back to 'DEFAULT' and the WebUI's `getDecoration` returned undefined,
    which is why a hot Intel NPU -- the one driver that reports the reading -- was
    printed in the plain style at any temperature.
    """

    def test_a_hot_npu_is_alerted(self, plugin_for):
        plugin = plugin_for(DEFAULT_LIMITS, {'load': 10, 'freq': 10, 'mem': 10, 'temperature': 85})

        assert plugin.views['npu0']['temperature']['decoration'] == 'CRITICAL'

    @pytest.mark.parametrize(
        ('celsius', 'expected'),
        [(20, 'OK'), (59, 'OK'), (60, 'CAREFUL'), (70, 'WARNING'), (80, 'CRITICAL')],
    )
    def test_each_threshold_boundary(self, plugin_for, celsius, expected):
        plugin = plugin_for(DEFAULT_LIMITS, {'temperature': celsius})

        assert plugin.views['npu0']['temperature']['decoration'] == expected

    def test_the_curses_line_reads_the_decoration_that_is_written(self, plugin_for):
        """The wiring: `msg_curse` asks for it by (item, key), not off a bare view."""
        plugin = plugin_for(DEFAULT_LIMITS, {'temperature': 85})

        assert plugin.get_views(item='npu0', key='temperature', option='decoration') == 'CRITICAL'

    def test_a_card_that_reports_no_temperature_keeps_a_view_without_a_decoration(self, plugin_for):
        """The AMD and Rockchip drivers leave it None; that must not become an alert."""
        plugin = plugin_for(DEFAULT_LIMITS, {'load': 10, 'temperature': None})

        assert plugin.views['npu0']['temperature'] == {}
        assert plugin.get_views(item='npu0', key='temperature', option='decoration') == 'DEFAULT'

    def test_the_other_fields_still_carry_their_own_alerts(self, plugin_for):
        """Adding a key to the view dict must not disturb the three already there."""
        plugin = plugin_for(DEFAULT_LIMITS, {'load': 95, 'freq': 10, 'temperature': 20})

        assert plugin.views['npu0']['load']['decoration'] == 'CRITICAL'
        assert plugin.views['npu0']['freq']['decoration'] == 'OK'
        assert plugin.views['npu0']['temperature']['decoration'] == 'OK'


class TestShippedNpuLimits:
    """The code half is inert without thresholds: `get_alert` returns DEFAULT when a
    stat has none configured, so the shipped config has to carry them for the alert to
    be visible out of the box -- exactly as `[gpu]` already does."""

    @staticmethod
    def _limits(section):
        config = Config(config_dir='./conf/glances.conf')
        return dict(config.as_dict()[section])

    @pytest.mark.parametrize('criticality', ['careful', 'warning', 'critical'])
    def test_the_npu_section_defines_a_temperature_threshold(self, criticality):
        assert f'temperature_{criticality}' in self._limits('npu')

    def test_the_npu_thresholds_match_the_gpu_ones(self):
        """Both read a die temperature in Celsius; two different ladders would be a
        difference with no reason behind it."""
        npu, gpu = self._limits('npu'), self._limits('gpu')

        for criticality in ('careful', 'warning', 'critical'):
            key = f'temperature_{criticality}'
            assert npu[key] == gpu[key]

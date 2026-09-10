#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the Quicklook plugin stats list configuration."""

import os

import pytest

from glances.config import Config
from glances.plugins.quicklook import QuicklookPlugin


@pytest.fixture
def plugin_for(tmp_path):
    """Build a Quicklook plugin from a `[quicklook] list=...` config value."""

    def build(list_value):
        config_file = tmp_path / f'glances-{abs(hash(list_value))}.conf'
        config_file.write_text(f'[quicklook]\nlist={list_value}\n', encoding='utf-8')
        return QuicklookPlugin(args=None, config=Config(config_dir=os.fspath(config_file)))

    return build


class TestQuicklookStatsList:
    def test_a_plain_list_is_honoured(self, plugin_for):
        assert plugin_for('cpu,mem,load').stats_list == ['cpu', 'mem', 'load']

    @pytest.mark.parametrize(
        'list_value',
        [
            'cpu, mem, load',
            'cpu ,mem ,load',
            ' cpu , mem , load ',
            'cpu,\tmem,\tload',
        ],
    )
    def test_whitespace_around_items_is_ignored(self, plugin_for, list_value):
        """`list=cpu, mem, load` is how anyone writes a comma-separated value.

        glances.conf writes it that way in its own `# Available stats are:` comment, so
        a user copying that line got a list where every item but the first carried a
        leading space, matched nothing, and was discarded whole.
        """
        assert plugin_for(list_value).stats_list == ['cpu', 'mem', 'load']

    def test_a_typo_falls_back_to_the_default_not_to_everything(self, plugin_for):
        """A config mistake must not answer by displaying MORE than was asked for.

        The fallback used to be AVAILABLE_STATS_LIST, which includes both GPU entries —
        and those flip the gpu_stats polling flags. A single typo therefore started
        polling the GPU on a machine whose owner never asked for it.
        """
        plugin = plugin_for('cpu,mem,typo')

        assert plugin.stats_list == QuicklookPlugin.DEFAULT_STATS_LIST
        assert 'gpu_mem' not in plugin.stats_list
        assert 'gpu_proc' not in plugin.stats_list

    def test_the_gpu_entries_are_still_selectable_on_purpose(self, plugin_for):
        """The fallback must not become a filter: an explicit request still works."""
        assert plugin_for('cpu,gpu_mem,gpu_proc').stats_list == ['cpu', 'gpu_mem', 'gpu_proc']

    def test_no_list_configured_uses_the_default(self, tmp_path):
        config_file = tmp_path / 'glances-empty.conf'
        config_file.write_text('[quicklook]\ndisable=False\n', encoding='utf-8')
        plugin = QuicklookPlugin(args=None, config=Config(config_dir=os.fspath(config_file)))

        assert plugin.stats_list == QuicklookPlugin.DEFAULT_STATS_LIST


class TestQuicklookPercpuDecoration:
    """Every --percpu bar used to be coloured by the aggregate CPU alert.

    `_msg_create_line` read `views['cpu']['decoration']` for every row, and the WebUI
    read `getDecoration('cpu')` in the same loop, so a core pegged at 100% was drawn
    in the colour of the average across all cores.
    """

    @staticmethod
    def _plugin(tmp_path, cores, max_cpu_display=4):
        config_file = tmp_path / 'glances-percpu.conf'
        config_file.write_text(
            '\n'.join(
                [
                    '[quicklook]',
                    'list=cpu',
                    'cpu_careful=50',
                    'cpu_warning=70',
                    'cpu_critical=90',
                    '[percpu]',
                    f'max_cpu_display={max_cpu_display}',
                ]
            ),
            encoding='utf-8',
        )
        plugin = QuicklookPlugin(args=None, config=Config(config_dir=os.fspath(config_file)))
        plugin.stats = {
            'cpu': sum(cores) / len(cores),
            'percpu': [
                {'key': 'cpu_number', 'cpu_number': number, 'total': total} for number, total in enumerate(cores)
            ],
        }
        plugin.update_views()
        return plugin

    def test_a_busy_core_is_not_hidden_by_a_quiet_average(self, tmp_path):
        """One core at 95% among three idle ones: the aggregate is 24%, an OK value."""
        plugin = self._plugin(tmp_path, [95.0, 1.0, 1.0, 1.0])

        assert plugin.views['cpu']['decoration'] == 'OK'
        assert plugin.views['percpu_decoration']['0'] == 'CRITICAL'
        assert plugin.views['percpu_decoration']['1'] == 'OK'

    @pytest.mark.parametrize(
        ('percent', 'expected'),
        [(0.0, 'OK'), (49.9, 'OK'), (50.0, 'CAREFUL'), (69.9, 'CAREFUL'), (70.0, 'WARNING'), (90.0, 'CRITICAL')],
    )
    def test_each_threshold_boundary(self, tmp_path, percent, expected):
        """The cores use the plugin's own quicklook_cpu_* limits, not a second set."""
        plugin = self._plugin(tmp_path, [percent, 0.0, 0.0, 0.0])

        assert plugin.views['percpu_decoration']['0'] == expected

    def test_the_summary_row_is_styled_by_the_cores_it_averages(self, tmp_path):
        """With more cores than max_cpu_display, both UIs add one averaged row.

        Cores are sorted by load and the four busiest are shown, so the row labelled
        `CPU*` (`x` in the WebUI) always averages the quietest ones. Here its 60% is
        CAREFUL, which is neither the shown cores' CRITICAL nor the 83% aggregate's
        WARNING -- so the assertion fails if the row borrows either.
        """
        plugin = self._plugin(tmp_path, [95.0, 95.0, 95.0, 95.0, 60.0, 60.0])

        assert plugin.views['cpu']['decoration'] == 'WARNING'
        assert plugin.views['percpu_decoration']['0'] == 'CRITICAL'
        assert plugin.views['percpu_decoration']['other'] == 'CAREFUL'

    def test_no_summary_row_when_every_core_is_shown(self, tmp_path):
        plugin = self._plugin(tmp_path, [10.0, 10.0, 10.0, 10.0])

        assert 'other' not in plugin.views['percpu_decoration']

    def test_the_styles_reach_the_curses_bars(self, tmp_path):
        """The wiring, not just the map: `_msg_per_cpu` must use the per-core style.

        Reverting `_msg_create_line` to the aggregate lookup leaves every assertion
        above passing and fails only this one.
        """
        plugin = self._plugin(tmp_path, [95.0, 1.0, 1.0, 1.0])
        data = {'cpu': _StubBar()}

        decorations = [
            line['decoration'] for line in plugin._msg_per_cpu(data, 'cpu', 10) if line['msg'] == _StubBar.RENDERED
        ]

        assert decorations == ['CRITICAL', 'OK', 'OK', 'OK']

    def test_scanning_the_cores_does_not_move_the_global_threshold(self, tmp_path):
        """The per-core styles must not be computed with get_alert().

        get_alert() records a threshold the event list reads and can run a [quicklook]
        action, and both are keyed by 'quicklook_cpu' alone. The per-core pass runs
        after the aggregate one, so calling get_alert() there would leave the last
        core — an idle one here — as the value those two see.

        The values are chosen so the two disagree: the aggregate is 71.5% (WARNING)
        while the last core is 1% (OK).
        """
        from glances.thresholds import glances_thresholds

        self._plugin(tmp_path, [95.0, 95.0, 95.0, 1.0])

        assert glances_thresholds.get()['quicklook_cpu'].description() == 'WARNING'


class _StubBar:
    """Stands in for Bar/Sparkline: `_msg_per_cpu` only sets a value and renders."""

    RENDERED = '<bar>'

    def __init__(self):
        self.percent = None

    def get(self):
        return self.RENDERED


class TestConfigListParsing:
    """The strip belongs to `load_limits`, so every plugin reading a list gets it."""

    def test_limits_carry_stripped_items(self, plugin_for):
        assert plugin_for('cpu, mem, load').get_limits('list') == ['cpu', 'mem', 'load']

    def test_a_hide_pattern_written_with_spaces_still_hides(self, tmp_path):
        """The show/hide filters are the loudest symptom of the same parsing bug.

        Every item in those lists is used as a `re.fullmatch` pattern, so a leading
        space made the pattern match nothing at all — `hide=sda2, loop.*` hid `sda2`
        and silently kept showing every loop device.
        """
        from glances.plugins.diskio import DiskioPlugin

        config_file = tmp_path / 'glances-hide.conf'
        config_file.write_text('[diskio]\nhide=sda2, loop.*\n', encoding='utf-8')
        plugin = DiskioPlugin(args=None, config=Config(config_dir=os.fspath(config_file)))

        assert plugin.get_conf_value('hide') == ['sda2', 'loop.*']
        assert plugin.is_hide('sda2')
        assert plugin.is_hide('loop0')
        assert not plugin.is_hide('sda1')

    def test_internal_spaces_are_kept(self, tmp_path):
        """Only the edges are stripped — a value may legitimately contain spaces."""
        config_file = tmp_path / 'glances-alias.conf'
        config_file.write_text('[quicklook]\nlist=cpu\nalias=sda1:System Disk , sdb1:Data Disk\n', encoding='utf-8')
        plugin = QuicklookPlugin(args=None, config=Config(config_dir=os.fspath(config_file)))

        assert plugin.get_limits('alias') == ['sda1:System Disk', 'sdb1:Data Disk']

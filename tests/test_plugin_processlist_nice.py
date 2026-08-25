#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the NI column of the Processlist plugin (#3672)."""

from unittest.mock import Mock, patch

import pytest

import glances.plugins.processlist as processlist_module
from glances.plugins.processlist import ProcesslistPlugin, nice_to_str

# The six documented Windows priority classes and the label each must show.
# Values are psutil's constants; the labels are the ones Windows itself uses.
WINDOWS_CLASSES = [
    (256, 'RT'),  # REALTIME_PRIORITY_CLASS
    (128, 'Hi'),  # HIGH_PRIORITY_CLASS
    (32768, 'AN'),  # ABOVE_NORMAL_PRIORITY_CLASS
    (32, 'No'),  # NORMAL_PRIORITY_CLASS
    (16384, 'BN'),  # BELOW_NORMAL_PRIORITY_CLASS
    (64, 'Lo'),  # IDLE_PRIORITY_CLASS
]


@pytest.fixture
def plugin():
    """A Processlist plugin whose curses helpers can be called directly."""
    args = Mock(disable_irix=False)
    args.time = 2
    return ProcesslistPlugin(args=args)


def nice_cell(plugin, nice):
    """The NI cell the TUI would draw for *nice*."""
    return plugin._get_process_curses_nice({'nice': nice}, False, Mock())['msg']


class TestNiceToStr:
    @pytest.mark.parametrize(("value", "label"), WINDOWS_CLASSES)
    def test_windows_classes_map_to_their_label(self, value, label):
        with patch.object(processlist_module, 'WINDOWS', True):
            assert nice_to_str(value) == label

    @pytest.mark.parametrize(("value", "label"), WINDOWS_CLASSES)
    def test_other_platforms_are_untouched(self, value, label):
        # A nice level of 32 on Linux is a nice level, not a priority class.
        with patch.object(processlist_module, 'WINDOWS', False):
            assert nice_to_str(value) == value

    def test_unknown_windows_class_stays_visible(self):
        # Blanking it would hide a value psutil started returning; showing the
        # number keeps the reporter honest even when the table is out of date.
        with patch.object(processlist_module, 'WINDOWS', True):
            assert nice_to_str(99999) == 99999

    def test_missing_value_passes_through(self):
        # `_get_process_curses_nice` substitutes '?' before formatting.
        with patch.object(processlist_module, 'WINDOWS', True):
            assert nice_to_str('?') == '?'


class TestNiceColumn:
    @pytest.mark.parametrize(("value", "label"), WINDOWS_CLASSES)
    def test_every_class_fits_the_column_on_windows(self, plugin, value, label):
        # The column is '{:>3} '. Before the fix, 32768 and 16384 rendered six
        # characters into it and pushed every column to their right out of line.
        with patch.object(processlist_module, 'WINDOWS', True):
            cell = nice_cell(plugin, value)
        assert cell == f'{label:>3} '
        assert len(cell) == 4

    def test_wide_classes_overflowed_before(self, plugin):
        # The regression itself: off Windows these stay numbers, and the two
        # five-digit ones are exactly the pair that did not fit.
        with patch.object(processlist_module, 'WINDOWS', False):
            assert len(nice_cell(plugin, 32768)) == 6
            assert len(nice_cell(plugin, 16384)) == 6
        with patch.object(processlist_module, 'WINDOWS', True):
            assert len(nice_cell(plugin, 32768)) == 4
            assert len(nice_cell(plugin, 16384)) == 4

    def test_linux_nice_levels_are_not_relabelled(self, plugin):
        with patch.object(processlist_module, 'WINDOWS', False):
            assert nice_cell(plugin, 0) == '  0 '
            assert nice_cell(plugin, -20) == '-20 '
            assert nice_cell(plugin, 19) == ' 19 '

    def test_none_is_still_a_question_mark(self, plugin):
        for windows in (True, False):
            with patch.object(processlist_module, 'WINDOWS', windows):
                assert nice_cell(plugin, None) == '  ? '

    def test_alert_reads_the_raw_value_not_the_label(self, plugin):
        # The nice_* thresholds in glances.conf are numbers. Handing the alert a
        # label instead would silently disable every one of them on Windows.
        seen = []
        with patch.object(processlist_module, 'WINDOWS', True):
            with patch.object(ProcesslistPlugin, 'get_nice_alert', lambda self, v: seen.append(v)):
                nice_cell(plugin, 32768)
        assert seen == [32768]

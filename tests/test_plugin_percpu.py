#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the PerCPU plugin."""

import re
from unittest.mock import MagicMock

import pytest

from glances.plugins.percpu import PercpuPlugin


def build_plugin(totals, max_cpu_display=4):
    """Return a PerCPU plugin seeded with one core per entry in `totals`."""
    args = MagicMock()
    args.percpu = True
    plugin = PercpuPlugin(args=args, config=None)
    plugin.max_cpu_display = max_cpu_display
    plugin.stats = [
        {'key': 'cpu_number', 'cpu_number': number, 'total': total, 'user': total, 'system': 0.0}
        for number, total in enumerate(totals)
    ]
    return plugin


def summary_percentages(plugin, header=None):
    """Render the real CPU* row and return the percentages it prints."""
    percpu_list = plugin.manage_max_cpu_to_display()
    row = plugin.summarize_all_cpus_not_displayed(percpu_list, header or ['total'], [])
    return [float(value) for value in re.findall(r'(-?\d+\.\d)%', ''.join(part['msg'] for part in row))]


def displayed_percentages(plugin, stat='total'):
    """The cores msg_curse prints above the summary row."""
    percpu_list = plugin.manage_max_cpu_to_display()
    return [i[stat] for i in percpu_list[0 : plugin.max_cpu_display]]


class TestPercpuSummaryRow:
    """The CPU* row summarizes the cores that did NOT fit on screen."""

    def test_summary_is_the_leftover_mean_not_the_displayed_mean(self):
        # Four busy cores fill the display; four idle ones are left over. Averaging the
        # displayed slice reported 87.0% for a group of cores sitting at 2.0%, and
        # repeated a figure already visible one line above.
        plugin = build_plugin([90.0, 88.0, 86.0, 84.0, 2.0, 2.0, 2.0, 2.0])

        assert summary_percentages(plugin) == [2.0]
        assert 87.0 not in summary_percentages(plugin)

    def test_summary_ignores_the_displayed_cores_entirely(self):
        # Same leftovers, wildly different displayed values: the summary must not move.
        idle_tail = [5.0, 5.0, 5.0, 5.0]
        quiet = build_plugin([10.0, 9.0, 8.0, 7.0] + idle_tail)
        busy = build_plugin([99.0, 99.0, 99.0, 99.0] + idle_tail)

        assert summary_percentages(quiet) == summary_percentages(busy) == [5.0]

    def test_summary_averages_rather_than_sums(self):
        plugin = build_plugin([90.0, 88.0, 86.0, 84.0, 10.0, 20.0, 30.0, 40.0])
        assert summary_percentages(plugin)[0] == pytest.approx(25.0)

    def test_summary_covers_every_core_that_is_not_displayed(self):
        # A single leftover core must be reported as itself, not diluted or dropped.
        plugin = build_plugin([90.0, 88.0, 86.0, 84.0, 42.0])
        assert summary_percentages(plugin) == [42.0]
        assert 42.0 not in displayed_percentages(plugin)

    def test_one_percentage_per_header_column(self):
        plugin = build_plugin([90.0, 88.0, 86.0, 84.0, 2.0, 6.0])
        # 'total' and 'user' hold the same value here, 'system' is 0.0 for every core.
        assert summary_percentages(plugin, header=['total', 'user', 'system']) == [4.0, 4.0, 0.0]

    def test_no_summary_row_when_every_core_fits(self):
        plugin = build_plugin([10.0, 20.0], max_cpu_display=4)
        assert plugin.summarize_all_cpus_not_displayed(plugin.stats, ['total'], []) == []

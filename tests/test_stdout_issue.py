#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the --issue diagnostic output."""

from glances.outputs.glances_stdout_issue import GlancesStdoutIssue


def test_top_slowest_plugins_are_sorted_and_limited(capsys):
    """The diagnostic table displays at most ten plugins, slowest first."""
    screen = GlancesStdoutIssue()
    durations = [(f"plugin-{index}", float(index)) for index in range(12)]

    screen.print_top_slowest_plugins(durations)

    lines = capsys.readouterr().out.splitlines()
    assert lines[:2] == ["Top 10 slowest plugins:", "Plugin                         Update duration"]  # nosec B101
    assert lines[2].split() == ["plugin-11", "11.00000s"]  # nosec B101
    assert lines[-1].split() == ["plugin-2", "2.00000s"]  # nosec B101
    assert "plugin-1" not in lines  # nosec B101
    assert "plugin-0" not in lines  # nosec B101

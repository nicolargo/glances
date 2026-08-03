#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — unit tests for the `amps` curses renderer."""

from __future__ import annotations

from glances.outputs.curses_renderer_v5 import ColorRole
from glances.plugins.amps.render_curses_v5 import render


def _payload(items, levels=None):
    return {"data": items, "_levels": levels or {}}


def test_empty_payload_renders_nothing():
    assert render(_payload([])) == []


def test_amp_without_result_is_skipped():
    """v4 `msg_curse` skips an AMP whose result is still None."""
    rows = render(_payload([{"name": "Python", "result": None, "count": 1, "regex": True}]))
    assert rows == []


def test_no_title_row_deliberate_do_not_fix():
    """v4 `amps.msg_curse` emits no title and no column header — the block
    sits between `processcount` and `processlist` and reads as part of that
    run. The missing title is that continuity, not an oversight."""
    rows = render(_payload([{"name": "Python", "result": "CPU: 1.0%", "count": 1, "regex": True}]))
    assert len(rows) == 1
    assert rows[0].cells[0].text.strip() == "Python"


def test_three_columns_name_count_result():
    rows = render(_payload([{"name": "Python", "result": "CPU: 1.0% | MEM: 2.0%", "count": 2, "regex": True}]))
    assert len(rows) == 1
    assert [c.text.strip() for c in rows[0].cells] == ["Python", "2", "CPU: 1.0% | MEM: 2.0%"]


def test_count_column_is_blank_without_a_regex():
    rows = render(_payload([{"name": "Conntrack", "result": "tracked: 12", "count": 0, "regex": False}]))
    assert rows[0].cells[1].text.strip() == ""


def test_multiline_result_repeats_neither_name_nor_count():
    rows = render(
        _payload([{"name": "Systemd", "result": "Services\nactive: 3\nfailed: 1", "count": 1, "regex": True}])
    )
    assert len(rows) == 3
    assert [c.text.strip() for c in rows[0].cells] == ["Systemd", "1", "Services"]
    assert [c.text.strip() for c in rows[1].cells] == ["", "", "active: 3"]
    assert [c.text.strip() for c in rows[2].cells] == ["", "", "failed: 1"]


def test_name_is_coloured_from_the_count_level():
    rows = render(
        _payload(
            [{"name": "Python", "result": "CPU: 1.0%", "count": 0, "regex": True}],
            {"Python": {"count": {"level": "critical", "prominent": False}}},
        )
    )
    assert rows[0].cells[0].color is ColorRole.CRITICAL
    assert rows[0].cells[0].prominent is False


def test_missing_level_falls_back_to_default_colour():
    rows = render(_payload([{"name": "Python", "result": "CPU: 1.0%", "count": 1, "regex": True}]))
    assert rows[0].cells[0].color is ColorRole.DEFAULT


def test_continuation_rows_are_not_coloured():
    rows = render(
        _payload(
            [{"name": "Systemd", "result": "Services\nfailed: 1", "count": 0, "regex": True}],
            {"Systemd": {"count": {"level": "critical", "prominent": False}}},
        )
    )
    assert rows[0].cells[0].color is ColorRole.CRITICAL
    assert rows[1].cells[0].color is ColorRole.DEFAULT

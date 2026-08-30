#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — tests for the wifi curses renderer."""

from __future__ import annotations

from glances.plugins.wifi.render_curses_v5 import (
    _LEFT_SIDEBAR_MAX_WIDTH,
    _NAME_MAX_WIDTH,
    _VALUE_COL_WIDTH,
    render,
)


def _payload(rows, levels=None):
    return {"data": rows, "_levels": levels or {}}


def _flat(rows):
    return "\n".join(" ".join(c.text for c in r.cells) for r in rows)


def _wifi(ssid, link, level):
    return {"ssid": ssid, "quality_link": link, "quality_level": level}


def test_empty_returns_header_only():
    rows = render(_payload([]))
    assert "WIFI" in _flat(rows)
    assert len(rows) == 1  # header only


def test_header_and_one_row():
    rows = render(_payload([_wifi("wlan0", -50, -60)]))
    flat = _flat(rows)
    assert "WIFI" in flat
    assert "dBm" in flat
    assert "wlan0" in flat
    assert "-60" in flat


def test_rows_sorted_by_ssid():
    rows = render(_payload([_wifi("wlan1", -50, -60), _wifi("wlan0", -40, -55)]))
    flat = _flat(rows)
    assert flat.index("wlan0") < flat.index("wlan1")


def test_skip_empty_ssid():
    rows = render(_payload([_wifi("", -50, -60)]))
    assert len(rows) == 1  # header only, row skipped


def test_skip_none_quality_level():
    rows = render(_payload([_wifi("wlan0", -50, None)]))
    assert "wlan0" not in _flat(rows)


def test_level_colour_applied():
    levels = {"wlan0": {"quality_level": {"level": "critical", "prominent": False}}}
    rows = render(_payload([_wifi("wlan0", -50, -90)], levels))
    value_cells = [c for r in rows for c in r.cells if "-90" in c.text]
    assert value_cells and value_cells[0].color.value == "critical"
    assert value_cells[0].prominent is False


def test_skip_non_numeric_quality_level():
    # A stray non-None, non-numeric signal must be skipped, not crash the
    # `f"{quality_level:.0f}"` format (renderer robustness independent of the
    # model's float/None guarantee).
    rows = render(_payload([_wifi("wlan0", -50, "N/A")]))
    assert "wlan0" not in _flat(rows)
    assert len(rows) == 1  # header only


def test_row_fits_left_sidebar_budget():
    assert _NAME_MAX_WIDTH + 1 + _VALUE_COL_WIDTH <= _LEFT_SIDEBAR_MAX_WIDTH
    rows = render(_payload([_wifi("wlan0", -50, -60)]))
    label_cell, value_cell = rows[1].cells
    assert len(label_cell.text) + 1 + len(value_cell.text) <= _LEFT_SIDEBAR_MAX_WIDTH
    # Over-long ssid (> _NAME_MAX_WIDTH) exercises _format_name's truncation
    # branch — the label must be clamped to the column so the block still fits.
    long_ssid = "W" * (_NAME_MAX_WIDTH + 12)
    rows = render(_payload([_wifi(long_ssid, -50, -60)]))
    label_cell, value_cell = rows[1].cells
    assert len(label_cell.text) == _NAME_MAX_WIDTH  # truncated, not overflowing
    assert len(label_cell.text) + 1 + len(value_cell.text) <= _LEFT_SIDEBAR_MAX_WIDTH


def test_item_rows_are_marked_for_the_truncation_counter():
    rows = render(_payload([_wifi("wlan0", -50, -60), _wifi("wlan1", -40, -55)]))
    assert rows[0].item_start is False  # header
    assert sum(r.item_start for r in rows) == 2


def test_skipped_items_are_not_counted():
    """A skipped SSID must not inflate the counter's total."""
    rows = render(_payload([_wifi("wlan0", -50, -60), _wifi("", -40, -55)]))
    assert sum(r.item_start for r in rows) == 1

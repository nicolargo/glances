#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the Glances v5 connections TUI renderer."""

from __future__ import annotations

from glances.outputs.curses_renderer_v5 import ColorRole
from glances.plugins.connections.render_curses_v5 import render


def _payload(**over):
    base = {
        "net_connections_enabled": True,
        "nf_conntrack_enabled": True,
        "LISTEN": 3,
        "ESTABLISHED": 12,
        "initiated": 0,
        "terminated": 204,
        "nf_conntrack_count": 512,
        "nf_conntrack_max": 1024,
        "_levels": {"nf_conntrack_percent": {"level": "ok", "prominent": True}},
    }
    base.update(over)
    return base


def _flat(rows):
    return " ".join(c.text for r in rows for c in r.cells)


def test_empty_payload_returns_nothing():
    assert render({}) == []


def test_both_sources_disabled_returns_nothing():
    payload = _payload(net_connections_enabled=False, nf_conntrack_enabled=False)
    assert render(payload) == []


def test_title_row_is_header_and_bold():
    rows = render(_payload())
    assert rows[0].cells[0].text == "TCP CONNECTIONS"
    assert rows[0].cells[0].color == ColorRole.HEADER
    assert rows[0].cells[0].bold is True


def test_rows_in_fixed_order():
    rows = render(_payload())
    labels = [row.cells[0].text.strip() for row in rows[1:5]]
    assert labels == ["Listen", "Initiated", "Established", "Terminated"]


def test_missing_key_row_is_skipped():
    payload = _payload()
    del payload["terminated"]
    rows = render(payload)
    labels = [row.cells[0].text.strip() for row in rows]
    assert "Terminated" not in labels


def test_net_connections_disabled_hides_state_rows():
    payload = _payload(net_connections_enabled=False)
    flat = _flat(render(payload))
    for label in ("Listen", "Initiated", "Established", "Terminated"):
        assert label not in flat
    assert "TCP CONNECTIONS" in flat
    assert "Tracked" in flat


def test_tracked_row_shown_when_enabled_and_present():
    rows = render(_payload())
    tracked = [row for row in rows if row.cells[0].text.strip() == "Tracked"]
    assert len(tracked) == 1
    assert tracked[0].cells[1].text.strip() == "512/1024"


def test_tracked_row_hidden_when_conntrack_disabled():
    payload = _payload(nf_conntrack_enabled=False)
    assert "Tracked" not in _flat(render(payload))


def test_tracked_row_hidden_when_count_missing():
    payload = _payload()
    del payload["nf_conntrack_count"]
    assert "Tracked" not in _flat(render(payload))


def test_tracked_row_hidden_when_max_missing():
    payload = _payload()
    del payload["nf_conntrack_max"]
    assert "Tracked" not in _flat(render(payload))


def test_tracked_row_renders_default_when_levels_key_absent():
    """`_levels` missing entirely (not merely emptied) must not crash and
    must fall back to the default, uncoloured, non-prominent cell."""
    payload = _payload()
    del payload["_levels"]
    rows = render(payload)
    tracked = [row for row in rows if row.cells[0].text.strip() == "Tracked"][0]
    assert tracked.cells[1].text.strip() == "512/1024"
    assert tracked.cells[1].color == ColorRole.DEFAULT
    assert tracked.cells[1].prominent is False


def test_tracked_row_colour_reflects_level():
    payload = _payload(_levels={"nf_conntrack_percent": {"level": "warning", "prominent": True}})
    rows = render(payload)
    tracked = [row for row in rows if row.cells[0].text.strip() == "Tracked"][0]
    assert tracked.cells[1].color == ColorRole.WARNING


def test_tracked_row_prominent_forwarded_when_levels_carry_it():
    payload = _payload(_levels={"nf_conntrack_percent": {"level": "critical", "prominent": True}})
    rows = render(payload)
    tracked = [row for row in rows if row.cells[0].text.strip() == "Tracked"][0]
    assert tracked.cells[1].prominent is True


def test_tracked_row_prominent_not_set_when_levels_lack_it():
    payload = _payload(_levels={"nf_conntrack_percent": {"level": "critical"}})
    rows = render(payload)
    tracked = [row for row in rows if row.cells[0].text.strip() == "Tracked"][0]
    assert tracked.cells[1].prominent is False


def test_state_rows_never_coloured():
    payload = _payload(_levels={"nf_conntrack_percent": {"level": "critical", "prominent": True}})
    rows = render(payload)
    for row in rows:
        label = row.cells[0].text.strip()
        if label in ("TCP CONNECTIONS", "Tracked"):
            continue
        for cell in row.cells:
            assert cell.color == ColorRole.DEFAULT


def test_row_width_matches_34_char_budget():
    rows = render(_payload())
    for row in rows[1:]:
        assert len(row.cells[0].text) + len(row.cells[1].text) == 33


def test_value_cells_are_right_aligned():
    """Guard against a broken implementation that left-pads or centres the
    value: every data row's value cell must be right-flushed, i.e. its
    stripped text sits at the END of the raw cell text."""
    rows = render(_payload())
    for row in rows[1:]:
        value_cell_text = row.cells[1].text
        stripped = value_cell_text.strip()
        assert value_cell_text.endswith(stripped)
        # Right-aligned means padding (if any) is all on the left.
        assert value_cell_text == value_cell_text.lstrip().rjust(len(value_cell_text))


def test_label_cells_are_left_aligned_not_right():
    """A label right-flushed instead of left-flushed would still pass a
    naive 'contains substring' check — assert the label starts at index 0."""
    rows = render(_payload())
    for row in rows[1:]:
        label_cell_text = row.cells[0].text
        stripped = label_cell_text.strip()
        assert label_cell_text.startswith(stripped)

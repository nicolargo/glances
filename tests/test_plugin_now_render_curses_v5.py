"""Glances v5 — tests for the now curses renderer (header block, far right)."""

from __future__ import annotations

from glances.plugins.now.render_curses_v5 import render

NOW_FIELDS = {"custom": {"unit": "string"}, "iso": {"unit": "string"}}


def test_render_shows_custom_only_unpadded():
    # Use +0200 (numeric offset) so the custom string has no literal 'T',
    # which guards against accidentally rendering the ISO field (e.g.
    # "2026-06-06T12:00:00+02:00" has 'T' as the date/time separator).
    payload = {"custom": "2026-06-06 12:00:00 +0200", "iso": "2026-06-06T12:00:00+02:00", "_levels": {}}
    rows = render(payload, NOW_FIELDS)
    assert len(rows) == 1
    text = rows[0].cells[0].text
    # No padding: the block is right-aligned in the header, so trailing blanks
    # would push the date away from the right edge.
    assert text == "2026-06-06 12:00:00 +0200"
    assert "T" not in text


def test_render_short_date_is_not_padded():
    """A date shorter than v4's 23-char process-list padding stays bare."""
    rows = render({"custom": "12:00:00"}, NOW_FIELDS)
    assert rows[0].cells[0].text == "12:00:00"


def test_render_empty_payload_yields_no_rows():
    assert render({}, NOW_FIELDS) == []

"""Glances v5 — tests for the now curses renderer (left-sidebar one-liner)."""

from __future__ import annotations

from glances.plugins.now.render_curses_v5 import render

NOW_FIELDS = {"custom": {"unit": "string"}, "iso": {"unit": "string"}}


def test_render_shows_custom_only_padded():
    # Use +0200 (numeric offset) so the custom string has no literal 'T',
    # which guards against accidentally rendering the ISO field (e.g.
    # "2026-06-06T12:00:00+02:00" has 'T' as the date/time separator).
    payload = {"custom": "2026-06-06 12:00:00 +0200", "iso": "2026-06-06T12:00:00+02:00", "_levels": {}}
    rows = render(payload, NOW_FIELDS)
    assert len(rows) == 1
    text = rows[0].cells[0].text
    assert text.startswith("2026-06-06 12:00:00 +0200")
    assert len(text) >= 23
    assert "T" not in text


def test_render_empty_payload_yields_no_rows():
    assert render({}, NOW_FIELDS) == []

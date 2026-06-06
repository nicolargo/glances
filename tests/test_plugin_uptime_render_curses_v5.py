"""Glances v5 — tests for the uptime curses renderer (header-right block)."""

from __future__ import annotations

from glances.plugins.uptime.render_curses_v5 import render

UPTIME_FIELDS = {"seconds": {"unit": "seconds"}}


def test_render_shows_uptime_label_and_value():
    rows = render({"seconds": 273_840, "_levels": {}}, UPTIME_FIELDS)  # 3d04h
    assert len(rows) == 1
    flat = " ".join(c.text for c in rows[0].cells)
    assert "Uptime:" in flat
    assert "3d04h" in flat


def test_render_empty_payload_yields_no_rows():
    assert render({}, UPTIME_FIELDS) == []

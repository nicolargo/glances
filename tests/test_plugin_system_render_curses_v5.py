"""Glances v5 — tests for the system curses renderer (header-left block)."""

from __future__ import annotations

from glances.outputs.curses_renderer_v5 import ColorRole
from glances.plugins.system.render_curses_v5 import render

SYSTEM_FIELDS = {
    "hostname": {"unit": "string"},
    "hr_name": {"unit": "string"},
}


def test_render_shows_hostname_as_header_and_hr_name():
    payload = {"hostname": "myhost", "hr_name": "Ubuntu 24.04 64bit", "_levels": {}}
    rows = render(payload, SYSTEM_FIELDS)
    assert len(rows) == 1
    cells = rows[0].cells
    assert cells[0].text == "myhost"
    assert cells[0].color == ColorRole.HEADER
    flat = " ".join(c.text for c in cells)
    assert "Ubuntu 24.04 64bit" in flat


def test_render_empty_payload_yields_no_rows():
    assert render({}, SYSTEM_FIELDS) == []

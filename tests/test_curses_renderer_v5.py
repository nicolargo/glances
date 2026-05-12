"""Glances v5 — tests for the pure curses renderer."""

from __future__ import annotations

from glances.outputs.curses_renderer_v5 import (
    Cell,
    ColorRole,
    Row,
    render_scalar_plugin,
)

# ---------------------------------------------------------------- dataclasses


def test_cell_defaults_to_default_color():
    cell = Cell(text="42")
    assert cell.color == ColorRole.DEFAULT


def test_row_holds_cells():
    row = Row(cells=[Cell("A"), Cell("B")])
    assert [c.text for c in row.cells] == ["A", "B"]


# ---------------------------------------------------------------- scalar plugin


MEM_FIELDS = {
    "total": {"unit": "bytes", "label": "total"},
    "available": {"unit": "bytes", "label": "avail"},
    "percent": {
        "unit": "percent",
        "label": "MEM",
        "watched": True,
        "prominent": True,
    },
    "used": {"unit": "bytes", "label": "used"},
    "free": {"unit": "bytes", "label": "free"},
}


def _mem_payload(level: str = "ok") -> dict:
    return {
        "total": 16_000_000_000,
        "available": 8_000_000_000,
        "percent": 72.0,
        "used": 8_000_000_000,
        "free": 4_000_000_000,
        "_levels": {"percent": {"level": level, "prominent": True}},
    }


def test_render_scalar_returns_at_least_one_row():
    rows = render_scalar_plugin("mem", _mem_payload(), MEM_FIELDS)
    assert len(rows) >= 1


def test_render_scalar_header_includes_plugin_label():
    """The first row carries the plugin's prominent label ('MEM') in upper-case."""
    rows = render_scalar_plugin("mem", _mem_payload(), MEM_FIELDS)
    header = rows[0]
    joined = " ".join(c.text for c in header.cells)
    assert "MEM" in joined


def test_render_scalar_shows_percent_value():
    rows = render_scalar_plugin("mem", _mem_payload(), MEM_FIELDS)
    flat = " ".join(c.text for row in rows for c in row.cells)
    assert "72.0%" in flat


def test_render_scalar_formats_bytes_fields():
    rows = render_scalar_plugin("mem", _mem_payload(), MEM_FIELDS)
    flat = " ".join(c.text for row in rows for c in row.cells)
    # 16 GB total
    assert "14.9G" in flat or "15.9G" in flat  # 16_000_000_000 / 1024^3 ≈ 14.9


def test_render_scalar_applies_warning_color_on_watched_field():
    rows = render_scalar_plugin("mem", _mem_payload(level="warning"), MEM_FIELDS)
    percent_cells = [c for row in rows for c in row.cells if "%" in c.text]
    assert percent_cells
    assert percent_cells[0].color == ColorRole.WARNING


def test_render_scalar_applies_critical_color_with_prominent():
    rows = render_scalar_plugin("mem", _mem_payload(level="critical"), MEM_FIELDS)
    percent_cells = [c for row in rows for c in row.cells if "%" in c.text]
    assert percent_cells[0].color == ColorRole.CRITICAL
    # prominent=True triggers background-highlight rendering — exposed as
    # the `prominent` flag on the cell so the curses layer can pick the
    # right attribute (A_REVERSE vs plain colour).
    assert percent_cells[0].prominent is True


def test_render_scalar_handles_empty_payload():
    """Cycle-0: plugin registered but no data yet."""
    rows = render_scalar_plugin("mem", {}, MEM_FIELDS)
    flat = " ".join(c.text for row in rows for c in row.cells)
    assert "MEM" in flat  # header still rendered
    # No percent value — should not crash.


def test_render_scalar_honours_explicit_format_hint():
    fields = {
        "percent": {"unit": "percent", "label": "CPU", "format": "%.3f%%"},
    }
    rows = render_scalar_plugin("cpu", {"percent": 12.345}, fields)
    flat = " ".join(c.text for row in rows for c in row.cells)
    assert "12.345%" in flat

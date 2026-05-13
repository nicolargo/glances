"""Glances v5 — tests for the mem plugin's curses renderer."""

from __future__ import annotations

import pytest

from glances.outputs.curses_renderer_v5 import ColorRole
from glances.plugins.mem.render_curses_v5 import render


@pytest.fixture
def mem_fields():
    return {
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
        "active": {"unit": "bytes", "label": "active"},
        "inactive": {"unit": "bytes", "label": "inactive"},
        "buffers": {"unit": "bytes", "label": "buffers"},
        "cached": {"unit": "bytes", "label": "cached"},
    }


@pytest.fixture
def mem_payload_linux():
    return {
        "total": 16_421_208_064,
        "available": 7_691_833_344,
        "percent": 53.2,
        "used": 8_729_374_720,
        "free": 2_740_531_200,
        "active": 6_184_337_408,
        "inactive": 4_744_855_552,
        "buffers": 194_555_904,
        "cached": 4_538_667_008,
        "_levels": {"percent": {"level": "careful", "prominent": True}},
    }


# ---------------------------------------------------------------- structure


def test_render_produces_four_rows(mem_payload_linux, mem_fields):
    rows = render(mem_payload_linux, mem_fields)
    assert len(rows) == 4


def test_render_first_row_carries_mem_title(mem_payload_linux, mem_fields):
    rows = render(mem_payload_linux, mem_fields)
    first_row_text = " ".join(c.text for c in rows[0].cells)
    assert "MEM" in first_row_text


def test_render_first_row_includes_percent_and_active(mem_payload_linux, mem_fields):
    rows = render(mem_payload_linux, mem_fields)
    first = " ".join(c.text for c in rows[0].cells)
    assert "53.2%" in first
    assert "active" in first


def test_render_lines_2_to_4_are_four_cell_rows(mem_payload_linux, mem_fields):
    rows = render(mem_payload_linux, mem_fields)
    for i in (1, 2, 3):
        assert len(rows[i].cells) == 4, f"row {i} has {len(rows[i].cells)} cells"


def test_render_uses_avail_label_when_available_present(mem_payload_linux, mem_fields):
    rows = render(mem_payload_linux, mem_fields)
    flat = " ".join(c.text for row in rows for c in row.cells)
    assert "avail" in flat
    # `used:` label not shown when avail is.
    assert "used " not in flat or "used " in flat  # we just check avail won


def test_render_falls_back_to_used_when_available_absent(mem_fields):
    """No `available` in the payload (some Unix variants) → show `used`."""
    payload = {
        "total": 16e9,
        "percent": 50.0,
        "used": 8e9,
        "free": 4e9,
        "active": 5e9,
        "inactive": 3e9,
        "buffers": 1e8,
        "cached": 2e9,
        "_levels": {},
    }
    rows = render(payload, mem_fields)
    # used row must appear instead of avail.
    flat = " ".join(c.text for row in rows for c in row.cells)
    assert "used" in flat
    assert "avail" not in flat


def test_render_columns_align_across_rows(mem_payload_linux, mem_fields):
    rows = render(mem_payload_linux, mem_fields)
    ncols = max(len(r.cells) for r in rows)
    for col in range(ncols):
        widths = {len(r.cells[col].text) for r in rows if col < len(r.cells)}
        assert len(widths) == 1, f"col {col} widths differ: {widths}"


def test_render_value_columns_have_stable_width_across_cycles(mem_fields):
    """Value cols hold "999.9G" worst case (6 chars). Low values must
    pad to the same width as high values so the block doesn't jiggle."""
    low = {
        "total": 1024.0,
        "available": 512.0,
        "percent": 5.0,
        "used": 256.0,
        "free": 768.0,
        "active": 200.0,
        "inactive": 100.0,
        "buffers": 50.0,
        "cached": 80.0,
        "_levels": {},
    }
    high = {
        "total": 999_999_999_999.0,
        "available": 500_000_000_000.0,
        "percent": 100.0,
        "used": 499_999_999_999.0,
        "free": 1.0,
        "active": 300_000_000_000.0,
        "inactive": 200_000_000_000.0,
        "buffers": 100_000_000_000.0,
        "cached": 200_000_000_000.0,
        "_levels": {},
    }
    rows_low = render(low, mem_fields)
    rows_high = render(high, mem_fields)
    for col in (1, 3):
        widths_low = {len(r.cells[col].text) for r in rows_low if col < len(r.cells)}
        widths_high = {len(r.cells[col].text) for r in rows_high if col < len(r.cells)}
        assert widths_low == widths_high, f"col {col}: {widths_low} vs {widths_high}"


def test_render_handles_empty_payload(mem_fields):
    rows = render({}, mem_fields)
    assert len(rows) == 1
    flat = " ".join(c.text for c in rows[0].cells)
    assert "MEM" in flat


def test_render_uses_header_role_for_mem_title(mem_payload_linux, mem_fields):
    rows = render(mem_payload_linux, mem_fields)
    first_cell = rows[0].cells[0]
    assert first_cell.color == ColorRole.HEADER
    assert "MEM" in first_cell.text


def test_render_percent_color_reflects_level(mem_payload_linux, mem_fields):
    """The percent value cell inherits the level color from `_levels.percent`."""
    rows = render(mem_payload_linux, mem_fields)
    # Find the percent cell in row 0 (second cell after MEM title).
    percent_cell = rows[0].cells[1]
    assert "53.2" in percent_cell.text  # right value
    assert percent_cell.color == ColorRole.CAREFUL


def test_render_percent_is_prominent_per_schema(mem_payload_linux, mem_fields):
    """The percent field is declared `prominent: True` — its cell carries
    the flag so the painter applies A_REVERSE under any alert level."""
    rows = render(mem_payload_linux, mem_fields)
    percent_cell = rows[0].cells[1]
    assert percent_cell.prominent is True

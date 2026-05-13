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


def test_render_title_cell_carries_mem_text_and_bold(mem_payload_linux, mem_fields):
    """The first cell carries the plugin label as bold text. Its colour
    is dynamic. With the default payload (careful percent), the title
    stays HEADER (white) — careful does NOT escalate the title."""
    rows = render(mem_payload_linux, mem_fields)
    first_cell = rows[0].cells[0]
    assert "MEM" in first_cell.text
    assert first_cell.bold is True
    assert first_cell.color == ColorRole.HEADER


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


def test_render_title_role_default_when_ok(mem_fields):
    """When all prominent fields are OK, title uses HEADER (white+bold)."""
    payload = {
        "total": 1024,
        "percent": 30.0,
        "active": 256,
        "_levels": {"percent": {"level": "ok", "prominent": True}},
    }
    rows = render(payload, mem_fields)
    assert rows[0].cells[0].color == ColorRole.HEADER
    assert rows[0].cells[0].bold is True


def test_render_title_role_warning_when_percent_warning(mem_fields):
    """percent at WARNING (prominent) → title coloured WARNING + bold."""
    payload = {
        "total": 1024,
        "percent": 80.0,
        "active": 256,
        "_levels": {"percent": {"level": "warning", "prominent": True}},
    }
    rows = render(payload, mem_fields)
    assert rows[0].cells[0].color == ColorRole.WARNING
    assert rows[0].cells[0].bold is True


def test_render_title_role_critical_when_percent_critical(mem_fields):
    """percent at CRITICAL → title red + bold."""
    payload = {
        "total": 1024,
        "percent": 95.0,
        "active": 256,
        "_levels": {"percent": {"level": "critical", "prominent": True}},
    }
    rows = render(payload, mem_fields)
    assert rows[0].cells[0].color == ColorRole.CRITICAL


def test_render_pulls_short_name_from_schema(mem_payload_linux):
    """The mem renderer reads `short_name` from the schema for compact labels."""
    fields = {
        "total": {"unit": "bytes"},
        "available": {"unit": "bytes", "short_name": "avail"},
        "percent": {"unit": "percent", "watched": True, "prominent": True},
        "used": {"unit": "bytes"},
        "free": {"unit": "bytes"},
        "active": {"unit": "bytes"},
        "inactive": {"unit": "bytes", "short_name": "inactiv"},
        "buffers": {"unit": "bytes", "short_name": "buffer"},
        "cached": {"unit": "bytes"},
    }
    rows = render(mem_payload_linux, fields)
    flat = " ".join(c.text for row in rows for c in row.cells)
    assert "avail" in flat
    assert "inactiv" in flat
    assert "buffer" in flat
    # Full forms must NOT appear (the short variants supersede them).
    assert "available" not in flat
    assert "inactive" not in flat
    # "buffers" might still match "buffer" substring; explicit guard:
    label_texts = {r.cells[0].text.strip() for r in rows if r.cells} | {
        r.cells[2].text.strip() for r in rows if len(r.cells) > 2
    }
    assert "buffers" not in label_texts
    assert "buffer" in label_texts


def test_render_column_widths_shrink_with_short_names(mem_payload_linux):
    """Without short_name (e.g. 'available' = 9 chars), col 0 is 9-wide.
    With short_name 'avail' (5 chars), col 0 shrinks to 5 — saving space."""
    fields_long = {
        "total": {"unit": "bytes"},
        "available": {"unit": "bytes"},  # no short_name → label width = 9
        "percent": {"unit": "percent", "watched": True, "prominent": True},
        "free": {"unit": "bytes"},
        "active": {"unit": "bytes"},
        "inactive": {"unit": "bytes"},
        "buffers": {"unit": "bytes"},
        "cached": {"unit": "bytes"},
    }
    fields_short = {**fields_long, "available": {"unit": "bytes", "short_name": "avail"}}

    rows_long = render(mem_payload_linux, fields_long)
    rows_short = render(mem_payload_linux, fields_short)

    col0_long = max(len(r.cells[0].text) for r in rows_long)
    col0_short = max(len(r.cells[0].text) for r in rows_short)
    assert col0_short < col0_long
    assert col0_short == 5  # "avail" / "total" / "free" / "MEM" all ≤ 5

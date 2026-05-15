"""Glances v5 — tests for the memswap plugin's curses renderer."""

from __future__ import annotations

import pytest

from glances.outputs.curses_renderer_v5 import ColorRole
from glances.plugins.memswap.render_curses_v5 import render


@pytest.fixture
def memswap_fields():
    return {
        "total": {"unit": "bytes"},
        "used": {"unit": "bytes"},
        "free": {"unit": "bytes"},
        "percent": {
            "unit": "percent",
            "watched": True,
            "prominent": True,
        },
        "sin": {"unit": "bytespers", "rate": True},
        "sout": {"unit": "bytespers", "rate": True},
    }


@pytest.fixture
def memswap_payload():
    return {
        "total": 16 * 1024**3,
        "used": 4 * 1024**3,  # kept in payload but not rendered
        "free": 12 * 1024**3,  # kept in payload but not rendered
        "percent": 25.0,
        "sin": 100_000.0,  # bytes/s, computed by the framework
        "sout": 0.0,
        "_levels": {"percent": {"level": "ok", "prominent": True}},
    }


# ---------------------------------------------------------------- structure


def test_render_produces_four_rows(memswap_payload, memswap_fields):
    rows = render(memswap_payload, memswap_fields)
    assert len(rows) == 4


def test_render_first_row_carries_swap_title(memswap_payload, memswap_fields):
    rows = render(memswap_payload, memswap_fields)
    text = " ".join(c.text for c in rows[0].cells)
    assert "SWAP" in text


def test_render_first_row_includes_percent(memswap_payload, memswap_fields):
    rows = render(memswap_payload, memswap_fields)
    text = " ".join(c.text for c in rows[0].cells)
    assert "25.0%" in text


def test_render_body_rows_have_total_sin_sout(memswap_payload, memswap_fields):
    """Layout: total (capacity) + sin/sout (swap I/O rates). ``used``/``free``
    are dropped — redundant with ``percent`` + ``total``."""
    rows = render(memswap_payload, memswap_fields)
    flat = " ".join(c.text for row in rows[1:] for c in row.cells)
    assert "total" in flat
    assert "sin" in flat
    assert "sout" in flat


def test_render_does_not_show_used_or_free(memswap_payload, memswap_fields):
    """``used`` and ``free`` are intentionally not rendered (redundant)."""
    rows = render(memswap_payload, memswap_fields)
    # Only check the label columns (col 0) to avoid false positives from
    # arbitrary substring matches in the value column.
    labels = {r.cells[0].text.strip() for r in rows[1:] if r.cells}
    assert "used" not in labels
    assert "free" not in labels


def test_render_sin_sout_use_default_color_without_thresholds(memswap_fields):
    """When sin/sout have no _levels entry (no thresholds configured), the
    rendered cells must use ``ColorRole.DEFAULT`` — never a threshold colour.
    Also verifies the cells are not marked prominent (no reverse-video)."""
    payload = {
        "total": 16 * 1024**3,
        "percent": 25.0,
        "sin": 100_000.0,
        "sout": 50_000.0,
        # No _levels entries for sin/sout — the framework skipped them
        # because no thresholds were configured.
        "_levels": {"percent": {"level": "ok", "prominent": True}},
    }
    rows = render(payload, memswap_fields)
    sin_row = next(r for r in rows[1:] if r.cells[0].text.strip() == "sin")
    sout_row = next(r for r in rows[1:] if r.cells[0].text.strip() == "sout")
    # Value cell is col 1.
    assert sin_row.cells[1].color == ColorRole.DEFAULT
    assert sin_row.cells[1].prominent is False
    assert sout_row.cells[1].color == ColorRole.DEFAULT
    assert sout_row.cells[1].prominent is False


def test_render_sin_carries_level_color_when_thresholds_set(memswap_fields):
    """With a _levels.sin entry (user configured thresholds), the cell picks
    up the level role but stays non-prominent."""
    payload = {
        "total": 16 * 1024**3,
        "percent": 25.0,
        "sin": 15_000.0,
        "sout": 0.0,
        "_levels": {
            "percent": {"level": "ok", "prominent": True},
            "sin": {"level": "warning", "prominent": False},
        },
    }
    rows = render(payload, memswap_fields)
    sin_row = next(r for r in rows[1:] if r.cells[0].text.strip() == "sin")
    assert sin_row.cells[1].color == ColorRole.WARNING
    assert sin_row.cells[1].prominent is False


def test_render_handles_missing_sin_sout_on_first_cycle(memswap_fields):
    """Cycle 1: sin/sout absent from payload (no baseline) — renderer shows ``-``."""
    payload = {
        "total": 16 * 1024**3,
        "percent": 25.0,
        "_levels": {},
    }
    rows = render(payload, memswap_fields)
    # 4 rows still produced; sin/sout values are the dash placeholder.
    assert len(rows) == 4
    sin_row = next(r for r in rows[1:] if r.cells[0].text.strip() == "sin")
    sout_row = next(r for r in rows[1:] if r.cells[0].text.strip() == "sout")
    assert sin_row.cells[1].text.strip() == "-"
    assert sout_row.cells[1].text.strip() == "-"


def test_render_each_body_row_has_two_cells(memswap_payload, memswap_fields):
    rows = render(memswap_payload, memswap_fields)
    for r in rows[1:]:
        assert len(r.cells) == 2


def test_render_columns_align_across_rows(memswap_payload, memswap_fields):
    rows = render(memswap_payload, memswap_fields)
    ncols = max(len(r.cells) for r in rows)
    for col in range(ncols):
        widths = {len(r.cells[col].text) for r in rows if col < len(r.cells)}
        assert len(widths) == 1, f"col {col} widths differ: {widths}"


def test_render_value_columns_have_stable_width_across_cycles(memswap_fields):
    """Value cells must keep a stable width when stats vary cycle-to-cycle."""
    low = {
        "total": 1024.0,
        "percent": 5.0,
        "sin": 100.0,
        "sout": 0.0,
        "_levels": {},
    }
    high = {
        "total": 999_999_999_999.0,
        "percent": 100.0,
        "sin": 999_999_999.0,
        "sout": 999_999_999.0,
        "_levels": {},
    }
    rows_low = render(low, memswap_fields)
    rows_high = render(high, memswap_fields)
    for col in (1,):
        w_low = {len(r.cells[col].text) for r in rows_low if col < len(r.cells)}
        w_high = {len(r.cells[col].text) for r in rows_high if col < len(r.cells)}
        assert w_low == w_high, f"col {col} jiggles: {w_low} vs {w_high}"


def test_render_handles_empty_payload(memswap_fields):
    rows = render({}, memswap_fields)
    assert len(rows) == 1
    text = " ".join(c.text for c in rows[0].cells)
    assert "SWAP" in text


# ---------------------------------------------------------------- colour


def test_render_title_role_default_when_ok(memswap_payload, memswap_fields):
    """When percent _level is ok or careful, the SWAP title stays HEADER (white)."""
    rows = render(memswap_payload, memswap_fields)
    assert rows[0].cells[0].color == ColorRole.HEADER
    assert rows[0].cells[0].bold is True


def test_render_title_role_warning_escalates(memswap_fields):
    payload = {
        "total": 1024,
        "used": 800,
        "free": 224,
        "percent": 80.0,
        "_levels": {"percent": {"level": "warning", "prominent": True}},
    }
    rows = render(payload, memswap_fields)
    assert rows[0].cells[0].color == ColorRole.WARNING
    assert rows[0].cells[0].bold is True


def test_render_percent_cell_carries_level_and_prominent(memswap_payload, memswap_fields):
    """The percent cell on row 1 inherits ColorRole + prominent flag from _levels."""
    payload = {**memswap_payload, "_levels": {"percent": {"level": "warning", "prominent": True}}}
    rows = render(payload, memswap_fields)
    percent_cell = rows[0].cells[1]
    assert "25.0" in percent_cell.text
    assert percent_cell.color == ColorRole.WARNING
    assert percent_cell.prominent is True

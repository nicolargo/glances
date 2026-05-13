"""Glances v5 — tests for the load plugin's curses renderer."""

from __future__ import annotations

import pytest

from glances.outputs.curses_renderer_v5 import ColorRole
from glances.plugins.load.render_curses_v5 import render


@pytest.fixture
def load_fields():
    return {
        "min1": {"unit": "float", "label": "1 min", "watched": True},
        "min5": {"unit": "float", "label": "5 min", "watched": True, "prominent": True},
        "min15": {"unit": "float", "label": "15 min", "watched": True, "prominent": True},
        "cpucore": {"unit": "number", "internal": True},
    }


@pytest.fixture
def load_payload():
    return {
        "min1": 0.857,
        "min5": 0.716,
        "min15": 0.801,
        "cpucore": 16,
        "_levels": {
            "min5": {"level": "ok", "prominent": False},
            "min15": {"level": "ok", "prominent": True},
        },
    }


# --------------------------------------------------------------- structure


def test_render_produces_four_rows(load_payload, load_fields):
    rows = render(load_payload, load_fields)
    assert len(rows) == 4


def test_render_first_row_has_load_title(load_payload, load_fields):
    rows = render(load_payload, load_fields)
    first = " ".join(c.text for c in rows[0].cells)
    assert "LOAD" in first


def test_render_first_row_carries_corecount(load_payload, load_fields):
    rows = render(load_payload, load_fields)
    first = " ".join(c.text for c in rows[0].cells)
    assert "core" in first
    assert "16" in first


def test_render_first_cell_uses_header_role(load_payload, load_fields):
    rows = render(load_payload, load_fields)
    assert rows[0].cells[0].color == ColorRole.HEADER


def test_render_load_average_rows_have_n_min_labels(load_payload, load_fields):
    rows = render(load_payload, load_fields)
    labels = [r.cells[0].text.strip() for r in rows[1:]]
    assert labels == ["1 min", "5 min", "15 min"]


def test_render_load_values_use_two_decimals(load_payload, load_fields):
    """v4 fidelity: `{:>6.2f}` produces e.g. '  0.86'."""
    rows = render(load_payload, load_fields)
    # min1 = 0.857 → "  0.86"
    assert "0.86" in rows[1].cells[1].text
    # min5 = 0.716 → "  0.72"
    assert "0.72" in rows[2].cells[1].text
    # min15 = 0.801 → "  0.80"
    assert "0.80" in rows[3].cells[1].text


def test_render_cpucore_is_internal_not_rendered_as_row(load_payload, load_fields):
    """cpucore is `internal: True` — never appears as its own row, only
    on line 1 as the 'Ncore' suffix."""
    rows = render(load_payload, load_fields)
    label_texts = [r.cells[0].text.strip() for r in rows]
    assert "cpucore" not in label_texts
    assert "cores" not in label_texts


def test_render_min5_inherits_level_color(load_payload, load_fields):
    """The min5 row's value cell carries the OK color from `_levels.min5`."""
    rows = render(load_payload, load_fields)
    min5_cell = rows[2].cells[1]
    assert min5_cell.color == ColorRole.OK


def test_render_min15_prominent_flag(load_payload, load_fields):
    """min15 is declared prominent: True — the level entry tags it as such."""
    rows = render(load_payload, load_fields)
    min15_cell = rows[3].cells[1]
    assert min15_cell.prominent is True


def test_render_min15_warning_level(load_fields):
    payload = {
        "min1": 5.0,
        "min5": 3.0,
        "min15": 2.0,
        "cpucore": 2,
        "_levels": {"min15": {"level": "warning", "prominent": True}},
    }
    rows = render(payload, load_fields)
    assert rows[3].cells[1].color == ColorRole.WARNING


def test_render_handles_empty_payload(load_fields):
    rows = render({}, load_fields)
    assert len(rows) == 1
    flat = " ".join(c.text for c in rows[0].cells)
    assert "LOAD" in flat


def test_render_handles_missing_cpucore(load_fields):
    """When cpucore is unknown (Windows, locked-down env) → no '4core' suffix."""
    payload = {"min1": 1.0, "min5": 1.0, "min15": 1.0, "_levels": {}}
    rows = render(payload, load_fields)
    first = " ".join(c.text for c in rows[0].cells)
    assert "core" not in first


def test_render_columns_align(load_payload, load_fields):
    """Label column has a uniform width across rows."""
    rows = render(load_payload, load_fields)
    label_widths = {len(r.cells[0].text) for r in rows if r.cells}
    assert len(label_widths) == 1


def test_render_value_cells_share_width_across_header_and_body(load_payload, load_fields):
    """The corecount cell (header) and the load-average cells (body) must
    have the same width so right edges align. Earlier bug: `{:3}core`
    produced 7-char header value vs 6-char body values → 1-char overhang."""
    rows = render(load_payload, load_fields)
    widths = {len(r.cells[1].text) for r in rows if len(r.cells) >= 2}
    assert len(widths) == 1, f"value cells not uniform: {widths}"


def test_render_total_line_width_matches_across_rows(load_payload, load_fields):
    """Each line's total rendered width (cells joined with 1 space) is identical."""
    rows = render(load_payload, load_fields)
    totals = {sum(len(c.text) for c in r.cells) + max(0, len(r.cells) - 1) for r in rows}
    assert len(totals) == 1, f"line widths differ: {totals}"

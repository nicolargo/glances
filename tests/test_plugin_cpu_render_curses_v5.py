"""Glances v5 — tests for the cpu plugin's curses renderer."""

from __future__ import annotations

import pytest

from glances.outputs.curses_renderer_v5 import ColorRole
from glances.plugins.cpu.render_curses_v5 import render


@pytest.fixture
def cpu_fields():
    """A minimal subset of the cpu fields_description schema."""
    return {
        "total": {"unit": "percent", "watched": True, "prominent": True, "label": "CPU"},
        "user": {"unit": "percent"},
        "system": {"unit": "percent"},
        "idle": {"unit": "percent"},
        "nice": {"unit": "percent"},
        "iowait": {"unit": "percent"},
        "irq": {"unit": "percent"},
        "steal": {"unit": "percent"},
        "guest": {"unit": "percent"},
        "ctx_switches": {"unit": "number", "rate": True, "short_name": "ctx_sw"},
        "interrupts": {"unit": "number", "rate": True, "short_name": "inter"},
        "soft_interrupts": {"unit": "number", "rate": True, "short_name": "sw_int"},
    }


@pytest.fixture
def cpu_payload_linux():
    """Realistic cpu payload with all Linux fields, post-_transform_gauge."""
    return {
        "total": 4.5,
        "user": 3.8,
        "system": 0.7,
        "idle": 95.5,
        "nice": 0.0,
        "iowait": 0.5,
        "irq": 0.0,
        "steal": 0.0,
        "guest": 0.1,
        "ctx_switches": 6727.5,
        "interrupts": 3000.4,
        "soft_interrupts": 1782.5,
        "_levels": {
            "total": {"level": "ok", "prominent": True},
            "steal": {"level": "ok", "prominent": False},
        },
    }


# ---------------------------------------------------------------- structure


def test_render_produces_four_rows(cpu_payload_linux, cpu_fields):
    rows = render(cpu_payload_linux, cpu_fields)
    assert len(rows) == 4


def test_render_first_row_has_cpu_title(cpu_payload_linux, cpu_fields):
    rows = render(cpu_payload_linux, cpu_fields)
    first_row_text = " ".join(c.text for c in rows[0].cells)
    assert "CPU" in first_row_text


def test_render_first_row_carries_total_value(cpu_payload_linux, cpu_fields):
    rows = render(cpu_payload_linux, cpu_fields)
    flat = " ".join(c.text for row in rows for c in row.cells)
    assert "4.5%" in flat


def test_render_first_row_includes_idle_and_ctx_sw(cpu_payload_linux, cpu_fields):
    rows = render(cpu_payload_linux, cpu_fields)
    first = " ".join(c.text for c in rows[0].cells)
    assert "idle" in first
    assert "95.5%" in first
    assert "ctx_sw" in first


def test_render_ctx_switches_uses_k_scaling(cpu_payload_linux, cpu_fields):
    rows = render(cpu_payload_linux, cpu_fields)
    flat = " ".join(c.text for row in rows for c in row.cells)
    # 6727.5 → "6.6K" with our auto-unit (6727.5/1024 ≈ 6.57)
    assert "K" in flat


def test_render_lines_2_4_form_three_column_grid(cpu_payload_linux, cpu_fields):
    """Lines 2-4 must each carry 6 cells (3 label+value pairs)."""
    rows = render(cpu_payload_linux, cpu_fields)
    for i in (1, 2, 3):
        assert len(rows[i].cells) == 6, f"row {i} has {len(rows[i].cells)} cells"


def test_render_columns_align_across_rows(cpu_payload_linux, cpu_fields):
    """Each column has uniform width across all rows."""
    rows = render(cpu_payload_linux, cpu_fields)
    ncols = max(len(r.cells) for r in rows)
    for col in range(ncols):
        widths = {len(r.cells[col].text) for r in rows if col < len(r.cells)}
        assert len(widths) == 1, f"col {col} widths differ: {widths}"


def test_render_includes_user_system_iowait_on_linux(cpu_payload_linux, cpu_fields):
    rows = render(cpu_payload_linux, cpu_fields)
    flat = " ".join(c.text for row in rows for c in row.cells)
    assert "user" in flat
    assert "system" in flat
    assert "iowait" in flat


def test_render_includes_irq_nice_steal(cpu_payload_linux, cpu_fields):
    rows = render(cpu_payload_linux, cpu_fields)
    flat = " ".join(c.text for row in rows for c in row.cells)
    assert "irq" in flat
    assert "nice" in flat
    assert "steal" in flat


def test_render_handles_empty_payload(cpu_fields):
    """Cycle-0: just the title, no data rows."""
    rows = render({}, cpu_fields)
    assert len(rows) == 1
    flat = " ".join(c.text for c in rows[0].cells)
    assert "CPU" in flat


def test_render_windows_path_uses_idle_core_dpc(cpu_fields):
    """Without `user`, the renderer falls back to idle/core/dpc (v4 Windows)."""
    payload = {
        "total": 5.0,
        "idle": 95.0,  # idle is present but no user → idle_tag triggers
        "irq": 0.0,
        "nice": 0.0,
        "steal": 0.0,
        "interrupts": 2000.0,
        "_levels": {},
    }
    rows = render(payload, cpu_fields)
    flat = " ".join(c.text for row in rows for c in row.cells)
    # On the Windows path, idle/core/dpc populate column 1.
    assert "idle" in flat


def test_render_value_columns_have_stable_width_across_cycles(cpu_fields):
    """Value columns are floored at a fixed width — same width whether
    every stat is 5.0% or 100.0%."""
    payload_low = {
        "total": 5.0,
        "user": 1.0,
        "system": 0.5,
        "idle": 95.0,
        "iowait": 0.0,
        "irq": 0.0,
        "nice": 0.0,
        "steal": 0.0,
        "guest": 0.0,
        "ctx_switches": 100.0,
        "interrupts": 50.0,
        "soft_interrupts": 20.0,
        "_levels": {},
    }
    payload_high = {
        "total": 100.0,
        "user": 99.9,
        "system": 99.9,
        "idle": 0.0,
        "iowait": 99.9,
        "irq": 99.9,
        "nice": 99.9,
        "steal": 99.9,
        "guest": 99.9,
        "ctx_switches": 9999.0,
        "interrupts": 9999.0,
        "soft_interrupts": 9999.0,
        "_levels": {},
    }
    rows_low = render(payload_low, cpu_fields)
    rows_high = render(payload_high, cpu_fields)

    # Compare value-column widths (cols 1, 3, 5) between the two cycles.
    for col in (1, 3, 5):
        w_low = {len(r.cells[col].text) for r in rows_low if col < len(r.cells)}
        w_high = {len(r.cells[col].text) for r in rows_high if col < len(r.cells)}
        assert w_low == w_high, f"col {col} widths differ across cycles: {w_low} vs {w_high}"


def test_render_uses_short_name_from_schema_for_counter_labels(cpu_payload_linux, cpu_fields):
    """The cpu renderer pulls short labels from `short_name` in the schema
    rather than hardcoding 'ctx_sw' / 'sw_int' / 'inter'."""
    rows = render(cpu_payload_linux, cpu_fields)
    flat = " ".join(c.text for row in rows for c in row.cells)
    assert "ctx_sw" in flat
    assert "sw_int" in flat
    # 'interrupts' (full name) should NOT appear — the schema's short_name
    # 'inter' wins.
    assert "interrupts" not in flat
    assert "inter" in flat


def test_render_falls_back_to_field_name_when_short_name_absent():
    """If short_name is not declared, the field name (or label) is used."""
    minimal_fields = {
        "total": {"unit": "percent", "watched": True, "prominent": True},
        "user": {"unit": "percent"},
        "system": {"unit": "percent"},
        "iowait": {"unit": "percent"},
        "irq": {"unit": "percent"},
        "nice": {"unit": "percent"},
        "steal": {"unit": "percent"},
        "guest": {"unit": "percent"},
        "interrupts": {"unit": "number", "rate": True},  # no short_name
    }
    payload = {
        "total": 5.0,
        "user": 4.0,
        "system": 1.0,
        "iowait": 0.0,
        "irq": 0.0,
        "nice": 0.0,
        "steal": 0.0,
        "guest": 0.0,
        "interrupts": 100.0,
        "_levels": {},
    }
    rows = render(payload, minimal_fields)
    flat = " ".join(c.text for row in rows for c in row.cells)
    # Falls back to the field name itself.
    assert "interrupts" in flat


def test_render_uses_header_role_for_cpu_title(cpu_payload_linux, cpu_fields):
    rows = render(cpu_payload_linux, cpu_fields)
    # First cell of first row is the CPU title (after potential padding).
    first_cell = rows[0].cells[0]
    assert first_cell.color == ColorRole.HEADER
    assert "CPU" in first_cell.text


# ---------------------------------------------------------- responsive cols
#
# NOTE (adapted from the plan): the `cpu_fields` fixture declares
# `short_name: "inter"` for `interrupts`, so the rendered col-3 label is
# "inter", not "interrupts". We key the column-3 detection off the
# unambiguous col-3 labels actually emitted by the fixture: "sw_int"
# (soft_interrupts), "guest", and the line-1 "ctx_sw" pair.


def test_cpu_cols_2_drops_third_column(cpu_payload_linux, cpu_fields):
    full = render(cpu_payload_linux, cpu_fields)
    two = render(cpu_payload_linux, cpu_fields, view={"cpu_cols": 2})
    full_text = "\n".join("".join(c.text for c in r.cells) for r in full)
    two_text = "\n".join("".join(c.text for c in r.cells) for r in two)
    # Column 3 labels (interrupts / soft_interrupts / ctx_switches / guest)
    # gone. The fixture emits these as "inter"/"sw_int"/"guest"/"ctx_sw".
    for label in ("sw_int", "guest", "ctx_sw"):
        assert label in full_text
        assert label not in two_text
    # Column 1 + 2 survive.
    assert "user" in two_text and "irq" in two_text
    # Narrower block.
    assert max(len(r) for r in two_text.splitlines()) < max(len(r) for r in full_text.splitlines())


def test_cpu_cols_1_keeps_only_first_column(cpu_payload_linux, cpu_fields):
    one = render(cpu_payload_linux, cpu_fields, view={"cpu_cols": 1})
    text = "\n".join("".join(c.text for c in r.cells) for r in one)
    assert "user" in text  # col1 stays
    assert "irq" not in text  # col2 gone
    assert "sw_int" not in text  # col3 gone
    assert "guest" not in text  # col3 gone
    assert "ctx_sw" not in text  # line-1 col3 pair gone
    assert "idle" not in text  # line-1 col2 pair gone
    assert "CPU" in text and "%" in text  # title + total stay


def test_cpu_default_is_three_columns(cpu_payload_linux, cpu_fields):
    assert render(cpu_payload_linux, cpu_fields) == render(cpu_payload_linux, cpu_fields, view={"cpu_cols": 3})

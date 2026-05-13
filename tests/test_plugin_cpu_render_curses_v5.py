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
        "ctx_switches": {"unit": "number", "rate": True},
        "interrupts": {"unit": "number", "rate": True},
        "soft_interrupts": {"unit": "number", "rate": True},
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
            "steal": {"level": "ok", "prominent": True},
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


def test_render_uses_header_role_for_cpu_title(cpu_payload_linux, cpu_fields):
    rows = render(cpu_payload_linux, cpu_fields)
    # First cell of first row is the CPU title (after potential padding).
    first_cell = rows[0].cells[0]
    assert first_cell.color == ColorRole.HEADER
    assert "CPU" in first_cell.text

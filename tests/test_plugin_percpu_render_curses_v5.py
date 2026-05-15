"""Glances v5 — tests for the percpu plugin's curses renderer."""

from __future__ import annotations

import pytest

from glances.outputs.curses_renderer_v5 import ColorRole
from glances.plugins.percpu.render_curses_v5 import render


@pytest.fixture
def percpu_fields():
    return {
        "cpu_number": {"unit": "number", "primary_key": True},
        "total": {"unit": "percent"},
        "user": {"unit": "percent"},
        "system": {"unit": "percent"},
        "idle": {"unit": "percent"},
        "iowait": {"unit": "percent"},
        "irq": {"unit": "percent"},
        "nice": {"unit": "percent"},
        "steal": {"unit": "percent"},
        "guest": {"unit": "percent"},
    }


def _core(n: int, **overrides):
    base = {
        "cpu_number": n,
        "total": 20.0,
        "user": 10.0,
        "system": 5.0,
        "iowait": 0.5,
        "idle": 80.0,
        "irq": 0.0,
        "nice": 0.0,
        "steal": 0.0,
        "guest": 0.0,
    }
    base.update(overrides)
    return base


@pytest.fixture
def percpu_payload_4cores():
    return {
        "data": [
            _core(0, total=21.7, user=12.5, system=3.2, iowait=0.5, idle=83.8),
            _core(1, total=11.9, user=8.1, system=2.0, iowait=0.1, idle=89.8),
            _core(2, total=21.5, user=15.0, system=4.5, iowait=1.2, idle=79.3),
            _core(3, total=8.1, user=6.3, system=1.8, iowait=0.0, idle=91.9),
        ],
        "_levels": {},
    }


# ---------------------------------------------------------------- structure


def test_render_first_row_is_header(percpu_payload_4cores, percpu_fields, monkeypatch):
    monkeypatch.setattr("sys.platform", "linux")
    rows = render(percpu_payload_4cores, percpu_fields)
    flat = " ".join(c.text for c in rows[0].cells)
    assert "CPU" in flat
    assert "total" in flat
    assert "user" in flat
    assert "system" in flat


def test_render_header_includes_linux_columns(percpu_payload_4cores, percpu_fields, monkeypatch):
    monkeypatch.setattr("sys.platform", "linux")
    rows = render(percpu_payload_4cores, percpu_fields)
    flat = " ".join(c.text for c in rows[0].cells)
    # Linux: user, system, iowait, idle, irq, nice, steal, guest
    for col in ("iowait", "idle", "irq", "nice", "steal", "guest"):
        assert col in flat, f"missing column {col}"


def test_render_one_row_per_cpu_plus_header(percpu_payload_4cores, percpu_fields, monkeypatch):
    monkeypatch.setattr("sys.platform", "linux")
    rows = render(percpu_payload_4cores, percpu_fields)
    # 1 header + 4 cores = 5 rows (no overflow when len <= max_cpu_display).
    assert len(rows) == 5


def test_render_cpu_labels_for_single_digit_ids(percpu_payload_4cores, percpu_fields, monkeypatch):
    monkeypatch.setattr("sys.platform", "linux")
    rows = render(percpu_payload_4cores, percpu_fields)
    labels = [r.cells[0].text.strip() for r in rows[1:]]
    # cores are sorted by total desc, but each row label should be CPU<n>.
    assert all(lbl.startswith("CPU") for lbl in labels)
    assert {"CPU0", "CPU1", "CPU2", "CPU3"} == set(labels)


def test_render_data_rows_sorted_by_total_desc(percpu_payload_4cores, percpu_fields, monkeypatch):
    monkeypatch.setattr("sys.platform", "linux")
    rows = render(percpu_payload_4cores, percpu_fields)
    # Top-N by total: CPU2 (21.5), CPU0 (21.7) → highest first.
    # Wait: CPU0=21.7, CPU2=21.5 → CPU0 first.
    labels = [r.cells[0].text.strip() for r in rows[1:]]
    assert labels[0] == "CPU0"
    assert labels[-1] == "CPU3"  # 8.1, lowest


def test_render_each_data_row_has_label_plus_one_cell_per_column(percpu_payload_4cores, percpu_fields, monkeypatch):
    monkeypatch.setattr("sys.platform", "linux")
    rows = render(percpu_payload_4cores, percpu_fields)
    # Header on Linux: title + total + 8 stats = 10 cells.
    header_ncells = len(rows[0].cells)
    for r in rows[1:]:
        assert len(r.cells) == header_ncells


def test_render_value_cells_use_percent_format(percpu_payload_4cores, percpu_fields, monkeypatch):
    monkeypatch.setattr("sys.platform", "linux")
    rows = render(percpu_payload_4cores, percpu_fields)
    flat = " ".join(c.text for row in rows[1:] for c in row.cells)
    # 12.5% formatted as "  12.5%" must appear for CPU0.user.
    assert "12.5%" in flat


def test_render_columns_align_across_rows(percpu_payload_4cores, percpu_fields, monkeypatch):
    monkeypatch.setattr("sys.platform", "linux")
    rows = render(percpu_payload_4cores, percpu_fields)
    ncols = max(len(r.cells) for r in rows)
    for col in range(ncols):
        widths = {len(r.cells[col].text) for r in rows if col < len(r.cells)}
        assert len(widths) == 1, f"col {col} widths differ: {widths}"


# ---------------------------------------------------------------- overflow


def test_render_more_than_max_cpu_display_adds_overflow_row(percpu_fields, monkeypatch):
    """6 cores → 4 displayed + 1 CPU* overflow row (default max_cpu_display=4)."""
    monkeypatch.setattr("sys.platform", "linux")
    payload = {
        "data": [_core(i, total=float(i * 10)) for i in range(6)],
        "_levels": {},
    }
    rows = render(payload, percpu_fields)
    # 1 header + 4 displayed + 1 overflow = 6 rows.
    assert len(rows) == 6
    labels = [r.cells[0].text.strip() for r in rows[1:]]
    assert labels[-1] == "CPU*"


def test_render_no_overflow_row_when_exact_max(percpu_payload_4cores, percpu_fields, monkeypatch):
    monkeypatch.setattr("sys.platform", "linux")
    rows = render(percpu_payload_4cores, percpu_fields)
    labels = [r.cells[0].text.strip() for r in rows[1:]]
    assert "CPU*" not in labels


# ---------------------------------------------------------------- OS variation


def test_render_macos_headers(percpu_fields, monkeypatch):
    monkeypatch.setattr("sys.platform", "darwin")
    payload = {"data": [_core(0)], "_levels": {}}
    rows = render(payload, percpu_fields)
    flat = " ".join(c.text for c in rows[0].cells)
    assert "user" in flat
    assert "system" in flat
    assert "idle" in flat
    assert "nice" in flat
    # iowait is Linux-only
    assert "iowait" not in flat


def test_render_windows_headers(percpu_fields, monkeypatch):
    monkeypatch.setattr("sys.platform", "win32")
    payload = {"data": [_core(0)], "_levels": {}}
    rows = render(payload, percpu_fields)
    flat = " ".join(c.text for c in rows[0].cells)
    assert "dpc" in flat
    assert "interrupt" in flat
    # iowait/idle exclusive to other OSes shouldn't appear here.
    assert "iowait" not in flat


# ---------------------------------------------------------------- edge cases


def test_render_empty_payload(percpu_fields, monkeypatch):
    monkeypatch.setattr("sys.platform", "linux")
    rows = render({}, percpu_fields)
    # Header only.
    assert len(rows) == 1


def test_render_empty_data_list(percpu_fields, monkeypatch):
    monkeypatch.setattr("sys.platform", "linux")
    rows = render({"data": [], "_levels": {}}, percpu_fields)
    assert len(rows) == 1


def test_render_double_digit_cpu_label(percpu_fields, monkeypatch):
    """cpu_number=10 → right-aligned numeric label (no `CPU` prefix per v4)."""
    monkeypatch.setattr("sys.platform", "linux")
    payload = {"data": [_core(10)], "_levels": {}}
    rows = render(payload, percpu_fields)
    label_text = rows[1].cells[0].text
    # v4: `f'{cpu_id:4}'` → "  10" (4-char right-aligned).
    assert "10" in label_text
    assert "CPU10" not in label_text


def test_render_handles_missing_value(percpu_fields, monkeypatch):
    """A missing stat field falls back to a `?` placeholder, not a crash."""
    monkeypatch.setattr("sys.platform", "linux")
    payload = {"data": [{"cpu_number": 0, "total": 10.0}], "_levels": {}}
    rows = render(payload, percpu_fields)
    flat = " ".join(c.text for row in rows[1:] for c in row.cells)
    assert "?" in flat


# ---------------------------------------------------------------- title


def test_render_title_cell_is_header_bold(percpu_payload_4cores, percpu_fields, monkeypatch):
    """Percpu carries no _levels (per model_v5 docstring) → title stays HEADER."""
    monkeypatch.setattr("sys.platform", "linux")
    rows = render(percpu_payload_4cores, percpu_fields)
    title = rows[0].cells[0]
    assert "CPU" in title.text
    assert title.color == ColorRole.HEADER
    assert title.bold is True

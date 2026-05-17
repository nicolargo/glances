"""Glances v5 — tests for the processlist plugin's curses renderer."""

from __future__ import annotations

import pytest

from glances.outputs.curses_renderer_v5 import ColorRole
from glances.plugins.processlist.render_curses_v5 import render


@pytest.fixture
def fields():
    return {
        "pid": {"unit": "number", "primary_key": True},
        "name": {"unit": "string"},
        "username": {"unit": "string"},
        "status": {"unit": "string"},
        "nice": {"unit": "number"},
        "num_threads": {"unit": "number"},
        "cpu_percent": {"unit": "percent", "watched": True, "prominent": False},
        "memory_percent": {"unit": "percent", "watched": True, "prominent": False},
        "cmdline": {"unit": "list"},
        "cpu_num": {"unit": "number"},
    }


def _proc(**overrides):
    base = {
        "pid": 1234,
        "name": "python3",
        "username": "alice",
        "status": "S",
        "nice": 0,
        "num_threads": 4,
        "cpu_percent": 12.5,
        "memory_percent": 3.1,
        "cmdline": ["python3", "myscript.py"],
        "cpu_num": 2,
    }
    base.update(overrides)
    return base


@pytest.fixture
def payload():
    return {
        "data": [
            _proc(pid=1, cpu_percent=78.4, memory_percent=12.5, name="hot"),
            _proc(pid=42, cpu_percent=12.5, memory_percent=3.1, name="med"),
            _proc(pid=512, cpu_percent=0.5, memory_percent=0.2, username="root", name="sshd"),
        ],
        "_levels": {
            1: {
                "cpu_percent": {"level": "warning", "prominent": False},
                "memory_percent": {"level": "ok", "prominent": False},
            },
            42: {
                "cpu_percent": {"level": "ok", "prominent": False},
                "memory_percent": {"level": "ok", "prominent": False},
            },
            512: {
                "cpu_percent": {"level": "ok", "prominent": False},
                "memory_percent": {"level": "ok", "prominent": False},
            },
        },
    }


# ---------------------------------------------------------- structure


def test_render_header_first_row(payload, fields):
    rows = render(payload, fields)
    flat = " ".join(c.text for c in rows[0].cells)
    for col in ("CPU%", "MEM%", "PID", "USER", "THR", "NI", "S", "Command"):
        assert col in flat, col


def test_render_one_row_per_process_plus_header(payload, fields):
    rows = render(payload, fields)
    # 1 header + 3 processes = 4 rows.
    assert len(rows) == 4


def test_render_preserves_engine_sort_order(payload, fields):
    """Engine pre-sorts by cpu_percent desc — renderer keeps that order."""
    rows = render(payload, fields)
    pids = [int(r.cells[2].text.strip()) for r in rows[1:]]
    # Engine order from payload: 1 (78.4), 42 (12.5), 512 (0.5).
    assert pids == [1, 42, 512]


def test_render_cpu_cell_inherits_level_color(payload, fields):
    rows = render(payload, fields)
    cpu_cell = rows[1].cells[0]  # First process, CPU% column.
    assert cpu_cell.color == ColorRole.WARNING
    assert cpu_cell.prominent is False


def test_render_mem_cell_inherits_level_color(payload, fields):
    rows = render(payload, fields)
    mem_cell = rows[1].cells[1]
    assert mem_cell.color == ColorRole.OK


def test_render_status_is_single_char(payload, fields):
    rows = render(payload, fields)
    for r in rows[1:]:
        assert len(r.cells[6].text.strip()) <= 1


def test_render_long_username_truncated(fields):
    payload = {
        "data": [_proc(pid=1, username="averylongusername_indeed")],
        "_levels": {},
    }
    rows = render(payload, fields)
    user_cell = rows[1].cells[3]
    # Trailing '+' marker indicates truncation.
    assert user_cell.text.rstrip().endswith("+")


def test_render_caps_at_top_20(fields):
    """If the engine returns more than 20 processes, the renderer clips."""
    payload = {
        "data": [_proc(pid=i + 1, cpu_percent=100.0 - i) for i in range(50)],
        "_levels": {},
    }
    rows = render(payload, fields)
    # 1 header + 20 processes.
    assert len(rows) == 21


def test_render_handles_empty_data(fields):
    rows = render({"data": [], "_levels": {}}, fields)
    # Header only.
    assert len(rows) == 1


def test_render_handles_empty_payload(fields):
    rows = render({}, fields)
    assert len(rows) == 1
    flat = " ".join(c.text for c in rows[0].cells)
    assert "CPU%" in flat


def test_render_handles_missing_cmdline(fields):
    """When cmdline is empty, fall back to ``[name]`` (v4 parity)."""
    payload = {"data": [_proc(pid=1, cmdline=[], name="kthread")], "_levels": {}}
    rows = render(payload, fields)
    flat = " ".join(c.text for c in rows[1].cells)
    assert "[kthread]" in flat


def test_render_handles_missing_numeric_fields(fields):
    """Missing num_threads / nice degrade gracefully to '?'."""
    payload = {
        "data": [_proc(pid=1, num_threads=None, nice=None, cpu_percent=None, memory_percent=None)],
        "_levels": {},
    }
    rows = render(payload, fields)
    # No crash; some cells now contain '?'.
    flat = " ".join(c.text for c in rows[1].cells)
    assert "?" in flat


def test_render_pid_width_scales_with_largest_pid(fields):
    """Per-row PID width follows the widest PID in the payload."""
    payload = {
        "data": [
            _proc(pid=1),
            _proc(pid=1234567),  # 7 digits
        ],
        "_levels": {},
    }
    rows = render(payload, fields)
    # Header PID cell + data PID cells share a common width >= 7.
    widths = {len(r.cells[2].text) for r in rows}
    assert len(widths) == 1
    assert next(iter(widths)) >= 7


def test_render_columns_align_across_rows(payload, fields):
    rows = render(payload, fields)
    # All non-command cells must share widths.
    ncols = 7  # everything but the Command column
    for col in range(ncols):
        widths = {len(r.cells[col].text) for r in rows if col < len(r.cells)}
        assert len(widths) == 1, f"col {col} widths differ: {widths}"

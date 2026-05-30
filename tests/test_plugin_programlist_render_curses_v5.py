#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — tests for the programlist plugin's curses renderer."""

from __future__ import annotations

import pytest

from glances.outputs.curses_renderer_v5 import ColorRole
from glances.plugins.programlist.render_curses_v5 import render

# Fixed-column indices (header + data rows share this prefix).
CPU_COL = 0
MEM_COL = 1
VIRT_COL = 2
RES_COL = 3
NPROCS_COL = 4
USER_COL = 5
THR_COL = 6
NICE_COL = 7
STATUS_COL = 8
TIME_COL = 9
RS_COL = 10
WS_COL = 11
CMD_START = 12


def _program(**overrides):
    base = {
        "name": "python3",
        "username": "alice",
        "nprocs": 3,
        "num_threads": 12,
        "cpu_percent": 42.5,
        "memory_percent": 9.3,
        "cmdline": ["python3"],
        "memory_info": {"rss": 96 * 1024**2, "vms": 360 * 1024**2},
        "cpu_times": {"user": 3.0, "system": 1.5},
        "io_counters": [0, 0, 0, 0, 1],
        "status": "S",
        "nice": 0,
        "time_since_update": 1.0,
        "pid": "_",
    }
    base.update(overrides)
    return base


@pytest.fixture
def fields():
    return {
        "name": {"unit": "string", "primary_key": True},
        "username": {"unit": "string"},
        "nprocs": {"unit": "number"},
        "num_threads": {"unit": "number"},
        "cpu_percent": {"unit": "percent", "watched": True, "prominent": False},
        "memory_percent": {"unit": "percent", "watched": True, "prominent": False},
        "cmdline": {"unit": "list"},
        "status": {"unit": "string", "watched": True, "threshold_type": "categorical"},
        "nice": {"unit": "number", "watched": True, "threshold_type": "categorical"},
        "memory_info": {"unit": "byte", "internal": True},
        "cpu_times": {"unit": "second", "internal": True},
        "io_counters": {"unit": "byte", "internal": True},
        "time_since_update": {"unit": "second", "internal": True},
    }


@pytest.fixture
def payload():
    return {
        "data": [
            _program(name="python3", cpu_percent=78.4, memory_percent=12.5, nprocs=5),
            _program(name="bash", cpu_percent=2.0, memory_percent=1.0, nprocs=1),
        ],
        "_levels": {
            "python3": {
                "cpu_percent": {"level": "warning", "prominent": False},
                "memory_percent": {"level": "ok", "prominent": False},
            },
            "bash": {
                "cpu_percent": {"level": "ok", "prominent": False},
                "memory_percent": {"level": "ok", "prominent": False},
            },
        },
    }


# ---------------------------------------------------------- structure


def test_render_header_has_nprocs_not_pid(payload, fields):
    rows = render(payload, fields)
    flat = " ".join(c.text for c in rows[0].cells)
    for col in ("CPU%", "MEM%", "VIRT", "RES", "NPROCS", "USER", "THR", "NI", "S", "TIME+", "R/s", "W/s", "Command"):
        assert col in flat, col
    assert "PID" not in flat


def test_render_one_row_per_program_plus_header(payload, fields):
    rows = render(payload, fields)
    assert len(rows) == 3


def test_render_nprocs_column_shows_child_count(payload, fields):
    rows = render(payload, fields)
    assert rows[1].cells[NPROCS_COL].text.strip() == "5"
    assert rows[2].cells[NPROCS_COL].text.strip() == "1"


def test_render_cpu_cell_inherits_level_color(payload, fields):
    rows = render(payload, fields)
    assert rows[1].cells[CPU_COL].color == ColorRole.WARNING


def test_render_levels_keyed_by_name(fields):
    payload = {
        "data": [_program(name="redis", status="Z")],
        "_levels": {"redis": {"status": {"level": "critical", "prominent": False}}},
    }
    rows = render(payload, fields)
    assert rows[1].cells[STATUS_COL].color == ColorRole.CRITICAL


def test_render_command_shows_program_name(payload, fields):
    rows = render(payload, fields)
    cmd_cells = rows[1].cells[CMD_START:]
    assert any("python3" in c.text and c.bold for c in cmd_cells)


def test_render_time_column_aggregated_dict(fields):
    """Program cpu_times is a merged dict — TIME+ formats user+system."""
    p = _program(name="x", cpu_times={"user": 60.0, "system": 30.0})  # 1m30s
    rows = render({"data": [p], "_levels": {}}, fields)
    assert "1:30" in rows[1].cells[TIME_COL].text


def test_render_memory_columns_from_aggregated_dict(payload, fields):
    rows = render(payload, fields)
    assert "M" in rows[1].cells[VIRT_COL].text
    assert "M" in rows[1].cells[RES_COL].text


# ---------------------------------------------------------- sort indicator


def test_render_sort_indicator_underlines_active_column(payload, fields):
    rows = render(payload, fields, view={"sort_key": "memory_percent"})
    assert rows[0].cells[MEM_COL].underline is True
    assert rows[0].cells[CPU_COL].underline is False


def test_render_sort_indicator_name_underlines_command(payload, fields):
    rows = render(payload, fields, view={"sort_key": "name"})
    assert rows[0].cells[CMD_START].underline is True


def test_render_nprocs_never_underlined(payload, fields):
    """NPROCS has no engine sort key — never marked, whatever the sort."""
    for key in ("cpu_percent", "memory_percent", "cpu_times", "io_counters", "name"):
        rows = render(payload, fields, view={"sort_key": key})
        assert rows[0].cells[NPROCS_COL].underline is False, key


# ---------------------------------------------------------- robustness


def test_render_handles_empty_data(fields):
    rows = render({"data": [], "_levels": {}}, fields)
    assert len(rows) == 1


def test_render_handles_empty_payload(fields):
    rows = render({}, fields)
    assert len(rows) == 1
    assert "NPROCS" in " ".join(c.text for c in rows[0].cells)


def test_render_caps_at_top_20(fields):
    payload = {"data": [_program(name=f"p{i}", cpu_percent=100.0 - i) for i in range(50)], "_levels": {}}
    rows = render(payload, fields)
    assert len(rows) == 21


def test_render_nprocs_underscore_when_unparsable(fields):
    """A program whose nice differs across children ('_') renders '?'."""
    p = _program(name="x", nice="_")
    rows = render({"data": [p], "_levels": {}}, fields)
    assert "?" in rows[1].cells[NICE_COL].text

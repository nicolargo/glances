#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — TUI curses renderer for the processlist plugin.

Minimal port of v4 ``processlist.msg_curse``. Renders a header row +
top-N processes (engine pre-sorts by ``cpu_percent`` descending).

Reference layout (G4 minimal — fixed column set, no extended view):

    CPU%   MEM%      PID USER       THR  NI S Command
     78.4   3.1     1234 alice        4   0 S python3 myscript.py
     12.5   0.5      512 root         2   0 S sshd
    ...

Columns (v4 widths preserved for visual continuity):
- ``CPU%``  — ``{:>5.1f}`` (right-aligned, watched, coloured by ``_levels``)
- ``MEM%``  — ``{:>5.1f}`` (right-aligned, watched, coloured by ``_levels``)
- ``PID``   — right-aligned, width follows ``pid_max`` (1…7)
- ``USER``  — ``{:<10}`` (left-aligned, truncated)
- ``THR``   — ``{:>3}`` (number of threads)
- ``NI``    — ``{:>2}`` (nice, signed)
- ``S``     — ``{:>1}`` (status letter)
- ``Command`` — joined cmdline (left-aligned, takes the remaining width)

Limit: top 20 processes for G4 (engine returns the full sorted list; we
clip here to avoid a wall of rows in narrow terminals).
"""

from __future__ import annotations

from typing import Any

from glances.outputs.curses_renderer_v5 import _LEVEL_TO_ROLE, Cell, ColorRole, Row, title_role

# Column widths (v4 parity — see ``processlist.layout_stat``).
_W_CPU = 5
_W_MEM = 5
_W_USER = 10
_W_THR = 3
_W_NI = 2
_W_STATUS = 1
_W_PID_DEFAULT = 7
_MAX_ROWS = 20


def _format_percent(value: Any, width: int) -> str:
    try:
        return f"{float(value):>{width}.1f}"
    except (TypeError, ValueError):
        return "?".rjust(width)


def _format_int(value: Any, width: int, *, signed: bool = False) -> str:
    try:
        ival = int(value)
        return (f"{ival:>+{width}d}" if signed else f"{ival:>{width}d}")[-width:].rjust(width)
    except (TypeError, ValueError):
        return "?".rjust(width)


def _format_username(value: Any) -> str:
    text = str(value) if value is not None else "?"
    if len(text) > _W_USER:
        return text[: _W_USER - 1] + "+"
    return text.ljust(_W_USER)


def _format_command(item: dict[str, Any]) -> str:
    """Join cmdline tokens; fall back to ``name`` in brackets when empty."""
    cmdline = item.get("cmdline")
    if isinstance(cmdline, list) and cmdline:
        return " ".join(str(t) for t in cmdline if t)
    name = item.get("name")
    if name:
        return f"[{name}]"
    return ""


def _percent_cell(value: Any, level_entry: dict[str, Any] | None, width: int) -> Cell:
    text = _format_percent(value, width)
    if isinstance(level_entry, dict):
        role = _LEVEL_TO_ROLE.get(level_entry.get("level"), ColorRole.DEFAULT)
        return Cell(text=text, color=role, prominent=bool(level_entry.get("prominent")))
    return Cell(text=text)


def _pid_width(items: list[dict[str, Any]]) -> int:
    width = len(str(max((int(i.get("pid") or 0) for i in items), default=0)))
    return max(width, 4)  # never shorter than 4 chars so the header label fits


def render(payload: dict[str, Any], fields_desc: dict[str, dict[str, Any]]) -> list[Row]:
    """Render the processlist plugin's process table."""
    pid_width = _W_PID_DEFAULT
    items: list[dict[str, Any]] = []

    if isinstance(payload, dict):
        raw_items = payload.get("data")
        if isinstance(raw_items, list):
            items = [i for i in raw_items if isinstance(i, dict)]
            if items:
                pid_width = _pid_width(items)

    raw_levels = payload.get("_levels") if isinstance(payload, dict) else None
    levels_index = raw_levels if isinstance(raw_levels, dict) else {}

    # Header row.
    header_cells = [
        Cell(text="CPU%".rjust(_W_CPU), color=title_role(payload) if items else ColorRole.HEADER, bold=True),
        Cell(text="MEM%".rjust(_W_MEM), color=ColorRole.HEADER, bold=True),
        Cell(text="PID".rjust(pid_width), color=ColorRole.HEADER, bold=True),
        Cell(text="USER".ljust(_W_USER), color=ColorRole.HEADER, bold=True),
        Cell(text="THR".rjust(_W_THR), color=ColorRole.HEADER, bold=True),
        Cell(text="NI".rjust(_W_NI), color=ColorRole.HEADER, bold=True),
        Cell(text="S".rjust(_W_STATUS), color=ColorRole.HEADER, bold=True),
        Cell(text="Command", color=ColorRole.HEADER, bold=True),
    ]
    rows: list[Row] = [Row(cells=header_cells)]

    for item in items[:_MAX_ROWS]:
        pid = item.get("pid")
        pid_levels = levels_index.get(pid) if isinstance(levels_index, dict) else None
        pid_levels = pid_levels if isinstance(pid_levels, dict) else {}

        rows.append(
            Row(
                cells=[
                    _percent_cell(item.get("cpu_percent"), pid_levels.get("cpu_percent"), _W_CPU),
                    _percent_cell(item.get("memory_percent"), pid_levels.get("memory_percent"), _W_MEM),
                    Cell(text=_format_int(pid, pid_width)),
                    Cell(text=_format_username(item.get("username"))),
                    Cell(text=_format_int(item.get("num_threads"), _W_THR)),
                    Cell(text=_format_int(item.get("nice"), _W_NI, signed=False)),
                    Cell(text=str(item.get("status") or "?")[:1].rjust(_W_STATUS)),
                    Cell(text=_format_command(item)),
                ]
            )
        )

    return rows

#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — TUI curses renderer for the programlist plugin.

The per-program view (v4 ``j`` hotkey) is the per-thread ``processlist`` with
the ``PID`` column replaced by ``NPROCS`` (the number of aggregated children).
Every other column is identical, so this renderer reuses the processlist cell
builders verbatim — only the header set and the per-row identity column differ.

Reference layout:

    CPU%  MEM%  VIRT   RES   NPROCS USER       THR  NI S  TIME+    R/s  W/s  Command
    78.4   3.1  120M  32.1M       4 alice        4   0 S  0:12     0B   0B   python3
    ...

``NPROCS`` has no sort key (the program sort keys are cpu/mem/time/io/name),
so it is never underlined; the other columns honour the active engine sort
key passed via ``view`` exactly like processlist.
"""

from __future__ import annotations

from typing import Any

from glances.outputs.curses_renderer_v5 import Cell, ColorRole, Row, title_role
from glances.plugins.processlist.render_curses_v5 import (
    _HEADER_SORT_KEY,
    _W_CPU,
    _W_IO,
    _W_MEM,
    _W_NI,
    _W_RES,
    _W_STATUS,
    _W_THR,
    _W_TIME,
    _W_USER,
    _W_VIRT,
    _command_cells,
    _format_bytes,
    _format_cpu_time,
    _format_int,
    _format_username,
    _io_cell,
    _io_rate,
    _level_text_cell,
    _memory_info_field,
    _percent_cell,
)

# Number-of-children column (v4 ``nprocs`` layout ``{:>7}``).
_W_NPROCS = 7
_MAX_ROWS = 20


def render(
    payload: dict[str, Any],
    fields_desc: dict[str, dict[str, Any]],
    view: dict[str, Any] | None = None,
) -> list[Row]:
    """Render the programlist plugin's per-program table.

    ``view`` carries the active engine ``sort_key`` (column underline) and
    ``process_short_name`` (command rendering) — same contract as processlist.
    """
    sort_key = (view or {}).get("sort_key")
    short_name = (view or {}).get("process_short_name", True)

    def _header(label: str, width: int, *, ljust: bool = False, color: ColorRole = ColorRole.HEADER) -> Cell:
        text = label.ljust(width) if ljust else label.rjust(width)
        return Cell(
            text=text,
            color=color,
            bold=True,
            underline=_HEADER_SORT_KEY.get(label) == sort_key if sort_key else False,
        )

    items: list[dict[str, Any]] = []
    if isinstance(payload, dict):
        raw_items = payload.get("data")
        if isinstance(raw_items, list):
            items = [i for i in raw_items if isinstance(i, dict)]

    raw_levels = payload.get("_levels") if isinstance(payload, dict) else None
    levels_index = raw_levels if isinstance(raw_levels, dict) else {}

    title_color = title_role(payload) if items else ColorRole.HEADER

    header_cells = [
        _header("CPU%", _W_CPU, color=title_color),
        _header("MEM%", _W_MEM),
        _header("VIRT", _W_VIRT),
        _header("RES", _W_RES),
        _header("NPROCS", _W_NPROCS),
        _header("USER", _W_USER, ljust=True),
        _header("THR", _W_THR),
        _header("NI", _W_NI),
        _header("S", _W_STATUS),
        _header("TIME+", _W_TIME),
        _header("R/s", _W_IO),
        _header("W/s", _W_IO),
        _header("Command", len("Command")),
    ]
    rows: list[Row] = [Row(cells=header_cells)]

    for item in items[:_MAX_ROWS]:
        name = item.get("name")
        item_levels = levels_index.get(name) if isinstance(levels_index, dict) else None
        item_levels = item_levels if isinstance(item_levels, dict) else {}

        r_rate, r_unknown = _io_rate(item, read=True)
        w_rate, w_unknown = _io_rate(item, read=False)
        status_letter = str(item.get("status") or "?")[:1].rjust(_W_STATUS)
        nice_text = _format_int(item.get("nice"), _W_NI, signed=False)

        fixed_cells = [
            _percent_cell(item.get("cpu_percent"), item_levels.get("cpu_percent"), _W_CPU),
            _percent_cell(item.get("memory_percent"), item_levels.get("memory_percent"), _W_MEM),
            Cell(text=_format_bytes(_memory_info_field(item, "vms"), _W_VIRT)),
            Cell(text=_format_bytes(_memory_info_field(item, "rss"), _W_RES)),
            Cell(text=_format_int(item.get("nprocs"), _W_NPROCS)),
            Cell(text=_format_username(item.get("username"))),
            Cell(text=_format_int(item.get("num_threads"), _W_THR)),
            _level_text_cell(nice_text, item_levels.get("nice")),
            _level_text_cell(status_letter, item_levels.get("status")),
            Cell(text=_format_cpu_time(item, _W_TIME)),
            _io_cell(r_rate, r_unknown, _W_IO),
            _io_cell(w_rate, w_unknown, _W_IO),
        ]
        rows.append(Row(cells=fixed_cells + _command_cells(item, short_name)))

    return rows

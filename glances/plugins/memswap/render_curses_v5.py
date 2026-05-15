#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — TUI curses renderer for the memswap plugin.

Replicates v4 ``memswap.msg_curse()``
(`glances/plugins/memswap/__init__.py::msg_curse`): a 4-line block
laid out as a single-column label/value grid, with line 1 carrying the
``SWAP`` title + percent usage.

Reference layout:

    SWAP   25.0%
    total  16.0G
    sin   100.0K/s
    sout    0.0K/s

- Line 1: ``SWAP`` (HEADER) + percent value coloured by ``_levels.percent``.
- Line 2: ``total`` capacity (used/free intentionally dropped — they are
  redundant with ``percent`` and ``total``).
- Lines 3-4: ``sin`` / ``sout`` swap I/O rates. Absent until cycle 2 (no
  baseline) — the renderer shows ``-`` in that case.

V4 displayed ``total``/``used``/``free`` on three lines; v5 trades the
redundant pair for actionable I/O rates that highlight live paging
activity. The columns ``sin``/``sout`` are only coloured when the user
explicitly enables thresholds in ``[memswap]`` of ``glances.conf``
(no default ladder — see model_v5).
"""

from __future__ import annotations

from typing import Any

from glances.outputs.curses_renderer_v5 import Cell, ColorRole, Row, _cell_for_field, field_label, title_role

# Stable floor for the value column. ``mem`` and ``memswap`` both deal
# with bytes / percent — same minimum width keeps the SWAP and MEM
# blocks visually aligned in the top row.
_SWAP_VALUE_WIDTH = 6


def _stat_pair(payload: dict[str, Any], fields_desc: dict[str, dict[str, Any]], key: str) -> list[Cell]:
    """Return [label, value] cells for one swap stat."""
    schema = fields_desc.get(key, {})
    label_cell = Cell(text=field_label(schema, key, prefer_short=True))
    if key not in payload or payload.get(key) is None:
        return [label_cell, Cell(text="-")]
    return [label_cell, _cell_for_field(key, payload[key], schema, payload)]


def _align_grid(rows: list[list[Cell]]) -> list[Row]:
    """Per-column alignment for a 2-cell grid (label, value).

    Value cells are floored at ``_SWAP_VALUE_WIDTH`` so the column does
    not jiggle when stats shrink between cycles.
    """
    if not rows:
        return []
    ncols = max(len(r) for r in rows)
    widths = [0] * ncols
    for r in rows:
        for i, c in enumerate(r):
            widths[i] = max(widths[i], len(c.text))
    if ncols >= 2:
        widths[1] = max(widths[1], _SWAP_VALUE_WIDTH)

    aligned: list[Row] = []
    for r in rows:
        new_cells: list[Cell] = []
        for i, c in enumerate(r):
            text = c.text.ljust(widths[i]) if i == 0 else c.text.rjust(widths[i])
            new_cells.append(Cell(text=text, color=c.color, prominent=c.prominent, bold=c.bold))
        aligned.append(Row(cells=new_cells))
    return aligned


def render(payload: dict[str, Any], fields_desc: dict[str, dict[str, Any]]) -> list[Row]:
    """Render the memswap plugin's TUI block — mirrors v4 ``memswap.msg_curse``."""
    if not payload:
        return [Row(cells=[Cell(text="SWAP", color=ColorRole.HEADER, bold=True)])]

    # Line 1: title + percent.
    line1: list[Cell] = [
        Cell(text="SWAP", color=title_role(payload), bold=True),
        _cell_for_field("percent", payload.get("percent"), fields_desc.get("percent", {}), payload),
    ]

    # Lines 2-4: total capacity + sin/sout swap I/O rates.
    grid: list[list[Cell]] = [line1]
    for key in ("total", "sin", "sout"):
        grid.append(_stat_pair(payload, fields_desc, key))

    return _align_grid(grid)

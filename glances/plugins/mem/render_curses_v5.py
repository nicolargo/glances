#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — TUI curses renderer for the mem plugin.

Replicates v4's ``mem.msg_curse()``
(`glances/plugins/mem/__init__.py::msg_curse`): a 4-line block laid out
as a 2-column grid of (label, value) pairs, with line 1 carrying the
plugin title + percent usage.

Reference layout (Linux):

    MEM    53.2%      active   5.8G
    total  15.3G    inactive   4.4G
    avail   7.2G     buffers   185M
    free    2.6G      cached   4.2G

- Line 1: ``MEM`` (HEADER) + percent (decorated by ``_levels.percent``) +
  ``active`` label + value.
- Lines 2-4: 2-column grid; col 1 = total/avail|used/free, col 2 =
  inactive/buffers/cached.
- Avail vs used: when ``available`` is in the payload (Linux, macOS),
  show ``avail`` (and the corresponding bytes); otherwise show ``used``.
"""

from __future__ import annotations

from typing import Any

from glances.outputs.curses_renderer_v5 import Cell, ColorRole, Row, _cell_for_field

# Fixed widths so the block doesn't jiggle cycle-to-cycle.
#   value cols hold "999.9G" (6) at worst — pick 6.
#   label cols: col 1 = max("total"/"avail"/"used"/"free") = 5; col 2 = max("inactive") = 8.
_MEM_VALUE_WIDTH = 6
_MEM_LABEL_MIN_WIDTHS = (5, 8)


def _stat_pair(payload: dict[str, Any], fields_desc: dict[str, dict[str, Any]], key: str, label: str) -> list[Cell]:
    """Return a [label_cell, value_cell] pair for a single mem stat."""
    label_cell = Cell(text=label)
    if key not in payload or payload.get(key) is None:
        return [label_cell, Cell(text="-")]
    schema = fields_desc.get(key, {})
    return [label_cell, _cell_for_field(key, payload[key], schema, payload)]


def _align_grid(rows: list[list[Cell]]) -> list[Row]:
    """Per-column alignment for a 4-cell grid (2 label/value pairs):

    col 0: label (left)   floor `_MEM_LABEL_MIN_WIDTHS[0]`
    col 1: value (right)  fixed `_MEM_VALUE_WIDTH`
    col 2: label (left)   floor `_MEM_LABEL_MIN_WIDTHS[1]`
    col 3: value (right)  fixed `_MEM_VALUE_WIDTH`
    """
    if not rows:
        return []
    ncols = max(len(r) for r in rows)
    widths = [0] * ncols
    for r in rows:
        for i, c in enumerate(r):
            widths[i] = max(widths[i], len(c.text))
    for i in range(ncols):
        if i % 2 == 1:  # value col
            widths[i] = max(widths[i], _MEM_VALUE_WIDTH)
        else:  # label col
            floor_idx = i // 2
            if floor_idx < len(_MEM_LABEL_MIN_WIDTHS):
                widths[i] = max(widths[i], _MEM_LABEL_MIN_WIDTHS[floor_idx])

    aligned: list[Row] = []
    for r in rows:
        new_cells: list[Cell] = []
        for i, c in enumerate(r):
            if i % 2 == 0:
                text = c.text.ljust(widths[i])
            else:
                text = c.text.rjust(widths[i])
            new_cells.append(Cell(text=text, color=c.color, prominent=c.prominent))
        aligned.append(Row(cells=new_cells))
    return aligned


def render(payload: dict[str, Any], fields_desc: dict[str, dict[str, Any]]) -> list[Row]:
    """Render the mem plugin's TUI block — mirrors v4 ``mem.msg_curse``."""
    if not payload:
        return [Row(cells=[Cell(text="MEM", color=ColorRole.HEADER)])]

    # Line 1: title + percent + active.
    line1: list[Cell] = [
        Cell(text="MEM", color=ColorRole.HEADER),
        _cell_for_field("percent", payload.get("percent"), fields_desc.get("percent", {}), payload),
    ]
    line1 += _stat_pair(payload, fields_desc, "active", "active")

    # Lines 2-4. Each row: col-1 pair + col-2 pair.
    # Col 1 (line 2-4): total / (avail|used) / free
    # Col 2 (line 2-4): inactive / buffers / cached
    if "available" in payload and payload.get("available") is not None:
        col1_line3 = ("available", "avail")
    else:
        col1_line3 = ("used", "used")

    rows_spec: list[tuple[tuple[str, str], tuple[str, str]]] = [
        (("total", "total"), ("inactive", "inactive")),
        (col1_line3, ("buffers", "buffers")),
        (("free", "free"), ("cached", "cached")),
    ]

    grid: list[list[Cell]] = [line1]
    for (c1_key, c1_label), (c2_key, c2_label) in rows_spec:
        row: list[Cell] = []
        row += _stat_pair(payload, fields_desc, c1_key, c1_label)
        row += _stat_pair(payload, fields_desc, c2_key, c2_label)
        grid.append(row)

    return _align_grid(grid)

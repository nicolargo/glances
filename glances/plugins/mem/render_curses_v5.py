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

from glances.outputs.curses_renderer_v5 import Cell, ColorRole, Row, _cell_for_field, field_label, title_role

# Value cells need a stable floor because their content can shrink
# cycle-to-cycle (e.g. "5.0%" vs "100.0%"). Label cells don't — labels
# are constant strings, so the content-driven auto-size is naturally
# stable. Picking up `short_name` from the schema lets the auto-size
# pick the most compact label available (cf. v4 `short_name`).
_MEM_VALUE_WIDTH = 6


def _stat_pair(payload: dict[str, Any], fields_desc: dict[str, dict[str, Any]], key: str) -> list[Cell]:
    """Return a [label_cell, value_cell] pair for a single mem stat.

    The label comes from the schema (``short_name`` → ``label`` →
    field name) so the renderer doesn't hardcode any user-visible text.
    """
    schema = fields_desc.get(key, {})
    label_cell = Cell(text=field_label(schema, key, prefer_short=True))
    if key not in payload or payload.get(key) is None:
        return [label_cell, Cell(text="-")]
    return [label_cell, _cell_for_field(key, payload[key], schema, payload)]


def _align_grid(rows: list[list[Cell]]) -> list[Row]:
    """Per-column alignment for a 4-cell grid (2 label/value pairs).

    Value columns are floored at ``_MEM_VALUE_WIDTH`` so they don't
    jiggle when their content shrinks. Label columns auto-size to the
    widest observed text (stable because labels are constant strings).
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

    aligned: list[Row] = []
    for r in rows:
        new_cells: list[Cell] = []
        for i, c in enumerate(r):
            if i % 2 == 0:
                text = c.text.ljust(widths[i])
            else:
                text = c.text.rjust(widths[i])
            new_cells.append(Cell(text=text, color=c.color, prominent=c.prominent, bold=c.bold))
        aligned.append(Row(cells=new_cells))
    return aligned


def render(payload: dict[str, Any], fields_desc: dict[str, dict[str, Any]], view: dict | None = None) -> list[Row]:
    """Render the mem plugin's TUI block — mirrors v4 ``mem.msg_curse``.

    ``view["mem_cols"]`` (default 2, clamped to 1..2) controls how many
    grid columns are rendered. With ``mem_cols == 1`` the 2nd column
    (inactive/buffers/cached) and the line-1 ``active`` pair are dropped,
    and the block genuinely shrinks (no placeholder cells).
    """
    if not payload:
        return [Row(cells=[Cell(text="MEM", color=ColorRole.HEADER, bold=True)])]

    n_cols = min(max(int((view or {}).get("mem_cols", 2)), 1), 2)

    # Line 1: title + percent (+ active pair only when col-2 survives).
    # Title colour reflects the worst prominent alert level in the payload.
    line1: list[Cell] = [
        Cell(text="MEM", color=title_role(payload), bold=True),
        _cell_for_field("percent", payload.get("percent"), fields_desc.get("percent", {}), payload),
    ]
    if n_cols >= 2:
        line1 += _stat_pair(payload, fields_desc, "active")

    # Lines 2-4. Each row: col-1 pair (+ col-2 pair when n_cols >= 2).
    # Col 1 (line 2-4): total / (avail|used) / free
    # Col 2 (line 2-4): inactive / buffers / cached
    if "available" in payload and payload.get("available") is not None:
        col1_line3 = "available"
    else:
        col1_line3 = "used"

    # All labels come from the schema (short_name -> label -> field name).
    rows_spec: list[tuple[str, str]] = [
        ("total", "inactive"),
        (col1_line3, "buffers"),
        ("free", "cached"),
    ]

    grid: list[list[Cell]] = [line1]
    for c1_key, c2_key in rows_spec:
        row: list[Cell] = []
        row += _stat_pair(payload, fields_desc, c1_key)
        if n_cols >= 2:
            row += _stat_pair(payload, fields_desc, c2_key)
        grid.append(row)

    return _align_grid(grid)

#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — TUI curses renderer for the load plugin.

Replicates v4's ``load.msg_curse()``
(`glances/plugins/load/__init__.py::msg_curse`): a 4-line block laid out
as a single-column 2-cell table, with line 1 carrying the title and the
core count.

Reference layout:

    LOAD     4core
    1 min     0.86
    5 min     0.72
    15 min    0.80

- Line 1: ``LOAD`` (HEADER, 4 chars) + ``{Ncore}`` (cpucore prefix).
- Lines 2-4: ``{N min}`` left-aligned + load value formatted as
  ``{:>6.2f}`` (2 decimals, right-aligned, 6 chars).
- Colors:
  - ``min15`` decoration from ``_levels.min15`` (v4 = primary alert path).
  - ``min5`` decoration from ``_levels.min5``.
  - ``min1`` plain (no alert in v4).
- ``cpucore`` is declared ``internal: True`` in the schema: never
  rendered as its own row — only used as the ``Ncore`` suffix on line 1.

Irix mode (v4 ``args.disable_irix``) is not yet plumbed through v5 —
load values are shown as plain floats; per-core normalisation is
implicit in the threshold computation via ``normalize_by: cpucore``.
"""

from __future__ import annotations

from typing import Any

from glances.outputs.curses_renderer_v5 import _LEVEL_TO_ROLE, Cell, ColorRole, Row

# Fixed widths.
_LOAD_LABEL_WIDTH = 6  # "15 min" = 6 chars
_LOAD_VALUE_WIDTH = 6  # "999.99" worst case = 6 chars


def _format_load(value: Any) -> str:
    """Format a load average value as v4 does — `{:>6.2f}`."""
    try:
        return f"{float(value):>6.2f}"
    except (TypeError, ValueError):
        return "     -"


def _load_value_cell(payload: dict[str, Any], key: str) -> Cell:
    """Return a Cell for a single load average, coloured per `_levels`."""
    if key not in payload or payload.get(key) is None:
        return Cell(text="     -")
    text = _format_load(payload[key])
    levels = payload.get("_levels", {}) if isinstance(payload, dict) else {}
    entry = levels.get(key, {}) if isinstance(levels, dict) else {}
    level = entry.get("level") if isinstance(entry, dict) else None
    role = _LEVEL_TO_ROLE.get(level, ColorRole.DEFAULT)
    prominent = bool(entry.get("prominent")) if isinstance(entry, dict) else False
    return Cell(text=text, color=role, prominent=prominent)


def render(payload: dict[str, Any], fields_desc: dict[str, dict[str, Any]]) -> list[Row]:
    """Render the load plugin's TUI block — mirrors v4 ``load.msg_curse``."""
    if not payload:
        return [Row(cells=[Cell(text="LOAD", color=ColorRole.HEADER)])]

    # Line 1: title + cpucore suffix.
    # The value cell width must match the body load-average value width
    # (`_LOAD_VALUE_WIDTH = 6`) so the right edges of every line in the
    # block align. v4 padded the int with `{:3}core` (7 chars), which
    # made the corecount cell 1 char wider than the load-average values
    # and produced a visible 1-char overhang.
    header_cells: list[Cell] = [Cell(text="LOAD".ljust(_LOAD_LABEL_WIDTH), color=ColorRole.HEADER)]
    cores = payload.get("cpucore")
    if isinstance(cores, (int, float)) and cores > 0:
        header_cells.append(Cell(text=f"{int(cores)}core".rjust(_LOAD_VALUE_WIDTH)))
    else:
        header_cells.append(Cell(text="".rjust(_LOAD_VALUE_WIDTH)))
    rows: list[Row] = [Row(cells=header_cells)]

    # Lines 2-4: "{N min}" + value, per-row label.
    for key, label in [("min1", "1 min"), ("min5", "5 min"), ("min15", "15 min")]:
        label_cell = Cell(text=label.ljust(_LOAD_LABEL_WIDTH))
        value_cell = _load_value_cell(payload, key)
        rows.append(Row(cells=[label_cell, value_cell]))

    return rows

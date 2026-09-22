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
- ``cpucore`` is declared ``internal: True`` in the schema: never rendered
  as its own row — it supplies the ``Ncore`` suffix on line 1, and the
  divisor for Irix mode below.

Irix mode (v4 ``args.disable_irix``, the ``0`` hotkey, issue #1554) divides
each average by ``cpucore`` and shows a percentage instead of a plain float.
Off by default, as in v4. Note that per-core normalisation is ALREADY implicit
in the threshold computation (``normalize_by: cpucore``) — this key changes
only what the cell displays, never which level it is coloured with.
"""

from __future__ import annotations

from typing import Any

from glances.outputs.curses_renderer_v5 import _LEVEL_TO_ROLE, Cell, ColorRole, Row, field_label

# Fixed widths.
_LOAD_LABEL_WIDTH = 6  # "15 min" = 6 chars
_LOAD_VALUE_WIDTH = 6  # "999.99" worst case = 6 chars


def _format_load(value: Any) -> str:
    """Format a load average value as v4 does — `{:>6.2f}`."""
    try:
        return f"{float(value):>6.2f}"
    except (TypeError, ValueError):
        return "     -"


def _load_value_cell(payload: dict[str, Any], key: str, irix: bool = False) -> Cell:
    """Return a Cell for a single load average, coloured per `_levels`.

    `irix` is the `0` key (v4 `args.disable_irix`, issue #1554): the raw load
    average is divided by the core count and shown as a percentage. v4 reads
    the count from the `core` plugin's `log_core()`
    (`load/__init__.py:168-171`); v5 reads the `cpucore` field the load
    payload already carries, which is the same number without the
    cross-plugin reach.
    """
    if key not in payload or payload.get(key) is None:
        return Cell(text="     -")
    if irix:
        cores = payload.get("cpucore")
        # v4 guards on `log_core() != 0`; an absent or zero count falls back
        # to the default mode rather than dividing by zero.
        if isinstance(cores, (int, float)) and cores > 0:
            text = f"{payload[key] / cores * 100:>5.1f}%"
            levels = payload.get("_levels", {}) if isinstance(payload, dict) else {}
            entry = levels.get(key, {}) if isinstance(levels, dict) else {}
            level = entry.get("level") if isinstance(entry, dict) else None
            return Cell(
                text=text,
                color=_LEVEL_TO_ROLE.get(level, ColorRole.DEFAULT),
                prominent=bool(entry.get("prominent")) if isinstance(entry, dict) else False,
            )
    text = _format_load(payload[key])
    levels = payload.get("_levels", {}) if isinstance(payload, dict) else {}
    entry = levels.get(key, {}) if isinstance(levels, dict) else {}
    level = entry.get("level") if isinstance(entry, dict) else None
    role = _LEVEL_TO_ROLE.get(level, ColorRole.DEFAULT)
    prominent = bool(entry.get("prominent")) if isinstance(entry, dict) else False
    return Cell(text=text, color=role, prominent=prominent)


def render(
    payload: dict[str, Any], fields_desc: dict[str, dict[str, Any]], view: dict[str, Any] | None = None
) -> list[Row]:
    """Render the load plugin's TUI block — mirrors v4 ``load.msg_curse``."""
    irix = bool((view or {}).get("load_irix"))
    if not payload:
        return [Row(cells=[Cell(text="LOAD", color=ColorRole.HEADER, bold=True)])]

    # Line 1: title + cpucore suffix.
    # The value cell width must match the body load-average value width
    # (`_LOAD_VALUE_WIDTH = 6`) so the right edges of every line in the
    # block align. v4 padded the int with `{:3}core` (7 chars), which
    # made the corecount cell 1 char wider than the load-average values
    # and produced a visible 1-char overhang.
    # Title colour reflects the worst prominent alert level in the payload.
    header_cells: list[Cell] = [
        Cell(text="LOAD".ljust(_LOAD_LABEL_WIDTH), color=ColorRole.HEADER, bold=True),
    ]
    cores = payload.get("cpucore")
    if isinstance(cores, (int, float)) and cores > 0:
        header_cells.append(Cell(text=f"{int(cores)}core".rjust(_LOAD_VALUE_WIDTH)))
    else:
        header_cells.append(Cell(text="".rjust(_LOAD_VALUE_WIDTH)))
    rows: list[Row] = [Row(cells=header_cells)]

    # Lines 2-4: label from the schema (short_name -> label -> field name),
    # so the string exists in exactly one place and the WebUI, which resolves
    # its labels from /api/5/load/info, shows the same one.
    for key in ("min1", "min5", "min15"):
        label = field_label(fields_desc.get(key, {}), key, prefer_short=True)
        label_cell = Cell(text=label.ljust(_LOAD_LABEL_WIDTH))
        value_cell = _load_value_cell(payload, key, irix=irix)
        rows.append(Row(cells=[label_cell, value_cell]))

    return rows

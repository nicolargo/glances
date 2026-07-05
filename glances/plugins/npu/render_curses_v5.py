#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — TUI curses renderer for the npu plugin.

Mirrors v4 `npu.msg_curse()` — renders the FIRST NPU only:

    Intel NPU             <- header (name[:17])
    45%        1.0G/2.0GHz  <- load% (or freq% if load is None) + freq range
    mem:              N/A%
    temperature:       55C
"""

from __future__ import annotations

from typing import Any

from glances.globals import to_fahrenheit
from glances.outputs.curses_renderer_v5 import _LEVEL_TO_ROLE, Cell, ColorRole, Row, title_role

_HEADER_MAX = 17
_RANGE_WIDTH = 14


def _format_value(value: Any, unit: str) -> str:
    if value is None:
        return "{:>5}".format("N/A")
    return f"{value:>4.0f}{unit}"


def _auto_hz(hz: Any) -> str:
    try:
        v = float(hz)
    except (TypeError, ValueError):
        return "?"
    for symbol, threshold in (("G", 1e9), ("M", 1e6), ("K", 1e3)):
        if abs(v) >= threshold:
            return f"{v / threshold:.1f}{symbol}"
    return f"{int(v)}"


def _level_role(levels: dict[str, Any], npu_id: Any, field: str) -> ColorRole:
    entry = levels.get(npu_id, {})
    level = entry.get(field, {}).get("level") if isinstance(entry, dict) else None
    return _LEVEL_TO_ROLE.get(level, ColorRole.DEFAULT)


def render(payload: dict[str, Any], fields_desc: dict[str, dict[str, Any]] | None = None, view=None) -> list[Row]:
    if not isinstance(payload, dict):
        return []
    npus = payload.get("data")
    if not isinstance(npus, list) or not npus:
        return []
    npu = npus[0]
    if not isinstance(npu, dict):
        return []
    levels = payload.get("_levels") if isinstance(payload.get("_levels"), dict) else {}
    view = view or {}
    npu_id = npu.get("npu_id")

    rows: list[Row] = [
        Row(cells=[Cell(text=str(npu.get("name") or "NPU")[:_HEADER_MAX], color=title_role(payload), bold=True)])
    ]

    # Row 2: load% (or freq% fallback) + right-justified current/max freq range.
    if npu.get("load") is not None:
        pct_cell = Cell(text=f"{npu['load']:>3.0f}%", color=_level_role(levels, npu_id, "load"))
    else:
        freq = npu.get("freq")
        pct_cell = Cell(
            text=("{:>4}".format("N/A") if freq is None else f"{freq:>3.0f}%"),
            color=_level_role(levels, npu_id, "freq"),
        )
    freq_range = f"{_auto_hz(npu.get('freq_current'))}/{_auto_hz(npu.get('freq_max'))}Hz"
    rows.append(Row(cells=[pct_cell, Cell(text=freq_range.rjust(_RANGE_WIDTH))]))

    # Row 3: mem.
    rows.append(
        Row(
            cells=[
                Cell(text="{:<12}".format("mem:")),
                Cell(text=_format_value(npu.get("mem"), "%"), color=_level_role(levels, npu_id, "mem")),
            ]
        )
    )

    # Row 4: temperature (never watched in v4 — default colour).
    temp = npu.get("temperature")
    if temp is not None and view.get("fahrenheit"):
        temp = to_fahrenheit(temp)
    unit = "F" if view.get("fahrenheit") else "C"
    rows.append(Row(cells=[Cell(text="{:<12}".format("temperature:")), Cell(text=_format_value(temp, unit))]))

    return rows

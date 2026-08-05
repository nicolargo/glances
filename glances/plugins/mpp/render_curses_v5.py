#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — TUI curses renderer for the mpp plugin (top slot).

Mirrors v4 `mpp.msg_curse()`:

    MPP
    RKVENC    enc   24.8%  2 sess
    JPEGD    jpeg    0.0%
"""

from __future__ import annotations

from typing import Any

from glances.outputs.curses_renderer_v5 import _LEVEL_TO_ROLE, Cell, ColorRole, Row


def _load_role(levels: dict[str, Any], engine_id: Any) -> ColorRole:
    entry = levels.get(engine_id, {})
    level = entry.get("load", {}).get("level") if isinstance(entry, dict) else None
    return _LEVEL_TO_ROLE.get(level, ColorRole.DEFAULT)


def render(payload: dict[str, Any], fields_desc: dict[str, dict[str, Any]]) -> list[Row]:
    if not isinstance(payload, dict):
        return []
    engines = payload.get("data")
    if not isinstance(engines, list) or not engines:
        return []
    levels = payload.get("_levels") if isinstance(payload.get("_levels"), dict) else {}

    rows: list[Row] = [Row(cells=[Cell(text="MPP", color=ColorRole.HEADER, bold=True)])]
    for engine in engines:
        if not isinstance(engine, dict):
            continue
        label = "{:<8}{:>5}".format(str(engine.get("name", "unknown")), str(engine.get("type", "")))
        cells = [Cell(text=label)]

        load = engine.get("load")
        if load is None:
            cells.append(Cell(text="{:>7}".format("N/A")))
        else:
            cells.append(Cell(text=f"{load:>6.1f}%", color=_load_role(levels, engine.get("engine_id"))))

        # v4 omits the session column entirely when the count is zero.
        sessions = engine.get("sessions") or 0
        if sessions:
            cells.append(Cell(text=f"  {sessions} sess"))

        rows.append(Row(cells=cells))
    return rows

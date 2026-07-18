#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — TUI curses renderer for the raid plugin.

Mirrors v4 `raid.msg_curse()`: a `RAID disks` header (name col + Used +
Avail) then one row per array, with inactive/degraded sub-lines. LEFT
sidebar; the header/data block must fit the 34-char left-sidebar maximum
*including* the one-space separators the painter inserts between cells:

    name (_NAME_MAX_WIDTH) + 1 + used (7) + 1 + avail (7) = 18 + 16 = 34

Overshooting by one char makes the painter clip the rightmost column
(mirror of the fs renderer's documented budget).

    RAID disks           Used   Avail
    RAID1 md0               2       2
    RAID0 md9               2       -

Row shapes (v4 parity):
- raid0 + active   -> Used = len(components), Avail = "-".
- active non-raid0 -> Used = used, Avail = available.
- inactive         -> name-only row + `└─ Status inactive` + one line per
                      sorted component (Task 5).
- degraded         -> `└─ Degraded mode` + optional layout line (Task 5).
"""

from __future__ import annotations

from typing import Any

from glances.outputs.curses_renderer_v5 import _LEVEL_TO_ROLE, Cell, ColorRole, Row

_NAME_MAX_WIDTH = 18
_USED_COL_WIDTH = 7
_AVAIL_COL_WIDTH = 7
# Painter inserts a 1-space separator between adjacent cells, so the block
# spans _NAME_MAX_WIDTH + 1 + _USED_COL_WIDTH + 1 + _AVAIL_COL_WIDTH. Must
# stay <= the left-sidebar maximum or the trailing column is clipped.
_LEFT_SIDEBAR_MAX_WIDTH = 34


def _format_name(array_type: Any, name: str) -> str:
    """`<TYPE> <name>` (v4 parity), truncated/padded to _NAME_MAX_WIDTH."""
    type_str = str(array_type).upper() if array_type is not None else "UNKNOWN"
    full = f"{type_str} {name}"
    if len(full) > _NAME_MAX_WIDTH:
        return full[:_NAME_MAX_WIDTH]
    return full.ljust(_NAME_MAX_WIDTH)


def _status_role(levels: dict[str, Any], name: str) -> tuple[ColorRole, bool]:
    entry = levels.get(name, {}) if isinstance(levels, dict) else {}
    status_entry = entry.get("status", {}) if isinstance(entry, dict) else {}
    level = status_entry.get("level")
    prominent = bool(status_entry.get("prominent"))
    return _LEVEL_TO_ROLE.get(level, ColorRole.DEFAULT), prominent


def render(payload: dict[str, Any], fields_desc: dict[str, dict[str, Any]] | None = None, view=None) -> list[Row]:
    header = Row(
        cells=[
            Cell(text="RAID disks".ljust(_NAME_MAX_WIDTH), color=ColorRole.HEADER, bold=True),
            Cell(text="Used".rjust(_USED_COL_WIDTH), color=ColorRole.HEADER, bold=True),
            Cell(text="Avail".rjust(_AVAIL_COL_WIDTH), color=ColorRole.HEADER, bold=True),
        ]
    )
    rows: list[Row] = [header]

    if not isinstance(payload, dict):
        return rows
    items = payload.get("data")
    if not isinstance(items, list):
        return rows
    levels = payload.get("_levels") if isinstance(payload.get("_levels"), dict) else {}

    # Sort by array name (v4: sorted(self.stats.keys())).
    for item in sorted(items, key=lambda it: str(it.get("name", ""))):
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", ""))
        if not name:
            continue
        array_type = item.get("type")
        status = item.get("status")
        used = item.get("used")
        available = item.get("available")
        components = item.get("components") or {}
        config = str(item.get("config") or "")
        role, prominent = _status_role(levels, name)

        if array_type == "raid0" and status == "active":
            rows.append(
                Row(
                    cells=[
                        Cell(text=_format_name(array_type, name)),
                        Cell(text=str(len(components)).rjust(_USED_COL_WIDTH), color=role, prominent=prominent),
                        Cell(text="-".rjust(_AVAIL_COL_WIDTH), color=role, prominent=prominent),
                    ]
                )
            )
        elif status == "active":
            rows.append(
                Row(
                    cells=[
                        Cell(text=_format_name(array_type, name)),
                        Cell(text=str(used).rjust(_USED_COL_WIDTH), color=role, prominent=prominent),
                        Cell(text=str(available).rjust(_AVAIL_COL_WIDTH), color=role, prominent=prominent),
                    ]
                )
            )
        else:
            # inactive / unknown status: name-only row (sub-lines follow — Task 5).
            rows.append(Row(cells=[Cell(text=_format_name(array_type, name))]))

        # Inactive: list the component disks under a status sub-line.
        if status == "inactive":
            rows.append(Row(cells=[Cell(text=f"└─ Status {status}", color=role, prominent=prominent)]))
            component_names = sorted(components.keys())
            for i, component in enumerate(component_names):
                tree_char = "└─" if i == len(component_names) - 1 else "├─"
                rows.append(Row(cells=[Cell(text=f"   {tree_char} disk {components[component]}: {component}")]))

        # Degraded: non-raid0 array with fewer used than available disks.
        if array_type != "raid0" and used is not None and available is not None and used < available:
            rows.append(Row(cells=[Cell(text="└─ Degraded mode", color=role, prominent=prominent)]))
            if len(config) < 17:
                rows.append(Row(cells=[Cell(text=f"   └─ {config.replace('_', 'A')}")]))

    return rows

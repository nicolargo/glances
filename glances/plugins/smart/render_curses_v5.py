#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — TUI curses renderer for the smart plugin.

Mirrors v4 `smart.msg_curse()`: a `SMART disks` header, then per device a
name line followed by one line per SMART attribute (`name` + right-aligned
raw value). LEFT sidebar; the two-cell attribute rows must fit the 34-char
left-sidebar maximum *including* the one-space separator the painter inserts:

    name (_NAME_COL_WIDTH) + 1 + value (_VALUE_COL_WIDTH) = 25 + 1 + 8 = 34

Overshooting by one char makes the painter truncate the value cell.

    SMART disks
    /dev/sda Samsung SSD 850
     Power On Hours            12345
     Reallocated Sector Ct         0
"""

from __future__ import annotations

from typing import Any

from glances.globals import auto_unit
from glances.outputs.curses_renderer_v5 import Cell, ColorRole, Row
from glances.plugins.smart import LARGE_VALUE_KEYS

_NAME_COL_WIDTH = 25
_VALUE_COL_WIDTH = 8
# Painter inserts a 1-space separator between the two cells, so the block
# spans _NAME_COL_WIDTH + 1 + _VALUE_COL_WIDTH. Must stay <= the left-sidebar
# maximum or the trailing value is clipped (see module docstring).
_LEFT_SIDEBAR_MAX_WIDTH = 34


def _attr_name_text(name: Any) -> str:
    """Leading-space-indented attribute name, '_'→' ', clamped to the column."""
    display = " " + str(name).replace("_", " ")
    return display[:_NAME_COL_WIDTH].ljust(_NAME_COL_WIDTH)


def _attr_value_text(attr: dict[str, Any]) -> str:
    """Format the raw value: auto_unit for LARGE_VALUE_KEYS, else str; None→''."""
    raw = attr.get("raw")
    if raw is None:
        text = ""
    elif attr.get("key") in LARGE_VALUE_KEYS:
        text = auto_unit(raw)
    else:
        text = str(raw)
    return text.rjust(_VALUE_COL_WIDTH)


def render(payload: dict[str, Any], fields_desc: dict[str, dict[str, Any]] | None = None, view=None) -> list[Row]:
    header = Row(cells=[Cell(text="SMART disks".ljust(_NAME_COL_WIDTH), color=ColorRole.HEADER, bold=True)])
    rows: list[Row] = [header]

    if not isinstance(payload, dict):
        return rows
    devices = payload.get("data")
    if not isinstance(devices, list):
        return rows

    for device in devices:
        if not isinstance(device, dict):
            continue
        name = str(device.get("name", ""))
        rows.append(Row(cells=[Cell(text=name[:_LEFT_SIDEBAR_MAX_WIDTH])]))
        for attr in device.get("attributes", []):
            if not isinstance(attr, dict):
                continue
            rows.append(
                Row(
                    cells=[
                        Cell(text=_attr_name_text(attr.get("name", ""))),
                        Cell(text=_attr_value_text(attr)),
                    ]
                )
            )
    return rows

#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — TUI curses renderer for the sensors plugin.

Mirrors v4 `sensors.msg_curse()`: a `SENSORS` header then one row per
sensor (`label` + right-aligned value). LEFT sidebar; the block must fit
the v5 left-sidebar maximum (34 chars) *including* the one-space cell
separator the painter inserts between the two cells:

    name (_NAME_MAX_WIDTH) + 1 + value (_VALUE_COL_WIDTH) = 19 + 1 + 14 = 34

Overshooting by even one char makes the painter truncate the rightmost
cell — clipping the trailing unit/trend off the value (v4 parity via the
fs renderer's documented budget).

    SENSORS
    Core 0                  42C
    fan1                  1200R
    Battery                80%v

- Fahrenheit (`view["fahrenheit"]`) converts temperature rows only
  (not battery / fan_speed).
- Battery rows show a trend arrow from `status`.
- hddtemp string sentinels (ERR/SLP/UNK/NOS) render verbatim.
- Empty-value battery rows are skipped.
"""

from __future__ import annotations

from typing import Any

from glances.globals import to_fahrenheit
from glances.outputs.curses_renderer_v5 import _LEVEL_TO_ROLE, Cell, ColorRole, Row
from glances.outputs.glances_unicode import unicode_message

_NAME_MAX_WIDTH = 19
_VALUE_COL_WIDTH = 14
# Painter inserts a 1-space separator between the two cells, so the block
# spans _NAME_MAX_WIDTH + 1 + _VALUE_COL_WIDTH. Must stay <= the left-sidebar
# maximum or the trailing unit/trend is clipped (see module docstring).
_LEFT_SIDEBAR_MAX_WIDTH = 34
_SENTINELS = ("ERR", "SLP", "UNK", "NOS")
_NO_FAHRENHEIT_TYPES = ("battery", "fan_speed")


def _format_label(label: str) -> str:
    if len(label) > _NAME_MAX_WIDTH:
        return label[:_NAME_MAX_WIDTH]
    return label.ljust(_NAME_MAX_WIDTH)


def _battery_trend(row: dict[str, Any]) -> str:
    status = str(row.get("status", ""))
    if status.startswith("Charg"):
        return unicode_message("ARROW_UP")
    if status.startswith("Discharg"):
        return unicode_message("ARROW_DOWN")
    if status.startswith("Full"):
        return unicode_message("CHECK")
    return ""


def _level_role(levels: dict[str, Any], label: str) -> tuple[ColorRole, bool]:
    entry = levels.get(label, {}) if isinstance(levels, dict) else {}
    value_entry = entry.get("value", {}) if isinstance(entry, dict) else {}
    level = value_entry.get("level")
    prominent = bool(value_entry.get("prominent"))
    return _LEVEL_TO_ROLE.get(level, ColorRole.DEFAULT), prominent


def _value_text(row: dict[str, Any], fahrenheit: bool) -> str:
    value = row.get("value")
    sensor_type = str(row.get("type", ""))
    unit = str(row.get("unit", ""))

    if isinstance(value, str) and value in _SENTINELS:
        return value.rjust(_VALUE_COL_WIDTH)

    if not isinstance(value, (int, float)):
        return ""  # empty battery ([]) or unknown -> caller skips

    if fahrenheit and sensor_type not in _NO_FAHRENHEIT_TYPES:
        text = f"{to_fahrenheit(value):.0f}F"
    else:
        trend = _battery_trend(row) if sensor_type == "battery" else ""
        text = f"{value:.0f}{unit}{trend}"
    return text.rjust(_VALUE_COL_WIDTH)


def render(payload: dict[str, Any], fields_desc: dict[str, dict[str, Any]] | None = None, view=None) -> list[Row]:
    header = Row(cells=[Cell(text="SENSORS".ljust(_NAME_MAX_WIDTH), color=ColorRole.HEADER, bold=True)])
    rows: list[Row] = [header]

    if not isinstance(payload, dict):
        return rows
    items = payload.get("data")
    if not isinstance(items, list):
        return rows
    levels = payload.get("_levels") if isinstance(payload.get("_levels"), dict) else {}
    view = view or {}
    fahrenheit = bool(view.get("fahrenheit"))

    for row in items:
        if not isinstance(row, dict):
            continue
        # Skip empty-value battery rows (v4 parity).
        if str(row.get("type", "")) == "battery" and row.get("value") in ([], None, ""):
            continue
        value_text = _value_text(row, fahrenheit)
        if not value_text:
            continue
        role, prominent = _level_role(levels, str(row.get("label", "")))
        rows.append(
            Row(
                cells=[
                    Cell(text=_format_label(str(row.get("label", "")))),
                    Cell(text=value_text, color=role, prominent=prominent),
                ],
                item_start=True,
            )
        )
    return rows

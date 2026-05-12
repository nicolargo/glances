#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — pure curses renderer (no I/O).

The renderer is the layout brain of the TUI: it takes a snapshot of the
StatsStore (a `dict` of `plugin_name → payload`) plus the alert history
and produces a structured `Frame` of `Row`s of `Cell`s. The curses I/O
thread (glances_curses_v5.py) then plots the frame onto the terminal.

Keeping the renderer pure (no curses, no threading, no I/O) lets us
unit-test layout decisions exhaustively without driving a real terminal.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from glances.outputs.curses_formatters_v5 import format_value


class ColorRole(Enum):
    """Renderer-internal color role.

    The curses I/O layer maps each role to a concrete curses color pair
    (see glances_curses_v5).
    """

    DEFAULT = "default"
    OK = "ok"
    CAREFUL = "careful"
    WARNING = "warning"
    CRITICAL = "critical"
    HEADER = "header"


_LEVEL_TO_ROLE: dict[str, ColorRole] = {
    "ok": ColorRole.OK,
    "careful": ColorRole.CAREFUL,
    "warning": ColorRole.WARNING,
    "critical": ColorRole.CRITICAL,
}


@dataclass
class Cell:
    """One renderable unit on a row."""

    text: str
    color: ColorRole = ColorRole.DEFAULT
    prominent: bool = False  # background highlight when True (cf. §3.3)


@dataclass
class Row:
    cells: list[Cell] = field(default_factory=list)


@dataclass
class Frame:
    """The complete TUI screen: ordered rows for left/right columns + footer."""

    left: list[Row] = field(default_factory=list)
    right: list[Row] = field(default_factory=list)
    footer: list[Row] = field(default_factory=list)


# ----------------------------------------------------------------- helpers


def _level_entry(payload: dict[str, Any], field_name: str) -> dict[str, Any]:
    levels = payload.get("_levels", {})
    if isinstance(levels, dict):
        entry = levels.get(field_name)
        if isinstance(entry, dict):
            return entry
    return {}


def _cell_for_field(
    field_name: str,
    value: Any,
    schema: dict[str, Any],
    payload: dict[str, Any],
) -> Cell:
    text = format_value(value, schema)
    entry = _level_entry(payload, field_name)
    level = entry.get("level")
    role = _LEVEL_TO_ROLE.get(level, ColorRole.DEFAULT)
    prominent = bool(entry.get("prominent")) if entry else False
    return Cell(text=text, color=role, prominent=prominent)


# ----------------------------------------------------------------- scalar


def render_scalar_plugin(
    plugin_name: str,
    payload: dict[str, Any],
    fields_desc: dict[str, dict[str, Any]],
) -> list[Row]:
    """Render a scalar plugin (`mem`, `cpu`, `load`).

    Layout: a header row carrying the plugin label, then one row per
    visible field showing `label: value`. The "primary" field (the only
    `watched: True` one or the first declared) is highlighted in the
    header alongside the plugin name.

    The header label is the plugin's most-prominent watched field's
    `label` upper-cased (e.g. `MEM` for the `percent` field of the `mem`
    plugin). Falls back to the plugin_name in upper case when no watched
    field is found.
    """
    header_label, primary_field = _resolve_header(plugin_name, fields_desc)
    header_cells: list[Cell] = [Cell(text=header_label, color=ColorRole.HEADER)]

    if primary_field and primary_field in payload:
        header_cells.append(
            _cell_for_field(primary_field, payload.get(primary_field), fields_desc[primary_field], payload)
        )

    rows: list[Row] = [Row(cells=header_cells)]

    for field_name, schema in fields_desc.items():
        if field_name == primary_field:
            continue
        if field_name not in payload:
            continue
        label = schema.get("label") or field_name
        value_cell = _cell_for_field(field_name, payload.get(field_name), schema, payload)
        rows.append(Row(cells=[Cell(text=f"{label}:"), value_cell]))

    return rows


def _resolve_header(plugin_name: str, fields_desc: dict[str, dict[str, Any]]) -> tuple[str, str | None]:
    """Pick (header label, primary field) for a scalar plugin.

    Heuristic: the first watched field wins; if none is watched, the
    plugin_name itself becomes the header and no primary field is shown
    inline.
    """
    for name, schema in fields_desc.items():
        if schema.get("watched"):
            label = (schema.get("label") or plugin_name).upper()
            return label, name
    return plugin_name.upper(), None

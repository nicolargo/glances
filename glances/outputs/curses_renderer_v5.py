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


# ----------------------------------------------------------------- collection


def render_collection_plugin(
    plugin_name: str,
    payload: dict[str, Any],
    fields_desc: dict[str, dict[str, Any]],
) -> list[Row]:
    """Render a collection plugin (`network`, `fs`, …).

    Layout:
        Header row with the plugin name and column labels.
        One row per item, each cell formatted per `fields_desc`.

    The primary-key field is always the leftmost column. Other columns
    appear in `fields_desc` declaration order. Per-item `_levels` are
    looked up under `payload['_levels'][pk_value]`.
    """
    pk_field = _resolve_primary_key(fields_desc)
    visible_fields = [name for name in fields_desc if name != pk_field]

    header_cells: list[Cell] = [Cell(text=plugin_name.upper(), color=ColorRole.HEADER)]
    if pk_field:
        header_cells.append(Cell(text=fields_desc[pk_field].get("label", pk_field), color=ColorRole.HEADER))
    for name in visible_fields:
        header_cells.append(Cell(text=fields_desc[name].get("label", name), color=ColorRole.HEADER))
    rows: list[Row] = [Row(cells=header_cells)]

    items = payload.get("data", []) if isinstance(payload, dict) else []
    levels_index = payload.get("_levels", {}) if isinstance(payload, dict) else {}

    for item in items:
        if not isinstance(item, dict):
            continue
        pk_value = item.get(pk_field) if pk_field else None
        item_levels = levels_index.get(pk_value, {}) if isinstance(levels_index, dict) else {}
        per_item_payload = {**item, "_levels": item_levels}

        cells: list[Cell] = [Cell(text="")]  # spacer under the plugin-name header column
        if pk_field:
            cells.append(Cell(text=format_value(item.get(pk_field), fields_desc[pk_field])))
        for name in visible_fields:
            cells.append(_cell_for_field(name, item.get(name), fields_desc[name], per_item_payload))
        rows.append(Row(cells=cells))

    return rows


def _resolve_primary_key(fields_desc: dict[str, dict[str, Any]]) -> str | None:
    for name, schema in fields_desc.items():
        if schema.get("primary_key"):
            return name
    return None


# ----------------------------------------------------------------- footer


def render_alert_footer(history: list[dict[str, Any]], limit: int = 10) -> list[Row]:
    """Render the alert history footer (vertical list, most recent at top).

    Header row: `ALERTS (n)`. Then up to `limit` event rows showing
    timestamp, plugin/key, field, transition (previous → new). When the
    history is empty, a single info row is shown.
    """
    rows: list[Row] = [Row(cells=[Cell(text=f"ALERTS ({len(history)})", color=ColorRole.HEADER)])]
    if not history:
        rows.append(Row(cells=[Cell(text="(no events)")]))
        return rows

    recent = list(reversed(history[-limit:]))
    for evt in recent:
        ts = str(evt.get("ts", "")).split("T")[-1][:8]  # HH:MM:SS
        plugin = str(evt.get("plugin", ""))
        key = evt.get("key")
        target = f"{plugin}[{key}]" if key is not None else plugin
        field_name = str(evt.get("field", ""))
        previous = str(evt.get("previous_level", ""))
        new_level = str(evt.get("level", ""))
        prominent = bool(evt.get("prominent", False))
        role = _LEVEL_TO_ROLE.get(new_level, ColorRole.DEFAULT)
        rows.append(
            Row(
                cells=[
                    Cell(text=ts),
                    Cell(text=target),
                    Cell(text=field_name),
                    Cell(text=f"{previous} → {new_level}", color=role, prominent=prominent),
                ]
            )
        )
    return rows


# ----------------------------------------------------------------- frame


def build_frame(
    store_snapshot: dict[str, dict[str, Any]],
    fields_by_plugin: dict[str, dict[str, dict[str, Any]]],
    registry: list[tuple[str, bool]],
    alerts_history: list[dict[str, Any]],
    alerts_limit: int = 10,
) -> Frame:
    """Assemble a complete TUI Frame.

    Args:
        store_snapshot: `{plugin_name: payload}` — a shallow copy of the store.
        fields_by_plugin: `{plugin_name: fields_description}`.
        registry: ordered list of `(plugin_name, is_collection)` — controls
            which plugins are displayed and in which order.
        alerts_history: the deque output of `GlancesAlerts.get_history()`.
        alerts_limit: cap on the number of events rendered in the footer.

    Rules:
        - Scalar plugins → left column.
        - Collection plugins → right column.
        - Footer → alerts history.
        - A plugin in the registry with no payload (cycle-0) still gets its
          header rendered.
    """
    frame = Frame()
    for plugin_name, is_collection in registry:
        payload = store_snapshot.get(plugin_name) or {}
        fields_desc = fields_by_plugin.get(plugin_name, {})
        if is_collection:
            frame.right.extend(render_collection_plugin(plugin_name, payload, fields_desc))
            frame.right.append(Row(cells=[Cell(text="")]))  # spacer between plugins
        else:
            frame.left.extend(render_scalar_plugin(plugin_name, payload, fields_desc))
            frame.left.append(Row(cells=[Cell(text="")]))
    frame.footer = render_alert_footer(alerts_history, limit=alerts_limit)
    return frame

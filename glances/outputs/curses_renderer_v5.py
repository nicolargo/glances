#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — pure curses renderer (no I/O).

Layout mirrors v4 (`glances/outputs/glances_curses.py`):

    +--------------------------------------------------+
    | (optional header — not in G0)                    |
    +--------------------------------------------------+
    | CPU block | MEM block | LOAD block | ...         |   top row (horizontal)
    +--------------------------------------------------+
    | NETWORK            | ALERT                       |
    | ...                | ...                         |   left + right sidebars
    | (other left)       | (other right)               |
    +--------------------------------------------------+

The renderer produces three slot lists of `PluginBlock`s (each a list of
`Row`s). The curses I/O thread (`glances_curses_v5.py`) is responsible
for placing the blocks onto the terminal:
    - top blocks are painted side-by-side from row 0
    - left/right blocks are stacked vertically below the top row

Keeping the renderer pure (no curses, no threading) lets us unit-test
slot routing + per-plugin rendering without driving a real terminal.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from glances.outputs.curses_formatters_v5 import format_value

# --------------------------------------------------------------- v4 slot lists
#
# Mirrors v4's `_top`, `_left_sidebar`, `_right_sidebar` (see
# `glances/outputs/glances_curses.py`). Plugin names not in any list
# default to LEFT (same fallback as v4). Configurable via [outputs] later.

TOP_SLOT: tuple[str, ...] = ("quicklook", "cpu", "percpu", "gpu", "mem", "memswap", "load")
LEFT_SLOT: tuple[str, ...] = (
    "network",
    "ports",
    "wifi",
    "connections",
    "diskio",
    "fs",
    "irq",
    "folders",
    "raid",
    "smart",
    "sensors",
    "now",
)
RIGHT_SLOT: tuple[str, ...] = (
    "vms",
    "containers",
    "processcount",
    "amps",
    "processlist",
    "programlist",
    "alert",
)


def slot_for(plugin_name: str) -> str:
    """Return the layout slot for a plugin: 'top', 'left', or 'right'."""
    if plugin_name in TOP_SLOT:
        return "top"
    if plugin_name in RIGHT_SLOT:
        return "right"
    # Default to left sidebar (matches v4: an unknown plugin lands there).
    return "left"


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
class PluginBlock:
    """A plugin's multi-line output as a self-contained block.

    The painter places blocks: TOP-slot blocks side-by-side on row 0,
    LEFT/RIGHT-slot blocks stacked vertically below the top row.
    """

    name: str
    rows: list[Row] = field(default_factory=list)

    @property
    def height(self) -> int:
        return len(self.rows)

    @property
    def width(self) -> int:
        """Max printable width across rows (single-space cell separator)."""
        return max((sum(len(c.text) for c in r.cells) + max(0, len(r.cells) - 1) for r in self.rows), default=0)


@dataclass
class Frame:
    """The complete TUI screen, sliced into v4-equivalent slots."""

    top: list[PluginBlock] = field(default_factory=list)
    left: list[PluginBlock] = field(default_factory=list)
    right: list[PluginBlock] = field(default_factory=list)


# --------------------------------------------------------------- helpers


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


# --------------------------------------------------------------- scalar


def render_scalar_plugin(
    plugin_name: str,
    payload: dict[str, Any],
    fields_desc: dict[str, dict[str, Any]],
) -> list[Row]:
    """Render a scalar plugin (`mem`, `cpu`, `load`) as a block.

    Layout — replicates v4's compact "block per plugin" style used in the
    top row:

        HEADER  primary%               <- header row: label (HEADER) + primary value
        label1: value1                 <- one row per remaining displayed field
        label2: value2
        ...

    The header label is the plugin's most-prominent watched field's `label`
    upper-cased (e.g. `MEM` for the `percent` field of the `mem` plugin).
    Falls back to plugin_name.upper() when no watched field is found.
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


# --------------------------------------------------------------- collection


def render_collection_plugin(
    plugin_name: str,
    payload: dict[str, Any],
    fields_desc: dict[str, dict[str, Any]],
) -> list[Row]:
    """Render a collection plugin (`network`, `fs`, …) as a block.

    Layout — replicates v4's left-sidebar style (header row + one row per
    item):

        NETWORK         Rx     Tx        <- header: plugin name + column labels
        eth0            1.2M   300K
        wlp0s20f3       45K    12K
        ...

    Per-item `_levels` are looked up under `payload['_levels'][pk_value]`.
    """
    pk_field = _resolve_primary_key(fields_desc)
    visible_fields = [name for name in fields_desc if name != pk_field]

    header_cells: list[Cell] = [Cell(text=plugin_name.upper(), color=ColorRole.HEADER)]
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

        cells: list[Cell] = []
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


# --------------------------------------------------------------- alert block


def render_alert_block(history: list[dict[str, Any]], limit: int = 10) -> list[Row]:
    """Render the alert history (vertical list, most recent at top).

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


# --------------------------------------------------------------- frame


def build_frame(
    store_snapshot: dict[str, dict[str, Any]],
    fields_by_plugin: dict[str, dict[str, dict[str, Any]]],
    registry: list[tuple[str, bool]],
    alerts_history: list[dict[str, Any]],
    alerts_limit: int = 10,
) -> Frame:
    """Assemble a complete TUI Frame following v4's slot layout.

    Args:
        store_snapshot: `{plugin_name: payload}` — a shallow copy of the store.
        fields_by_plugin: `{plugin_name: fields_description}`.
        registry: ordered list of `(plugin_name, is_collection)`. The
            collection flag drives the rendering function (scalar vs
            collection) — the slot (top / left / right) is derived from
            the plugin name via `slot_for()`.
        alerts_history: output of `GlancesAlerts.get_history()`.
        alerts_limit: cap on the number of events rendered in the alert block.

    Rules (matching v4's `__display_top` / `__display_left` / `__display_right`):
        - cpu / percpu / mem / load → TOP slot (rendered side-by-side
          horizontally by the painter).
        - network and other collections → LEFT slot.
        - alerts (synthesized) → RIGHT slot.
        - Unknown plugins default to LEFT (same as v4's fallback).
    """
    frame = Frame()
    for plugin_name, is_collection in registry:
        payload = store_snapshot.get(plugin_name) or {}
        fields_desc = fields_by_plugin.get(plugin_name, {})
        if is_collection:
            rows = render_collection_plugin(plugin_name, payload, fields_desc)
        else:
            rows = render_scalar_plugin(plugin_name, payload, fields_desc)
        block = PluginBlock(name=plugin_name, rows=rows)

        slot = slot_for(plugin_name)
        if slot == "top":
            frame.top.append(block)
        elif slot == "right":
            frame.right.append(block)
        else:
            frame.left.append(block)

    # Synthesize the alerts block in the RIGHT slot (mirrors v4's `alert`
    # plugin in `_right_sidebar`).
    frame.right.append(PluginBlock(name="alert", rows=render_alert_block(alerts_history, limit=alerts_limit)))
    return frame

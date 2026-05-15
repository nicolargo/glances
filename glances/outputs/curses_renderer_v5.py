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

import importlib
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from glances.outputs.curses_formatters_v5 import format_value

logger = logging.getLogger(__name__)

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

# Severity ordering for picking the "worst" level across multiple
# prominent fields in a single plugin payload.
_LEVEL_PRIORITY: dict[str, int] = {"ok": 0, "careful": 1, "warning": 2, "critical": 3}


def _max_prominent_level(payload: dict[str, Any]) -> str:
    """Return the worst level among prominent `_levels` entries.

    Supports both scalar payload (`_levels` is `{field: {level, prominent}}`)
    and collection payload (`_levels` is `{pk: {field: {level, prominent}}}`).
    Returns ``"ok"`` when no prominent field is escalated.
    """
    levels = payload.get("_levels", {}) if isinstance(payload, dict) else {}
    if not isinstance(levels, dict):
        return "ok"

    def _scan(entries: dict) -> str:
        worst = "ok"
        worst_pri = 0
        for entry in entries.values():
            if not isinstance(entry, dict):
                continue
            # Detect shape: leaf entry has a `level` key.
            if "level" in entry:
                if not entry.get("prominent"):
                    continue
                lvl = entry.get("level", "ok")
                pri = _LEVEL_PRIORITY.get(lvl, 0)
                if pri > worst_pri:
                    worst, worst_pri = lvl, pri
            else:
                # Nested (collection) — recurse one level.
                nested = _scan(entry)
                pri = _LEVEL_PRIORITY.get(nested, 0)
                if pri > worst_pri:
                    worst, worst_pri = nested, pri
        return worst

    return _scan(levels)


def title_role(payload: dict[str, Any]) -> ColorRole:
    """Pick the renderer role for a plugin title given its payload.

    - No prominent field at warning or above → ``ColorRole.HEADER``
      (bold white, v4 TITLE decoration). ``ok`` and ``careful`` keep
      the title neutral.
    - Worst prominent level is warning/critical → the level's role
      (rendered bold + that colour).
    """
    level = _max_prominent_level(payload)
    if level in ("ok", "careful"):
        return ColorRole.HEADER
    return _LEVEL_TO_ROLE.get(level, ColorRole.HEADER)


@dataclass
class Cell:
    """One renderable unit on a row."""

    text: str
    color: ColorRole = ColorRole.DEFAULT
    prominent: bool = False  # background highlight when True (cf. §3.3)
    bold: bool = False  # explicit bold attribute (HEADER cells are bold automatically)


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


# Per-unit minimum column widths (chars). Picked so a "full" value never
# resizes the column cycle-to-cycle:
#   percent     "100.0%"   = 6
#   bytes       "999.9G"   = 6
#   bytespers   "999.9G/s" = 8
#   seconds     "1d23h"    = 5  (rounded to 6 for breathing room)
#   number      "9999"     = 5
#   bool        "yes"/"no" = 3
# An explicit `column_width` in the schema overrides the unit default.
_UNIT_MIN_WIDTHS: dict[str, int] = {
    "percent": 6,
    "bytes": 6,
    "bytespers": 8,
    "seconds": 6,
    "number": 5,
    "bool": 3,
}


def _min_value_width(schema: dict[str, Any]) -> int:
    """Return the fixed minimum width for a value cell, given its schema."""
    cw = schema.get("column_width")
    if isinstance(cw, int) and cw > 0:
        return cw
    return _UNIT_MIN_WIDTHS.get(schema.get("unit", ""), 0)


def field_label(schema: dict[str, Any], field_name: str, prefer_short: bool = False) -> str:
    """Resolve the user-visible label for a field, honouring renderer hints.

    Precedence:
        - When ``prefer_short`` is True: ``short_name`` → ``label`` → field name.
        - When ``prefer_short`` is False (default — generic renderer):
          ``label`` → field name.

    Per-plugin renderers (``render_curses_v5.py``) pass ``prefer_short=True``
    when they pack a block into a tight grid (e.g. cpu's 3-column row of
    counter rates). v5 ``short_name`` mirrors v4 ``short_name`` (cf.
    ``curse_add_stat`` in ``glances/plugins/plugin/model.py``).
    """
    if prefer_short:
        short = schema.get("short_name")
        if isinstance(short, str) and short:
            return short
    label = schema.get("label")
    if isinstance(label, str) and label:
        return label
    return field_name


def _cell_for_field(
    field_name: str,
    value: Any,
    schema: dict[str, Any],
    payload: dict[str, Any],
) -> Cell:
    text = format_value(value, schema)
    min_w = _min_value_width(schema)
    if min_w > 0 and len(text) < min_w:
        text = text.rjust(min_w)
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
    top row, laid out as a 2-column table:

        HEADER          primary%       <- header row: label (HEADER) + primary value
        label1          value1         <- one row per remaining displayed field
        label2          value2
        ...

    The header label is the plugin's most-prominent watched field's `label`
    upper-cased (e.g. `MEM` for the `percent` field of the `mem` plugin).
    Falls back to plugin_name.upper() when no watched field is found.

    Fields flagged ``internal: True`` in the schema (e.g. ``time_since_update``,
    ``cpucore``) are skipped — they support computation but never appear in
    the UI.
    """
    header_label, primary_field = _resolve_header(plugin_name, fields_desc)
    # Header row.
    header_label_cell = Cell(text=header_label, color=ColorRole.HEADER)
    if primary_field and primary_field in payload:
        header_value_cell = _cell_for_field(
            primary_field, payload.get(primary_field), fields_desc[primary_field], payload
        )
    else:
        header_value_cell = Cell(text="")
    rows: list[Row] = [Row(cells=[header_label_cell, header_value_cell])]

    # Body rows.
    for field_name, schema in fields_desc.items():
        if field_name == primary_field:
            continue
        if schema.get("internal"):
            continue
        if field_name not in payload:
            continue
        label = schema.get("label") or field_name
        value_cell = _cell_for_field(field_name, payload.get(field_name), schema, payload)
        rows.append(Row(cells=[Cell(text=label), value_cell]))

    return _align_two_column_table(rows)


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
    item) as a multi-column table:

        NETWORK         Rx     Tx        <- header: plugin name + column labels
        eth0           1.2M   300K       <- primary key left-aligned, values right-aligned
        wlp0s20f3       45K    12K
        ...

    Per-item `_levels` are looked up under `payload['_levels'][pk_value]`.
    Fields flagged ``internal: True`` are skipped.
    """
    pk_field = _resolve_primary_key(fields_desc)
    visible_fields = [name for name in fields_desc if name != pk_field and not fields_desc[name].get("internal")]

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

    return _align_multi_column_table(rows)


def _resolve_primary_key(fields_desc: dict[str, dict[str, Any]]) -> str | None:
    for name, schema in fields_desc.items():
        if schema.get("primary_key"):
            return name
    return None


# --------------------------------------------------------------- alignment


def _align_two_column_table(rows: list[Row]) -> list[Row]:
    """Pad each row's two cells for table-style alignment:
    column 0 (label) left-aligned, column 1 (value) right-aligned.
    Column widths auto-fit to the widest content. Padding is baked into
    the cell text so the painter's natural one-space cell gap separates
    the columns.
    """
    if not rows:
        return rows
    label_w = max((len(r.cells[0].text) for r in rows if r.cells), default=0)
    value_w = max((len(r.cells[1].text) for r in rows if len(r.cells) >= 2), default=0)

    aligned: list[Row] = []
    for r in rows:
        if not r.cells:
            aligned.append(r)
            continue
        label_cell = r.cells[0]
        padded_label = Cell(
            text=label_cell.text.ljust(label_w),
            color=label_cell.color,
            prominent=label_cell.prominent,
            bold=label_cell.bold,
        )
        if len(r.cells) >= 2:
            value_cell = r.cells[1]
            padded_value = Cell(
                text=value_cell.text.rjust(value_w),
                color=value_cell.color,
                prominent=value_cell.prominent,
                bold=value_cell.bold,
            )
            aligned.append(Row(cells=[padded_label, padded_value]))
        else:
            aligned.append(Row(cells=[padded_label]))
    return aligned


def _align_multi_column_table(rows: list[Row]) -> list[Row]:
    """Pad each row's cells for multi-column table alignment:
    column 0 (primary key / plugin name header) left-aligned, every other
    column right-aligned. Column widths auto-fit to the widest content
    across all rows.
    """
    if not rows:
        return rows
    ncols = max((len(r.cells) for r in rows), default=0)
    if ncols == 0:
        return rows
    col_widths = [0] * ncols
    for r in rows:
        for i, cell in enumerate(r.cells):
            col_widths[i] = max(col_widths[i], len(cell.text))

    aligned: list[Row] = []
    for r in rows:
        new_cells: list[Cell] = []
        for i, cell in enumerate(r.cells):
            if i == 0:
                text = cell.text.ljust(col_widths[i])
            else:
                text = cell.text.rjust(col_widths[i])
            new_cells.append(Cell(text=text, color=cell.color, prominent=cell.prominent, bold=cell.bold))
        aligned.append(Row(cells=new_cells))
    return aligned


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
        is_initial = bool(evt.get("is_initial", False))
        # Initial state observed at startup: show the bare level instead of
        # ``ok → <level>`` since no transition actually happened — Glances
        # just discovered the system was already in this state.
        level_text = new_level if is_initial else f"{previous} → {new_level}"
        role = _LEVEL_TO_ROLE.get(new_level, ColorRole.DEFAULT)
        rows.append(
            Row(
                cells=[
                    Cell(text=ts),
                    Cell(text=target),
                    Cell(text=field_name),
                    Cell(text=level_text, color=role, prominent=prominent),
                ]
            )
        )
    return rows


# --------------------------------------------------------------- frame


# --------------------------------------------------------------- per-plugin renderer discovery


# Cache: plugin_name → render function or None (sentinel for "no custom renderer").
# Avoids retrying failed imports on every cycle.
_PLUGIN_RENDERERS: dict[str, Callable[[dict[str, Any], dict[str, dict[str, Any]]], list[Row]] | None] = {}


def _discover_plugin_renderer(
    plugin_name: str,
) -> Callable[[dict[str, Any], dict[str, dict[str, Any]]], list[Row]] | None:
    """Look up `glances.plugins.<name>.render_curses_v5.render`.

    The convention: a plugin opts in to a custom TUI layout (v4-style)
    by providing a `render_curses_v5.py` module next to `model_v5.py`.
    The module exports `render(payload, fields_desc) -> list[Row]`.

    When the module is absent or fails to import, returns `None` and the
    caller falls back to the generic `render_scalar_plugin` /
    `render_collection_plugin`.
    """
    if plugin_name in _PLUGIN_RENDERERS:
        return _PLUGIN_RENDERERS[plugin_name]

    full_name = f"glances.plugins.{plugin_name}.render_curses_v5"
    try:
        module = importlib.import_module(full_name)
    except ModuleNotFoundError:
        _PLUGIN_RENDERERS[plugin_name] = None
        return None
    except Exception as e:  # pragma: no cover — defensive
        logger.warning("TUI: failed to import %s (%s); using generic renderer", full_name, e)
        _PLUGIN_RENDERERS[plugin_name] = None
        return None

    fn = getattr(module, "render", None)
    if not callable(fn):
        logger.warning("TUI: %s does not expose a callable `render`; using generic renderer", full_name)
        _PLUGIN_RENDERERS[plugin_name] = None
        return None

    _PLUGIN_RENDERERS[plugin_name] = fn
    return fn


def _reset_plugin_renderer_cache() -> None:
    """Test-only helper to clear the discovery cache."""
    _PLUGIN_RENDERERS.clear()


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
            collection flag drives the generic fallback (scalar vs
            collection) — the slot (top / left / right) is derived from
            the plugin name via `slot_for()`.
        alerts_history: output of `GlancesAlerts.get_history()`.
        alerts_limit: cap on the number of events rendered in the alert block.

    Per-plugin renderer:
        If `glances.plugins.<name>.render_curses_v5` exists and exposes a
        callable `render(payload, fields_desc) -> list[Row]`, that
        function is used to build the plugin's block — replicating v4's
        `msg_curse()` style of per-plugin layout. Otherwise the generic
        2-col / N-col table fallback is used.

    Rules (matching v4's `__display_top` / `__display_left` / `__display_right`):
        - cpu / percpu / mem / load → TOP slot.
        - network and other collections → LEFT slot.
        - alerts (synthesized) → RIGHT slot.
        - Unknown plugins default to LEFT (same as v4's fallback).
    """
    frame = Frame()
    for plugin_name, is_collection in registry:
        payload = store_snapshot.get(plugin_name) or {}
        fields_desc = fields_by_plugin.get(plugin_name, {})

        custom = _discover_plugin_renderer(plugin_name)
        if custom is not None:
            try:
                rows = custom(payload, fields_desc)
            except Exception as e:  # pragma: no cover — defensive
                logger.warning(
                    "TUI: custom renderer for %r raised %s; using generic fallback this cycle",
                    plugin_name,
                    e,
                )
                rows = (
                    render_collection_plugin(plugin_name, payload, fields_desc)
                    if is_collection
                    else render_scalar_plugin(plugin_name, payload, fields_desc)
                )
        elif is_collection:
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

    # v4 fidelity: enforce the slot-declared order, not the discovery
    # order (which is alphabetical and would give cpu/load/mem instead
    # of cpu/mem/load in the top row).
    frame.top.sort(key=lambda b: TOP_SLOT.index(b.name) if b.name in TOP_SLOT else len(TOP_SLOT))
    frame.left.sort(key=lambda b: LEFT_SLOT.index(b.name) if b.name in LEFT_SLOT else len(LEFT_SLOT))
    frame.right.sort(key=lambda b: RIGHT_SLOT.index(b.name) if b.name in RIGHT_SLOT else len(RIGHT_SLOT))

    # Synthesize the alerts block in the RIGHT slot (mirrors v4's `alert`
    # plugin in `_right_sidebar`).
    frame.right.append(PluginBlock(name="alert", rows=render_alert_block(alerts_history, limit=alerts_limit)))
    return frame

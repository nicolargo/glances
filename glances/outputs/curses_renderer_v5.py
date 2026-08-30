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

The renderer produces four slot lists of `PluginBlock`s (each a list of
`Row`s). The curses I/O thread (`glances_curses_v5.py`) is responsible
for placing the blocks onto the terminal:
    - header blocks are painted side-by-side above the top row
    - top blocks are painted side-by-side below the header
    - left/right blocks are stacked vertically below the top row

Keeping the renderer pure (no curses, no threading) lets us unit-test
slot routing + per-plugin rendering without driving a real terminal.
"""

from __future__ import annotations

import importlib
import inspect
import logging
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from glances.outputs.curses_formatters_v5 import format_value

logger = logging.getLogger(__name__)

# --------------------------------------------------------------- v4 slot lists
#
# Mirrors v4's `_top`, `_left_sidebar`, `_right_sidebar` (see
# `glances/outputs/glances_curses.py`). Plugin names not in any list
# default to LEFT (same fallback as v4). Configurable via [outputs] later.

# The header slot is split in two alignment groups: the LEFT group is packed
# from the left edge, the RIGHT group is painted right-aligned as a whole (see
# `glances_curses_v5._paint_header`). `now` closes the banner on the far right.
HEADER_SLOT_LEFT: tuple[str, ...] = ("system", "ip")
HEADER_SLOT_RIGHT: tuple[str, ...] = ("uptime", "cloud", "now")
HEADER_SLOT: tuple[str, ...] = HEADER_SLOT_LEFT + HEADER_SLOT_RIGHT
TOP_SLOT: tuple[str, ...] = ("quicklook", "cpu", "percpu", "npu", "mpp", "gpu", "mem", "memswap", "load")
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

# In full-quicklook mode these TOP-slot plugins are hidden so quicklook
# takes the full width. EXACT v4 parity: `enable_fullquicklook`
# (glances/outputs/glances_curses.py:455) disables cpu/npu/mpp/gpu/mem/memswap
# only — `load` and `percpu` stay visible.
_FULL_QUICKLOOK_HIDDEN: frozenset[str] = frozenset({"cpu", "npu", "mpp", "gpu", "mem", "memswap"})


def slot_for(plugin_name: str) -> str:
    """Return the layout slot for a plugin: 'header', 'top', 'left', or 'right'."""
    if plugin_name in HEADER_SLOT:
        return "header"
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

# Plugin titles and column headers are ALWAYS ``ColorRole.HEADER`` (v4's
# fixed "TITLE" decoration). An alert is signalled on the VALUE only — its
# colour plus, for a `prominent` field, the highlighted background. Do not
# escalate a header's colour from `_levels`.


@dataclass
class Cell:
    """One renderable unit on a row."""

    text: str
    color: ColorRole = ColorRole.DEFAULT
    prominent: bool = False  # background highlight when True (cf. §3.3)
    bold: bool = False  # explicit bold attribute (HEADER cells are bold automatically)
    underline: bool = False  # v4 'SORT' decoration (A_UNDERLINE) — active sort column header
    glue: bool = False  # paint with NO separating space before it (contiguous segments,
    # e.g. exec path "/usr/bin/" + bold name "python3" → "/usr/bin/python3")


@dataclass
class Row:
    cells: list[Cell] = field(default_factory=list)
    # True on the FIRST row of a list item. A block whose renderer marks its
    # item rows opts in to the truncation counter ("SENSORS 5/7"): the painter
    # counts the marked rows that survived the cut. Multi-row items (raid's
    # `└─ Degraded mode` sub-lines, smart's per-attribute rows) mark only their
    # head row, so the count stays a count of ITEMS, not of lines.
    item_start: bool = False


@dataclass
class PluginBlock:
    """A plugin's multi-line output as a self-contained block.

    The painter places blocks: TOP-slot blocks side-by-side on row 0,
    LEFT/RIGHT-slot blocks stacked vertically below the top row.
    """

    name: str
    rows: list[Row] = field(default_factory=list)
    # Number of items available in the payload BEFORE the renderer applied
    # any row budget — the RIGHT-column solver needs the real count, which a
    # truncated block no longer reveals. None for scalar plugins.
    data_count: int | None = None
    # Items the vertical fit pass must keep visible whatever the height costs
    # the other blocks. Only `alert` sets it (its active incidents); every
    # other block leaves it at 0 and stays fully elastic.
    data_pinned: int = 0

    @property
    def height(self) -> int:
        return len(self.rows)

    @property
    def width(self) -> int:
        """Max printable width across rows.

        One space separates adjacent cells, except a ``glue`` cell which is
        painted flush against the previous one (no separator)."""

        def row_width(row: Row) -> int:
            text = sum(len(c.text) for c in row.cells)
            separators = sum(1 for i, c in enumerate(row.cells) if i > 0 and not c.glue)
            return text + separators

        return max((row_width(r) for r in self.rows), default=0)


@dataclass
class Frame:
    """The complete TUI screen, sliced into v4-equivalent slots."""

    header: list[PluginBlock] = field(default_factory=list)
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


def _format_alert_time(ts: str, now: datetime | None = None) -> str:
    """Convert an ISO-8601 timestamp (UTC, as emitted by `GlancesAlerts._build_event`)
    to a short local-time string.

    Same-day events: ``HH:MM:SS``. Events from any other day: ``YY-MM-DD``.
    Both forms are exactly 8 columns, the width the alert grid gives the TIME
    column — the full timestamp used to include the hour, but the grid's
    DURATION column now carries the age, so it was redundant.

    Naive timestamps (no tz suffix) are assumed UTC — matches what
    ``_build_event`` produces. Unparseable input falls back to the raw
    first 8 chars so the renderer can never crash on a malformed event.
    """
    try:
        dt = datetime.fromisoformat(ts)
    except (ValueError, TypeError):
        return str(ts)[:8]
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    local_dt = dt.astimezone()
    now_local = (now or datetime.now(tz=timezone.utc)).astimezone()
    if local_dt.date() == now_local.date():
        return local_dt.strftime("%H:%M:%S")
    # Another day: `YY-MM-DD` fills the column exactly, and reads in the same
    # descending order as the `HH:MM:SS` of the same-day rows — `MM-DD` alone
    # was ambiguous about the year. The full timestamp used to be printed
    # here, but the grid's DURATION column now carries the age (design §6.2),
    # so the hour is redundant.
    return local_dt.strftime("%y-%m-%d")


def _format_duration_compact(seconds: float) -> str:
    """Elapsed time in at most 8 columns (design §6.4).

    ``43s`` / ``2m58s`` / ``1h13m`` / ``2d04h``. Replaces ``str(timedelta)``,
    whose ``0:02:04`` reads as a clock rather than an elapsed time and whose
    width is unpredictable. Sub-second precision is dropped so the value does
    not jitter between refreshes.
    """
    total = int(max(0.0, seconds))
    if total < 60:
        return f"{total}s"
    if total < 3600:
        return f"{total // 60}m{total % 60:02d}s"
    if total < 86400:
        return f"{total // 3600}h{(total % 3600) // 60:02d}m"
    return f"{total // 86400}d{(total % 86400) // 3600:02d}h"


def _incident_duration(incident: dict[str, Any], now: datetime | None = None) -> str | None:
    """Rendered duration of one incident, or ``None`` when it cannot be known.

    Ongoing incidents measure from ``begin`` to now; resolved ones from
    ``begin`` to ``end``, so a resolved row freezes instead of ticking. A
    ``partial`` incident — one whose opening transition has aged out of the
    history — is prefixed ``>`` because its duration is a lower bound.

    Returns ``None`` for an unknown, malformed or future ``begin`` (clock
    skew): the caller then leaves the column blank rather than printing
    something false. Never raises — the renderer must not crash on a
    malformed event.
    """
    begin_raw = incident.get("begin")
    if not begin_raw:
        return None
    try:
        begin = datetime.fromisoformat(str(begin_raw))
    except (ValueError, TypeError):
        return None
    if begin.tzinfo is None:
        begin = begin.replace(tzinfo=timezone.utc)

    end_raw = incident.get("end")
    end: datetime | None = None
    if end_raw:
        try:
            end = datetime.fromisoformat(str(end_raw))
        except (ValueError, TypeError):
            end = None
        if end is not None and end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
    if end is None:
        end = now or datetime.now(tz=timezone.utc)

    elapsed = (end - begin).total_seconds()
    if elapsed < 0:
        return None
    text = _format_duration_compact(elapsed)
    return f">{text}" if incident.get("partial") else text


# Severity ranking, used to keep an incident's level monotonic: once an
# incident has reached `critical` it keeps reporting `critical` even if it
# later de-escalates. v4 parity — `GlancesEvent.update()` assigns `state`
# only on CRITICAL (design §2.6).
_LEVEL_ORDER: dict[str, int] = {"ok": 0, "careful": 1, "warning": 2, "critical": 3}


def _derive_incidents(
    history: list[dict[str, Any]],
    ongoing: dict[tuple[str, Any, str], str] | None = None,
    ongoing_since: dict[tuple[str, Any, str], str] | None = None,
) -> list[dict[str, Any]]:
    """Collapse a transition log into incidents (design §5.6).

    The alert engine records level *transitions*; the block shows *incidents*.
    An incident opens on the first transition to a non-``ok`` level for a
    ``(plugin, key, field)`` tuple and closes on its transition back to
    ``ok``. Escalations mutate the open incident, they never open a new one —
    that is the "one row per incident" rule (§5.4).

    ``ongoing`` is ``GlancesAlerts.get_ongoing()``. It is the AUTHORITY on
    what is still active: the history is a bounded ring buffer, so an alert
    can outlive its own transitions. Passing ``None`` falls back to deriving
    "ongoing" from the history alone, which is what direct callers (export,
    tests) want.

    ``ongoing_since`` is ``GlancesAlerts.get_ongoing_since()`` — same keys,
    and for the same reason the AUTHORITY on when each active incident
    opened. Without it, an alert whose opening event has aged out of the
    history has no start at all (rendered ``--:--:--``) or only a lower bound
    taken from a surviving escalation (rendered ``>2h04m``).

    Returns incidents already sorted: ongoing first, newest first within each
    group (§5.3), so a long-running alert cannot sink out of the visible
    window behind newer resolved ones.
    """
    open_by_tuple: dict[tuple[str, Any, str], dict[str, Any]] = {}
    incidents: list[dict[str, Any]] = []

    for evt in history:
        state_key = (str(evt.get("plugin", "")), evt.get("key"), str(evt.get("field", "")))
        level = str(evt.get("level", ""))
        ts = str(evt.get("ts", "")) or None
        if level == "ok":
            closed = open_by_tuple.pop(state_key, None)
            if closed is not None:
                closed["end"] = ts
                closed["ongoing"] = False
            continue
        incident = open_by_tuple.get(state_key)
        if incident is None:
            # A first surviving transition that did not come from `ok` means
            # the opening transition has been evicted from the ring buffer:
            # `begin` is then a lower bound, not the real start. An
            # `is_initial` event is exempt — it IS the start, Glances simply
            # found the system already in that state at boot.
            previous = str(evt.get("previous_level", "ok"))
            partial = previous != "ok" and not bool(evt.get("is_initial", False))
            incident = {
                "plugin": state_key[0],
                "key": state_key[1],
                "field": state_key[2],
                "level": level,
                "begin": ts,
                "end": None,
                "ongoing": True,
                "partial": partial,
                "prominent": bool(evt.get("prominent", False)),
            }
            open_by_tuple[state_key] = incident
            incidents.append(incident)
            continue
        if _LEVEL_ORDER.get(level, 0) > _LEVEL_ORDER.get(incident["level"], 0):
            incident["level"] = level
        incident["prominent"] = incident["prominent"] or bool(evt.get("prominent", False))

    if ongoing is not None:
        for state_key, incident in open_by_tuple.items():
            committed = ongoing.get(state_key)
            if committed is None:
                # The engine says recovered but no `→ ok` event survives.
                # Trust the engine and close the incident with an unknown end.
                incident["ongoing"] = False
            elif _LEVEL_ORDER.get(committed, 0) > _LEVEL_ORDER.get(incident["level"], 0):
                incident["level"] = committed
        # Tuples the engine reports active but the history no longer covers at
        # all. Without this the block would silently drop a live alert.
        for state_key, committed in ongoing.items():
            if state_key in open_by_tuple:
                continue
            incidents.append(
                {
                    "plugin": state_key[0],
                    "key": state_key[1],
                    "field": state_key[2],
                    "level": committed,
                    "begin": None,
                    "end": None,
                    "ongoing": True,
                    "partial": True,
                    "prominent": False,
                }
            )

    # The engine remembers when every ACTIVE incident opened, even once the
    # history has evicted the opening event, so its timestamp wins over
    # whatever the history could reconstruct. That turns a `--:--:--` start
    # (nothing survived) or a `>` lower bound (only an escalation survived)
    # back into the real one. Applied before the sort so the ordering uses the
    # corrected `begin`. Resolved incidents are absent from the map and keep
    # their history-derived values.
    if ongoing_since:
        for incident in incidents:
            if not incident["ongoing"]:
                continue
            since = ongoing_since.get((incident["plugin"], incident["key"], incident["field"]))
            if since:
                incident["begin"] = since
                incident["partial"] = False

    # Two stable passes: chronological within a group, then ongoing on top.
    incidents.sort(key=lambda i: i["begin"] or "", reverse=True)
    incidents.sort(key=lambda i: 0 if i["ongoing"] else 1)
    return incidents


# Alert grid geometry (design §6.2). The painter puts one space between
# adjacent cells, so the TIME and DURATION cells carry one trailing pad
# column each to land the spec's offsets (TIME at 2, DURATION at 12,
# TARGET at 22).
_ALERT_W_GLYPH = 1
_ALERT_W_TIME = 8
_ALERT_W_DURATION = 8
_ALERT_W_LEVEL = 8
_ALERT_MIN_TARGET = 12
# Block width at or above which the LEVEL / DURATION columns still fit
# without starving TARGET below its floor.
_ALERT_W_WITH_LEVEL = 31 + _ALERT_MIN_TARGET  # 43
_ALERT_W_WITH_DURATION = 22 + _ALERT_MIN_TARGET  # 34
_ALERT_GLYPHS = {
    True: {True: "●", False: "*"},  # ongoing
    False: {True: "○", False: "-"},  # resolved
}
_ALERT_TIME_UNKNOWN = "--:--:--"
# Field names that identify nothing on their own — the plugin (and its key)
# already says what the alert is about, so `sensors[i915 0].value` reads better
# as `Sensors i915 0`. Matched on the WHOLE field name, never as a suffix, so
# `memory_usage_percent` keeps its `percent`.
#
# Closed list, grounded on the fields that can actually raise an alert:
# cpu.system/user/total, fs[…].percent, mem.percent, memswap.percent,
# network[…].bytes_*, gpu/npu percentages, sensors[…].value. Do not widen it
# without redoing that check — every name added here silently erases
# information from a row.
_ALERT_GENERIC_FIELDS = frozenset({"value", "percent"})


def _fit_text(text: str, width: int, *, right: bool = False, ellipsis: str = "") -> str:
    """Pad or truncate ``text`` to exactly ``width`` columns.

    ``ellipsis`` — when non-empty — replaces the tail of a cut string so a
    truncated target reads as truncated. The caller passes ``…`` or ``.``
    depending on ``unicode_ok``; it is a parameter rather than a constant
    precisely so ASCII mode cannot leak a non-ASCII character.

    Guarantees the return value is exactly ``width`` long — the grid depends
    on it.
    """
    if width <= 0:
        return ""
    if len(text) > width:
        cut = width - len(ellipsis)
        text = text[:cut] + ellipsis if ellipsis and cut > 0 else text[:width]
    return text.rjust(width) if right else text.ljust(width)


def _humanise_target(plugin: Any, key: Any, field: Any) -> str:
    """Render an incident's target for a human reader rather than a parser.

    ::

        cpu        / None     / system     -> "Cpu system"
        sensors    / "i915 0" / value      -> "Sensors i915 0"
        fs         / "/"      / percent    -> "Fs /"
        containers / "nginx"  / mem_usage  -> "Containers nginx mem usage"

    Only the plugin name is capitalised, and only its first letter: there is no
    acronym table, so ``gpu`` renders as ``Gpu``. The key is kept verbatim —
    device names, mountpoints and container names are already human-readable
    and rewriting them would be lying about what the engine watched.

    A field whose whole name is in `_ALERT_GENERIC_FIELDS` is dropped: it adds
    a column's worth of width and no information.
    """
    parts: list[str] = []
    plugin_name = str(plugin)
    if plugin_name:
        parts.append(plugin_name[:1].upper() + plugin_name[1:])
    if key is not None:
        key_text = str(key).strip()
        if key_text:
            parts.append(key_text)
    field_name = str(field)
    if field_name and field_name not in _ALERT_GENERIC_FIELDS:
        parts.append(field_name.replace("_", " "))
    return " ".join(parts)


def _alert_block_height(n_incidents: int, quota: int) -> int:
    """Row cost of the alert block — kept in lock-step with what
    `render_alert_block` actually emits, so `plan_right_column.cost()` never
    drifts from the painter (design §5, §10).

    Mirrors `render_alert_block`'s own collapse rules exactly:
    - no incidents at all → the single-line ``ALERT (...)`` collapse (§11);
    - ``quota <= 0`` → the shrink ladder's "header only" step (h) — title row
      alone, regardless of how many incidents exist;
    - otherwise → title row + column-header row + up to ``quota`` incident
      rows.
    """
    if n_incidents <= 0 or quota <= 0:
        return 1
    return 2 + min(n_incidents, quota)


def render_alert_block(
    history: list[dict[str, Any]],
    limit: int = 10,
    is_initializing: bool = False,
    now: datetime | None = None,
    ongoing: dict[tuple[str, Any, str], str] | None = None,
    width: int | None = None,
    unicode_ok: bool = True,
    incidents: list[dict[str, Any]] | None = None,
    ongoing_since: dict[tuple[str, Any, str], str] | None = None,
) -> list[Row]:
    """Render the alert history as an aligned incident grid (design §6).

    The block is a JOURNAL, not a gauge: it answers "what happened", never
    "where are we now" — the owning plugin already shows the live value
    (§5.1). One row per incident, ongoing ones pinned above resolved ones.

    Args:
        history: output of ``GlancesAlerts.get_history()``.
        limit: DATA-row budget (the title and column-header rows are extra).
            ``0`` emits the title alone — the vertical shrink ladder's
            "header only" step.
        is_initializing: ``GlancesAlerts.is_initializing()``.
        now: reference instant, so every row of a frame agrees.
        ongoing: ``GlancesAlerts.get_ongoing()`` — the authority on what is
            still active. ``None`` derives it from the history alone.
        width: painted block width (``view["right_width"]``). ``None`` keeps
            the full grid and sizes TARGET to its natural maximum, which is
            what export and direct callers want.
        unicode_ok: ``False`` under ``--disable-unicode`` — ASCII glyphs and
            an ASCII title rule (§6.5).
        incidents: pre-derived incidents (``_derive_incidents(history,
            ongoing)``). Callers that already derived the incidents for this
            frame — ``build_frame``, so ``PluginBlock.data_count`` counts the
            exact same list this function renders, never a second derivation
            that could drift from it — pass them here to skip re-deriving.
            ``None`` (direct callers, tests, export) derives from ``history``
            and ``ongoing`` as before.
        ongoing_since: ``GlancesAlerts.get_ongoing_since()`` — when each
            active incident opened, for the ones the bounded history can no
            longer date. Ignored when ``incidents`` is passed (the caller
            already applied it while deriving).

    Empty history AND nothing ongoing collapses to a single header-styled
    line, exactly as before the redesign:
    - ``is_initializing=True``  → ``ALERT (initializing)``
    - ``is_initializing=False`` → ``ALERT (no alert detected)``
    """
    if incidents is None:
        incidents = _derive_incidents(history, ongoing, ongoing_since)
    if not incidents:
        # Only the state fragment is coloured; `ALERT` stays HEADER, exactly
        # like the `ALERTS` prefix of the populated title. Green is the
        # "all clear" signal — nothing has ever fired. Warmup is not an
        # all-clear (an alert simply cannot have fired yet), so it stays
        # neutral rather than claiming a healthy system.
        if is_initializing:
            state, state_role = "(initializing)", ColorRole.DEFAULT
        else:
            state, state_role = "(no alert detected)", ColorRole.OK
        # Glued, so the painted line is unchanged: `ALERT (no alert detected)`.
        return [
            Row(
                cells=[
                    Cell(text="ALERT ", color=ColorRole.HEADER),
                    Cell(text=state, color=state_role, glue=True),
                ]
            )
        ]

    now_local = (now or datetime.now(tz=timezone.utc)).astimezone()
    n_ongoing = sum(1 for i in incidents if i["ongoing"])
    n_resolved = len(incidents) - n_ongoing

    # Which columns fit. TARGET is the only elastic one and never drops.
    show_level = width is None or width >= _ALERT_W_WITH_LEVEL
    show_duration = width is None or width >= _ALERT_W_WITH_DURATION

    visible = incidents[:limit] if limit > 0 else []

    def target_of(incident: dict[str, Any]) -> str:
        return _humanise_target(incident["plugin"], incident["key"], incident["field"])

    if width is None:
        target_width = max((len(target_of(i)) for i in visible), default=_ALERT_MIN_TARGET)
        target_width = max(target_width, _ALERT_MIN_TARGET)
    elif show_level:
        target_width = width - (_ALERT_W_WITH_LEVEL - _ALERT_MIN_TARGET)
    elif show_duration:
        target_width = width - (_ALERT_W_WITH_DURATION - _ALERT_MIN_TARGET)
    else:
        target_width = width - _ALERT_MIN_TARGET
    target_width = max(0, target_width)

    # Title shortens in the same order as the columns (design §6.3): the
    # trailing rule goes first, then the `resolved` clause, and only the
    # `ongoing` count survives to a hard truncation.
    # The title is split into glued cells so only the ongoing-count fragment
    # carries state: green when nothing is active, default otherwise. `ALERTS`
    # and the rule stay HEADER, so the block still reads as a titled block.
    # This does NOT break the standing rule that a title is never escalated by
    # an alert level — `ok` and `default` are reassurance, not escalation; no
    # title cell may ever carry careful/warning/critical (design §6.5).
    # Glued cells mean the painter inserts no separator, so the rendered text
    # is identical to the single-cell version it replaces.
    separator = "·" if unicode_ok else "-"
    rule_char = "─" if unicode_ok else "-"
    count_role = ColorRole.OK if n_ongoing == 0 else ColorRole.DEFAULT
    prefix = "ALERTS  "
    count = f"{n_ongoing} ongoing"
    resolved = f" {separator} {n_resolved} resolved"
    base_len = len(prefix) + len(count)
    full_len = base_len + len(resolved)

    segments: list[tuple[str, ColorRole]] = [(prefix, ColorRole.HEADER), (count, count_role)]
    if width is None or width >= full_len:
        segments.append((resolved, ColorRole.HEADER))
        # The rule needs a separating space of its own before it fits.
        if width is not None and width > full_len + 1:
            segments.append((" " + rule_char * (width - full_len - 1), ColorRole.HEADER))
    elif width < base_len:
        # Last resort: cut across the segments, keeping the ongoing count as
        # long as anything survives.
        truncated: list[tuple[str, ColorRole]] = []
        remaining = width
        for text, role in segments:
            if remaining <= 0:
                break
            truncated.append((text[:remaining], role))
            remaining -= len(truncated[-1][0])
        segments = truncated

    title_cells = [
        Cell(text=text, color=role, glue=index > 0)
        for index, (text, role) in enumerate(seg for seg in segments if seg[0])
    ]
    rows: list[Row] = [Row(cells=title_cells or [Cell(text="", color=ColorRole.HEADER)])]

    if not visible:
        return rows

    header_cells = [Cell(text=" " * _ALERT_W_GLYPH, color=ColorRole.HEADER, bold=True)]
    header_cells.append(Cell(text=_fit_text("TIME", _ALERT_W_TIME + 1), color=ColorRole.HEADER, bold=True))
    if show_duration:
        header_cells.append(
            Cell(text=_fit_text("DURATION", _ALERT_W_DURATION, right=True) + " ", color=ColorRole.HEADER, bold=True)
        )
    header_cells.append(Cell(text=_fit_text("TARGET", target_width), color=ColorRole.HEADER, bold=True))
    if show_level:
        header_cells.append(
            Cell(text=_fit_text("LEVEL", _ALERT_W_LEVEL, right=True), color=ColorRole.HEADER, bold=True)
        )
    rows.append(Row(cells=header_cells))

    for incident in visible:
        is_ongoing = bool(incident["ongoing"])
        level = str(incident["level"])
        role = _LEVEL_TO_ROLE.get(level, ColorRole.DEFAULT)
        prominent = bool(incident["prominent"])
        begin = incident["begin"]
        ts_text = _format_alert_time(str(begin), now=now_local) if begin else _ALERT_TIME_UNKNOWN
        duration = _incident_duration(incident, now=now_local) or ""

        cells = [
            Cell(
                text=_ALERT_GLYPHS[is_ongoing][unicode_ok],
                color=role,
                # When LEVEL is dropped the glyph is the only cell left that
                # can carry `prominent` — never silently lose the flag.
                prominent=prominent and not show_level,
            ),
            Cell(text=_fit_text(ts_text, _ALERT_W_TIME + 1)),
        ]
        if show_duration:
            cells.append(Cell(text=_fit_text(duration, _ALERT_W_DURATION, right=True) + " "))
        cells.append(Cell(text=_fit_text(target_of(incident), target_width, ellipsis="…" if unicode_ok else ".")))
        if show_level:
            cells.append(
                Cell(
                    text=_fit_text(level.upper(), _ALERT_W_LEVEL, right=True),
                    # A resolved incident goes neutral here so colour in this
                    # column means "still happening". Its glyph keeps the level
                    # colour, so the severity it reached stays readable.
                    color=role if is_ongoing else ColorRole.DEFAULT,
                    prominent=prominent,
                )
            )
        rows.append(Row(cells=cells))

    return rows


# ------------------------------------------------- RIGHT column vertical budget
#
# The RIGHT column adapts to the terminal height the way the TOP row adapts to
# its width. `plan_right_column` is pure: it turns an available height into a
# per-plugin row budget, published as `view["row_budget"]` and consumed by the
# renderers. See docs/superpowers/specs/2026-08-05-tui-v5-right-column-vertical-fit-design.md

# Nominal budgets, in DATA rows (the block's own header row is not counted).
# These reproduce the historical behaviour: 20 processes, 10 alerts.
_NOMINAL_WORKLOADS = 10
_NOMINAL_ALERTS = 10
_NOMINAL_PROCESSES = 20
# Growth ceiling for the shared vms+containers budget on a tall terminal.
_MAX_WORKLOADS = 20


def row_budget(view: dict[str, Any] | None, plugin_name: str, default: int | None) -> int | None:
    """Max number of DATA rows `plugin_name` may emit this cycle.

    Every key counts DATA rows — the block's own header row is excluded — EXCEPT
    `amps`, which has no header row: its budget counts all its rows, truncation
    marker included.

    Reads `view["row_budget"]`, published by the TUI's vertical fit pass.
    Returns `default` when the view carries no budget (export, tests, direct
    renderer calls) so those paths keep their historical output.
    """
    budget = (view or {}).get("row_budget")
    if not isinstance(budget, dict):
        return default
    value = budget.get(plugin_name)
    return value if isinstance(value, int) else default


def with_truncation_counter(row: Row, shown: int, total: int) -> Row:
    """Return a copy of `row` whose first cell carries a `shown/total` counter.

    Used on a block's header row when the painter could not fit every item
    ("SENSORS" → "SENSORS 5/7"). The counter is padded back to the header
    cell's original width so the value columns to its right do not shift; a
    counter wider than that column is left to overflow rather than clipped
    (the ratio matters more than one row of alignment).

    Pure: the source row and its cells are never mutated.
    """
    if not row.cells:
        return row
    first = row.cells[0]
    label = f"{first.text.rstrip()} {shown}/{total}"
    return Row(
        cells=[replace(first, text=label.ljust(len(first.text))), *row.cells[1:]],
        item_start=row.item_start,
    )


def _split_workloads(quota: int, n_vms: int, n_containers: int) -> tuple[int, int]:
    """Split the shared workload budget between `vms` and `containers`.

    Max-min fairness: each block first gets an equal share, then whatever a
    block does not use is handed to the other one. A sparsely populated block
    is therefore never squeezed out by a crowded one (2 VMs + 30 containers
    shows both VMs). An odd leftover is offered to `vms` first, matching the
    RIGHT_SLOT order.
    """
    share = quota // 2
    vms = min(n_vms, share)
    containers = min(n_containers, share)
    leftover = quota - vms - containers
    if leftover > 0:
        take = min(leftover, n_vms - vms)
        vms += take
        leftover -= take
    if leftover > 0:
        containers += min(leftover, n_containers - containers)
    return (vms, containers)


# Shrink ladder, applied in order until the layout fits (design §4.4).
# `None` marks the special "truncate amps to whatever is left" step.
_SHRINK_STEPS: tuple[tuple[str, int | None], ...] = (
    ("workloads", 5),  # a
    ("alerts", 5),  # b
    ("processes", 10),  # c
    ("workloads", 3),  # d
    ("alerts", 3),  # e
    ("processes", 5),  # f
    ("workloads", 0),  # g — block hidden entirely
    ("alerts", 0),  # h — header only
    ("processes", 3),  # i
    ("amps", None),  # j — truncated to what remains, "+N lines" marker
    ("processes", 1),  # k — beyond this, curses clips
)

# Terminal steps, reached ONLY when an alert is still active and the ladder
# above could not free enough rows (see `plan_right_column`):
#   l — processes 0: the block vanishes, header included.
#   m — the alert floor itself gives way, one row at a time.
# Without an active alert they never fire, so a host with a quiet alert block
# keeps the exact historical cascade.


def plan_right_column(
    *,
    body_height: int,
    static_heights: dict[str, int],
    amps_height: int,
    n_vms: int,
    n_containers: int,
    n_processes: int,
    n_alerts: int,
    n_ongoing: int = 0,
) -> dict[str, int]:
    """Return the RIGHT column row budget for the available `body_height`.

    Pure and analytic — no frame rebuild is needed to evaluate a candidate
    layout, because every elastic block costs exactly one line per data row
    plus one header row — except `alerts`, which carries a second, fixed
    column-header row on top of its own header (see `_alert_block_height`).

    Args:
        body_height: rows available below the top row separator.
        static_heights: heights of the non-elastic RIGHT blocks that are
            present (currently only `processcount`, always 1 row).
        amps_height: natural height of the amps block, 0 when absent.
        n_vms / n_containers / n_processes: item counts available in the
            payloads (`PluginBlock.data_count`).
        n_alerts: incident count available (`PluginBlock.data_count` of the
            synthesized `alert` block — one per incident, not one per raw
            history event).
        n_ongoing: how many of those incidents are still ACTIVE
            (`PluginBlock.data_pinned`). An active alert must stay visible at
            the expense of everything else, so `min(n_ongoing,
            _NOMINAL_ALERTS)` is a floor the shrink ladder's alert steps
            (b, e, h) may not cross, and two terminal steps are unlocked to
            honour it (l, m — see `_SHRINK_STEPS`). Incidents are sorted
            ongoing-first by `_derive_incidents`, so a quota at or above this
            floor provably shows every active one. `0` (the default, and every
            host with a quiet alert block) leaves the cascade untouched.

    Returns:
        `{plugin: max data rows}`. `amps` is present only when the ladder had
        to truncate it (step j); its budget counts ALL its rows, marker
        included.

    On BOTH branches the process block ends up absorbing the slack: it is the
    elastic block that fills the terminal (design R4). On the shrink branch the
    ladder's process steps (c, f, i, k) are therefore temporary concessions —
    once the layout fits, the rows the ladder freed beyond the deficit are
    refunded to the processes. `workloads` and `alerts` keep the value the
    ladder left them at, so the ladder's meaning is preserved for those two.
    """
    state = {
        "workloads": _NOMINAL_WORKLOADS,
        "alerts": _NOMINAL_ALERTS,
        "processes": _NOMINAL_PROCESSES,
        "amps": amps_height,
    }
    # Rows the alert block may never give up while the cascade still has
    # anything else to take. Capped by the nominal, which is also the maximum
    # number of alert lines the block ever paints.
    floor_alerts = min(max(0, n_ongoing), _NOMINAL_ALERTS)

    def cost(candidate: dict[str, int]) -> int:
        """Rows occupied by `candidate` — mirrors `_paint_sidebar`: the sum of
        the visible block heights plus one blank line between blocks."""
        vms_q, containers_q = _split_workloads(candidate["workloads"], n_vms, n_containers)
        heights: list[int] = []
        if n_vms and vms_q:
            heights.append(1 + vms_q)
        if n_containers and containers_q:
            heights.append(1 + containers_q)
        heights.extend(h for h in static_heights.values() if h)
        if candidate["amps"]:
            heights.append(candidate["amps"])
        # A zero quota hides the block outright, header included (step l) —
        # mirroring `_paint_sidebar`, which skips a block with no rows.
        if n_processes and candidate["processes"]:
            heights.append(1 + min(n_processes, candidate["processes"]))
        # The alert block is always emitted, if only as a header line. Its
        # height is title + column-header + data rows, not title + data rows
        # (`_alert_block_height` mirrors `render_alert_block`'s own collapse
        # rules exactly — see design §5, §10).
        heights.append(_alert_block_height(n_alerts, candidate["alerts"]))
        return sum(heights) + max(0, len(heights) - 1)

    def grow_processes() -> None:
        """Hand every remaining free row to the process block, one at a time,
        so the result provably fills the terminal without overflowing it. A
        no-op when the layout already overflows (exhausted ladder)."""
        while state["processes"] < n_processes and cost({**state, "processes": state["processes"] + 1}) <= body_height:
            state["processes"] += 1

    if cost(state) <= body_height:
        # Growth: workloads first (step A), then processes absorb the rest
        # (step B). One row at a time so the result provably fills the
        # terminal without overflowing it.
        while (
            state["workloads"] < _MAX_WORKLOADS and cost({**state, "workloads": state["workloads"] + 1}) <= body_height
        ):
            state["workloads"] += 1
        grow_processes()
    else:
        for key, value in _SHRINK_STEPS:
            if key == "amps":
                if not state["amps"]:
                    continue
                # Truncate to what remains, keeping at least the marker line.
                deficit = cost(state) - body_height
                state["amps"] = max(1, state["amps"] - deficit)
            else:
                if key == "alerts":
                    value = max(value, floor_alerts)
                if value >= state[key]:
                    continue
                state[key] = value
            if cost(state) <= body_height:
                break
        if floor_alerts and cost(state) > body_height:
            # The floor made steps b/e/h no-ops and what is left did not
            # cover the deficit. Step l: drop the process block entirely.
            state["processes"] = 0
            # Step m: nothing else remains to take, so the floor itself gives
            # way — one row at a time, so the block keeps as many active
            # alerts as the terminal can physically hold.
            while state["alerts"] > 0 and cost(state) > body_height:
                state["alerts"] -= 1
        # The step that made the layout fit usually freed more than the
        # deficit; refund that slack to the processes rather than leaving
        # blank rows at the bottom of the column.
        grow_processes()

    vms_q, containers_q = _split_workloads(state["workloads"], n_vms, n_containers)
    budget = {
        "vms": vms_q,
        "containers": containers_q,
        "processlist": state["processes"],
        "programlist": state["processes"],
        "alert": state["alerts"],
    }
    if state["amps"] != amps_height:
        budget["amps"] = state["amps"]
    return budget


# --------------------------------------------------------------- frame


# --------------------------------------------------------------- per-plugin renderer discovery


# Cache: plugin_name → render function or None (sentinel for "no custom renderer").
# Avoids retrying failed imports on every cycle.
_PLUGIN_RENDERERS: dict[str, Callable[..., list[Row]] | None] = {}
# Parallel cache: does the discovered renderer accept a ``view`` argument?
# Renderers predating the hotkey work keep the 2-arg ``(payload, fields_desc)``
# signature and must still be called with exactly two args.
_RENDERER_ACCEPTS_VIEW: dict[str, bool] = {}


def _accepts_view(fn: Callable[..., Any]) -> bool:
    """True if ``fn`` can receive the optional ``view`` keyword.

    Either it declares a ``view`` parameter explicitly or it captures
    ``**kwargs``. Inspection failures default to False (call with two args)."""
    try:
        params = inspect.signature(fn).parameters
    except (ValueError, TypeError):  # pragma: no cover — builtins / C funcs
        return False
    if "view" in params:
        return True
    return any(p.kind == p.VAR_KEYWORD for p in params.values())


def _discover_plugin_renderer(
    plugin_name: str,
) -> Callable[..., list[Row]] | None:
    """Look up `glances.plugins.<name>.render_curses_v5.render`.

    The convention: a plugin opts in to a custom TUI layout (v4-style)
    by providing a `render_curses_v5.py` module next to `model_v5.py`.
    The module exports `render(payload, fields_desc[, view]) -> list[Row]`.

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
    _RENDERER_ACCEPTS_VIEW[plugin_name] = _accepts_view(fn)
    return fn


def _reset_plugin_renderer_cache() -> None:
    """Test-only helper to clear the discovery cache."""
    _PLUGIN_RENDERERS.clear()
    _RENDERER_ACCEPTS_VIEW.clear()


def build_frame(
    store_snapshot: dict[str, dict[str, Any]],
    fields_by_plugin: dict[str, dict[str, dict[str, Any]]],
    registry: list[tuple[str, bool]],
    alerts_history: list[dict[str, Any]],
    alerts_limit: int = 10,
    alerts_initializing: bool = False,
    alerts_ongoing: dict[tuple[str, Any, str], str] | None = None,
    alerts_ongoing_since: dict[tuple[str, Any, str], str] | None = None,
    view: dict[str, Any] | None = None,
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
        alerts_limit: DATA-row budget for the alert block (the title and
            column-header rows are extra) — the block is incident-based, not
            event-based.
        alerts_ongoing: output of `GlancesAlerts.get_ongoing()` — the
            authority on which alerts are still active (design §5.6).
        alerts_ongoing_since: output of `GlancesAlerts.get_ongoing_since()` —
            the authority on when each of them opened, for the incidents the
            bounded history can no longer date.

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
        if view and view.get("full_quicklook") and plugin_name in _FULL_QUICKLOOK_HIDDEN:
            continue
        if view and view.get("hide_quicklook") and plugin_name == "quicklook":
            continue
        if view and view.get("hide_memswap") and plugin_name == "memswap":
            continue
        if view and view.get("hide_gpu") and plugin_name == "gpu":
            continue
        # Header line progressive degradation (system … ip … uptime … cloud …
        # now): when the terminal is too narrow, cloud (opt-in, so sacrificed
        # first) is dropped, then two content shrinks handled by the plugins'
        # own renderers (`hide_ip_location`, then `hide_os_info`), then the
        # now, ip and uptime blocks.
        if view and view.get("hide_cloud") and plugin_name == "cloud":
            continue
        if view and view.get("hide_now") and plugin_name == "now":
            continue
        if view and view.get("hide_ip") and plugin_name == "ip":
            continue
        if view and view.get("hide_uptime") and plugin_name == "uptime":
            continue
        payload = store_snapshot.get(plugin_name) or {}
        # v4 parity: a collection (list) plugin with an empty list renders
        # nothing at all — not even its header. v4 `msg_curse` starts with
        # `if not self.stats or self.is_disabled(): return []`, so an absent /
        # empty / disabled list plugin contributes no block (no lonely header).
        # Scalar plugins are unaffected (their own renderer decides emptiness).
        if is_collection and not payload.get("data"):
            continue
        fields_desc = fields_by_plugin.get(plugin_name, {})

        custom = _discover_plugin_renderer(plugin_name)
        if custom is not None:
            try:
                if _RENDERER_ACCEPTS_VIEW.get(plugin_name):
                    rows = custom(payload, fields_desc, view=view)
                else:
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

        # Skip empty blocks: any block with zero rows has nothing to paint and
        # must not reserve layout space (gap accounting in _paint_header et al).
        # This covers scalar plugins like `cloud` that may render nothing despite
        # a non-empty payload (e.g. cloud on a non-cloud host → {}). Catches top
        # and sidebar slots too, future-proofing against other plugins.
        if not rows:
            continue

        raw_data = payload.get("data") if isinstance(payload, dict) else None
        block = PluginBlock(
            name=plugin_name,
            rows=rows,
            data_count=len(raw_data) if isinstance(raw_data, list) else None,
        )
        slot = slot_for(plugin_name)
        if slot == "header":
            frame.header.append(block)
        elif slot == "top":
            frame.top.append(block)
        elif slot == "right":
            frame.right.append(block)
        else:
            frame.left.append(block)

    # Synthesize the alerts block in the RIGHT slot (mirrors v4's `alert`
    # plugin in `_right_sidebar`). Appended BEFORE the sort so `RIGHT_SLOT`
    # is the single source of placement (design §10.3) — `"alert"` is last
    # in the tuple, so it still renders at the bottom of the column.
    #
    # Incidents are derived exactly ONCE per frame here and handed to
    # `render_alert_block`, so `data_count` — consumed by `plan_right_column`
    # as `n_alerts` — counts the very same list the block renders, never a
    # second, independently derived list that could drift from it.
    alert_incidents = _derive_incidents(alerts_history, alerts_ongoing, alerts_ongoing_since)
    frame.right.append(
        PluginBlock(
            name="alert",
            rows=render_alert_block(
                alerts_history,
                limit=row_budget(view, "alert", alerts_limit),
                is_initializing=alerts_initializing,
                ongoing=alerts_ongoing,
                width=(view or {}).get("right_width"),
                unicode_ok=bool((view or {}).get("unicode", True)),
                incidents=alert_incidents,
            ),
            data_count=len(alert_incidents),
            data_pinned=sum(1 for i in alert_incidents if i["ongoing"]),
        )
    )

    # v4 fidelity: enforce the slot-declared order, not the discovery
    # order (which is alphabetical and would give cpu/load/mem instead
    # of cpu/mem/load in the top row).
    frame.header.sort(key=lambda b: HEADER_SLOT.index(b.name) if b.name in HEADER_SLOT else len(HEADER_SLOT))
    frame.top.sort(key=lambda b: TOP_SLOT.index(b.name) if b.name in TOP_SLOT else len(TOP_SLOT))
    frame.left.sort(key=lambda b: LEFT_SLOT.index(b.name) if b.name in LEFT_SLOT else len(LEFT_SLOT))
    frame.right.sort(key=lambda b: RIGHT_SLOT.index(b.name) if b.name in RIGHT_SLOT else len(RIGHT_SLOT))
    return frame

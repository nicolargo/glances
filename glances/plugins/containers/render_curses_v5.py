#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — TUI curses renderer for the containers plugin.

Mirror of v4 ``containers.msg_curse``. Header row + one row per container,
MAIN-column full width. Columns are gated by ``[containers] disable_stats``
(surfaced via payload metadata), by the data (Engine only with >1 engine,
Pod only when a pod is present), and by the painted width (see
``_hidden_columns``).
"""

from __future__ import annotations

from typing import Any

from glances.globals import auto_unit
from glances.outputs.curses_renderer_v5 import _LEVEL_TO_ROLE, Cell, ColorRole, Row, row_budget

# Header → the GLOBAL process sort key (view["sort_key"], dynamic/auto-resolved),
# processlist-aligned. MEM maps to memory_percent because the process sort-key
# space uses memory_percent (the model's data sort maps that onto the
# memory_usage column — same column underlined as is actually sorted).
_HEADER_SORT_KEY: dict[str, str] = {"CONTAINER": "name", "CPU%": "cpu_percent", "MEM": "memory_percent"}

# v4 container_alert(status) → ColorRole. No ERROR/INFO roles in v5 →
# dead/unhealthy fold to CRITICAL, everything unclassified to DEFAULT.
_STATUS_ROLE: dict[str, ColorRole] = {
    "running": ColorRole.OK,
    "healthy": ColorRole.OK,
    "dead": ColorRole.CRITICAL,
    "unhealthy": ColorRole.CRITICAL,
    "created": ColorRole.WARNING,
    "exited": ColorRole.WARNING,
    "paused": ColorRole.CAREFUL,
    "restarting": ColorRole.CAREFUL,
}


# Responsive columns (see ``view["right_width"]``). Same mechanism as the
# processlist renderer: when the painted width cannot hold the natural row,
# the lowest-priority columns are dropped one at a time, in ``_DROP_ORDER``,
# until the row fits — or the order is exhausted and the painter clips, as it
# already did before. Never dropped: CONTAINER, CPU%, MEM.
#
# ``command`` is the FIRST victim, unlike processlist where it is the
# protected flexible tail: in containers the identity is the NAME, and the
# container command is the least informative column of the row.
#
# ``engine``, ``pod`` and ``memory_max`` are display-only keys extending the
# ``[containers] disable_stats`` vocabulary (name/status/uptime/cpu/mem/
# diskio/networkio/ports/command) without colliding with it, so a single
# ``hidden`` set gates every column.
_MIN_COMMAND_WIDTH = 8
_DROP_ORDER = ["command", "ports", "memory_max", "pod", "engine", "diskio", "networkio", "uptime", "status"]

# key -> (painted cells, total width of those cells). The cell count matters
# because the painter inserts one space between two consecutive cells; the
# IO and network pairs are single keys so a half-pair can never be shown.
_COL_GEOMETRY: dict[str, tuple[int, int]] = {
    "engine": (1, 6),
    "pod": (1, 12),
    "status": (1, 10),
    "uptime": (1, 10),
    "cpu": (1, 6),
    "mem": (1, 7),
    "memory_max": (1, 8),
    "diskio": (2, 14),
    "networkio": (2, 14),
    "ports": (1, 16),
    "command": (1, _MIN_COMMAND_WIDTH),
}


def _hidden_columns(available: int, hidden: set[str], name_w: int) -> set[str]:
    """Return the columns to hide so the row fits within ``available``.

    Starts from ``hidden`` — the config ``disable_stats`` plus the columns the
    data makes irrelevant — and adds ``_DROP_ORDER`` entries until the natural
    row width fits. ``name`` / ``cpu`` / ``mem`` are absent from the order and
    therefore always survive. ``command`` is counted at ``_MIN_COMMAND_WIDTH``
    since its data cell is unbounded.
    """
    dropped = set(hidden)

    def row_width() -> int:
        cells = 0 if "name" in dropped else 1
        width = 0 if "name" in dropped else name_w
        for key, (n_cells, w) in _COL_GEOMETRY.items():
            if key not in dropped:
                cells += n_cells
                width += w
        return width + max(0, cells - 1)

    for key in _DROP_ORDER:
        if row_width() <= available:
            break
        dropped.add(key)
    return dropped


def _status_role(status: str) -> ColorRole:
    return _STATUS_ROLE.get(status, ColorRole.DEFAULT)


def _level_role(level_entry: Any) -> tuple[ColorRole, bool]:
    if isinstance(level_entry, dict):
        return (_LEVEL_TO_ROLE.get(level_entry.get("level"), ColorRole.DEFAULT), bool(level_entry.get("prominent")))
    return (ColorRole.DEFAULT, False)


def _header_cell(
    label: str, width: int, *, ljust: bool = False, color: ColorRole = ColorRole.HEADER, sort_key: str | None = None
) -> Cell:
    text = f"{label:<{width}}" if ljust else f"{label:>{width}}"
    return Cell(text=text, color=color, bold=True, underline=bool(sort_key) and _HEADER_SORT_KEY.get(label) == sort_key)


def _build_header_row(
    disable: set[str],
    *,
    show_engine: bool,
    show_pod: bool,
    show_mem_max: bool,
    name_w: int,
    sort_key: str | None,
    name_label: str = "CONTAINER",
) -> Row:
    def hdr(label: str, width: int, *, ljust: bool = False, color: ColorRole = ColorRole.HEADER) -> Cell:
        return _header_cell(label, width, ljust=ljust, color=color, sort_key=sort_key)

    h: list[Cell] = []
    if show_engine:
        h.append(hdr("Engine", 6, ljust=True))
    if show_pod:
        h.append(hdr("Pod", 12, ljust=True))
    if "name" not in disable:
        # The sort underline is resolved on the CANONICAL label: `name_label` may
        # carry a truncation counter ("CONTAINER 7/25"), which is not a table key.
        name_underline = bool(sort_key) and _HEADER_SORT_KEY.get("CONTAINER") == sort_key
        h.append(Cell(text=f"{name_label:<{name_w}}", color=ColorRole.HEADER, bold=True, underline=name_underline))
    if "status" not in disable:
        h.append(hdr("Status", 10))
    if "uptime" not in disable:
        h.append(hdr("Uptime", 10))
    if "cpu" not in disable:
        h.append(hdr("CPU%", 6))
    if "mem" not in disable:
        h.append(hdr("MEM", 7))
        if show_mem_max:
            h.append(Cell(text=f"/{'MAX':<7}", color=ColorRole.HEADER, bold=True))
    if "diskio" not in disable:
        h.append(hdr("IOR/s", 7))
        h.append(hdr("IOW/s", 7, ljust=True))
    if "networkio" not in disable:
        h.append(hdr("Rx/s", 7))
        h.append(hdr("Tx/s", 7, ljust=True))
    if "ports" not in disable:
        h.append(hdr("Ports", 16, ljust=True))
    if "command" not in disable:
        h.append(hdr("Command", 8, ljust=True))
    return Row(cells=h)


def _name_status_uptime_cells(c: dict[str, Any], disable: set[str], name_w: int) -> list[Cell]:
    cells: list[Cell] = []
    if "name" not in disable:
        cells.append(Cell(text=f"{str(c.get('name', ''))[:name_w]:<{name_w}}"))
    if "status" not in disable:
        status = str(c.get("status", ""))
        cells.append(Cell(text=f"{status[:10]:>10}", color=_status_role(status)))
    if "uptime" not in disable:
        cells.append(Cell(text=f"{(c.get('uptime') or '_'):>10}"))
    return cells


def _cpu_mem_cells(c: dict[str, Any], disable: set[str], item_levels: dict[str, Any], show_mem_max: bool) -> list[Cell]:
    cells: list[Cell] = []
    if "cpu" not in disable:
        cpu = c.get("cpu_percent")
        role, prom = _level_role(item_levels.get("cpu_percent"))
        text = f"{cpu:>6.1f}" if isinstance(cpu, (int, float)) else f"{'_':>6}"
        cells.append(Cell(text=text, color=role, prominent=prom))
    if "mem" not in disable:
        # Display the no-cache value (v4 MEM column); /MAX = limit. Colour
        # from the memory_percent level. memory_usage (export) is NOT shown.
        usage, limit = c.get("memory_usage_no_cache"), c.get("memory_limit")
        role, prom = _level_role(item_levels.get("memory_percent"))
        mtext = f"{auto_unit(usage):>7}" if isinstance(usage, (int, float)) else f"{'_':>7}"
        cells.append(Cell(text=mtext, color=role, prominent=prom))
        if show_mem_max:
            ltext = f"/{auto_unit(limit):<7}" if isinstance(limit, (int, float)) else f"/{'_':<7}"
            cells.append(Cell(text=ltext))
    return cells


def _io_net_ports_command_cells(c: dict[str, Any], disable: set[str], to_bit: int, net_unit: str) -> list[Cell]:
    cells: list[Cell] = []
    if "diskio" not in disable:
        cells.append(Cell(text=_io_cell(c.get("io_rx"), 7, ljust=False)))
        cells.append(Cell(text=_io_cell(c.get("io_wx"), 7, ljust=True)))
    if "networkio" not in disable:
        cells.append(Cell(text=_net_cell(c.get("network_rx"), to_bit, net_unit, 7, ljust=False)))
        cells.append(Cell(text=_net_cell(c.get("network_tx"), to_bit, net_unit, 7, ljust=True)))
    if "ports" not in disable:
        ports = c.get("ports") or ""
        cells.append(Cell(text=f"{(ports if ports != '' else '_'):16}"))
    if "command" not in disable:
        cells.append(Cell(text=f" {c.get('command') or '_'}"))
    return cells


def _build_data_row(
    c: dict[str, Any],
    disable: set[str],
    levels: dict[str, Any],
    *,
    show_engine: bool,
    show_pod: bool,
    show_mem_max: bool,
    name_w: int,
    to_bit: int,
    net_unit: str,
) -> Row:
    item_levels = levels.get(c.get("name"), {}) if isinstance(levels, dict) else {}
    cells: list[Cell] = []
    if show_engine:
        cells.append(Cell(text=f"{str(c.get('engine', '')):<6}"))
    if show_pod:
        cells.append(Cell(text=f"{str(c.get('pod_id') or '-'):<12}"))
    cells.extend(_name_status_uptime_cells(c, disable, name_w))
    cells.extend(_cpu_mem_cells(c, disable, item_levels, show_mem_max))
    cells.extend(_io_net_ports_command_cells(c, disable, to_bit, net_unit))
    return Row(cells=cells)


def render(
    payload: dict[str, Any],
    fields_desc: dict[str, dict[str, Any]] | None = None,
    view: dict[str, Any] | None = None,
) -> list[Row]:
    items: list[dict[str, Any]] = []
    if isinstance(payload, dict):
        raw = payload.get("data")
        if isinstance(raw, list):
            items = [i for i in raw if isinstance(i, dict)]
    if not items:
        return []

    view = view or {}
    sort_key = view.get("sort_key")
    to_bit, net_unit = (1, "") if view.get("byte") else (8, "b")

    disable = set(payload.get("disable_stats") or [])
    levels = payload.get("_levels") if isinstance(payload.get("_levels"), dict) else {}
    conf_max = payload.get("max_name_size") or 20
    name_w = min(int(conf_max), max((len(str(i.get("name", ""))) for i in items), default=1))

    show_engine = len({i.get("engine") for i in items}) > 1
    show_pod = any(i.get("pod_name") for i in items)

    total = len(items)
    budget = row_budget(view, "containers", None)
    if isinstance(budget, int):
        if budget <= 0:
            # Step g of the vertical cascade: the block is dropped entirely.
            return []
        items = items[:budget]
    truncated = len(items) < total
    # The counter replaces the bare label when the list is cut. `name_w` stays
    # computed on the FULL list so the column does not jump width from one
    # cycle to the next, and is only widened when the counter needs it.
    name_label = f"CONTAINER {len(items)}/{total}" if truncated else "CONTAINER"
    name_w = max(name_w, len(name_label))

    # Responsive columns. Computed AFTER the truncation counter, since the
    # counter is what fixes the final `name_w` the fit has to budget against.
    # Absent / non-int `right_width` (export, REST, direct callers, tests) →
    # nothing is dropped and the output is byte-identical to the historical
    # one, pinned by `test_no_right_width_keeps_all_columns`.
    hidden = set(disable)
    if "mem" in hidden:
        hidden.add("memory_max")
    if not show_engine:
        hidden.add("engine")
    if not show_pod:
        hidden.add("pod")
    available = view.get("right_width")
    if isinstance(available, int):
        hidden = _hidden_columns(available, hidden, name_w)
    show_engine = "engine" not in hidden
    show_pod = "pod" not in hidden
    show_mem_max = "memory_max" not in hidden

    header = _build_header_row(
        hidden,
        show_engine=show_engine,
        show_pod=show_pod,
        show_mem_max=show_mem_max,
        name_w=name_w,
        sort_key=sort_key,
        name_label=name_label,
    )
    rows: list[Row] = [header]
    rows.extend(
        _build_data_row(
            c,
            hidden,
            levels,
            show_engine=show_engine,
            show_pod=show_pod,
            show_mem_max=show_mem_max,
            name_w=name_w,
            to_bit=to_bit,
            net_unit=net_unit,
        )
        for c in items
    )
    return rows


def _io_cell(value: Any, width: int, *, ljust: bool) -> str:
    try:
        text = auto_unit(int(value)) + "B"
    except (TypeError, ValueError):
        text = "_"
    return f"{text:<{width}}" if ljust else f"{text:>{width}}"


def _net_cell(value: Any, to_bit: int, unit: str, width: int, *, ljust: bool) -> str:
    try:
        text = auto_unit(int(value * to_bit)) + unit
    except (TypeError, ValueError):
        text = "_"
    return f"{text:<{width}}" if ljust else f"{text:>{width}}"

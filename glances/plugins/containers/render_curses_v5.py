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
(surfaced via payload metadata) and by the data (Engine only with >1 engine,
Pod only when a pod is present).
"""

from __future__ import annotations

from typing import Any

from glances.globals import auto_unit
from glances.outputs.curses_renderer_v5 import _LEVEL_TO_ROLE, Cell, ColorRole, Row

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
    disable: set[str], *, show_engine: bool, show_pod: bool, name_w: int, sort_key: str | None
) -> Row:
    def hdr(label: str, width: int, *, ljust: bool = False, color: ColorRole = ColorRole.HEADER) -> Cell:
        return _header_cell(label, width, ljust=ljust, color=color, sort_key=sort_key)

    h: list[Cell] = []
    if show_engine:
        h.append(hdr("Engine", 6, ljust=True))
    if show_pod:
        h.append(hdr("Pod", 12, ljust=True))
    if "name" not in disable:
        h.append(hdr("CONTAINER", name_w, ljust=True))
    if "status" not in disable:
        h.append(hdr("Status", 10))
    if "uptime" not in disable:
        h.append(hdr("Uptime", 10))
    if "cpu" not in disable:
        h.append(hdr("CPU%", 6))
    if "mem" not in disable:
        h.append(hdr("MEM", 7))
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


def _cpu_mem_cells(c: dict[str, Any], disable: set[str], item_levels: dict[str, Any]) -> list[Cell]:
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
    cells.extend(_cpu_mem_cells(c, disable, item_levels))
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
    header = _build_header_row(disable, show_engine=show_engine, show_pod=show_pod, name_w=name_w, sort_key=sort_key)
    rows: list[Row] = [header]
    rows.extend(
        _build_data_row(
            c,
            disable,
            levels,
            show_engine=show_engine,
            show_pod=show_pod,
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

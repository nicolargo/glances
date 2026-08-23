#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — TUI curses renderer for the vms plugin.

Mirror of v4 ``vms.msg_curse`` (``glances/plugins/vms/__init__.py``,
``msg_curse``/``vm_alert``/``sort_vm_stats``). Title row + column-header
row + one row per VM, MAIN (RIGHT) column, full width. No alerts
(``EMITS_ALERTS = False`` — the payload carries no ``_levels``).

Columns: Engine (only with >1 distinct engine), Name (``max_name_size``),
Status, Core, CPU% (``cpu_time`` — the per-second rate the base already
computed; ``None`` on the first cycle → placeholder), MEM/MAX (glued into
one cell — v4 underlines only the ``MEM`` sub-cell, here MEM and MAX share
a single ``Cell`` so the underline spans both; cosmetic, intentional
simplification), LOAD 1/5/15min (only when ``load_1min`` is not None on
the first VM — v4 parity), Release.

Sort-column underline follows ``view["sort_key"]`` — the GLOBAL process
sort key (processlist-aligned, dynamic/auto-resolved), NOT a key read
from the payload (the collection payload carries no ``sort_key``).
"""

from __future__ import annotations

from typing import Any

from glances.globals import auto_unit
from glances.outputs.curses_renderer_v5 import Cell, ColorRole, Row, row_budget

_DEFAULT_MAX_NAME_SIZE = 20
_STATUS_WIDTH = 10
_CORE_WIDTH = 6
_CPU_WIDTH = 6
_MEM_WIDTH = 7
_LOAD_HEADER_WIDTH = 17
_ENGINE_MIN_WIDTH = 8

# Header label -> the GLOBAL process sort key (view["sort_key"]),
# processlist-aligned. Mirrors how sort_vm_stats maps
# glances_processes.sort_key onto a vms field: name -> Name, memory_percent
# -> MEM/MAX, everything else -> CPU%. Core and LOAD have no process-sort
# equivalent and are never underlined.
_HEADER_SORT_FIELD: dict[str, str] = {"Name": "name", "CPU%": "cpu_percent", "MEM/MAX": "memory_percent"}

# v4 vm_alert(status) -> ColorRole. No INFO role in v5 -> DEFAULT (neutral).
_STATUS_ROLE: dict[str, ColorRole] = {
    "running": ColorRole.OK,
    "starting": ColorRole.WARNING,
    "restarting": ColorRole.WARNING,
    "delayed shutdown": ColorRole.WARNING,
}


def _status_role(status: Any) -> ColorRole:
    return _STATUS_ROLE.get(str(status or "").lower(), ColorRole.DEFAULT)


def _fmt(value: Any) -> str:
    return str(value) if value is not None else "-"


def _header(label: str, width: int, *, ljust: bool = False, sort_key: str | None = None) -> Cell:
    text = label.ljust(width) if ljust else label.rjust(width)
    underline = bool(sort_key) and _HEADER_SORT_FIELD.get(label) == sort_key
    return Cell(text=text, color=ColorRole.HEADER, bold=True, underline=underline)


def _build_header_row(
    *,
    show_engine: bool,
    engine_w: int,
    name_w: int,
    show_load: bool,
    sort_key: str | None,
    name_label: str = "Name",
) -> Row:
    cells: list[Cell] = []
    if show_engine:
        cells.append(_header("Engine", engine_w, ljust=True, sort_key=sort_key))
    # The sort underline is resolved on the CANONICAL label: `name_label` may
    # carry a truncation counter ("Name 3/12"), which is not a table key.
    name_underline = bool(sort_key) and _HEADER_SORT_FIELD.get("Name") == sort_key
    cells.append(Cell(text=name_label.ljust(name_w), color=ColorRole.HEADER, bold=True, underline=name_underline))
    cells.append(_header("Status", _STATUS_WIDTH, sort_key=sort_key))
    cells.append(_header("Core", _CORE_WIDTH, sort_key=sort_key))
    cells.append(_header("CPU%", _CPU_WIDTH, sort_key=sort_key))
    mem_text = f"{'MEM':>{_MEM_WIDTH}}/{'MAX':<{_MEM_WIDTH}}"
    mem_underline = bool(sort_key) and _HEADER_SORT_FIELD.get("MEM/MAX") == sort_key
    cells.append(Cell(text=mem_text, color=ColorRole.HEADER, bold=True, underline=mem_underline))
    if show_load:
        cells.append(_header("LOAD 1/5/15min", _LOAD_HEADER_WIDTH, sort_key=sort_key))
    cells.append(_header("Release", len("Release")))
    return Row(cells=cells)


def _build_data_row(vm: dict[str, Any], *, show_engine: bool, engine_w: int, name_w: int, show_load: bool) -> Row:
    cells: list[Cell] = []
    if show_engine:
        cells.append(Cell(text=str(vm.get("engine", "")).ljust(engine_w)))
    cells.append(Cell(text=str(vm.get("name", ""))[:name_w].ljust(name_w)))
    status = vm.get("status")
    cells.append(Cell(text=str(status or "")[:_STATUS_WIDTH].rjust(_STATUS_WIDTH), color=_status_role(status)))
    cells.append(Cell(text=_fmt(vm.get("cpu_count")).rjust(_CORE_WIDTH)))
    cells.append(Cell(text=_fmt(vm.get("cpu_time")).rjust(_CPU_WIDTH)))
    mem_text = f"{auto_unit(vm.get('memory_usage')):>{_MEM_WIDTH}}/{auto_unit(vm.get('memory_total')):<{_MEM_WIDTH}}"
    cells.append(Cell(text=mem_text))
    if show_load:
        try:
            cells.append(Cell(text=f"{vm['load_1min']:>5.1f}/{vm['load_5min']:>5.1f}/{vm['load_15min']:>5.1f}"))
        except (KeyError, TypeError):
            pass
    cells.append(Cell(text=str(vm["release"]) if vm.get("release") is not None else "-"))
    return Row(cells=cells)


def render(
    payload: dict[str, Any],
    fields_desc: dict[str, dict[str, Any]] | None = None,
    view: dict[str, Any] | None = None,
) -> list[Row]:
    """Render the vms plugin's column-header + per-VM rows (no title row, for
    consistency with the containers plugin)."""
    items: list[dict[str, Any]] = []
    if isinstance(payload, dict):
        raw = payload.get("data")
        if isinstance(raw, list):
            items = [i for i in raw if isinstance(i, dict)]
    if not items:
        return []

    sort_key = (view or {}).get("sort_key")
    max_name_size = payload.get("max_name_size", _DEFAULT_MAX_NAME_SIZE)

    show_engine = len({str(i.get("engine", "")) for i in items}) > 1
    name_w = min(int(max_name_size), max((len(str(i.get("name", ""))) for i in items), default=max_name_size))
    engine_w = 0
    if show_engine:
        engine_w = max(_ENGINE_MIN_WIDTH, max((len(str(i.get("engine", ""))) for i in items), default=0))
    show_load = items[0].get("load_1min") is not None

    total = len(items)
    budget = row_budget(view, "vms", None)
    if isinstance(budget, int):
        if budget <= 0:
            return []
        items = items[:budget]
    truncated = len(items) < total
    name_label = f"Name {len(items)}/{total}" if truncated else "Name"
    name_w = max(name_w, len(name_label))

    header_row = _build_header_row(
        show_engine=show_engine,
        engine_w=engine_w,
        name_w=name_w,
        show_load=show_load,
        sort_key=sort_key,
        name_label=name_label,
    )
    data_rows = [
        _build_data_row(vm, show_engine=show_engine, engine_w=engine_w, name_w=name_w, show_load=show_load)
        for vm in items
    ]
    return [header_row, *data_rows]

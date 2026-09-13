#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — TUI curses renderer for the percpu plugin.

Replicates v4's ``percpu.msg_curse()`` transposed grid: fields are
columns, CPU cores are rows.

Reference layout (Linux, quicklook disabled, 4 cores):

    CPU     total   user system iowait   idle    irq   nice  steal  guest
    CPU0    21.7%  12.5%   3.2%   0.5%  83.8%   0.0%   0.0%   0.0%   0.0%
    CPU1    11.9%   8.1%   2.0%   0.1%  89.8%   0.0%   0.0%   0.0%   0.0%
    CPU2    21.5%  15.0%   4.5%   1.2%  79.3%   0.0%   0.0%   0.0%   0.0%
    CPU3     8.1%   6.3%   1.8%   0.0%  91.9%   0.0%   0.0%   0.0%   0.0%

When more than ``_DEFAULT_MAX_CPU_DISPLAY`` cores exist, the top-N by
``total`` are shown plus a synthetic ``CPU*`` row carrying the mean of
the stats of the cores that did NOT fit on screen (v4
``summarize_all_cpus_not_displayed``).

When quicklook is on screen (``view["quicklook_enabled"]``), it already
shows the per-core totals, so this block drops its ``CPU`` title, its
``total`` column and its row labels (v4 parity,
``glances/plugins/percpu/__init__.py:158,183,210``).

V5 percpu carries no field-level alerts (see ``percpu/model_v5.py``
docstring), so every value cell is DEFAULT-coloured — no
warning/critical decoration here. The system-wide ``cpu`` plugin
remains the source of CPU alerts.
"""

from __future__ import annotations

import sys
from typing import Any

from glances.outputs.curses_renderer_v5 import Cell, ColorRole, Row

# v4 fidelity: top-N cores shown, the rest collapsed into a CPU* row.
_DEFAULT_MAX_CPU_DISPLAY = 4

# First column (CPU label) — 4 chars; the painter adds a 1-char gap,
# so the on-screen label area is 5 chars wide (v4 parity: ``CPU0 ``).
_LABEL_WIDTH = 4

# Each stat column — ``{:6.1f}%`` produces 7 chars.
_VALUE_WIDTH = 7


def _os_headers() -> list[str]:
    """Return the OS-specific stat columns (v4 ``define_headers_from_os``).

    Fallback only — used when the payload predates ``stat_fields`` (an older
    server): the model is now the authority (final review, Important 3), so
    that the WebUI, which cannot resolve ``sys.platform`` itself, renders the
    exact same subset in the exact same order.
    """
    base = ["user", "system"]
    p = sys.platform
    if p.startswith("linux"):
        return base + ["iowait", "idle", "irq", "nice", "steal", "guest"]
    if p == "darwin":
        return base + ["idle", "nice"]
    if "bsd" in p:
        return base + ["idle", "irq", "nice"]
    if p in ("win32", "cygwin"):
        return base + ["dpc", "interrupt"]
    # Unknown OS — fall back to the Linux column set.
    return base + ["iowait", "idle", "irq", "nice", "steal", "guest"]


def _resolve_stat_fields(payload: dict[str, Any]) -> list[str]:
    """Column order for this cycle: the model's published ``stat_fields``
    when present (the contract `max_cpu_display` already uses), else the
    ``_os_headers()`` fallback for a payload from an older server."""
    fields = payload.get("stat_fields")
    if isinstance(fields, list) and fields and all(isinstance(f, str) for f in fields):
        return list(fields)
    return _os_headers()


def _cpu_label(cpu_id: Any) -> str:
    """Format a CPU id as a 4-char label.

    ``CPU0`` … ``CPU9`` for single-digit ids (v4 ``f'CPU{id:1} '``
    minus the trailing space — painter adds the gap), ``{id:>4}`` for
    two-digit-plus ids (v4 ``f'{id:4} '`` likewise).
    """
    try:
        n = int(cpu_id)
    except (TypeError, ValueError):
        return "?".ljust(_LABEL_WIDTH)
    if n < 10:
        return f"CPU{n}"
    return f"{n:>4}"


def _format_value(value: Any) -> str:
    """``{value:6.1f}%`` → 7 chars total. Falls back to ``     ?%`` on bad data."""
    try:
        return f"{float(value):6.1f}%"
    except (TypeError, ValueError):
        return "     ?%"


def _value_cell(value: Any) -> Cell:
    return Cell(text=_format_value(value).rjust(_VALUE_WIDTH))


def _label_cell(text: str) -> Cell:
    return Cell(text=text.ljust(_LABEL_WIDTH))


def _header_cell(text: str) -> Cell:
    # v4 parity: column names are emitted via plain ``curse_add_line(msg)``
    # with no decoration — neither bold nor HEADER coloured.
    return Cell(text=text.rjust(_VALUE_WIDTH))


def _build_data_row(label: str | None, stats: dict[str, Any], headers: list[str], standalone: bool) -> Row:
    cells: list[Cell] = [_label_cell(label)] if standalone else []
    for stat in headers:
        cells.append(_value_cell(stats.get(stat)))
    return Row(cells=cells)


def render(
    payload: dict[str, Any], fields_desc: dict[str, dict[str, Any]], view: dict[str, Any] | None = None
) -> list[Row]:
    """Render the percpu plugin's TUI block — mirrors v4 ``percpu.msg_curse``.

    When quicklook is on screen it already shows the per-core totals, so v4
    drops this block's title, its ``total`` column and its row labels
    (``glances/plugins/percpu/__init__.py:158,183,210``, all gated on
    ``is_disabled('quicklook')``). ``view["quicklook_enabled"]`` carries that
    state; a caller that passes no view gets the standalone shape.
    """
    standalone = not (view or {}).get("quicklook_enabled")
    stat_fields = _resolve_stat_fields(payload) if isinstance(payload, dict) else _os_headers()
    headers = ["total", *stat_fields] if standalone else list(stat_fields)

    # Header row: "CPU" title (standalone only) + column labels.
    header_cells: list[Cell] = []
    if standalone:
        header_cells.append(Cell(text="CPU".ljust(_LABEL_WIDTH), color=ColorRole.HEADER, bold=True))
    for stat in headers:
        header_cells.append(_header_cell(stat))
    rows: list[Row] = [Row(cells=header_cells)]

    if not isinstance(payload, dict):
        return rows

    items = payload.get("data")
    if not isinstance(items, list) or not items:
        return rows

    sorted_items = sorted(
        (it for it in items if isinstance(it, dict)),
        key=lambda x: float(x.get("total") or 0.0),
        reverse=True,
    )

    # `[percpu] max_cpu_display`, published by the model. The constant stays as
    # the fallback for a payload that predates the field (a remote v5 server) —
    # the contract quicklook's renderer already uses.
    max_display = payload.get("max_cpu_display")
    if not isinstance(max_display, int):
        max_display = _DEFAULT_MAX_CPU_DISPLAY

    displayed = sorted_items[:max_display]
    overflow = sorted_items[max_display:]

    for item in displayed:
        label = _cpu_label(item.get("cpu_number")) if standalone else None
        rows.append(_build_data_row(label, item, headers, standalone))

    if overflow:
        # The "CPU*" row averages the cores that did NOT fit on screen — the
        # displayed ones already have a row of their own. Matches quicklook's
        # ``_msg_per_cpu`` and v4 ``summarize_all_cpus_not_displayed`` (#3687).
        means: dict[str, Any] = {}
        for stat in headers:
            vals = [float(it.get(stat) or 0.0) for it in overflow]
            means[stat] = sum(vals) / len(vals) if vals else 0.0
        rows.append(_build_data_row("CPU*" if standalone else None, means, headers, standalone))

    return rows

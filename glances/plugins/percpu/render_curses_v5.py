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
the displayed cores' stats (bug-for-bug with v4
``summarize_all_cpus_not_displayed``: the mean is computed over the
displayed cores, not the hidden ones).

For G1 we assume quicklook is disabled (no quicklook plugin in v5 yet),
so the ``CPU`` title + ``total`` column are always present.

V5 percpu carries no field-level alerts (see ``percpu/model_v5.py``
docstring), so every value cell is DEFAULT-coloured — no
warning/critical decoration here. The system-wide ``cpu`` plugin
remains the source of CPU alerts.

TODO(G2+): plumb args to honour quicklook=enabled (hide ``CPU`` title +
``total`` column) and to read ``[percpu] max_cpu_display`` from the
config.
"""

from __future__ import annotations

import sys
from typing import Any

from glances.outputs.curses_renderer_v5 import Cell, Row, title_role

# v4 fidelity: top-N cores shown, the rest collapsed into a CPU* row.
_DEFAULT_MAX_CPU_DISPLAY = 4

# First column (CPU label) — 4 chars; the painter adds a 1-char gap,
# so the on-screen label area is 5 chars wide (v4 parity: ``CPU0 ``).
_LABEL_WIDTH = 4

# Each stat column — ``{:6.1f}%`` produces 7 chars.
_VALUE_WIDTH = 7


def _os_headers() -> list[str]:
    """Return the OS-specific stat columns (v4 ``define_headers_from_os``)."""
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


def _build_data_row(label: str, stats: dict[str, Any], headers: list[str]) -> Row:
    cells: list[Cell] = [_label_cell(label)]
    for stat in headers:
        cells.append(_value_cell(stats.get(stat)))
    return Row(cells=cells)


def render(payload: dict[str, Any], fields_desc: dict[str, dict[str, Any]]) -> list[Row]:
    """Render the percpu plugin's TUI block — mirrors v4 ``percpu.msg_curse``."""
    headers = ["total", *_os_headers()]

    # Header row: "CPU" title + column labels.
    header_cells: list[Cell] = [
        Cell(text="CPU".ljust(_LABEL_WIDTH), color=title_role(payload), bold=True),
    ]
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

    displayed = sorted_items[:_DEFAULT_MAX_CPU_DISPLAY]
    overflow = sorted_items[_DEFAULT_MAX_CPU_DISPLAY:]

    for item in displayed:
        rows.append(_build_data_row(_cpu_label(item.get("cpu_number")), item, headers))

    if overflow:
        # v4 bug-for-bug parity: the "CPU*" row averages the **displayed**
        # cores, not the hidden overflow (see v4
        # ``summarize_all_cpus_not_displayed``).
        means: dict[str, Any] = {}
        for stat in headers:
            vals = [float(it.get(stat) or 0.0) for it in displayed]
            means[stat] = sum(vals) / len(vals) if vals else 0.0
        rows.append(_build_data_row("CPU*", means, headers))

    return rows

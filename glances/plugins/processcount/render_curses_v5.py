#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — TUI curses renderer for the processcount plugin.

Replicates v4 ``processcount.msg_curse()`` (top "TASKS …" header above the
process list).

Reference layout (G4 minimal — no filter UI, no programs/threads toggle):

    TASKS 215 (1452 thr), 3 run, 195 slp, 17 oth

- One row, one cell sequence: title ``TASKS`` (HEADER) followed by the
  aggregate values inline.
- ``M thr`` parenthesised only when ``thread`` is known (psutil exposes it
  on most OSes — see issue #1463 for the *Other / NetBSD case).
- The v4 sort indicator (``Threads``/``Programs`` + ``sorted automatically
  by …`` / ``sorted by …``) is appended from the TUI ``view`` (G5-hotkeys):
  it reflects the live engine sort key, the auto-sort flag, and the
  threads/programs toggle. When no ``view`` is supplied (export / tests),
  the indicator is omitted.
"""

from __future__ import annotations

from typing import Any

from glances.outputs.curses_renderer_v5 import Cell, ColorRole, Row
from glances.processes import sort_for_human


def _sort_indicator_cell(view: dict[str, Any]) -> Cell | None:
    """Build the v4-style ``Threads/Programs sorted [automatically] by X`` cell.

    Returns ``None`` when no view is supplied (export / no TUI context)."""
    if not view:
        return None
    prefix = "Programs" if view.get("programs") else "Threads"
    sort_human = sort_for_human.get(view.get("sort_key"), view.get("sort_key"))
    if view.get("auto_sort"):
        text = f"{prefix} sorted automatically by {sort_human}"
    else:
        text = f"{prefix} sorted by {sort_human}"
    return Cell(text=text)


def render(
    payload: dict[str, Any],
    fields_desc: dict[str, dict[str, Any]],
    view: dict[str, Any] | None = None,
) -> list[Row]:
    """Render the processcount plugin's single TASKS line."""
    if not isinstance(payload, dict):
        return [Row(cells=[Cell(text="TASKS", color=ColorRole.HEADER, bold=True)])]

    total = payload.get("total")
    if total is None:
        # No aggregate yet (engine never ran or returned empty) — show just
        # the title, no zeros (avoids a confusing ``TASKS 0`` at startup).
        return [Row(cells=[Cell(text="TASKS", color=ColorRole.HEADER, bold=True)])]

    cells: list[Cell] = [Cell(text="TASKS", color=ColorRole.HEADER, bold=True)]
    cells.append(Cell(text=f" {int(total)}"))

    thread = payload.get("thread")
    if thread is not None:
        cells.append(Cell(text=f" ({int(thread)} thr),"))
    else:
        cells.append(Cell(text=","))

    running = payload.get("running")
    if running is not None:
        cells.append(Cell(text=f" {int(running)} run,"))

    sleeping = payload.get("sleeping")
    if sleeping is not None:
        cells.append(Cell(text=f" {int(sleeping)} slp,"))

    # "Other" = total minus running minus sleeping (matches v4).
    other = int(total) - int(running or 0) - int(sleeping or 0)
    cells.append(Cell(text=f" {other} oth"))

    indicator = _sort_indicator_cell(view or {})
    if indicator is not None:
        cells.append(indicator)

    return [Row(cells=cells)]

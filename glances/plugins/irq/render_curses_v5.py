#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — TUI curses renderer for the irq plugin (left sidebar).

Mirrors v4 `irq.msg_curse()`: a two-column table, IRQ line name on the
left and interrupts-per-second right-aligned.

    IRQ                Rate/s
    1_i8042                12
    LOC                     3
"""

from __future__ import annotations

from typing import Any

from glances.outputs.curses_renderer_v5 import Cell, ColorRole, Row

_NAME_MAX_WIDTH = 24
_RATE_WIDTH = 9


def _rate_text(value: Any) -> str:
    # A rate field is absent on an item's first cycle (no previous sample).
    if value is None:
        return "{:>{w}}".format("-", w=_RATE_WIDTH)
    return "{:>{w}}".format(f"{value:.0f}", w=_RATE_WIDTH)


def render(payload: dict[str, Any], fields_desc: dict[str, dict[str, Any]]) -> list[Row]:
    if not isinstance(payload, dict):
        return []
    items = payload.get("data")
    if not isinstance(items, list) or not items:
        return []

    rows: list[Row] = [
        Row(
            cells=[
                Cell(text="IRQ".ljust(_NAME_MAX_WIDTH), color=ColorRole.HEADER, bold=True),
                Cell(text="{:>{w}}".format("Rate/s", w=_RATE_WIDTH), color=ColorRole.HEADER, bold=True),
            ]
        )
    ]
    for item in items:
        if not isinstance(item, dict):
            continue
        irq_line = str(item.get("irq_line", ""))[:_NAME_MAX_WIDTH].ljust(_NAME_MAX_WIDTH)
        rows.append(
            Row(
                cells=[
                    Cell(text=irq_line),
                    Cell(text=_rate_text(item.get("irq_rate"))),
                ]
            )
        )
    return rows

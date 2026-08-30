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

**Ranking lives here, not in the model.** `model_v5.py` now publishes
every IRQ line (a divergence from v4, made so exporters get the complete,
stable series instead of a churning top-5 — see its `_expand_parameters`
docstring). The TUI must still look like v4, so this renderer sorts by
`irq_rate` descending and keeps only the busiest `_TOP_N` lines. A `None`
rate (an item's first cycle) sorts last rather than raising — same
`or 0.0` idiom used for `_rate_text` below, after a prior
`TypeError: None < None` crash in this plugin.
"""

from __future__ import annotations

from typing import Any

from glances.outputs.curses_renderer_v5 import Cell, ColorRole, Row

_NAME_MAX_WIDTH = 24
_RATE_WIDTH = 9
_TOP_N = 5


def _rate_text(value: Any) -> str:
    # A rate field is None on an item's first cycle (no previous sample).
    if value is None:
        return "{:>{w}}".format("-", w=_RATE_WIDTH)
    return "{:>{w}}".format(f"{value:.0f}", w=_RATE_WIDTH)


def render(payload: dict[str, Any], fields_desc: dict[str, dict[str, Any]]) -> list[Row]:
    if not isinstance(payload, dict):
        return []
    items = payload.get("data")
    if not isinstance(items, list) or not items:
        return []

    ranked = sorted(
        (item for item in items if isinstance(item, dict)),
        key=lambda item: item.get("irq_rate") or 0.0,
        reverse=True,
    )[:_TOP_N]

    rows: list[Row] = [
        Row(
            cells=[
                Cell(text="IRQ".ljust(_NAME_MAX_WIDTH), color=ColorRole.HEADER, bold=True),
                Cell(text="{:>{w}}".format("Rate/s", w=_RATE_WIDTH), color=ColorRole.HEADER, bold=True),
            ]
        )
    ]
    for item in ranked:
        irq_line = str(item.get("irq_line", ""))[:_NAME_MAX_WIDTH].ljust(_NAME_MAX_WIDTH)
        rows.append(
            Row(
                cells=[
                    Cell(text=irq_line),
                    Cell(text=_rate_text(item.get("irq_rate"))),
                ],
                item_start=True,
            )
        )
    return rows

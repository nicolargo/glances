#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — TUI curses renderer for the gpu plugin.

Mirrors v4 `gpu.msg_curse()`:

    GeForce RTX 3080         <- header (name / "N NAME" / "N GPUs")
    proc:              30%   <- summary mode (1 GPU or view["meangpu"])
    mem:               40%
    temperature:       55C

Multi mode (>1 GPU, not meangpu): one row per GPU — `name[:9]  proc  mem N`.
"""

from __future__ import annotations

from typing import Any

from glances.globals import to_fahrenheit
from glances.outputs.curses_renderer_v5 import _LEVEL_TO_ROLE, Cell, ColorRole, Row, title_role

_HEADER_MAX = 17


def _format_value(value: Any, unit: str = "%") -> str:
    if value is None:
        return "{:>4}".format("N/A")
    return f"{value:>3.0f}{unit}"


def _mean(cards: list[dict[str, Any]], key: str) -> float | None:
    vals = [c[key] for c in cards if isinstance(c, dict) and c.get(key) is not None]
    if not vals:
        return None
    return sum(vals) / len(vals)


def _build_header(cards: list[dict[str, Any]]) -> str:
    first = cards[0].get("name") or "GPU"
    same = all((c.get("name") or "GPU") == first for c in cards)
    n = len(cards)
    if n > 1:
        header = f"{n} {first}" if same else f"{n} GPUs"
    else:
        header = first
    return header[:_HEADER_MAX]


def _level_role(levels: dict[str, Any], gpu_id: Any, field: str) -> ColorRole:
    entry = levels.get(gpu_id, {})
    level = entry.get(field, {}).get("level") if isinstance(entry, dict) else None
    return _LEVEL_TO_ROLE.get(level, ColorRole.DEFAULT)


def _summary_rows(cards: list[dict[str, Any]], levels: dict[str, Any], fahrenheit: bool) -> list[Row]:
    is_multi = len(cards) > 1
    first_id = cards[0].get("gpu_id")
    rows: list[Row] = []
    for key, label, label_mean in (("proc", "proc:", "proc mean:"), ("mem", "mem:", "mem mean:")):
        rows.append(
            Row(
                cells=[
                    Cell(text=f"{label_mean if is_multi else label:<13}"),
                    Cell(text=_format_value(_mean(cards, key)), color=_level_role(levels, first_id, key)),
                ]
            )
        )
    temp = _mean(cards, "temperature")
    if temp is not None and fahrenheit:
        temp = to_fahrenheit(temp)
    unit = "F" if fahrenheit else "C"
    temp_label = "temp mean:" if is_multi else "temperature:"
    rows.append(
        Row(
            cells=[
                Cell(text=f"{temp_label:<13}"),
                Cell(text=_format_value(temp, unit), color=_level_role(levels, first_id, "temperature")),
            ]
        )
    )
    return rows


def _multi_rows(cards: list[dict[str, Any]], levels: dict[str, Any]) -> list[Row]:
    rows: list[Row] = []
    for card in cards:
        gpu_id = card.get("gpu_id")
        cells = [Cell(text="{:<7}".format(str(card.get("name") or "")[0:9]))]
        if card.get("proc") is not None:
            cells.append(Cell(text=f" {_format_value(card.get('proc'))}", color=_level_role(levels, gpu_id, "proc")))
        if card.get("mem") is not None:
            cells.append(Cell(text=f" mem {_format_value(card.get('mem'))}", color=_level_role(levels, gpu_id, "mem")))
        rows.append(Row(cells=cells))
    return rows


def render(payload: dict[str, Any], fields_desc: dict[str, dict[str, Any]] | None = None, view=None) -> list[Row]:
    if not isinstance(payload, dict):
        return []
    cards = payload.get("data")
    if not isinstance(cards, list) or not cards:
        return []
    levels = payload.get("_levels") if isinstance(payload.get("_levels"), dict) else {}
    view = view or {}

    header = Row(cells=[Cell(text=_build_header(cards), color=title_role(payload), bold=True)])
    rows: list[Row] = [header]

    if len(cards) == 1 or view.get("meangpu"):
        rows.extend(_summary_rows(cards, levels, bool(view.get("fahrenheit"))))
    else:
        rows.extend(_multi_rows(cards, levels))
    return rows

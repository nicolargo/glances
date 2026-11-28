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
    proc               30%   <- summary mode (1 GPU or view["meangpu"])
    mem                40%
    temperature        55C

Multi mode (>1 GPU, not meangpu): one row per GPU — `name[:9] proc mem N temp`.
The `mem` / temperature column is dropped when no card reports it (narrower plugin).
A card flagged `hide_temperature` (its temperature is already in the sensors
plugin, or `[gpu] hide_temperature` is set) does not count as reporting one:
the temperature row / column only appears for a card that shows it.
Widths are the minimum that keeps rows aligned: the label / name column is as
wide as its longest entry, and value cells carry no leading space -- the
painter already separates adjacent cells with one.
"""

from __future__ import annotations

from typing import Any

from glances.globals import to_fahrenheit
from glances.outputs.curses_renderer import _LEVEL_TO_ROLE, Cell, ColorRole, Row, field_label

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
    if len(header) <= _HEADER_MAX:
        return header
    # Never cut a word in half: drop the partial trailing word.
    cut = header[: _HEADER_MAX + 1].rsplit(" ", 1)[0]
    return cut if " " in header[: _HEADER_MAX + 1] else header[:_HEADER_MAX]


def _shows_temperature(card: dict[str, Any]) -> bool:
    return not card.get("hide_temperature")


def _level_role(levels: dict[str, Any], gpu_id: Any, field: str) -> ColorRole:
    entry = levels.get(gpu_id, {})
    level = entry.get(field, {}).get("level") if isinstance(entry, dict) else None
    return _LEVEL_TO_ROLE.get(level, ColorRole.DEFAULT)


def _summary_rows(
    cards: list[dict[str, Any]],
    levels: dict[str, Any],
    fahrenheit: bool,
    fields_desc: dict[str, dict[str, Any]],
) -> list[Row]:
    is_multi = len(cards) > 1
    first_id = cards[0].get("gpu_id")
    # The schema holds ONE word per field; the "mean" suffix is the
    # renderer's, composed here.
    labels = {}
    for key in ("proc", "mem"):
        word = field_label(fields_desc.get(key, {}), key, prefer_short=True)
        labels[key] = f"{word} mean" if is_multi else word
    # Only the non-mean form comes from the schema. v4 shortens the word in the
    # mean form ("temperature" -> "temp mean"), i.e. the two forms use
    # DIFFERENT words, and a schema holds one string per field — so the mean
    # form cannot be composed by suffixing and stays a literal here.
    show_temp = any(_shows_temperature(card) for card in cards)
    if show_temp:
        temp_word = field_label(fields_desc.get("temperature", {}), "temperature", prefer_short=True)
        labels["temperature"] = "temp mean" if is_multi else temp_word
    width = max(len(label) for label in labels.values())
    rows: list[Row] = []
    for key in ("proc", "mem"):
        rows.append(
            Row(
                cells=[
                    Cell(text=f"{labels[key]:<{width}}"),
                    Cell(text=_format_value(_mean(cards, key)), color=_level_role(levels, first_id, key)),
                ]
            )
        )
    if not show_temp:
        return rows
    temp = _mean(cards, "temperature")
    if temp is not None and fahrenheit:
        temp = to_fahrenheit(temp)
    unit = "F" if fahrenheit else "C"
    rows.append(
        Row(
            cells=[
                Cell(text=f"{labels['temperature']:<{width}}"),
                Cell(text=_format_value(temp, unit), color=_level_role(levels, first_id, "temperature")),
            ]
        )
    )
    return rows


def _multi_rows(cards: list[dict[str, Any]], levels: dict[str, Any], fahrenheit: bool) -> list[Row]:
    # #3631: an unavailable sensor is displayed as N/A, not hidden — hiding it per
    # card drops a cell and misaligns the rows of heterogeneous cards. The mem and
    # temperature columns are dropped only when no card reports them: every row
    # stays aligned and the plugin gets narrower.
    show_mem = any(card.get("mem") is not None for card in cards)
    show_temp = any(_shows_temperature(card) and card.get("temperature") is not None for card in cards)
    unit = "F" if fahrenheit else "C"
    names = [str(card.get("name") or "")[0:9] for card in cards]
    name_width = max(len(name) for name in names)
    rows: list[Row] = []
    for card, name in zip(cards, names):
        gpu_id = card.get("gpu_id")
        cells = [Cell(text=f"{name:<{name_width}}")]
        cells.append(Cell(text=_format_value(card.get("proc")), color=_level_role(levels, gpu_id, "proc")))
        if show_mem:
            cells.append(Cell(text=f"mem {_format_value(card.get('mem'))}", color=_level_role(levels, gpu_id, "mem")))
        if show_temp:
            temp = card.get("temperature")
            if temp is not None and fahrenheit:
                temp = to_fahrenheit(temp)
            cells.append(Cell(text=_format_value(temp, unit), color=_level_role(levels, gpu_id, "temperature")))
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

    header = Row(cells=[Cell(text=_build_header(cards), color=ColorRole.HEADER, bold=True)])
    rows: list[Row] = [header]

    if len(cards) == 1 or view.get("meangpu"):
        rows.extend(_summary_rows(cards, levels, bool(view.get("fahrenheit")), fields_desc or {}))
    else:
        rows.extend(_multi_rows(cards, levels, bool(view.get("fahrenheit"))))
    return rows

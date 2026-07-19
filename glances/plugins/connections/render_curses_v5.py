#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — TUI curses renderer for the connections plugin.

Mirrors v4 `connections.msg_curse()`
(`glances/plugins/connections/__init__.py::msg_curse`): a `TCP CONNECTIONS`
title, then one row per connection-state counter in a fixed order
(`Listen`, `Initiated`, `Established`, `Terminated` — each skipped when its
key is absent from the payload), then a `Tracked` row (`count/max`) when
Netfilter conntrack is enabled and both values are present — the ONLY
coloured row, driven by the `nf_conntrack_percent` level.

Reference layout (LEFT sidebar):

    TCP CONNECTIONS
    Listen                                   3
    Initiated                                0
    Established                             12
    Terminated                             204
    Tracked                            512/1024

Width formula (see plan Key Finding 3): v4 computes each value cell's
width as `max_width - len(label) + 2` against a dynamically-supplied
`max_width`. v5 fixes the LEFT-sidebar budget at 34 chars (matching
`wifi`/`diskio`) and the v5 painter auto-inserts one separator space
between adjacent cells (unlike v4's raw concatenation), so the value
width here is `34 - len(label) - 1` — this keeps
`len(label) + 1(separator) + value_width == 34` exactly, reproducing
v4's on-screen shape (label at its natural width, value flushed to the
row's right edge) inside the fixed v5 budget.
"""

from __future__ import annotations

from typing import Any

from glances.outputs.curses_renderer_v5 import _LEVEL_TO_ROLE, Cell, ColorRole, Row

_LEFT_SIDEBAR_MAX_WIDTH = 34

# Fixed v4 display order (glances/plugins/connections/__init__.py:205).
_ROW_ORDER: tuple[tuple[str, str], ...] = (
    ("LISTEN", "Listen"),
    ("initiated", "Initiated"),
    ("ESTABLISHED", "Established"),
    ("terminated", "Terminated"),
)


def _stat_row(label: str, value: Any, color: ColorRole = ColorRole.DEFAULT, prominent: bool = False) -> Row:
    """One (label, right-flushed value) row filling the 34-char budget
    exactly: `len(label) + 1 (painter separator) + value_width == 34`.
    """
    value_width = _LEFT_SIDEBAR_MAX_WIDTH - len(label) - 1
    return Row(cells=[Cell(text=label), Cell(text=str(value).rjust(value_width), color=color, prominent=prominent)])


def render(
    payload: dict[str, Any],
    fields_desc: dict[str, dict[str, Any]] | None = None,
    view: dict | None = None,
) -> list[Row]:
    if not isinstance(payload, dict) or not payload:
        return []

    net_enabled = bool(payload.get("net_connections_enabled"))
    nf_enabled = bool(payload.get("nf_conntrack_enabled"))
    if not net_enabled and not nf_enabled:
        return []

    rows: list[Row] = [Row(cells=[Cell(text="TCP CONNECTIONS", color=ColorRole.HEADER, bold=True)])]

    if net_enabled:
        for key, label in _ROW_ORDER:
            if key not in payload:
                continue
            rows.append(_stat_row(label, payload[key]))

    if nf_enabled and payload.get("nf_conntrack_count") is not None and payload.get("nf_conntrack_max") is not None:
        levels = payload.get("_levels")
        levels = levels if isinstance(levels, dict) else {}
        level_entry = levels.get("nf_conntrack_percent", {})
        level = level_entry.get("level") if isinstance(level_entry, dict) else None
        role = _LEVEL_TO_ROLE.get(level, ColorRole.DEFAULT)
        prominent = bool(level_entry.get("prominent")) if isinstance(level_entry, dict) else False
        value_text = f"{payload['nf_conntrack_count']:.0f}/{payload['nf_conntrack_max']:.0f}"
        rows.append(_stat_row("Tracked", value_text, color=role, prominent=prominent))

    return rows

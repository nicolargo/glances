#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — TUI curses renderer for the amps plugin.

Mirror of v4 `amps.msg_curse()`: three columns — the AMP name on 16 chars,
the number of matching processes on 4, then the AMP result. A multi-line
result produces one row per line, with the name and count cells filled on
the first line only.

    Python           2    CPU: 1.0% | MEM: 2.0%
    Systemd          1    Services
                          active: 3

NO TITLE ROW and no column header — deliberate, v4 parity. The block sits
between `processcount` and `processlist` in `RIGHT_SLOT` and reads as part
of that run. `tests/test_plugin_amps_render_curses_v5.py::test_no_title_row_deliberate_do_not_fix`
locks it.

Divergence from v4: v4 marks the result line `splittable=True`, letting it
wrap. The v5 `Cell` has no such attribute, so an over-long result line is
clipped by curses instead. Adding wrapping to the shared renderer for a
single caller was ruled out of scope (design §7).
"""

from __future__ import annotations

from typing import Any

from glances.outputs.curses_renderer_v5 import _LEVEL_TO_ROLE, Cell, ColorRole, Row

# v4 formats the AMP name with `{:<16}` and the count with `{:<4}`.
_NAME_COL_WIDTH = 16
_COUNT_COL_WIDTH = 4


def _level_role(entry: Any) -> tuple[ColorRole, bool]:
    if isinstance(entry, dict):
        return (_LEVEL_TO_ROLE.get(entry.get("level"), ColorRole.DEFAULT), bool(entry.get("prominent")))
    return (ColorRole.DEFAULT, False)


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

    levels = payload.get("_levels")
    if not isinstance(levels, dict):
        levels = {}

    rows: list[Row] = []
    for item in items:
        result = item.get("result")
        if result is None:
            # The AMP has not produced anything yet — v4 skips it entirely
            # rather than rendering an empty row.
            continue

        name = str(item.get("name") or "")
        # v4 hides the count for a regex-less AMP: there is nothing to count.
        count = item.get("count")
        count_text = "" if not item.get("regex") or count is None else str(count)

        item_levels = levels.get(item.get("name"))
        role, prominent = _level_role(item_levels.get("count") if isinstance(item_levels, dict) else None)

        first = True
        for line in str(result).split("\n"):
            rows.append(
                Row(
                    cells=[
                        Cell(
                            text=f"{name if first else '':<{_NAME_COL_WIDTH}}",
                            color=role if first else ColorRole.DEFAULT,
                            prominent=prominent if first else False,
                        ),
                        Cell(text=f"{count_text if first else '':<{_COUNT_COL_WIDTH}}"),
                        Cell(text=line),
                    ]
                )
            )
            first = False
    return rows

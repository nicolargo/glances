#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — TUI curses renderer for the ports plugin.

Mirror of v4 `ports.msg_curse()`: one row per scanned item, the description
left-aligned and truncated, then the status right-aligned on 9 chars.

    Home Box                  12ms
    Internet ICMP          Timeout
    My Blog               Code 200

NO TITLE ROW — deliberate. `ports` sits directly under `network` in
`LEFT_SLOT`; the two belong to the same functional domain and read as one
continuous block. The missing title is that continuity, not an oversight
(design §5.3). `tests/test_plugin_ports_render_curses_v5.py::test_no_title_row_deliberate_do_not_fix`
locks it.

Width budget: v4 truncates the description to `max_width - 7` and then appends
a 9-char status, i.e. a block of `max_width + 2`. v5's painter hard-clips
LEFT-sidebar blocks at 34 chars, so the v4 formula is fed the `max_width` whose
+2 overshoot lands exactly on the budget: 32 - 7 = 25, and 25 + 9 = 34. The
status cell carries `glue=True` so the painter inserts no separating space
(v4 concatenates the two strings directly).

One list holds TWO item kinds and every branch below keys off that:

- web item  — has `url`; status is an HTTP code, `None`, or the string "Error";
- port item — has `host`; status is `None`, `True`, `False`/`0`, or a float RTT
  in seconds.
"""

from __future__ import annotations

import numbers
from typing import Any

from glances.outputs.curses_renderer_v5 import _LEVEL_TO_ROLE, Cell, ColorRole, Row

# Painter cap for a LEFT-sidebar block.
_LEFT_SIDEBAR_MAX_WIDTH = 34
# v4 right-aligns the status string on 9 chars.
_STATUS_COL_WIDTH = 9
# See the module docstring: 32 - 7 = 25, and 25 + 9 = _LEFT_SIDEBAR_MAX_WIDTH.
_MAX_WIDTH = _LEFT_SIDEBAR_MAX_WIDTH - _STATUS_COL_WIDTH + 7
_NAME_MAX_WIDTH = _MAX_WIDTH - 7


def _status_if_host(item: dict[str, Any]) -> str:
    """v4 `set_status_if_host`, reproduced verbatim."""
    if item.get("host") is None:
        # `get_default_gateway()` returns None when it cannot be resolved.
        return "None"
    status = item.get("status")
    if status is None:
        return "Scanning"
    if isinstance(status, bool) and status is True:
        return "Open"
    if status == 0:
        # `False == 0`: covers both the ICMP and the TCP timeout paths.
        return "Timeout"
    # v4 stores the RTT in seconds and displays milliseconds.
    return f"{status * 1000.0:.0f}ms"


def _status_if_url(item: dict[str, Any]) -> str:
    """v4 `set_status_if_url`, reproduced verbatim."""
    status = item.get("status")
    if isinstance(status, numbers.Number):
        return f"Code {status}"
    if status is None:
        return "Scanning"
    # The scanner writes the literal string "Error" when `requests` raises.
    return str(status)


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
        # Branch on item kind. An item with neither key cannot be scanned and
        # is skipped rather than rendered as a blank status.
        if "url" in item:
            status_text = _status_if_url(item)
        elif "host" in item:
            status_text = _status_if_host(item)
        else:
            continue

        item_levels = levels.get(item.get("indice"))
        status_level = item_levels.get("status") if isinstance(item_levels, dict) else None
        role, prominent = _level_role(status_level)
        description = str(item.get("description") or "")[:_NAME_MAX_WIDTH]
        rows.append(
            Row(
                cells=[
                    Cell(text=f"{description:<{_NAME_MAX_WIDTH}}"),
                    Cell(
                        text=f"{status_text:>{_STATUS_COL_WIDTH}}",
                        color=role,
                        prominent=prominent,
                        glue=True,
                    ),
                ]
            )
        )
    return rows

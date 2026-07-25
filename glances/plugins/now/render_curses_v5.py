#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — TUI renderer for the now plugin (header block, far right).

The ``custom`` date string as a bare one-liner. Unlike v4 ``now.msg_curse``
there is no 23-char padding: that padding aligned the block with the process
list in v4's left sidebar, and trailing blanks would push the date away from
the right edge here (see ``curses_renderer_v5.HEADER_SLOT_RIGHT`` +
``glances_curses_v5._paint_header``). The ISO field is REST-only.
"""

from __future__ import annotations

from typing import Any

from glances.outputs.curses_renderer_v5 import Cell, Row


def render(payload: dict[str, Any], fields_desc: dict[str, dict[str, Any]]) -> list[Row]:
    custom = payload.get("custom") if payload else None
    if not custom:
        return []
    return [Row(cells=[Cell(text=str(custom))])]

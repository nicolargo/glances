#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — TUI renderer for the system plugin (header-left block).

Mirrors v4 ``system.msg_curse``: ``hostname`` (TITLE) followed by the
human-readable OS name. Routed to the header slot and painted flush-left
(see ``curses_renderer_v5.HEADER_SLOT``). Client/SNMP status lines are not
ported (v5 standalone only).
"""

from __future__ import annotations

from typing import Any

from glances.outputs.curses_renderer_v5 import Cell, ColorRole, Row


def render(payload: dict[str, Any], fields_desc: dict[str, dict[str, Any]]) -> list[Row]:
    if not payload or not payload.get("hostname"):
        return []
    cells = [Cell(text=str(payload["hostname"]), color=ColorRole.HEADER)]
    hr_name = payload.get("hr_name")
    if hr_name:
        cells.append(Cell(text=str(hr_name)))
    return [Row(cells=cells)]

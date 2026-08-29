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


def render(payload: dict[str, Any], fields_desc: dict[str, dict[str, Any]], view=None) -> list[Row]:
    if not payload or not payload.get("hostname"):
        return []
    cells = [Cell(text=str(payload["hostname"]), color=ColorRole.HEADER)]
    # The OS/kernel string is static host metadata, so it is the first thing
    # dropped once the opt-in cloud block is gone — before any live block is
    # hidden (progressive degradation, driven by `view["hide_os_info"]`);
    # the hostname is mandatory and always kept.
    hr_name = payload.get("hr_name")
    if hr_name and not (view or {}).get("hide_os_info"):
        cells.append(Cell(text=str(hr_name)))
    return [Row(cells=cells)]

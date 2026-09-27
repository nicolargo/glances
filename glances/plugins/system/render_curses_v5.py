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
(see ``curses_renderer_v5.HEADER_SLOT``). In client mode the line starts with
v4's status, ``Connected to`` (OK) or ``Disconnected from`` (CRITICAL),
from ``view["client_status"]``; the SNMP status is not ported (SNMP dropped).
Disconnected, the TUI goes on showing the last values received, and the
hostname is followed by when they were received (``last update 14:02:31``).
"""

from __future__ import annotations

import time
from typing import Any

from glances.outputs.curses_renderer_v5 import Cell, ColorRole, Row

_CLIENT_STATUS = {
    "connected": ("Connected to", ColorRole.OK),
    "disconnected": ("Disconnected from", ColorRole.CRITICAL),
}


def render(payload: dict[str, Any], fields_desc: dict[str, dict[str, Any]], view=None) -> list[Row]:
    view = view or {}
    status = _CLIENT_STATUS.get(view.get("client_status") or "")
    hostname = (payload or {}).get("hostname")
    if not hostname and not status:
        return []
    cells = []
    if status:
        cells.append(Cell(text=status[0], color=status[1]))
    # A client that never reached the server has no payload: it still names
    # the host it is trying (v4 parity).
    cells.append(Cell(text=str(hostname or view.get("client_host") or "?"), color=ColorRole.HEADER))
    last_update = view.get("client_last_update")
    if view.get("client_status") == "disconnected" and last_update is not None:
        # Every value on screen is from then: say so next to the red status.
        stamp = time.strftime("%H:%M:%S", time.localtime(last_update))
        cells.append(Cell(text=f"(last update {stamp})", color=ColorRole.CRITICAL))
    payload = payload or {}
    # The OS/kernel string is static host metadata, so it is the first thing
    # dropped once the opt-in cloud block is gone — before any live block is
    # hidden (progressive degradation, driven by `view["hide_os_info"]`);
    # the hostname is mandatory and always kept.
    hr_name = payload.get("hr_name")
    if hr_name and not view.get("hide_os_info"):
        cells.append(Cell(text=str(hr_name)))
    return [Row(cells=cells)]

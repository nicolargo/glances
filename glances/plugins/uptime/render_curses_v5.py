#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — TUI renderer for the uptime plugin (header-right block).

Mirrors v4 ``uptime.msg_curse``: a single ``Uptime: <value>`` line. In the
v5 layout this block is routed to the header slot and painted flush-right
(see ``curses_renderer_v5.HEADER_SLOT`` + ``glances_curses_v5._paint_header``).
"""

from __future__ import annotations

from typing import Any

from glances.outputs.curses_formatters_v5 import format_value
from glances.outputs.curses_renderer_v5 import Cell, Row


def render(payload: dict[str, Any], fields_desc: dict[str, dict[str, Any]]) -> list[Row]:
    if not payload or payload.get("seconds") is None:
        return []
    value = format_value(payload["seconds"], fields_desc.get("seconds", {"unit": "seconds"}))
    return [Row(cells=[Cell(text="Uptime:"), Cell(text=value)])]

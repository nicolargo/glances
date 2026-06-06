#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — TUI renderer for the now plugin (left-sidebar one-liner).

Mirrors v4 ``now.msg_curse``: the ``custom`` date string left-padded to 23
chars (the v4 process-list padding). The ISO field is REST-only.
"""

from __future__ import annotations

from typing import Any

from glances.outputs.curses_renderer_v5 import Cell, Row

_NOW_PAD = 23


def render(payload: dict[str, Any], fields_desc: dict[str, dict[str, Any]]) -> list[Row]:
    custom = payload.get("custom") if payload else None
    if not custom:
        return []
    return [Row(cells=[Cell(text=f"{str(custom):{_NOW_PAD}}")])]

#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — TUI renderer for the ip plugin (inline single line).

Mirrors v4 `ip.msg_curse`: `IP <address>/<cidr>` and, when available,
` Pub <public_address> {public_info_human}`. Emitted as ONE Row; the
painter inserts a single space between cells. The `--hide-public-info`
CLI flag (surfaced via `view['hide_public_info']`, like `--fahrenheit`)
masks the public address `a.b.c.d` -> `a.b.*.*` at display time.

Note: v5 `Cell` has no per-segment `optional` flag (v4 used `optional=True`
to drop segments on narrow terminals); narrow-terminal handling is via
block clipping at paint time. Empty public fields are simply omitted.
"""

from __future__ import annotations

from typing import Any

from glances.outputs.curses_renderer_v5 import Cell, ColorRole, Row


def _hide_ip(ip: str) -> str:
    """Mask the last two octets of a dotted IPv4 address: a.b.c.d -> a.b.*.*"""
    return ".".join(ip.split(".")[0:2]) + ".*.*"


def render(payload: dict[str, Any], fields_desc: dict[str, dict[str, Any]] | None = None, view=None) -> list[Row]:
    if not isinstance(payload, dict) or not payload:
        return []
    view = view or {}
    hide_public = bool(view.get("hide_public_info"))

    cells: list[Cell] = []

    # Private IP (skip cleanly when no interface was found).
    address = payload.get("address")
    if address:
        cells.append(Cell(text="IP", color=ColorRole.HEADER))
        mask_cidr = payload.get("mask_cidr")
        text = f"{address}/{mask_cidr}" if mask_cidr is not None else str(address)
        cells.append(Cell(text=text))

    # Public IP (guarded — see issue #1469).
    try:
        public_address = payload.get("public_address") or ""
        if public_address:
            shown = _hide_ip(public_address) if hide_public else public_address
            cells.append(Cell(text="Pub", color=ColorRole.HEADER))
            cells.append(Cell(text=str(shown)))
            info = payload.get("public_info_human")
            if info:
                cells.append(Cell(text=str(info)))
    except (UnicodeEncodeError, KeyError):
        pass

    if not cells:
        return []
    return [Row(cells=cells)]

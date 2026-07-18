#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — TUI curses renderer for the wifi plugin.

Mirrors v4 `wifi.msg_curse()`: a `WIFI` header then one row per hotspot
(`ssid` + right-aligned `dBm` signal level). LEFT sidebar; the block must
fit the v5 left-sidebar maximum (34 chars) *including* the one-space cell
separator the painter inserts between the two cells:

    name (_NAME_MAX_WIDTH) + 1 + value (_VALUE_COL_WIDTH) = 26 + 1 + 7 = 34

Overshooting by even one char makes the painter truncate the rightmost
cell — clipping the trailing digits off the value (v4 parity via the
sensors renderer's documented budget).

    WIFI                       dBm
    wlan0                      -60

- Rows with an empty/missing `ssid` or a non-numeric/`None`
  `quality_level` are skipped (v4 parity, issues #1151/#1973).
"""

from __future__ import annotations

from typing import Any

from glances.outputs.curses_renderer_v5 import _LEVEL_TO_ROLE, Cell, ColorRole, Row

_NAME_MAX_WIDTH = 26
_VALUE_COL_WIDTH = 7
# Painter inserts a 1-space separator between the two cells, so the block
# spans _NAME_MAX_WIDTH + 1 + _VALUE_COL_WIDTH. Must stay <= the left-sidebar
# maximum or the trailing digits are clipped (see module docstring).
_LEFT_SIDEBAR_MAX_WIDTH = 34


def _format_name(ssid: str) -> str:
    if len(ssid) > _NAME_MAX_WIDTH:
        return ssid[:_NAME_MAX_WIDTH]
    return ssid.ljust(_NAME_MAX_WIDTH)


def _level_role(levels: dict[str, Any], ssid: str) -> tuple[ColorRole, bool]:
    entry = levels.get(ssid, {}) if isinstance(levels, dict) else {}
    quality_entry = entry.get("quality_level", {}) if isinstance(entry, dict) else {}
    level = quality_entry.get("level")
    prominent = bool(quality_entry.get("prominent"))
    return _LEVEL_TO_ROLE.get(level, ColorRole.DEFAULT), prominent


def render(payload: dict[str, Any], fields_desc: dict[str, dict[str, Any]] | None = None, view=None) -> list[Row]:
    header = Row(
        cells=[
            Cell(text="WIFI".ljust(_NAME_MAX_WIDTH), color=ColorRole.HEADER, bold=True),
            Cell(text="dBm".rjust(_VALUE_COL_WIDTH), color=ColorRole.HEADER, bold=True),
        ]
    )
    rows: list[Row] = [header]

    if not isinstance(payload, dict):
        return rows
    items = payload.get("data")
    if not isinstance(items, list):
        return rows
    levels = payload.get("_levels") if isinstance(payload.get("_levels"), dict) else {}

    for item in sorted(items, key=lambda r: str(r.get("ssid", "")) if isinstance(r, dict) else ""):
        if not isinstance(item, dict):
            continue
        ssid = item.get("ssid")
        if ssid in ("", None):
            continue
        quality_level = item.get("quality_level")
        # Skip a non-numeric (or missing) signal — mirrors the sensors
        # renderer's value guard so a stray string can never crash the
        # `f"{quality_level:.0f}"` format below (renderer stays robust
        # independently of the model's float/None guarantee).
        if not isinstance(quality_level, (int, float)):
            continue
        role, prominent = _level_role(levels, ssid)
        rows.append(
            Row(
                cells=[
                    Cell(text=_format_name(str(ssid))),
                    Cell(text=f"{quality_level:.0f}".rjust(_VALUE_COL_WIDTH), color=role, prominent=prominent),
                ]
            )
        )
    return rows

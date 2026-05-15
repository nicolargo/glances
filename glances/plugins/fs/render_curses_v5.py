#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — TUI curses renderer for the fs plugin.

Replicates v4 ``fs.msg_curse()``: header line + one row per filesystem
showing the mountpoint, used size, and total size.

Reference layout:

    FILE SYS              Used   Total
    /                   125.0G  500.0G
    /home               512.0G    1.0T

- Header: ``FILE SYS`` (HEADER) + ``Used`` + ``Total`` (right-aligned).
- One row per filesystem, sorted by mountpoint.
- The ``Used`` cell inherits the percent-threshold color (v4 parity:
  v4 decorates the ``used`` cell from ``get_alert(used, max=size)``).
- Long mountpoints are tail-truncated with a leading underscore.

TODO(G4+): plumb max_width / args so ``--fs-free-space`` (display Free
instead of Used) is honoured. Hardcoded ``Used`` for now.
"""

from __future__ import annotations

from typing import Any

from glances.outputs.curses_formatters_v5 import format_value
from glances.outputs.curses_renderer_v5 import _LEVEL_TO_ROLE, Cell, ColorRole, Row, title_role

# Block width capped at the v5 left-sidebar maximum (34 chars).
#     name (_NAME_MAX_WIDTH) + 1 + used (7) + 1 + total (7) = name + 16
# Set to 18 → block fits exactly in 34.
_NAME_MAX_WIDTH = 18
_USED_COL_WIDTH = 7
_TOTAL_COL_WIDTH = 7


def _format_bytes(value: Any) -> str:
    """Bytes → human-readable string with K/M/G/T scaling."""
    return format_value(value, {"unit": "bytes"})


def _format_mnt_point(mnt: str) -> str:
    """Truncate / pad a mountpoint string to ``_NAME_MAX_WIDTH`` (v4 parity)."""
    if len(mnt) > _NAME_MAX_WIDTH:
        return "_" + mnt[-(_NAME_MAX_WIDTH - 1) :]
    return mnt.ljust(_NAME_MAX_WIDTH)


def _used_cell(value: Any, level_entry: dict[str, Any]) -> Cell:
    text = _format_bytes(value).rjust(_USED_COL_WIDTH) if value is not None else "-".rjust(_USED_COL_WIDTH)
    level = level_entry.get("level") if isinstance(level_entry, dict) else None
    role = _LEVEL_TO_ROLE.get(level, ColorRole.DEFAULT)
    prominent = bool(level_entry.get("prominent")) if isinstance(level_entry, dict) else False
    return Cell(text=text, color=role, prominent=prominent)


def _total_cell(value: Any) -> Cell:
    text = _format_bytes(value).rjust(_TOTAL_COL_WIDTH) if value is not None else "-".rjust(_TOTAL_COL_WIDTH)
    return Cell(text=text)


def render(payload: dict[str, Any], fields_desc: dict[str, dict[str, Any]]) -> list[Row]:
    """Render the fs plugin's TUI block — mirrors v4 ``fs.msg_curse``."""
    header_row = Row(
        cells=[
            Cell(text="FILE SYS".ljust(_NAME_MAX_WIDTH), color=title_role(payload), bold=True),
            Cell(text="Used".rjust(_USED_COL_WIDTH), color=ColorRole.HEADER, bold=True),
            Cell(text="Total".rjust(_TOTAL_COL_WIDTH), color=ColorRole.HEADER, bold=True),
        ]
    )
    rows: list[Row] = [header_row]

    if not isinstance(payload, dict):
        return rows
    items = payload.get("data")
    if not isinstance(items, list):
        return rows

    raw_levels = payload.get("_levels")
    levels_index = raw_levels if isinstance(raw_levels, dict) else {}

    # Sort by mountpoint for stable ordering (v4 parity:
    # ``sorted(self.stats, key=operator.itemgetter('mnt_point'))``).
    for item in sorted(items, key=lambda it: str(it.get("mnt_point", ""))):
        if not isinstance(item, dict):
            continue
        mnt = str(item.get("mnt_point") or "")
        if not mnt:
            continue

        if_levels = levels_index.get(mnt) if isinstance(levels_index, dict) else None
        percent_entry = if_levels.get("percent", {}) if isinstance(if_levels, dict) else {}

        rows.append(
            Row(
                cells=[
                    Cell(text=_format_mnt_point(mnt)),
                    _used_cell(item.get("used"), percent_entry),
                    _total_cell(item.get("size")),
                ]
            )
        )

    return rows

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
- The ``Used``/``Free`` cell inherits the percent-threshold color (v4
  parity: v4 decorates that cell from ``get_alert(used, max=size)`` —
  the decoration key stays ``percent`` regardless of ``free_space``).
- Long mountpoints are tail-truncated with a leading underscore.

``[fs] free_space`` / ``--fs-free-space`` (design §5.4) switch the second
column from used to free space. The flag rides along as the plugin's
``free_space`` payload metadata (``fs/model_v5.py::_add_metadata``) — the
renderer has no other way to reach the config. The ``F`` hotkey (2.X-c)
overrides it through ``view["fs_free_space"]``, which is published only once
the key has been pressed.
"""

from __future__ import annotations

from typing import Any

from glances.outputs.curses_formatters_v5 import format_value
from glances.outputs.curses_renderer_v5 import _LEVEL_TO_ROLE, Cell, ColorRole, Row, field_label

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


def _value_cell(value: Any, level_entry: dict[str, Any]) -> Cell:
    text = _format_bytes(value).rjust(_USED_COL_WIDTH) if value is not None else "-".rjust(_USED_COL_WIDTH)
    level = level_entry.get("level") if isinstance(level_entry, dict) else None
    role = _LEVEL_TO_ROLE.get(level, ColorRole.DEFAULT)
    prominent = bool(level_entry.get("prominent")) if isinstance(level_entry, dict) else False
    return Cell(text=text, color=role, prominent=prominent)


def _total_cell(value: Any) -> Cell:
    text = _format_bytes(value).rjust(_TOTAL_COL_WIDTH) if value is not None else "-".rjust(_TOTAL_COL_WIDTH)
    return Cell(text=text)


def render(
    payload: dict[str, Any], fields_desc: dict[str, dict[str, Any]], view: dict[str, Any] | None = None
) -> list[Row]:
    """Render the fs plugin's TUI block — mirrors v4 ``fs.msg_curse``."""
    # `[fs] free_space` / `--fs-free-space` reach here as payload metadata.
    # The `F` hotkey overrides them for this session: it publishes
    # `view["fs_free_space"]` only once pressed, so an absent key means "keep
    # following the config" rather than "used".
    free_space = bool(payload.get("free_space")) if isinstance(payload, dict) else False
    if view is not None and "fs_free_space" in view:
        free_space = bool(view["fs_free_space"])
    value_field = "free" if free_space else "used"
    # The block title stays a literal; the column labels come from the schema
    # (single source of truth, shared with the WebUI), as network's do.
    value_label = field_label(fields_desc.get(value_field, {}), value_field, prefer_short=True)
    total_label = field_label(fields_desc.get("size", {}), "size", prefer_short=True)
    header_row = Row(
        cells=[
            Cell(text="FILE SYS".ljust(_NAME_MAX_WIDTH), color=ColorRole.HEADER, bold=True),
            Cell(text=value_label.rjust(_USED_COL_WIDTH), color=ColorRole.HEADER, bold=True),
            Cell(text=total_label.rjust(_TOTAL_COL_WIDTH), color=ColorRole.HEADER, bold=True),
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
        # `alias` (design §5.5, v4 parity `fs/__init__.py:310`) replaces the
        # raw mountpoint in the display only — `_levels` above stays keyed
        # by the raw `mnt`.
        display_mnt = str(item.get("alias") or mnt)

        rows.append(
            Row(
                cells=[
                    Cell(text=_format_mnt_point(display_mnt)),
                    _value_cell(item.get(value_field), percent_entry),
                    _total_cell(item.get("size")),
                ],
                item_start=True,
            )
        )

    return rows

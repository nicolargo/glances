#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — TUI curses renderer for the diskio plugin.

Replicates v4 ``diskio.msg_curse()`` default mode (R/s + W/s):

    DISK I/O              R/s     W/s
    nvme0n1              100B    50B
    sda                   1.4M   732K

- Header: ``DISK I/O`` (HEADER) + ``R/s`` + ``W/s`` (right-aligned).
- One row per disk, sorted by ``disk_name``.
- Rate cells display ``auto_unit(bytes_per_sec)`` WITHOUT a trailing
  ``/s`` — the header carries the per-second semantic, saving column
  width (v4 parity).
- Disks with no rate yet (cycle 1) are skipped — avoids a startup wall
  of ``-`` placeholders.
- Long disk names are tail-truncated with a leading underscore.

TODO(G4+): plumb args so ``--diskio-iops`` (IOR/s + IOW/s) and
``--diskio-latency`` (ms/opR + ms/opW) are honoured. Default mode only
for G4.
"""

from __future__ import annotations

from typing import Any

from glances.outputs.curses_renderer_v5 import _LEVEL_TO_ROLE, Cell, ColorRole, Row, title_role

# Block width capped at the v5 left-sidebar maximum (34 chars).
#     name (_NAME_MAX_WIDTH) + 1 + rx (7) + 1 + wx (7) = name + 16
# Set to 18 → block fits exactly in 34.
_NAME_MAX_WIDTH = 18
_RATE_COL_WIDTH = 7


def _format_byte_rate(bytes_per_sec: Any) -> str:
    """Bytes/s → human-readable, K/M/G/T scaled, no /s suffix.

    v4 parity: the header line carries the ``R/s`` / ``W/s`` labels, so
    each cell just shows the magnitude. Sub-K values stay raw (e.g.
    ``0B``, ``800B``).
    """
    try:
        bytes_value = float(bytes_per_sec)
    except (TypeError, ValueError):
        return "-"
    for symbol, threshold in (
        ("T", 1_099_511_627_776),
        ("G", 1_073_741_824),
        ("M", 1_048_576),
        ("K", 1024),
    ):
        if abs(bytes_value) >= threshold:
            return f"{bytes_value / threshold:.1f}{symbol}"
    return f"{int(bytes_value)}B"


def _rate_cell(value: Any, level_entry: dict[str, Any]) -> Cell:
    text = _format_byte_rate(value).rjust(_RATE_COL_WIDTH)
    level = level_entry.get("level") if isinstance(level_entry, dict) else None
    role = _LEVEL_TO_ROLE.get(level, ColorRole.DEFAULT)
    prominent = bool(level_entry.get("prominent")) if isinstance(level_entry, dict) else False
    return Cell(text=text, color=role, prominent=prominent)


def _format_disk_name(name: str) -> str:
    if len(name) > _NAME_MAX_WIDTH:
        return "_" + name[-(_NAME_MAX_WIDTH - 1) :]
    return name.ljust(_NAME_MAX_WIDTH)


def render(payload: dict[str, Any], fields_desc: dict[str, dict[str, Any]]) -> list[Row]:
    """Render the diskio plugin's TUI block — mirrors v4 ``diskio.msg_curse``."""
    header_row = Row(
        cells=[
            Cell(text="DISK I/O".ljust(_NAME_MAX_WIDTH), color=title_role(payload), bold=True),
            Cell(text="R/s".rjust(_RATE_COL_WIDTH), color=ColorRole.HEADER, bold=True),
            Cell(text="W/s".rjust(_RATE_COL_WIDTH), color=ColorRole.HEADER, bold=True),
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

    for item in sorted(items, key=lambda it: str(it.get("disk_name", ""))):
        if not isinstance(item, dict):
            continue
        # Skip disks with no rate yet — cycle 1 strips read_bytes/write_bytes.
        if "read_bytes" not in item or "write_bytes" not in item:
            continue

        name = str(item.get("disk_name") or "")
        if not name:
            continue
        disk_levels = levels_index.get(name) if isinstance(levels_index, dict) else None
        if not isinstance(disk_levels, dict):
            disk_levels = {}

        rows.append(
            Row(
                cells=[
                    Cell(text=_format_disk_name(name)),
                    _rate_cell(item.get("read_bytes"), disk_levels.get("read_bytes", {})),
                    _rate_cell(item.get("write_bytes"), disk_levels.get("write_bytes", {})),
                ]
            )
        )

    return rows

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
- Disks with no rate yet (cycle 1, value ``None``) are skipped — avoids
  a startup wall of ``-`` placeholders.
- Long disk names are tail-truncated with a leading underscore.

Three data modes, v4 precedence (``diskio/__init__.py:241-255``): ``B``
(IOR/s + IOW/s) wins over ``L`` / ``--diskio-latency`` (ms/opR + ms/opW),
which wins over the default byte rates. ``T`` folds the two columns into
one sum -- a v5 addition, network's ``T`` applied to disks -- except in
latency mode: the sum of two per-operation means is not a latency.
``U`` swaps the rates for the counters since boot -- network's
``network_cumul`` applied to disks, a v5 addition -- in byte and IOPS
mode alike, and not in latency mode, which has no counter to show.
"""

from __future__ import annotations

from typing import Any

from glances.outputs.curses_renderer_v5 import _LEVEL_TO_ROLE, Cell, ColorRole, Row, field_label

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


def _format_count_rate(ops_per_sec: Any) -> str:
    """Operations/s → human-readable, K/M/G scaled, no unit suffix.

    The `B` hotkey's IOPS mode. Same shape as `_format_byte_rate` above but
    decimal-scaled and unitless: these are counts, not bytes, so 1000 is the
    step and there is no `B` to append (v4 `auto_unit`, no unit argument,
    `diskio/__init__.py:272`).
    """
    try:
        value = float(ops_per_sec)
    except (TypeError, ValueError):
        return "-"
    for symbol, threshold in (("G", 1_000_000_000), ("M", 1_000_000), ("K", 1_000)):
        if abs(value) >= threshold:
            return f"{value / threshold:.1f}{symbol}"
    return f"{int(value)}"


def _rate_cell(value: Any, level_entry: dict[str, Any], iops: bool = False) -> Cell:
    # IOPS are a plain count, so they take the generic auto-unit rather than
    # the byte formatter -- v4 `auto_unit(read_count_rate_per_sec)` with no
    # unit suffix (`diskio/__init__.py:272`).
    text = (_format_count_rate(value) if iops else _format_byte_rate(value)).rjust(_RATE_COL_WIDTH)
    level = level_entry.get("level") if isinstance(level_entry, dict) else None
    role = _LEVEL_TO_ROLE.get(level, ColorRole.DEFAULT)
    prominent = bool(level_entry.get("prominent")) if isinstance(level_entry, dict) else False
    return Cell(text=text, color=role, prominent=prominent)


def _format_disk_name(name: str) -> str:
    if len(name) > _NAME_MAX_WIDTH:
        return "_" + name[-(_NAME_MAX_WIDTH - 1) :]
    return name.ljust(_NAME_MAX_WIDTH)


def render(
    payload: dict[str, Any], fields_desc: dict[str, dict[str, Any]], view: dict[str, Any] | None = None
) -> list[Row]:
    """Render the diskio plugin's TUI block — mirrors v4 ``diskio.msg_curse``."""
    # `B` (v4 `_handle_diskio_iops`): operations per second instead of byte
    # rates. Same two columns, different pair of fields -- the labels come
    # from the schema, so swapping the pair swaps the header too.
    iops = bool((view or {}).get("diskio_iops"))
    latency = not iops and bool((view or {}).get("diskio_latency"))
    if iops:
        read_key, write_key = "read_count", "write_count"
    elif latency:
        read_key, write_key = "read_latency", "write_latency"
    else:
        read_key, write_key = "read_bytes", "write_bytes"
    # `_levels` stays keyed by the rate fields, whatever the mode shows.
    level_keys = (read_key, write_key)
    # `U`: the same flag as network's, so one key switches both blocks.
    cumul = not latency and bool((view or {}).get("network_cumul"))
    if cumul:
        read_key, write_key = f"{read_key}_cumul", f"{write_key}_cumul"
    # `T`: the same flag as network's, so one key folds both blocks.
    combined = not latency and bool((view or {}).get("network_sum"))
    # The first header cell is the TUI block title, not a field label -- it
    # stays a literal. The rate columns read their labels from the schema
    # (single source of truth, shared with the WebUI), as network's do.
    header_row = Row(
        cells=[
            Cell(text="DISK I/O".ljust(_NAME_MAX_WIDTH), color=ColorRole.HEADER, bold=True),
            *(
                Cell(
                    text=field_label(fields_desc.get(key, {}), key, prefer_short=True).rjust(_RATE_COL_WIDTH),
                    color=ColorRole.HEADER,
                    bold=True,
                )
                for key in (read_key, write_key)
            ),
        ]
    )
    if combined:
        # Widened to the two columns it replaces, so the block keeps its width
        # (network's `Rx+Tx/s` does the same).
        header_row = Row(
            cells=[
                header_row.cells[0],
                Cell(
                    text=(("IOR+W" if iops else "R+W") + ("" if cumul else "/s")).rjust(_RATE_COL_WIDTH * 2 + 1),
                    color=ColorRole.HEADER,
                    bold=True,
                ),
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
        # hide_zero display filter (design §5.1) — sticky state computed and
        # reduced to this one boolean by the model (issue #1787 v4 parity).
        if item.get("hidden") is True:
            continue
        # Skip disks with no rate yet — cycle 1 sets read_bytes/write_bytes to None.
        if item.get(read_key) is None or item.get(write_key) is None:
            continue

        name = str(item.get("disk_name") or "")
        if not name:
            continue
        disk_levels = levels_index.get(name) if isinstance(levels_index, dict) else None
        if not isinstance(disk_levels, dict):
            disk_levels = {}
        # `alias` (design §5.5, v4 parity `diskio/__init__.py:262`) replaces
        # the raw disk name in the display only — `_levels` above stays
        # keyed by the raw `name`.
        display_name = str(item.get("alias") or name)

        # Latencies are unitless ms counts, formatted like IOPS (v4
        # `auto_unit(..., low_precision=True)`, `diskio/__init__.py:288`).
        count = iops or latency
        if combined:
            total = float(item[read_key]) + float(item[write_key])
            # No threshold colour: each field has its own level and a sum
            # belongs to neither (network's `T` cell is plain too).
            text = _format_count_rate(total) if iops else _format_byte_rate(total)
            value_cells = [Cell(text=text.rjust(_RATE_COL_WIDTH * 2 + 1))]
        else:
            value_cells = [
                _rate_cell(item.get(read_key), disk_levels.get(level_keys[0], {}), iops=count),
                _rate_cell(item.get(write_key), disk_levels.get(level_keys[1], {}), iops=count),
            ]

        rows.append(
            Row(
                cells=[Cell(text=_format_disk_name(display_name)), *value_cells],
                item_start=True,
            )
        )

    return rows

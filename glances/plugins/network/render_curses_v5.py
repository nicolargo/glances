#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — TUI curses renderer for the network plugin.

Replicates v4's ``network.msg_curse()``
(`glances/plugins/network/__init__.py::msg_curse`): a header line + one
row per active interface, with Rx/s + Tx/s rate columns.

Reference layout (default — rate display, bits/s, two columns):

    NETWORK              Rx/s    Tx/s
    eth0                1.1Mb  256.2Kb
    wlp0s20f3          43.9Kb  11.7Kb
    lo                     0b      0b

- Header: ``NETWORK`` (HEADER) + ``Rx/s`` + ``Tx/s`` (right-aligned).
- One row per interface filtered by ``is_up`` and rate availability.
- Rate values: bytes/s × 8 → bits/s, with K/M/G/T auto-scaling and a ``b``
  suffix (v4 ``auto_unit(int(value * 8)) + 'b'``). Sub-K values stay raw
  (e.g. ``0b``, ``800b``).
- Long interface names are tail-truncated with a leading underscore.
- Color of each rate cell from ``_levels[interface_name][bytes_recv|bytes_sent]``.

TODO(G2+): plumb ``max_width`` and ``args`` (``--byte``, ``--network-cumul``,
``--network-sum``) from the painter so this renderer can replicate every
v4 display mode. For G1 we hardcode ``name_max_width=20`` and the
rate-bits-two-column mode (v4 default).
"""

from __future__ import annotations

from typing import Any

from glances.outputs.curses_renderer_v5 import _LEVEL_TO_ROLE, Cell, ColorRole, Row, title_role

# Hardcoded for G1 — must match the v5 left sidebar max width.
# Painter caps the sidebar at 34 chars (`_left_sidebar_max_width=34`,
# mirrors v4) and inserts a 1-space gap between cells. Total block width:
#     name (_NAME_MAX_WIDTH) + 1 + rx (7) + 1 + tx (7) = _NAME_MAX_WIDTH + 16
# Set to 18 so the natural block width is exactly 34 and the Tx/s column
# is not clipped on the right.
# TODO(G2+): once render() accepts `max_width`, compute dynamically as
#     max_width - 2 (gaps) - 2 * _RATE_COL_WIDTH.
_NAME_MAX_WIDTH = 18
_RATE_COL_WIDTH = 7


def _format_bit_rate(bytes_per_sec: Any) -> str:
    """Bytes/s → human-readable bits/s string (v4 ``auto_unit(... ) + 'b'``).

    Multiplies by 8, scales to K/M/G/T with one decimal, suffix ``b``.
    Sub-K bits show as raw ``Nb`` (v4 ``min_symbol='K'``).
    """
    try:
        bits = float(bytes_per_sec) * 8.0
    except (TypeError, ValueError):
        return "-"
    for symbol, threshold in (
        ("T", 1_099_511_627_776),
        ("G", 1_073_741_824),
        ("M", 1_048_576),
        ("K", 1024),
    ):
        if abs(bits) >= threshold:
            return f"{bits / threshold:.1f}{symbol}b"
    return f"{int(bits)}b"


def _rate_cell(value: Any, level_entry: dict[str, Any]) -> Cell:
    text = _format_bit_rate(value).rjust(_RATE_COL_WIDTH) if value is not None else "-".rjust(_RATE_COL_WIDTH)
    level = level_entry.get("level") if isinstance(level_entry, dict) else None
    role = _LEVEL_TO_ROLE.get(level, ColorRole.DEFAULT)
    prominent = bool(level_entry.get("prominent")) if isinstance(level_entry, dict) else False
    return Cell(text=text, color=role, prominent=prominent)


def _format_if_name(name: str) -> str:
    """Truncate / pad an interface name to ``_NAME_MAX_WIDTH`` (v4 parity)."""
    if len(name) > _NAME_MAX_WIDTH:
        return "_" + name[-(_NAME_MAX_WIDTH - 1) :]
    return name.ljust(_NAME_MAX_WIDTH)


def render(payload: dict[str, Any], fields_desc: dict[str, dict[str, Any]]) -> list[Row]:
    """Render the network plugin's TUI block — mirrors v4 ``network.msg_curse``."""
    header_row = Row(
        cells=[
            Cell(text="NETWORK".ljust(_NAME_MAX_WIDTH), color=title_role(payload), bold=True),
            Cell(text="Rx/s".rjust(_RATE_COL_WIDTH), color=ColorRole.HEADER, bold=True),
            Cell(text="Tx/s".rjust(_RATE_COL_WIDTH), color=ColorRole.HEADER, bold=True),
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

    for item in items:
        if not isinstance(item, dict):
            continue
        # v4 fidelity: skip interfaces in the down state (issue #765).
        if item.get("is_up") is False:
            continue
        # Skip first-cycle interfaces — rate fields are absent until the
        # base class has two samples (cf. `_transform_gauge`).
        if "bytes_recv" not in item or "bytes_sent" not in item:
            continue

        name = str(item.get("interface_name") or "")
        if_levels = levels_index.get(name) if isinstance(levels_index, dict) else None
        if not isinstance(if_levels, dict):
            if_levels = {}

        rows.append(
            Row(
                cells=[
                    Cell(text=_format_if_name(name)),
                    _rate_cell(item.get("bytes_recv"), if_levels.get("bytes_recv", {})),
                    _rate_cell(item.get("bytes_sent"), if_levels.get("bytes_sent", {})),
                ]
            )
        )

    return rows

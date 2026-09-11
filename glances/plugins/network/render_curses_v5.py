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
  (e.g. ``0b``, ``800b``). With ``view["byte"]`` truthy (``--byte``), rates
  stay in bytes/s and drop the ``b`` suffix (v4 ``network/__init__.py:273``).
- Long interface names are tail-truncated with a leading underscore.
- Color of each rate cell from ``_levels[interface_name][bytes_recv|bytes_sent]``.

TODO(G2+): plumb ``max_width`` and ``args`` (``--network-cumul``,
``--network-sum``) from the painter so this renderer can replicate every
v4 display mode. For G1 we hardcode ``name_max_width=20`` and the
rate-bits-two-column mode (v4 default).
"""

from __future__ import annotations

from typing import Any

from glances.outputs.curses_renderer_v5 import _LEVEL_TO_ROLE, Cell, ColorRole, Row, field_label

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


def _format_rate(bytes_per_sec: Any, byte: bool = False) -> str:
    """Bytes/s → human-readable rate string (v4 ``auto_unit(...) [+ 'b']``).

    Default (``byte=False``): multiplies by 8, scales to K/M/G/T with one
    decimal, suffix ``b``. Sub-K bits show as raw ``Nb`` (v4
    ``min_symbol='K'``).

    With ``byte=True`` (``--byte``, v4 ``network/__init__.py:273``): no ×8,
    same K/M/G/T scaling, no unit suffix.
    """
    try:
        value = float(bytes_per_sec) if byte else float(bytes_per_sec) * 8.0
    except (TypeError, ValueError):
        return "-"
    suffix = "" if byte else "b"
    for symbol, threshold in (
        ("T", 1_099_511_627_776),
        ("G", 1_073_741_824),
        ("M", 1_048_576),
        ("K", 1024),
    ):
        if abs(value) >= threshold:
            return f"{value / threshold:.1f}{symbol}{suffix}"
    return f"{int(value)}{suffix}"


def _rate_cell(value: Any, level_entry: dict[str, Any], byte: bool = False) -> Cell:
    text = _format_rate(value, byte).rjust(_RATE_COL_WIDTH) if value is not None else "-".rjust(_RATE_COL_WIDTH)
    level = level_entry.get("level") if isinstance(level_entry, dict) else None
    role = _LEVEL_TO_ROLE.get(level, ColorRole.DEFAULT)
    prominent = bool(level_entry.get("prominent")) if isinstance(level_entry, dict) else False
    return Cell(text=text, color=role, prominent=prominent)


def _format_if_name(name: str) -> str:
    """Truncate / pad an interface name to ``_NAME_MAX_WIDTH`` (v4 parity)."""
    if len(name) > _NAME_MAX_WIDTH:
        return "_" + name[-(_NAME_MAX_WIDTH - 1) :]
    return name.ljust(_NAME_MAX_WIDTH)


def render(
    payload: dict[str, Any], fields_desc: dict[str, dict[str, Any]], view: dict[str, Any] | None = None
) -> list[Row]:
    """Render the network plugin's TUI block — mirrors v4 ``network.msg_curse``."""
    byte = bool((view or {}).get("byte"))
    # The first header cell is the TUI block title, not a field label — it
    # stays a literal. The value columns read their labels from the schema
    # (single source of truth, shared with the WebUI).
    header_row = Row(
        cells=[
            Cell(text="NETWORK".ljust(_NAME_MAX_WIDTH), color=ColorRole.HEADER, bold=True),
            *(
                Cell(
                    text=field_label(fields_desc.get(key, {}), key, prefer_short=True).rjust(_RATE_COL_WIDTH),
                    color=ColorRole.HEADER,
                    bold=True,
                )
                for key in ("bytes_recv", "bytes_sent")
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

    for item in items:
        if not isinstance(item, dict):
            continue
        # v4 fidelity: skip interfaces in the down state (issue #765).
        if item.get("is_up") is False:
            continue
        # hide_zero display filter (design §5.1) — sticky state computed and
        # reduced to this one boolean by the model (issue #1787 v4 parity).
        if item.get("hidden") is True:
            continue
        # Skip first-cycle interfaces — rate fields are None until the
        # base class has two samples (cf. `_transform_gauge`).
        if item.get("bytes_recv") is None or item.get("bytes_sent") is None:
            continue

        name = str(item.get("interface_name") or "")
        if_levels = levels_index.get(name) if isinstance(levels_index, dict) else None
        if not isinstance(if_levels, dict):
            if_levels = {}
        # `alias` (design §5.5, v4 parity `network/__init__.py:262`) replaces
        # the raw interface name in the display only — `_levels` above stays
        # keyed by the raw `name`.
        display_name = str(item.get("alias") or name)

        rows.append(
            Row(
                cells=[
                    Cell(text=_format_if_name(display_name)),
                    _rate_cell(item.get("bytes_recv"), if_levels.get("bytes_recv", {}), byte),
                    _rate_cell(item.get("bytes_sent"), if_levels.get("bytes_sent", {}), byte),
                ],
                item_start=True,
            )
        )

    return rows

#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — TUI curses renderer for the zfs plugin.

One compact row per pool:

    POOL       STATE   CAP FRAG ERR
    zroot      ONLINE  96%  34%   0
      └─ One or more devices are configured to use a non-native block size.

The block is capped at the 34-character left-sidebar maximum. ``[zfs]
show_datasets`` adds one row per dataset, using the full 34-character width
for name + used + available.
"""

from __future__ import annotations

import re
from typing import Any

from glances.outputs.curses_formatters import format_value
from glances.outputs.curses_renderer import _LEVEL_TO_ROLE, Cell, ColorRole, Row, field_label

_LEFT_SIDEBAR_MAX_WIDTH = 34
_NAME_WIDTH = 10
_STATE_WIDTH = 8
_CAP_WIDTH = 4
_FRAG_WIDTH = 4
_ERR_WIDTH = 3

_DATASET_NAME_WIDTH = 18
_DATASET_USED_WIDTH = 7
_DATASET_AVAIL_WIDTH = 7

_STATUS_PREFIX = '  └─ '
_STATUS_MAX_CHARS = 256
_ERROR_FIELDS = ('read_errors', 'write_errors', 'checksum_errors', 'error_count', 'scan_errors')
_LEVEL_ORDER = ('ok', 'careful', 'warning', 'critical')


def _first_sentence(text: Any) -> str:
    """Return the first sentence with whitespace normalized."""
    normalized = ' '.join(str(text or '').split())
    if not normalized:
        return ''
    match = re.search(r'[.!?:](?=\s|$)', normalized)
    return normalized[: match.end()] if match else normalized


def _truncate(text: str, limit: int) -> str:
    """Truncate to ``limit`` characters, adding an ellipsis if needed."""
    if limit <= 0:
        return ''
    if len(text) <= limit:
        return text
    if limit <= 3:
        return text[:limit]
    return text[: limit - 3] + '...'


def _status_text(status: Any, limit: int = _STATUS_MAX_CHARS) -> str:
    """Return the first sentence of a status message, capped at ``limit``."""
    return _truncate(_first_sentence(status), limit)


def _format_bytes(value: Any) -> str:
    if value is None:
        return '-'
    return format_value(value, {'unit': 'bytes'})


def _entry(levels: dict[str, Any], name: str, field: str) -> dict[str, Any]:
    item_levels = levels.get(name, {}) if isinstance(levels, dict) else {}
    entry = item_levels.get(field, {}) if isinstance(item_levels, dict) else {}
    return entry if isinstance(entry, dict) else {}


def _role(entry: dict[str, Any]) -> tuple[ColorRole, bool]:
    return _LEVEL_TO_ROLE.get(entry.get('level'), ColorRole.DEFAULT), bool(entry.get('prominent'))


def _worst_error_entry(levels: dict[str, Any], name: str) -> dict[str, Any]:
    worst = {}
    worst_rank = -1
    for field in _ERROR_FIELDS:
        entry = _entry(levels, name, field)
        level = entry.get('level')
        if level in _LEVEL_ORDER:
            rank = _LEVEL_ORDER.index(level)
            if rank > worst_rank:
                worst = entry
                worst_rank = rank
    return worst


def _header(schema: dict[str, dict[str, Any]]) -> Row:
    def label(field: str, width: int) -> str:
        return field_label(schema.get(field, {}), field, prefer_short=True)[:width].rjust(width)

    return Row(
        cells=[
            Cell(text='POOL'.ljust(_NAME_WIDTH), color=ColorRole.HEADER, bold=True),
            Cell(text=label('state', _STATE_WIDTH), color=ColorRole.HEADER, bold=True),
            Cell(text=label('capacity', _CAP_WIDTH), color=ColorRole.HEADER, bold=True),
            Cell(text=label('fragmentation', _FRAG_WIDTH), color=ColorRole.HEADER, bold=True),
            Cell(text=label('read_errors', _ERR_WIDTH), color=ColorRole.HEADER, bold=True),
        ]
    )


def render(payload: dict[str, Any], fields_desc: dict[str, dict[str, Any]] | None = None, view=None) -> list[Row]:
    """Render the ZFS block (one row per pool, plus optional detail rows)."""
    items = payload.get('data') if isinstance(payload, dict) else None
    if not isinstance(items, list) or not items:
        return []

    schema = fields_desc or {}
    levels = payload.get('_levels') if isinstance(payload.get('_levels'), dict) else {}
    show_datasets = bool(payload.get('show_datasets'))

    rows: list[Row] = [_header(schema)]
    for item in sorted(items, key=lambda it: str(it.get('name', ''))):
        if not isinstance(item, dict):
            continue
        name = str(item.get('name') or '')
        if not name:
            continue

        state_entry = _entry(levels, name, 'state')
        state_role, state_prominent = _role(state_entry)
        cap_role, cap_prominent = _role(_entry(levels, name, 'capacity'))
        error_entry = _worst_error_entry(levels, name)
        error_role, error_prominent = _role(error_entry)

        state = str(item.get('state') or '')[:_STATE_WIDTH].rjust(_STATE_WIDTH)
        capacity = f"{item.get('capacity') or 0:.0f}%".rjust(_CAP_WIDTH)
        fragmentation = f"{item.get('fragmentation') or 0:.0f}%".rjust(_FRAG_WIDTH)
        errors = (
            int(item.get('read_errors') or 0)
            + int(item.get('write_errors') or 0)
            + int(item.get('checksum_errors') or 0)
        )
        error_text = str(errors)[-_ERR_WIDTH:].rjust(_ERR_WIDTH)

        rows.append(
            Row(
                cells=[
                    Cell(text=name[:_NAME_WIDTH].ljust(_NAME_WIDTH)),
                    Cell(text=state, color=state_role, prominent=state_prominent),
                    Cell(text=capacity, color=cap_role, prominent=cap_prominent),
                    Cell(text=fragmentation),
                    Cell(text=error_text, color=error_role, prominent=error_prominent),
                ],
                item_start=True,
            )
        )

        status = item.get('status')
        if status:
            text = _status_text(status, _STATUS_MAX_CHARS)
            text = _truncate(text, max(_LEFT_SIDEBAR_MAX_WIDTH - len(_STATUS_PREFIX), 0))
            if text:
                rows.append(Row(cells=[Cell(text=_STATUS_PREFIX + text, color=ColorRole.WARNING, prominent=False)]))

        if show_datasets:
            for dataset in item.get('datasets') or []:
                if not isinstance(dataset, dict):
                    continue
                ds_name = str(dataset.get('name') or '')
                if not ds_name:
                    continue
                label = _STATUS_PREFIX + ds_name
                label = label[:_DATASET_NAME_WIDTH].ljust(_DATASET_NAME_WIDTH)
                rows.append(
                    Row(
                        cells=[
                            Cell(text=label),
                            Cell(text=_format_bytes(dataset.get('used')).rjust(_DATASET_USED_WIDTH)),
                            Cell(text=_format_bytes(dataset.get('available')).rjust(_DATASET_AVAIL_WIDTH)),
                        ]
                    )
                )

    return rows

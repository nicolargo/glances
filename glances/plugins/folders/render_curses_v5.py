#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — TUI curses renderer for the folders plugin.

Replicates v4 ``folders.msg_curse()``: a single ``FOLDERS`` title line
(no column headers — v4 has none either), then one row per monitored
folder showing its (possibly left-truncated) path and its size.

Reference layout (v4 ``glances/plugins/folders/__init__.py:132-169``):

    FOLDERS
    /tmp                    125.0M
    _os/nicolargo/Videos     17.0G
    /nonexisting            ?     -

- Path: left-justified, truncated **from the left** (tail kept) with a
  leading ``_`` when longer than the name column — v4 parity, deliberate:
  the tail of a path is usually more identifying than the head.
- Size: right-aligned on 9 chars via an ``auto_unit``-style formatter;
  prefixed with ``?`` (consuming one of the 9 chars) when ``errno != 0``.
- Colour: driven by ``payload["_levels"][path]["size"]["level"]`` — the
  size ladder. When the folder could not be read at all (``errno != 0``),
  the model emits NO ``_levels`` entry for it (see
  ``model_v5.PluginModel._folder_level`` — v4 parity: no alert, no
  history, no action dispatch), so the renderer renders that cell
  ``bold=True`` with ``ColorRole.DEFAULT`` — v4's ``curses.A_BOLD``, no
  colour (``glances/outputs/glances_colors.py:167``).

``view`` carries no behaviour here (no sort key, no toggle) — accepted
only so the discovery signature matches the group's common contract
(design §3, ``glances/outputs/curses_renderer_v5.py::_accepts_view``).
"""

from __future__ import annotations

from typing import Any

from glances.outputs.curses_formatters_v5 import format_value
from glances.outputs.curses_renderer_v5 import _LEVEL_TO_ROLE, Cell, ColorRole, Row

# v4 ``name_max_width = max_width - 7``, with ``max_width`` fixed at 31 so
# the rendered block fits exactly inside the v5 LEFT-sidebar's 34-char
# budget once the renderer's automatic 1-space cell separator is added:
#   name (_NAME_MAX_WIDTH=24) + 1 separator + size (_SIZE_COL_WIDTH=9) = 34
_MAX_WIDTH = 31
_NAME_MAX_WIDTH = _MAX_WIDTH - 7
_SIZE_COL_WIDTH = 9


def _format_bytes(value: Any) -> str:
    if value is None:
        return "-"
    return format_value(value, {"unit": "bytes"})


def _format_path(path: str) -> str:
    """Truncate from the LEFT (keep the tail) — v4 parity, deliberate."""
    if len(path) > _NAME_MAX_WIDTH:
        return ("_" + path[-(_NAME_MAX_WIDTH - 1) :]).ljust(_NAME_MAX_WIDTH)
    return path.ljust(_NAME_MAX_WIDTH)


def _size_cell(item: dict[str, Any], level_entry: dict[str, Any]) -> Cell:
    size = item.get("size")
    errno = item.get("errno") or 0
    text = _format_bytes(size)
    rendered = ("?" + text.rjust(_SIZE_COL_WIDTH - 1)) if errno != 0 else text.rjust(_SIZE_COL_WIDTH)
    if errno != 0:
        # v4 parity: a broken folder short-circuits the size ladder and
        # gets no _levels entry (see model_v5._folder_level) — render
        # bold/no-colour (v4's curses.A_BOLD), never alert-coloured.
        return Cell(text=rendered, color=ColorRole.DEFAULT, bold=True)
    level = level_entry.get("level") if isinstance(level_entry, dict) else None
    role = _LEVEL_TO_ROLE.get(level, ColorRole.DEFAULT)
    prominent = bool(level_entry.get("prominent")) if isinstance(level_entry, dict) else False
    return Cell(text=rendered, color=role, prominent=prominent)


def render(
    payload: dict[str, Any],
    fields_desc: dict[str, dict[str, Any]] | None = None,
    view: dict[str, Any] | None = None,
) -> list[Row]:
    """Render the folders plugin's TUI block — mirrors v4 ``folders.msg_curse``."""
    items = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        return []
    items = [i for i in items if isinstance(i, dict)]
    if not items:
        return []

    raw_levels = payload.get("_levels")
    levels_index = raw_levels if isinstance(raw_levels, dict) else {}

    rows: list[Row] = [Row(cells=[Cell(text="FOLDERS".ljust(_NAME_MAX_WIDTH), color=ColorRole.HEADER, bold=True)])]
    for item in items:
        path = str(item.get("path") or "")
        item_levels = levels_index.get(path)
        size_level = item_levels.get("size", {}) if isinstance(item_levels, dict) else {}
        rows.append(Row(cells=[Cell(text=_format_path(path)), _size_cell(item, size_level)], item_start=True))
    return rows

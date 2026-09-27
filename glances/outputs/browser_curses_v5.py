#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — the TUI browser: the server list, v4's layout in the TUI's colours.

Design: ``docs/superpowers/specs/2026-09-27-glances-v5-phase3-design.md`` §4.5
(chantier P3-4). v4: ``glances/outputs/glances_curses_browser.py``.

- A title line, the count per status, then a table: NAME (the alias, else
  the name), STATUS, and one column per ``[serverlist] columns`` entry, its
  header on two rows (plugin, then field) as in v4.
- Colours are the TUI's: a value takes its level's colour (the server's
  ``_levels``), a status its own (ONLINE green, PROTECTED magenta, OFFLINE
  red, UNSUPPORTED blue).
- Keys, as in v4: UP/DOWN, ENTER opens the server, ``1`` list order, ``2``
  sorted by status, ``3`` reversed, ``q``/ESC quits.

``build_lines`` is pure (no curses), so the layout is tested without a
terminal; ``BrowserTui`` only paints it and reads keys.
"""

from __future__ import annotations

import curses
from typing import Any

from glances.outputs.curses_renderer_v5 import _LEVEL_TO_ROLE, Cell, ColorRole
from glances.outputs.glances_curses_v5 import TuiV5, _attr_for, _init_colors, _set_style
from glances.servers_list_v5 import OFFLINE, ONLINE, PROTECTED, UNKNOWN, UNSUPPORTED, Column, ServerEntry

_STATUS_ROLE = {
    ONLINE: ColorRole.OK,
    PROTECTED: ColorRole.WARNING,
    OFFLINE: ColorRole.CRITICAL,
    UNSUPPORTED: ColorRole.CAREFUL,
    UNKNOWN: ColorRole.DEFAULT,
}
# v4's sort by status (keys `2` and `3`): the servers that need a look first.
_STATUS_ORDER = {UNKNOWN: 0, OFFLINE: 1, PROTECTED: 2, UNSUPPORTED: 3, ONLINE: 4}

_NAME_WIDTH = 16
_STATUS_WIDTH = 11
_MIN_COLUMN = 6
_MAX_COLUMN = 24
_GAP = 2
# Rows above the table: title, counts, the two header rows.
_TOP_ROWS = 4


def order_servers(servers: list[ServerEntry], order: str) -> list[ServerEntry]:
    """`list` (as configured), `status` (v4 key `2`) or `status-reversed` (key `3`)."""
    if order == "list":
        return list(servers)
    return sorted(servers, key=lambda s: _STATUS_ORDER.get(s.status, 99), reverse=order == "status-reversed")


def _text(value: Any) -> str:
    if value is None:
        return "?"
    if isinstance(value, float):
        return f"{value:.1f}"
    return str(value)


def _column_width(column: Column, servers: list[ServerEntry]) -> int:
    header = f"{column.field} {column.key}" if column.key else column.field
    values = [_text(s.columns[column.label]["value"]) for s in servers if column.label in s.columns]
    return max(_MIN_COLUMN, min(_MAX_COLUMN, max([len(header), len(column.plugin), *map(len, values)])))


def _pad(text: str, width: int) -> str:
    return text[:width].ljust(width + _GAP)


def build_lines(
    servers: list[ServerEntry], columns: list[Column], cursor: int, message: str | None = None
) -> list[list[Cell]]:
    """The whole screen, top to bottom, as rows of cells (already padded)."""
    count = len(servers)
    title = (
        "No Glances server available" if count == 0 else f"{count} Glances server{'s' if count > 1 else ''} available"
    )
    lines = [[Cell(text=title, color=ColorRole.HEADER)]]
    counts: dict[str, int] = {}
    for server in servers:
        counts[server.status] = counts.get(server.status, 0) + 1
    lines.append(
        [
            Cell(text=f"{status}: {n}  ", color=_STATUS_ROLE.get(status, ColorRole.DEFAULT))
            for status, n in counts.items()
        ]
    )
    if message:
        lines[1].append(Cell(text=message, color=ColorRole.CRITICAL))
    if not servers:
        return lines

    widths = [_column_width(c, servers) for c in columns]
    plugins = [Cell(text=" " * (2 + _NAME_WIDTH + _GAP + _STATUS_WIDTH + _GAP))]
    fields = [
        Cell(text="  "),
        Cell(text=_pad("NAME", _NAME_WIDTH), bold=True),
        Cell(text=_pad("STATUS", _STATUS_WIDTH), bold=True),
    ]
    for column, width in zip(columns, widths):
        plugins.append(Cell(text=_pad(column.plugin.upper(), width), bold=True))
        header = f"{column.field} {column.key}" if column.key else column.field
        fields.append(Cell(text=_pad(header.upper(), width), bold=True))
    lines += [plugins, fields]

    for i, server in enumerate(servers):
        row = [
            Cell(text="> " if i == cursor else "  ", bold=True),
            Cell(text=_pad(server.alias or server.name, _NAME_WIDTH)),
            Cell(text=_pad(server.status, _STATUS_WIDTH), color=_STATUS_ROLE.get(server.status, ColorRole.DEFAULT)),
        ]
        for column, width in zip(columns, widths):
            cell = server.columns.get(column.label)
            role = _LEVEL_TO_ROLE.get((cell or {}).get("level") or "", ColorRole.DEFAULT)
            row.append(Cell(text=_pad(_text(cell["value"]) if cell else "?", width), color=role))
        lines.append(row)
    return lines


class BrowserTui:
    """Paints the list and returns the server the user opens, or None when they quit."""

    # The list follows the poller: repaint this often even without a key.
    _REPAINT_MS = 1000

    # The TUI's key reader, borrowed as is: ncurses may hand an arrow key
    # over as a bare 27 followed by its sequence, and 27 means quit here too.
    _ESCAPE_SEQUENCES = TuiV5._ESCAPE_SEQUENCES
    _ESCAPE_TAIL_MAX = TuiV5._ESCAPE_TAIL_MAX
    _unget = staticmethod(TuiV5._unget)
    _read_key = TuiV5._read_key

    def __init__(self, poller: Any, theme: str = "dark", disable_bold: bool = False, disable_bg: bool = False) -> None:
        self._poller = poller
        self._theme = theme
        self._bold = not disable_bold
        self._background = not disable_bg
        self.cursor = 0
        self.order = "list"

    def select(self, message: str | None = None) -> ServerEntry | None:
        """Show the list until ENTER (that server) or `q`/ESC (None). `message`: why the last one did not open."""
        result: list[ServerEntry | None] = [None]

        def loop(stdscr: Any) -> None:
            result[0] = self._loop(stdscr, message)

        curses.wrapper(loop)
        return result[0]

    def handle_key(self, key: int, servers: list[ServerEntry]) -> str | None:
        """`"open"`, `"quit"` or None. Pure, like the TUI's `_handle_key`."""
        if key in (27, ord("q")):
            return "quit"
        if key in (curses.KEY_ENTER, 10, 13) and servers:
            return "open"
        if key == curses.KEY_UP:
            self.cursor = max(0, self.cursor - 1)
        elif key == curses.KEY_DOWN:
            self.cursor = min(len(servers) - 1, self.cursor + 1) if servers else 0
        elif key in (ord("1"), ord("2"), ord("3")):
            self.order = {ord("1"): "list", ord("2"): "status", ord("3"): "status-reversed"}[key]
            self.cursor = 0
        return None

    def _loop(self, stdscr: Any, message: str | None) -> ServerEntry | None:
        _init_colors(self._theme)
        _set_style(bold=self._bold, background=self._background)
        try:
            curses.curs_set(0)
        except curses.error:
            pass
        while True:
            servers = order_servers(self._poller.servers, self.order)
            self.cursor = min(self.cursor, max(0, len(servers) - 1))
            self._paint(stdscr, build_lines(servers, self._poller.columns, self.cursor, message))
            # `_read_key` leaves the window blocking: re-arm the repaint timeout.
            stdscr.timeout(self._REPAINT_MS)
            action = self.handle_key(self._read_key(stdscr), servers)
            if action == "quit":
                return None
            if action == "open":
                return servers[self.cursor]

    def _paint(self, stdscr: Any, lines: list[list[Cell]]) -> None:
        height, width = stdscr.getmaxyx()
        stdscr.erase()
        # Scroll the table so the cursor stays on screen.
        table = lines[_TOP_ROWS:]
        room = max(1, height - _TOP_ROWS)
        first = max(0, self.cursor - room + 1)
        for y, row in enumerate(lines[:_TOP_ROWS] + table[first : first + room]):
            x = 0
            for cell in row:
                if x >= width - 1 or y >= height:
                    break
                try:
                    stdscr.addnstr(y, x, cell.text, width - 1 - x, _attr_for(cell))
                except curses.error:
                    pass
                x += len(cell.text)
        stdscr.refresh()

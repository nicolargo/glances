#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — curses TUI thread.

A `threading.Thread` runs the curses event loop independently of the
asyncio scheduler (architecture §1.4). Each cycle:

    1. Build a Frame from a lockless store snapshot + alert history.
    2. Paint the Frame to stdscr via `_paint`.
    3. Poll a keypress (`q` / `ESC` → stop), refresh.
    4. Sleep `refresh_interval`.

A `threading.Event` is the shutdown channel; the main asyncio task sets
it in its `finally` clause to stop the thread cleanly.
"""

from __future__ import annotations

import curses
import logging
import threading
import time
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from glances.outputs.curses_renderer_v5 import (
    Cell,
    ColorRole,
    Frame,
    build_frame,
)

if TYPE_CHECKING:
    from glances.alerts_v5 import GlancesAlerts
    from glances.config_v5 import GlancesConfigV5
    from glances.stats_store_v5 import StatsStoreV5

logger = logging.getLogger(__name__)


# Map our renderer ColorRole → curses color pair index.
# Filled in `_init_colors` once curses is initialised.
_COLOR_PAIRS: dict[ColorRole, int] = {}


def _safe_curses_wrapper(fn):
    """`curses.wrapper` wrapper — separated so tests can monkeypatch it."""
    curses.wrapper(fn)


class TuiV5(threading.Thread):
    """Curses TUI v5 thread."""

    def __init__(
        self,
        store: StatsStoreV5,
        alerts: GlancesAlerts | None,
        config: GlancesConfigV5,
        registry: list[tuple[str, bool]],
        fields_by_plugin: dict[str, dict[str, dict[str, Any]]],
        refresh_interval: float = 1.0,
        on_quit: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(name="glances-tui-v5", daemon=True)
        self.store = store
        self.alerts = alerts
        self.config = config
        self.registry = registry
        self.fields_by_plugin = fields_by_plugin
        self.refresh_interval = refresh_interval
        # Fired once when the user quits the TUI via `q`/ESC, so the main
        # asyncio loop (uvicorn) can shut down too. Without this, closing
        # the TUI leaves the server running and the shell prompt blocked
        # until Ctrl-C. None = no-op (used in tests).
        self._on_quit = on_quit
        self._stop_event = threading.Event()

    # ----------------------------------------------------------- control

    def stop(self) -> None:
        """Signal the thread to exit at the next loop iteration."""
        self._stop_event.set()

    # ----------------------------------------------------------- run loop

    def run(self) -> None:
        try:
            _safe_curses_wrapper(self._loop)
        except Exception as e:  # pragma: no cover — defensive
            logger.warning("TUI v5 crashed: %s", e)

    def _loop(self, stdscr) -> None:
        _init_colors()
        stdscr.nodelay(True)
        try:
            curses.curs_set(0)
        except curses.error:
            pass

        while not self._stop_event.is_set():
            frame = self._build_frame()
            self._paint(stdscr, frame)
            stdscr.refresh()

            key = stdscr.getch()
            if key in (ord("q"), 27):  # 27 = ESC
                self.stop()
                if self._on_quit is not None:
                    try:
                        self._on_quit()
                    except Exception as e:  # pragma: no cover — defensive
                        logger.warning("TUI on_quit callback failed: %s", e)
                break

            self._sleep_responsive(self.refresh_interval)

    def _sleep_responsive(self, total: float, step: float = 0.05) -> None:
        elapsed = 0.0
        while elapsed < total and not self._stop_event.is_set():
            time.sleep(step)
            elapsed += step

    # ----------------------------------------------------------- helpers

    def _build_frame(self) -> Frame:
        snapshot = self.store.as_dict()
        history = self.alerts.get_history() if self.alerts is not None else []
        return build_frame(
            store_snapshot=snapshot,
            fields_by_plugin=self.fields_by_plugin,
            registry=self.registry,
            alerts_history=history,
        )

    # ----------------------------------------------------------- paint

    def _paint(self, stdscr, frame: Frame) -> None:
        stdscr.erase()
        max_y, max_x = stdscr.getmaxyx()

        left_width = max_x // 2
        right_x = left_width
        right_width = max_x - left_width

        footer_height = len(frame.footer)
        body_height = max(0, max_y - footer_height - 1)

        self._paint_column(stdscr, frame.left, 0, 0, left_width, body_height)
        self._paint_column(stdscr, frame.right, 0, right_x, right_width, body_height)
        self._paint_column(stdscr, frame.footer, max_y - footer_height, 0, max_x, footer_height)

    def _paint_column(self, stdscr, rows, y0: int, x0: int, width: int, height: int) -> None:
        for i, row in enumerate(rows[:height]):
            x = x0
            for cell in row.cells:
                if x >= x0 + width:
                    break
                text = cell.text[: x0 + width - x]
                attr = _attr_for(cell)
                try:
                    stdscr.addstr(y0 + i, x, text, attr)
                except curses.error:
                    break
                x += len(text) + 1  # one-space gap between cells


# ----------------------------------------------------------------- colors


def _init_colors() -> None:
    try:
        if not curses.has_colors():
            return
        curses.start_color()
        try:
            curses.use_default_colors()
        except curses.error:
            pass
        pairs = [
            (ColorRole.OK, curses.COLOR_GREEN),
            (ColorRole.CAREFUL, curses.COLOR_BLUE),
            (ColorRole.WARNING, curses.COLOR_MAGENTA),
            (ColorRole.CRITICAL, curses.COLOR_RED),
            (ColorRole.HEADER, curses.COLOR_CYAN),
        ]
        for i, (role, color) in enumerate(pairs, start=1):
            try:
                curses.init_pair(i, color, -1)
            except curses.error:
                curses.init_pair(i, color, curses.COLOR_BLACK)
            _COLOR_PAIRS[role] = curses.color_pair(i)
        _COLOR_PAIRS[ColorRole.DEFAULT] = curses.color_pair(0)
    except curses.error:
        # curses not initialised (e.g. under unit-test mock or non-TTY).
        # The renderer paints monochrome — that's fine.
        pass


def _attr_for(cell: Cell) -> int:
    attr = _COLOR_PAIRS.get(cell.color, 0)
    if cell.color == ColorRole.HEADER:
        attr |= curses.A_BOLD
    if cell.prominent and cell.color in (ColorRole.WARNING, ColorRole.CRITICAL):
        attr |= curses.A_REVERSE
    return attr

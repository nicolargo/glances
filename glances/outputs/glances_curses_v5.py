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
from dataclasses import dataclass
from itertools import zip_longest
from typing import TYPE_CHECKING, Any

from glances import __version__
from glances.outputs.curses_renderer_v5 import (
    Cell,
    ColorRole,
    Frame,
    PluginBlock,
    Row,
    build_frame,
)
from glances.processes import glances_processes, sort_stats

if TYPE_CHECKING:
    from glances.alerts_v5 import GlancesAlerts
    from glances.config_v5 import GlancesConfigV5
    from glances.stats_store_v5 import StatsStoreV5

logger = logging.getLogger(__name__)


# Map our renderer ColorRole → curses color pair index.
# Filled in `_init_colors` once curses is initialised.
_COLOR_PAIRS: dict[ColorRole, int] = {}


@dataclass
class ViewState:
    """User-toggled TUI view options, driven by hotkeys (v4 parity).

    Only the *boolean view switches* live here. The process **sort key**
    is owned by the ``glances_processes`` engine singleton (set via
    ``set_sort_key``) — duplicating it here would risk drift; the renderer
    reads it back from the engine each frame for the column indicator.

    Defaults mirror v4:
    - ``show_percpu=False`` — top row shows aggregate ``cpu`` (hotkey ``1``).
    - ``process_short_name=True`` — command column shows the short exec name,
      not the full path (hotkey ``/``).
    - ``programs=False`` — process list shows threads, not the per-program
      aggregation (hotkey ``j``).
    - ``show_help=False`` — the help overlay is hidden (hotkey ``h``).
    """

    show_percpu: bool = False
    process_short_name: bool = True
    programs: bool = False
    show_help: bool = False


def _safe_curses_wrapper(fn):
    """`curses.wrapper` wrapper — separated so tests can monkeypatch it."""
    curses.wrapper(fn)


class TuiV5(threading.Thread):
    """Curses TUI v5 thread."""

    # Hotkey dispatch table (v4 ``glances_curses._hotkeys`` parity).
    # Three action kinds:
    #   - ``switch``: toggle the named ``ViewState`` boolean.
    #   - ``sort``  : set the engine process sort key (``'auto'`` enables
    #                 the dynamic alert-driven auto-sort).
    #   - ``action``: a named control verb handled in ``_handle_key``
    #                 (``help`` toggles the overlay, ``quit`` exits).
    # Data-driven so a new hotkey is one dict entry, no control-flow edit
    # (cf. CLAUDE.md "extensibilité sans modification du cœur").
    #
    # Each entry ALSO carries ``group`` + ``desc``: this same table is the
    # single source of truth for the ``h`` help overlay (``_help_lines``),
    # so every dispatched key is documented and the two can never drift.
    _HOTKEYS: dict[str, dict[str, str]] = {
        # Process sort keys.
        "a": {"sort": "auto", "group": "SORT PROCESSES", "desc": "Automatically"},
        "c": {"sort": "cpu_percent", "group": "SORT PROCESSES", "desc": "By CPU consumption"},
        "m": {"sort": "memory_percent", "group": "SORT PROCESSES", "desc": "By MEM consumption"},
        "i": {"sort": "io_counters", "group": "SORT PROCESSES", "desc": "By disk I/O rate"},
        "t": {"sort": "cpu_times", "group": "SORT PROCESSES", "desc": "By CPU time"},
        "p": {"sort": "name", "group": "SORT PROCESSES", "desc": "By process name"},
        "u": {"sort": "username", "group": "SORT PROCESSES", "desc": "By user name"},
        "o": {"sort": "cpu_num", "group": "SORT PROCESSES", "desc": "By CPU core number"},
        # View toggles.
        "1": {"switch": "show_percpu", "group": "TOGGLE VIEW", "desc": "Per-CPU / aggregated CPU"},
        "/": {"switch": "process_short_name", "group": "TOGGLE VIEW", "desc": "Short / full process name"},
        "j": {"switch": "programs", "group": "TOGGLE VIEW", "desc": "Threads / programs view"},
        # Misc / control.
        "h": {"action": "help", "group": "MISCELLANEOUS", "desc": "Show / hide this help screen"},
        "q": {"action": "quit", "group": "MISCELLANEOUS", "desc": "Quit Glances (or Esc)"},
    }

    # Display order of the hotkey groups in the help overlay.
    _HELP_GROUPS: tuple[str, ...] = ("SORT PROCESSES", "TOGGLE VIEW", "MISCELLANEOUS")
    # Horizontal gap between the two help columns.
    _HELP_COL_GAP = 4
    # Documentation link shown in the help overlay (v4 parity).
    _HELP_DOC_URL = "https://glances.readthedocs.io/en/latest/cmds.html#interactive-commands"

    # Guard-rail: a key-driven repaint happens at most once per this window —
    # instant when idle, coalesced under rapid key mashing.
    _MIN_KEY_REPAINT_INTERVAL = 1.0
    # Upper bound on a single blocking ``getch`` so an external ``stop()`` is
    # honoured promptly even when the next scheduled repaint is far off.
    _MAX_GETCH_BLOCK = 0.25

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
        # User-toggled view options (percpu / short-name / programs),
        # driven by the hotkey dispatch table. The process sort key is
        # held by the ``glances_processes`` engine, not here.
        self._view = ViewState()
        # Vertical scroll offset of the help overlay (rows). Reset to 0 each
        # time the overlay is opened; clamped to the content in ``_paint_help``
        # (which is the only place that knows the terminal height).
        self._help_scroll = 0

    # ----------------------------------------------------------- control

    def stop(self) -> None:
        """Signal the thread to exit at the next loop iteration."""
        self._stop_event.set()

    # ----------------------------------------------------------- input

    def _handle_key(self, key: int) -> str:
        """Dispatch a single keypress. Returns one of:

        - ``"quit"``    — ``q`` / ESC: the loop should shut down.
        - ``"changed"`` — a mapped key mutated the view state or sort key
          (the caller should repaint, rate-limited).
        - ``"repaint"`` — a help-overlay key (open / close / scroll): the
          caller should repaint *immediately*, bypassing the key throttle
          (the help frame is static and cheap to rebuild).
        - ``"ignored"`` — unmapped key / non-character: no state change.

        Pure (no curses I/O) so it can be unit-tested without a terminal.
        """
        # While the help overlay is open it captures every key: scrolling and
        # closing only — q / ESC / h close the help instead of quitting.
        if self._view.show_help:
            return self._handle_help_key(key)

        if key == 27:  # ESC always quits (not a printable hotkey).
            return "quit"
        try:
            ch = chr(key)
        except ValueError:
            return "ignored"
        action = self._HOTKEYS.get(ch)
        if action is None:
            return "ignored"
        if "action" in action:
            verb = action["action"]
            if verb == "quit":
                return "quit"
            if verb == "help":
                self._view.show_help = True
                self._help_scroll = 0
                return "repaint"
            return "ignored"
        if "switch" in action:
            attr = action["switch"]
            setattr(self._view, attr, not getattr(self._view, attr))
            return "changed"
        if "sort" in action:
            sort_key = action["sort"]
            # v4 contract: pressing a manual key turns auto-sort OFF;
            # 'auto' turns it ON (set_sort_key resets the key to cpu_percent).
            try:
                glances_processes.set_sort_key(sort_key, sort_key == "auto")
            except Exception as e:  # pragma: no cover — defensive
                logger.warning("TUI: set_sort_key(%s) failed: %s", sort_key, e)
            return "changed"
        return "ignored"

    # Rows scrolled per PageUp / PageDown in the help overlay.
    _HELP_PAGE_STEP = 10

    def _handle_help_key(self, key: int) -> str:
        """Dispatch a keypress while the help overlay is open.

        Closing keys (``q`` / ESC / ``h``) hide the overlay; arrow / vim /
        page keys scroll it. The upper scroll bound depends on the terminal
        height, so it is clamped in ``_paint_help`` (here we only floor at 0).
        Returns ``"repaint"`` for any handled key, ``"ignored"`` otherwise.
        """
        if key in (ord("q"), 27, ord("h")):
            self._view.show_help = False
            return "repaint"
        if key in (curses.KEY_DOWN, ord("j")):
            self._help_scroll += 1
            return "repaint"
        if key in (curses.KEY_UP, ord("k")):
            self._help_scroll = max(0, self._help_scroll - 1)
            return "repaint"
        if key == curses.KEY_NPAGE:  # Page Down
            self._help_scroll += self._HELP_PAGE_STEP
            return "repaint"
        if key == curses.KEY_PPAGE:  # Page Up
            self._help_scroll = max(0, self._help_scroll - self._HELP_PAGE_STEP)
            return "repaint"
        if key == curses.KEY_HOME:
            self._help_scroll = 0
            return "repaint"
        return "ignored"

    # ----------------------------------------------------------- run loop

    def run(self) -> None:
        try:
            _safe_curses_wrapper(self._loop)
        except Exception as e:  # pragma: no cover — defensive
            logger.warning("TUI v5 crashed: %s", e)

    def _loop(self, stdscr) -> None:
        _init_colors()
        cursor_was_hidden = False
        try:
            curses.curs_set(0)
            cursor_was_hidden = True
        except curses.error:
            pass

        try:
            # Responsive input with low idle CPU: ``getch`` BLOCKS (with a
            # per-iteration timeout) instead of busy-polling. It returns the
            # instant a key is pressed — so a hotkey feels immediate — and
            # otherwise the thread sleeps in the kernel until the next paint
            # is due. Repaint policy:
            # - regular cadence: repaint every ``refresh_interval``;
            # - key-driven: a recognised key marks the frame dirty and forces
            #   an early repaint, throttled (leading-edge) to at most once per
            #   ``_MIN_KEY_REPAINT_INTERVAL`` *between key changes*. A lone
            #   keypress after a quiet period is therefore instant; only rapid
            #   mashing is coalesced (the guard-rail). The throttle is measured
            #   from the last key-driven repaint, NOT the last regular one, so
            #   a keypress right after a cadence refresh still reacts at once.
            # Each block is capped at ``_MAX_GETCH_BLOCK`` so an external
            # ``stop()`` is honoured within that bound.
            self._repaint(stdscr)
            now = time.monotonic()
            last_paint = now
            # Seed so the first keypress is eligible for an instant repaint.
            last_change_paint = now - self._MIN_KEY_REPAINT_INTERVAL
            dirty = False
            while not self._stop_event.is_set():
                now = time.monotonic()
                next_regular = last_paint + self.refresh_interval
                next_change = last_change_paint + self._MIN_KEY_REPAINT_INTERVAL if dirty else float("inf")
                block = max(0.0, min(min(next_regular, next_change) - now, self._MAX_GETCH_BLOCK))
                stdscr.timeout(int(block * 1000))

                key = stdscr.getch()
                if key != -1:
                    result = self._handle_key(key)
                    if result == "quit":
                        self.stop()
                        if self._on_quit is not None:
                            try:
                                self._on_quit()
                            except Exception as e:  # pragma: no cover — defensive
                                logger.warning("TUI on_quit callback failed: %s", e)
                        break
                    if result == "repaint":
                        # Help open / close / scroll: repaint at once, bypassing
                        # the key throttle (the help frame is static and cheap).
                        # Seed the throttle so the next *stats* key change is
                        # still eligible for an instant repaint.
                        self._repaint(stdscr)
                        now = time.monotonic()
                        last_paint = now
                        last_change_paint = now - self._MIN_KEY_REPAINT_INTERVAL
                        dirty = False
                        continue
                    if result == "changed":
                        dirty = True
                    # Loop back to recompute the block; a due (or rate-limited)
                    # repaint happens on the next timeout, not on every keystroke.
                    continue

                # getch timed out — repaint only if a paint is actually due
                # (a capped block may expire before the next paint is due).
                now = time.monotonic()
                regular_due, change_due = self._repaint_decision(now, last_paint, last_change_paint, dirty)
                if regular_due or change_due:
                    self._repaint(stdscr)
                    last_paint = now
                    if change_due:
                        last_change_paint = now
                    dirty = False
        finally:
            # `curses.endwin()` doesn't reliably restore cursor visibility
            # on every terminal — if we hid it, restore it ourselves so the
            # shell prompt that follows shows a blinking cursor.
            if cursor_was_hidden:
                try:
                    curses.curs_set(1)
                except curses.error:
                    pass

    def _repaint_decision(
        self, now: float, last_paint: float, last_change_paint: float, dirty: bool
    ) -> tuple[bool, bool]:
        """Return ``(regular_due, change_due)`` for the repaint policy. Pure.

        - ``regular_due``: the periodic ``refresh_interval`` cadence elapsed.
        - ``change_due``: a pending key change exists AND at least
          ``_MIN_KEY_REPAINT_INTERVAL`` has passed since the last key-driven
          repaint (the once-per-second guard-rail).
        """
        regular_due = (now - last_paint) >= self.refresh_interval
        change_due = dirty and (now - last_change_paint) >= self._MIN_KEY_REPAINT_INTERVAL
        return regular_due, change_due

    def _repaint(self, stdscr) -> None:
        """Build the current frame and paint it to the terminal.

        When the help overlay is open it fully replaces the stats frame
        (mirrors v4, where ``help_tag`` swaps the whole screen)."""
        if self._view.show_help:
            self._paint_help(stdscr)
        else:
            frame = self._build_frame()
            self._paint(stdscr, frame)
        stdscr.refresh()

    # ----------------------------------------------------------- helpers

    def _build_frame(self) -> Frame:
        snapshot = self.store.as_dict()
        # Re-sort the process collections by the engine's *current* sort key
        # so a key change is reflected on the very next repaint, without
        # waiting for the engine's next update cycle to re-sort the store.
        self._apply_live_sort(snapshot)
        history = self.alerts.get_history() if self.alerts is not None else []
        # Distinguish "still in warmup" (alerts cannot fire yet) from "truly
        # empty history" — the alert block shows different placeholders for
        # the two cases.
        initializing = self.alerts.is_initializing() if self.alerts is not None else False
        frame = build_frame(
            store_snapshot=snapshot,
            fields_by_plugin=self.fields_by_plugin,
            registry=self.registry,
            alerts_history=history,
            alerts_initializing=initializing,
            view=self._render_view(),
        )
        # CPU ↔ perCPU mutual exclusion (v4 parity, hotkey '1').
        hidden_top = "cpu" if self._view.show_percpu else "percpu"
        frame.top = [b for b in frame.top if b.name != hidden_top]
        # Threads ↔ programs mutual exclusion (v4 parity, hotkey 'j'):
        # show exactly one of processlist / programlist.
        hidden_right = "processlist" if self._view.programs else "programlist"
        frame.right = [b for b in frame.right if b.name != hidden_right]
        return frame

    # Process collections re-sorted live in the TUI so a sort hotkey takes
    # effect on the next repaint rather than on the engine's next update.
    _LIVE_SORT_PLUGINS = ("processlist", "programlist")

    def _apply_live_sort(self, snapshot: dict[str, Any]) -> None:
        """Re-sort process collections in-place on the *snapshot* by the
        engine's current sort key.

        ``store.as_dict()`` is a shallow copy — the payload objects are shared
        with the store. We therefore never mutate a payload: we replace the
        snapshot's entry with a fresh dict holding a freshly sorted list
        (``sort_stats`` returns a new list), leaving the store untouched."""
        key = getattr(glances_processes, "sort_key", None)
        if not key:
            return
        reverse = bool(getattr(glances_processes, "sort_reverse", True))
        for name in self._LIVE_SORT_PLUGINS:
            payload = snapshot.get(name)
            if not isinstance(payload, dict):
                continue
            data = payload.get("data")
            if not isinstance(data, list) or not data:
                continue
            try:
                ordered = sort_stats(list(data), sorted_by=key, reverse=reverse)
            except Exception as e:  # pragma: no cover — defensive (engine sort quirks)
                logger.debug("TUI live sort failed for %s: %s", name, e)
                continue
            snapshot[name] = {**payload, "data": ordered}

    def _render_view(self) -> dict[str, Any]:
        """Snapshot the view state the per-plugin renderers may consult.

        Carries the boolean switches plus the engine's current sort key /
        auto-sort flag (read back here so the processlist renderer can mark
        the active sort column without importing the engine itself)."""
        return {
            "process_short_name": self._view.process_short_name,
            "programs": self._view.programs,
            "sort_key": getattr(glances_processes, "sort_key", None),
            "auto_sort": getattr(glances_processes, "auto_sort", None),
        }

    # ----------------------------------------------------------- paint

    # Sidebar split spacing (left ↔ right column gap below the top row).
    _SIDEBAR_SEPARATOR_GAP = 2
    # Minimum gap between two adjacent top-row blocks when the terminal
    # is too narrow to distribute extra space — fallback only.
    _TOP_GAP_MIN = 1

    def _paint(self, stdscr, frame: Frame) -> None:
        """Lay out the frame on the terminal, mirroring v4:

        header line        (hostname/OS ............ Uptime)  row 0
        top blocks         (cpu | mem | load | ...)  side-by-side
        <separator line>
        left blocks         right blocks              two vertical columns
        """
        stdscr.erase()
        max_y, max_x = stdscr.getmaxyx()

        # 0. Header line (system flush-left, uptime flush-right).
        header_height = self._paint_header(stdscr, frame.header, 0, max_x)

        # 1. Top row, below the header.
        top_y0 = header_height
        top_height = self._paint_top_row(stdscr, frame.top, top_y0, max_x)

        # 2. Separator under the top row (if any top content was painted).
        body_y0 = top_y0 + top_height
        if top_height > 0 and body_y0 < max_y:
            self._paint_separator(stdscr, body_y0, 0, max_x)
            body_y0 += 1

        # 3. Below the top row: left + right sidebars side-by-side.
        body_height = max(0, max_y - body_y0)
        if body_height > 0:
            left_width = self._sidebar_split(frame, max_x)
            right_x = left_width + self._SIDEBAR_SEPARATOR_GAP
            right_width = max(0, max_x - right_x)

            self._paint_sidebar(stdscr, frame.left, body_y0, 0, left_width, body_height)
            self._paint_sidebar(stdscr, frame.right, body_y0, right_x, right_width, body_height)

    @staticmethod
    def _sidebar_split(frame: Frame, max_x: int) -> int:
        """Width allocated to the left sidebar — bounded like v4
        (`_left_sidebar_min_width=23`, `_left_sidebar_max_width=34`).
        """
        natural = max((b.width for b in frame.left), default=0)
        # +2 for breathing room, mirroring v4's column gap.
        natural = max(natural + 2, 23)
        return min(natural, 34, max(1, max_x // 2))

    def _paint_header(self, stdscr, blocks: list[PluginBlock], y0: int, max_x: int) -> int:
        """Paint the header line (v4 parity): first block flush-left, last
        block flush-right. Returns the header height (0 when empty, else the
        tallest block painted — normally 1).

        Only the first and last blocks are positioned explicitly; the header
        is expected to hold at most two blocks (system + uptime). Any middle
        block (not expected in v5) is skipped rather than overlapped.
        """
        if not blocks:
            return 0
        height = 0
        first = blocks[0]
        self._paint_block(stdscr, first, y0, 0, max_x, fit_to_term=False)
        height = max(height, first.height)
        if len(blocks) > 1:
            last = blocks[-1]
            # Flush-right, but never overlap the flush-left block.
            x = max(first.width + 1, max_x - last.width)
            if x < max_x:
                self._paint_block(stdscr, last, y0, x, max(1, max_x - x), fit_to_term=False)
                height = max(height, last.height)
        return height

    def _paint_top_row(self, stdscr, blocks: list[PluginBlock], y0: int, max_x: int) -> int:
        """Paint TOP blocks side-by-side. Returns the height of the row
        (the tallest block painted).

        Distribution rule (v4 fidelity):
        - first block flush-left (x=0),
        - last block flush-right (right edge at ``max_x``),
        - any blocks in between separated by an evenly-distributed gap
          computed from the remaining horizontal space.
        Fallback when the natural sum of block widths exceeds ``max_x``:
        pack each adjacent pair with the minimum gap and let curses clip
        whatever overflows the screen.
        """
        if not blocks:
            return 0
        widths = [b.width for b in blocks]
        gaps = self._top_row_gaps(widths, max_x)

        x = 0
        height = 0
        for i, block in enumerate(blocks):
            if x >= max_x:
                break
            self._paint_block(stdscr, block, y0, x, max(1, max_x - x), fit_to_term=False)
            height = max(height, block.height)
            x += widths[i]
            if i < len(gaps):
                x += gaps[i]
        return height

    def _top_row_gaps(self, widths: list[int], max_x: int) -> list[int]:
        """Return the N-1 inter-block gaps for the top row.

        - 0 or 1 block → no gaps.
        - N blocks fit within ``max_x``: distribute the remaining space
          evenly across N-1 gaps so the last block's right edge lands on
          column ``max_x - 1``. Remainder pixels (when ``available %
          n_gaps != 0``) are pushed into the leftmost gaps so the
          distribution stays balanced within ±1 char.
        - Otherwise: every gap collapses to ``_TOP_GAP_MIN``.
        """
        n = len(widths)
        if n <= 1:
            return []
        total = sum(widths)
        n_gaps = n - 1
        if total + n_gaps * self._TOP_GAP_MIN > max_x:
            return [self._TOP_GAP_MIN] * n_gaps
        available = max_x - total
        base = available // n_gaps
        extra = available - base * n_gaps
        return [base + (1 if i < extra else 0) for i in range(n_gaps)]

    def _paint_sidebar(self, stdscr, blocks: list[PluginBlock], y0: int, x0: int, width: int, height: int) -> None:
        """Stack blocks vertically; each block separated by one empty line
        (v4 sidebar parity)."""
        if width <= 0 or height <= 0:
            return
        y = y0
        end_y = y0 + height
        for block in blocks:
            if y >= end_y:
                break
            max_h = end_y - y
            self._paint_block(stdscr, block, y, x0, width, fit_to_term=True, max_height=max_h)
            # Advance by the number of rows actually painted (capped to the
            # remaining vertical room) plus one blank line. `_paint_block`
            # returns the width painted, not the height — using `block.height`
            # directly mirrors `_paint_top_row` and avoids the old bug where
            # the row width was added to `y` (visible as a large empty band
            # between two sidebar blocks).
            y += min(block.height, max_h) + 1

    def _paint_block(
        self,
        stdscr,
        block: PluginBlock,
        y0: int,
        x0: int,
        width: int,
        fit_to_term: bool,
        max_height: int | None = None,
    ) -> int:
        """Paint a single block at (y0, x0) within the given width.

        Returns the actual width painted (for top row layout to advance).
        """
        rows = block.rows
        if max_height is not None:
            rows = rows[:max_height]
        widest = 0
        for i, row in enumerate(rows):
            painted_w = self._paint_row(stdscr, row, y0 + i, x0, width)
            widest = max(widest, painted_w)
        return min(widest, width) if fit_to_term else widest

    def _paint_row(self, stdscr, row: Row, y: int, x0: int, width: int) -> int:
        """Paint a single row's cells. One space separates adjacent cells,
        except a ``glue`` cell which is painted flush against the previous
        one (no separator). Returns width consumed."""
        x = x0
        limit = x0 + width
        for i, cell in enumerate(row.cells):
            if i > 0 and not cell.glue:
                x += 1  # one-space separator before this cell
            if x >= limit:
                break
            text = cell.text[: limit - x]
            attr = _attr_for(cell)
            try:
                stdscr.addstr(y, x, text, attr)
            except curses.error:
                break
            x += len(text)
        return max(0, x - x0)

    def _paint_separator(self, stdscr, y: int, x0: int, width: int) -> None:
        try:
            stdscr.addstr(y, x0, "-" * max(0, width - 1))
        except curses.error:
            pass

    # ----------------------------------------------------------- help overlay

    def _help_lines(self) -> list[Row]:
        """Build the help body as a single column of display rows.

        Generated straight from ``_HOTKEYS`` (the dispatch table) so the
        overlay documents *every* key the TUI actually responds to — add a
        hotkey and it shows up here automatically, with no second list to
        keep in sync (CLAUDE.md "extensibilité sans modification du cœur").

        Each group is a bold header followed by one ``  k  description`` row
        per key, with a blank spacer line between groups.
        """
        lines: list[Row] = []
        for group in self._HELP_GROUPS:
            keys = [(k, spec) for k, spec in self._HOTKEYS.items() if spec.get("group") == group]
            if not keys:
                continue
            if lines:
                lines.append(Row(cells=[Cell(text="")]))  # spacer between groups
            lines.append(Row(cells=[Cell(text=group, color=ColorRole.HEADER)]))
            for k, spec in keys:
                lines.append(Row(cells=[Cell(text=f"  {k:>2}  {spec.get('desc', '')}")]))
        return lines

    @staticmethod
    def _help_row_width(row: Row) -> int:
        """Printable width of a (single-cell) help row."""
        return max((len(c.text) for c in row.cells), default=0)

    def _loaded_config_path(self) -> str:
        """Path of the configuration file actually in use, or a default note.

        v5 reads at most one file (``GlancesConfigV5.loaded_sources``).
        Wrapped defensively: the help overlay must never crash on a config
        object that lacks the attribute (e.g. a test stub)."""
        try:
            sources = self.config.loaded_sources
        except Exception:
            return ""
        if sources:
            return str(sources[-1])
        return "(none — built-in defaults)"

    def _help_color_rows(self) -> list[Row]:
        """Colour-binding legend, rendered in the *actual* TUI attributes.

        Each sample word carries the real ``ColorRole`` / decoration so the
        user sees exactly what each colour means on their terminal (v4's
        "Colors binding" section, adapted to v5's smaller palette)."""
        levels = Row(
            cells=[
                Cell(text="OK", color=ColorRole.OK),
                Cell(text="CAREFUL", color=ColorRole.CAREFUL),
                Cell(text="WARNING", color=ColorRole.WARNING),
                Cell(text="CRITICAL", color=ColorRole.CRITICAL),
                Cell(text="= stat severity (vs thresholds)"),
            ]
        )
        decorations = Row(
            cells=[
                Cell(text="Title", color=ColorRole.HEADER),
                Cell(text="Sort", color=ColorRole.DEFAULT, bold=True, underline=True),
                Cell(text="Alert", color=ColorRole.CRITICAL, prominent=True),
                Cell(text="= section title / active sort column / ongoing alert"),
            ]
        )
        return [levels, decorations]

    def _help_visual_rows(self, max_x: int) -> tuple[list[tuple[Row, Row | None]], int]:
        """Assemble the full scrollable help document as ``(left, right)`` rows.

        ``right is None`` marks a full-width line (config path, doc link,
        colour legend); a non-None ``right`` is the second column of the
        two-column key list. Returns the rows plus the key-column width so the
        painter can place the right column. Everything scrolls as one document.
        """
        key_lines = self._help_lines()
        col_w = max((self._help_row_width(r) for r in key_lines), default=0)

        # Two columns when both halves fit side-by-side, else a single column.
        if max_x >= col_w + self._HELP_COL_GAP + col_w:
            n_left = (len(key_lines) + 1) // 2
            key_pairs = list(zip_longest(key_lines[:n_left], key_lines[n_left:]))
        else:
            key_pairs = [(row, None) for row in key_lines]

        def full(text: str, **kw) -> tuple[Row, None]:
            return (Row(cells=[Cell(text=text, **kw)]), None)

        rows: list[tuple[Row, Row | None]] = []
        # 1. Configuration file currently in use (v4 parity).
        rows.append(full(f"Configuration file: {self._loaded_config_path()}"))
        rows.append(full(""))
        # 2. Key shortcuts (two columns).
        rows.extend(key_pairs)
        # 3. Documentation link (v4 parity).
        rows.append(full(""))
        rows.append(full("For an exhaustive list of key bindings:"))
        rows.append(full(self._HELP_DOC_URL, color=ColorRole.CAREFUL, underline=True))
        # 4. Colour binding legend (v4 parity, v5 palette).
        rows.append(full(""))
        rows.append(full("Color binding:", color=ColorRole.HEADER))
        rows.extend((r, None) for r in self._help_color_rows())
        return rows, col_w

    def _paint_help(self, stdscr) -> None:
        """Paint the help overlay: title, then a scrollable document holding
        the config path, the two-column key list, the doc link and the colour
        legend.

        Mirrors v4's help, then improves on it: the key list is generated from
        the dispatch table (exhaustive) and, when the whole document does not
        fit the terminal, it scrolls (↑/↓, PgUp/PgDn) instead of being
        silently clipped.
        """
        stdscr.erase()
        max_y, max_x = stdscr.getmaxyx()
        if max_y < 1 or max_x < 1:
            return

        title = f"Glances {__version__} help — h/q/Esc to close"
        try:
            stdscr.addstr(0, 0, title[: max_x - 1], curses.A_BOLD)
        except curses.error:
            pass

        rows, col_w = self._help_visual_rows(max_x)

        # Layout: row 0 = title, row 1 = blank, body below, last row = footer.
        body_y0 = 2
        footer_h = 1
        body_h = max(1, max_y - body_y0 - footer_h)

        total = len(rows)
        max_scroll = max(0, total - body_h)
        # Clamp here (the only place that knows the terminal height).
        self._help_scroll = max(0, min(self._help_scroll, max_scroll))
        start = self._help_scroll
        shown = rows[start : start + body_h]

        right_x = col_w + self._HELP_COL_GAP
        for i, (left_row, right_row) in enumerate(shown):
            y = body_y0 + i
            if right_row is not None:
                # Two-column key line.
                self._paint_row(stdscr, left_row, y, 0, col_w)
                self._paint_row(stdscr, right_row, y, right_x, max(1, max_x - right_x))
            else:
                # Full-width line (config / link / colour legend).
                self._paint_row(stdscr, left_row, y, 0, max_x)

        if max_scroll > 0:
            self._paint_help_footer(stdscr, max_y - 1, max_x, start, body_h, total, max_scroll)

    @staticmethod
    def _paint_help_footer(stdscr, y: int, max_x: int, start: int, body_h: int, total: int, max_scroll: int) -> None:
        """Bottom-line scroll indicator, shown only when the help overflows."""
        if start <= 0:
            arrow = "↓"
        elif start >= max_scroll:
            arrow = "↑"
        else:
            arrow = "↑↓"
        last = min(start + body_h, total)
        footer = f"  {arrow} more  ({start + 1}-{last}/{total})  ↑/↓ PgUp/PgDn to scroll"
        try:
            stdscr.addstr(y, 0, footer[: max_x - 1])
        except curses.error:
            pass


# ----------------------------------------------------------------- colors


# Separate dict: for each alert role, the "white-on-color" curses pair
# used when a cell is marked prominent. Filled in `_init_colors`.
_COLOR_PAIRS_REVERSE: dict[ColorRole, int] = {}


def _init_colors() -> None:
    try:
        if not curses.has_colors():
            return
        curses.start_color()
        try:
            curses.use_default_colors()
        except curses.error:
            pass
        # Foreground pairs (used by default for coloured text on the
        # terminal's native background).
        pairs = [
            (ColorRole.OK, curses.COLOR_GREEN),
            (ColorRole.CAREFUL, curses.COLOR_BLUE),
            (ColorRole.WARNING, curses.COLOR_MAGENTA),
            (ColorRole.CRITICAL, curses.COLOR_RED),
            # v4 fidelity: plugin titles use the TITLE decoration which is
            # bold + default-text (white-ish on dark terminals).
            (ColorRole.HEADER, curses.COLOR_WHITE),
        ]
        for i, (role, color) in enumerate(pairs, start=1):
            try:
                curses.init_pair(i, color, -1)
            except curses.error:
                curses.init_pair(i, color, curses.COLOR_BLACK)
            _COLOR_PAIRS[role] = curses.color_pair(i)
        _COLOR_PAIRS[ColorRole.DEFAULT] = curses.color_pair(0)

        # Reverse pairs — explicit "white fg on coloured bg" (v4 parity).
        # Using A_REVERSE alone would inherit the terminal's default
        # foreground for the swapped fg, often a mid-gray that is hard to
        # read on a magenta/red background. Defining a separate pair
        # guarantees a white foreground.
        reverse_pairs = [
            (ColorRole.OK, curses.COLOR_GREEN),
            (ColorRole.CAREFUL, curses.COLOR_BLUE),
            (ColorRole.WARNING, curses.COLOR_MAGENTA),
            (ColorRole.CRITICAL, curses.COLOR_RED),
        ]
        for j, (role, bg) in enumerate(reverse_pairs, start=len(pairs) + 1):
            try:
                curses.init_pair(j, curses.COLOR_WHITE, bg)
            except curses.error:
                # Terminal can't allocate the pair (very limited palettes).
                # Fall back to plain reverse so we don't crash.
                continue
            _COLOR_PAIRS_REVERSE[role] = curses.color_pair(j)
    except curses.error:
        # curses not initialised (e.g. under unit-test mock or non-TTY).
        # The renderer paints monochrome — that's fine.
        pass


def _attr_for(cell: Cell) -> int:
    # When the cell is `prominent: True` AND carries an alert level, use
    # the white-on-colour pair (v4 ``*_LOG`` decoration parity). Falls
    # back to plain `A_REVERSE` on the foreground pair if the dedicated
    # background pair couldn't be allocated.
    is_alert_color = cell.color in (
        ColorRole.OK,
        ColorRole.CAREFUL,
        ColorRole.WARNING,
        ColorRole.CRITICAL,
    )
    if cell.prominent and is_alert_color:
        attr = _COLOR_PAIRS_REVERSE.get(cell.color)
        if attr is None:
            attr = _COLOR_PAIRS.get(cell.color, 0) | curses.A_REVERSE
    else:
        attr = _COLOR_PAIRS.get(cell.color, 0)

    # HEADER role is bold by default (v4 TITLE decoration). Cells of any
    # other colour can opt in to bold via the `bold` flag — useful for
    # alert-coloured plugin titles (e.g. red+bold MEM when the percent
    # field hits critical).
    if cell.color == ColorRole.HEADER or cell.bold:
        attr |= curses.A_BOLD
    # v4 'SORT' decoration = A_UNDERLINE | A_BOLD — the active sort column
    # header sets `underline` (and is already bold).
    if cell.underline:
        attr |= curses.A_UNDERLINE
    return attr

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
import os
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from itertools import zip_longest
from typing import TYPE_CHECKING, Any, ClassVar

import psutil

from glances import __version__
from glances.outputs.curses_renderer_v5 import (
    HEADER_SLOT_RIGHT,
    LEFT_SLOT,
    TOP_SLOT,
    Cell,
    ColorRole,
    Frame,
    PluginBlock,
    Row,
    build_frame,
    plan_right_column,
    with_truncation_counter,
)
from glances.plugins.processlist.render_curses_v5 import process_extra_rows, summarise
from glances.processes import glances_processes, sort_processes_stats_list, sort_stats

if TYPE_CHECKING:
    from glances.alerts_v5 import GlancesAlerts
    from glances.config_v5 import GlancesConfigV5
    from glances.stats_store_v5 import StatsStoreV5

logger = logging.getLogger(__name__)

# C0 control characters and DEL, each painted as one space: same length, so the
# renderers' width arithmetic stays exact (see `_paint_row`).
_CONTROL_CHARS_TO_SPACE = dict.fromkeys([*range(0x20), 0x7F], " ")


# Ordered TOP-row degradation cascade (a→f). Each entry mutates the per-cycle
# ``view`` dict by one notch; the loop in ``_build_fitted_frame`` applies them
# one at a time until the row fits ``max_x``. The order is the maintainer's v4
# spec: drop the least-important detail first (MEM 2nd column) and only hide a
# whole block (quicklook, then swap) as a last resort. ``cpu_cols=1`` subsumes
# the col-3 drop, so step (b) (cpu_cols=2) is tried before (c) (cpu_cols=1).
_DEGRADE_STEPS: list[tuple[str, Any]] = [
    ("mem_cols", 1),  # (a) hide MEM 2nd column
    ("cpu_cols", 2),  # (b) hide CPU 3rd column
    ("cpu_cols", 1),  # (c) hide CPU 2nd column
    ("quicklook_freq_only", True),  # (d) "Frequency" header + shrink quicklook
    ("hide_quicklook", True),  # (e) hide quicklook block
    ("hide_memswap", True),  # (f) hide swap block
    ("hide_gpu", True),  # (g) hide gpu block (last resort)
]

# Header line (system … ip … uptime … cloud … now) progressive degradation,
# applied independently of the TOP row when the terminal is too narrow to
# show all blocks. Cumulative, in the maintainer-specified order: `cloud` is
# an opt-in block, so it must be the *first* one sacrificed — enabling it must
# never degrade information (ip, uptime, now) that was already on screen
# before it was turned on. The next two steps shrink a block rather than hide
# one, cheapest content first: the ip geolocation string (built from
# `[ip] public_template` — the widest, least essential segment of the banner,
# and the addresses themselves survive it), then the system OS/kernel string
# (static host metadata: distro, arch, kernel release, so it is worth less
# under width pressure than any live metric). Only then are whole blocks
# hidden: `now`, whose removal brings the banner back to exactly the v4
# `system … ip … uptime` layout, then ip, then uptime. v4 parity degrades only
# the OS-info drop (`display_system_optional`); the other steps refine it for
# very narrow terminals.
_HEADER_DEGRADE_STEPS: list[tuple[str, Any]] = [
    ("hide_cloud", True),  # (0) hide the opt-in cloud block (first to go)
    ("hide_ip_location", True),  # (1) drop the ip geolocation string
    ("hide_os_info", True),  # (2) drop the system OS/kernel string
    ("hide_now", True),  # (3) hide the now block
    ("hide_ip", True),  # (4) hide the ip block
    ("hide_uptime", True),  # (5) hide the uptime block (last resort)
]


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
    - ``hidden_plugins=set()`` — nothing hidden by the user (SHOW/HIDE keys).
    - ``cursor_position=0`` — the process list's first row (UP / DOWN).
    - ``extended=False`` — no extended stats block (hotkey ``e``).
    - ``filter_mmm`` — empty min/max accumulators (hotkeys ``ENTER``, ``M``).
    - ``command_offset=0`` — the command column unscrolled (LEFT / RIGHT).

    ``hidden_plugins`` is deliberately a namespace of its own, NOT the
    ``hide_<plugin>`` view keys the width-degradation cascades write
    (``_DEGRADE_STEPS``, ``_HEADER_DEGRADE_STEPS``). Those keys are rebuilt
    from scratch on every cycle by ``_build_view``, so a user choice stored
    there would be clobbered — or would make the cascade believe it had
    already spent a step. ``build_frame`` reads both and hides on the union:
    "hidden because I said so" and "hidden because there is no room" are both
    hidden, and neither authority can corrupt the other.
    """

    show_percpu: bool = False
    process_short_name: bool = True
    programs: bool = False
    show_help: bool = False
    hidden_plugins: set[str] = field(default_factory=set)
    # Process-selection cursor (2.X-b): an index into the order the process
    # block is CURRENTLY DRAWING, not into the store's list and not a pid.
    # The list is re-sorted every cycle (`_apply_live_sort`), so the process
    # under the cursor changes when the sort is volatile -- v4 behaves the
    # same way (design 5.2), and the one place where that is dangerous (`k`)
    # closes it by naming its target before it acts, not by pinning the index.
    cursor_position: int = 0
    # Extended stats for the selected process (hotkey `e`, 2.X-b3). While on,
    # the cursor is FROZEN -- v4 does the same (`glances_curses.py:356`),
    # because otherwise the block describes whatever the cursor last touched
    # while the user is still moving it.
    extended: bool = False
    # Accumulated min/max of the FILTERED summary (hotkey `M` resets it).
    # v4 keeps this on the plugin instance -- a stateful renderer
    # (`processlist/__init__.py` `mmm_min`/`mmm_max`). v5's renderers are pure
    # functions of (payload, fields, view), so the memory lives here and the
    # three rows reach the renderer through `view`.
    filter_mmm: dict[str, dict[str, float]] = field(default_factory=lambda: {"min": {}, "max": {}})
    # Horizontal scroll of the command column's ARGUMENTS, in characters
    # (LEFT / RIGHT, or SHIFT+ them under `--arrow-keys-sort`). The executable
    # name stays put: it is the part that identifies the row.
    command_offset: int = 0
    # TOGGLE DATA TYPE (2.X-c). Seeded from the CLI at construction, then
    # flipped by their keys.
    byte: bool = False
    meangpu: bool = False
    diskio_iops: bool = False
    diskio_latency: bool = False
    load_irix: bool = False
    network_sum: bool = False
    network_cumul: bool = False
    # Tri-state, unlike the two above: `[fs] free_space` lives in the fs
    # plugin's CONFIG and reaches the renderer as payload metadata, not as a
    # constructor argument the TUI could seed from. `None` therefore means
    # "whatever the payload says"; pressing `F` writes a boolean that wins.
    # Same shape as the browser's `viewOverrides` over `serverArgs`, and for
    # the same reason: a copy taken once would go stale against its source.
    fs_free_space: bool | None = None


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
    _HOTKEYS: dict[str, dict[str, Any]] = {
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
        "4": {"action": "full_quicklook", "group": "TOGGLE VIEW", "desc": "Full quicklook (hide the rest of the row)"},
        "/": {"switch": "process_short_name", "group": "TOGGLE VIEW", "desc": "Short / full process name"},
        "j": {"switch": "programs", "group": "TOGGLE VIEW", "desc": "Threads / programs view"},
        # Per-plugin and per-slot visibility (v4 SHOW/HIDE family). The value
        # is ALWAYS a tuple, so a key reaching several plugins (`f`, `z`) or a
        # whole slot (`2`, `5`) is not a special case in the dispatcher.
        "A": {"hide": ("amps",), "group": "SHOW/HIDE", "desc": "Show/hide AMPs"},
        "C": {"hide": ("cloud",), "group": "SHOW/HIDE", "desc": "Show/hide cloud"},
        "d": {"hide": ("diskio",), "group": "SHOW/HIDE", "desc": "Show/hide disk I/O"},
        "D": {"hide": ("containers",), "group": "SHOW/HIDE", "desc": "Show/hide containers"},
        "f": {"hide": ("fs", "folders"), "group": "SHOW/HIDE", "desc": "Show/hide filesystem and folders"},
        "G": {"hide": ("gpu",), "group": "SHOW/HIDE", "desc": "Show/hide GPU"},
        "I": {"hide": ("ip",), "group": "SHOW/HIDE", "desc": "Show/hide IP module"},
        "K": {"hide": ("connections",), "group": "SHOW/HIDE", "desc": "Show/hide TCP connections"},
        "l": {"hide": ("alert",), "group": "SHOW/HIDE", "desc": "Show/hide alerts"},
        "n": {"hide": ("network",), "group": "SHOW/HIDE", "desc": "Show/hide network stats"},
        "N": {"hide": ("now",), "group": "SHOW/HIDE", "desc": "Show/hide current time"},
        "P": {"hide": ("ports",), "group": "SHOW/HIDE", "desc": "Show/hide ports stats"},
        # v4 binds `Q` to `enable_irq` (irq is opt-in there). v5 stores one
        # uniform "hidden or not" state, so the polarity survives only in the
        # starting value — and a config-disabled irq is never instantiated,
        # which makes this key a visible no-op (design §6.1).
        "Q": {"hide": ("irq",), "group": "SHOW/HIDE", "desc": "Show/hide IRQ module"},
        # v4's in-app help and docs/cmds.rst both label `r` "Reset history",
        # but v4's own dispatch table binds it to `disable_smart`. We follow
        # the v4 CODE, not the v4 docs (design §5.5).
        "r": {"hide": ("smart",), "group": "SHOW/HIDE", "desc": "Show/hide SMART stats"},
        "R": {"hide": ("raid",), "group": "SHOW/HIDE", "desc": "Show/hide RAID plugin"},
        "s": {"hide": ("sensors",), "group": "SHOW/HIDE", "desc": "Show/hide sensors"},
        "V": {"hide": ("vms",), "group": "SHOW/HIDE", "desc": "Show/hide VMs"},
        "W": {"hide": ("wifi",), "group": "SHOW/HIDE", "desc": "Show/hide wifi module"},
        # v4 `_handle_disable_process` also stops the shared `glances_processes`
        # engine. v5 shares that engine with the REST API and the WebUI, so a
        # TUI keypress must not blank `/api/5/processlist` for every other
        # consumer: this hides the three blocks and nothing else (design §6.3).
        "z": {
            "hide": ("processlist", "programlist", "processcount"),
            "group": "SHOW/HIDE",
            "desc": "Show/hide processes",
        },
        "7": {"hide": ("npu",), "group": "SHOW/HIDE", "desc": "Show/hide NPU"},
        "8": {"hide": ("mpp",), "group": "SHOW/HIDE", "desc": "Show/hide MPP"},
        # Slot-wide toggles, expanded to their members at press time so that a
        # later single-plugin key acts on that one plugin (design §5.4).
        "2": {"hide": LEFT_SLOT, "group": "SHOW/HIDE", "desc": "Show/hide left sidebar"},
        "3": {"hide": ("quicklook",), "group": "SHOW/HIDE", "desc": "Show/hide quicklook"},
        "5": {"hide": TOP_SLOT, "group": "SHOW/HIDE", "desc": "Show/hide top menu"},
        # Data-type toggles: these change HOW a value is shown, not whether
        # its block is. Each flips one ViewState field that a renderer reads
        # through the per-cycle `view` dict.
        "b": {"switch": "byte", "group": "TOGGLE VIEW", "desc": "Network I/O in bit/s or byte/s"},
        "6": {"switch": "meangpu", "group": "TOGGLE VIEW", "desc": "GPU: per-card or mean"},
        "B": {"switch": "diskio_iops", "group": "TOGGLE VIEW", "desc": "Disk I/O in byte/s or IOPS"},
        "L": {"switch": "diskio_latency", "group": "TOGGLE VIEW", "desc": "Disk I/O in byte/s or latency"},
        "0": {"switch": "load_irix", "group": "TOGGLE VIEW", "desc": "Load average or Irix percentage"},
        "T": {"switch": "network_sum", "group": "TOGGLE VIEW", "desc": "Network and disk I/O apart or combined"},
        "U": {"switch": "network_cumul", "group": "TOGGLE VIEW", "desc": "Network and disk I/O rate or cumulative"},
        # Tri-state, so it cannot be a plain `switch`: `None` means "follow
        # `[fs] free_space`", which is why it has its own verb.
        "F": {"action": "fs_free_space", "group": "TOGGLE VIEW", "desc": "Filesystem: used or free space"},
        # Acting on the cursor-selected process (2.X-b). Each needs a target,
        # so each is `cursor: True` -- `_handle_key` refuses them outright
        # when the cursor is disabled, exactly as v4 guards them in its
        # dispatch dict (`glances_curses.py:279-290`).
        "E": {
            "action": "erase_filter",
            "group": "MISCELLANEOUS",
            "desc": "Erase the process filter",
        },
        "M": {
            "action": "reset_minmax",
            "group": "MISCELLANEOUS",
            "desc": "Reset the filtered summary's min/max",
        },
        "e": {
            "action": "extended",
            "cursor": True,
            "group": "MISCELLANEOUS",
            "desc": "Extended stats for the selected process",
        },
        "k": {
            "action": "kill_process",
            "cursor": True,
            "group": "MISCELLANEOUS",
            "desc": "Kill the selected process (asks first)",
        },
        "+": {
            "action": "nice_increase",
            "cursor": True,
            "group": "MISCELLANEOUS",
            "desc": "Increase nice (lower priority)",
        },
        "-": {
            "action": "nice_decrease",
            "cursor": True,
            "group": "MISCELLANEOUS",
            "desc": "Decrease nice (needs admin rights)",
        },
        # Misc / control.
        "h": {"action": "help", "group": "MISCELLANEOUS", "desc": "Show / hide this help screen"},
        "q": {"action": "quit", "group": "MISCELLANEOUS", "desc": "Quit Glances (or Esc)"},
    }

    # Hotkeys that have no character to be keyed by.
    #
    # `_HOTKEYS` is addressed by `chr(key)`, and every consumer relies on its
    # key being the character to press -- `hotkeys.js` and its drift test
    # (`tests/test_webui_v5_hotkeys_drift.py`) iterate it on that assumption.
    # `chr(curses.KEY_UP)` is a real character (U+0103), so an entry there
    # would dispatch and then print a nonsense key label in the help overlay.
    #
    # So: a second table, keyed by the curses keycode, carrying the same
    # `group` / `desc` plus the `label` to print. `_help_lines` reads BOTH,
    # which is what keeps "no bound key goes undocumented" true -- the
    # property 2.X-a established and the reason the help screen is worth
    # trusting.
    # v4 also accepts the raw ANSI codes 65 / 66 for terminals that do not
    # report KEY_UP / KEY_DOWN (`glances_curses.py:289-290`). v5 does NOT,
    # because 65 and 66 are `ord("A")` and `ord("B")` -- both bound here
    # (show/hide AMPs, disk I/O byte/s vs IOPS). v4 gets away with it only by
    # running BOTH of its dispatch tables on every keypress
    # (`glances_curses.py:303-305`), which means pressing `A` in v4 toggles
    # AMPs *and* moves the cursor up. `curses.wrapper` enables `keypad`, so
    # KEY_UP / KEY_DOWN arrive as themselves; the aliases buy nothing and
    # would cost two working hotkeys.
    _SPECIAL_HOTKEYS: dict[int, dict[str, Any]] = {
        # v4 binds ENTER as the CHARACTER `'\n'` (`glances_curses.py:42`) and
        # v5 could too -- `chr(10)` is well defined. It lives here anyway so
        # the help overlay prints "ENTER" rather than a line break.
        # `curses.KEY_ENTER` is the keypad variant some terminals send.
        10: {
            "action": "edit_filter",
            "group": "MISCELLANEOUS",
            "desc": "Set the process filter (a regular expression)",
            "label": "ENTER",
        },
        curses.KEY_ENTER: {"action": "edit_filter"},
        curses.KEY_UP: {
            "action": "cursor_up",
            "cursor": True,
            "group": "SELECT PROCESS",
            "desc": "Select the previous process",
            "label": "UP",
        },
        curses.KEY_DOWN: {
            "action": "cursor_down",
            "cursor": True,
            "group": "SELECT PROCESS",
            "desc": "Select the next process",
            "label": "DOWN",
        },
        curses.KEY_F5: {
            "action": "refresh",
            "group": "MISCELLANEOUS",
            "desc": "Refresh (drop the process cache)",
            "label": "F5",
        },
        # Ctrl-R, the other spelling v4 accepts (`glances_curses.py:291`).
        18: {"action": "refresh"},
    }

    # The four keys `--arrow-keys-sort` SWAPS (v4 issue #3385,
    # `glances_curses.py:281-288`). Not in the table above, because the table
    # is also what the `h` overlay is generated from: a static entry would
    # describe the wrong binding in one of the two configurations, and "the
    # overlay cannot drift from what the TUI does" is the property every
    # chantier since 2.X-a has kept. Resolved once, here, for both consumers.
    _SORT_ARROWS: tuple[dict[str, Any], dict[str, Any]] = (
        {"action": "sort_prev", "group": "SORT PROCESSES", "desc": "Previous sort column"},
        {"action": "sort_next", "group": "SORT PROCESSES", "desc": "Next sort column"},
    )
    _SCROLL_ARROWS: tuple[dict[str, Any], dict[str, Any]] = (
        {
            "action": "command_left",
            "cursor": True,
            "group": "SELECT PROCESS",
            "desc": "Scroll the command column left",
        },
        {
            "action": "command_right",
            "cursor": True,
            "group": "SELECT PROCESS",
            "desc": "Scroll the command column right",
        },
    )

    _ARROW_LABELS: ClassVar[dict[int, str]] = {
        curses.KEY_LEFT: "LEFT",
        curses.KEY_RIGHT: "RIGHT",
        curses.KEY_SLEFT: "SHIFT-LEFT",
        curses.KEY_SRIGHT: "SHIFT-RIGHT",
    }

    def _arrow_bindings(self) -> dict[int, dict[str, Any]]:
        """The four horizontal arrows, bound per `--arrow-keys-sort`."""
        plain = (curses.KEY_LEFT, curses.KEY_RIGHT)
        shifted = (curses.KEY_SLEFT, curses.KEY_SRIGHT)
        sort_keys, scroll_keys = (plain, shifted) if self._arrow_keys_sort else (shifted, plain)
        bindings: dict[int, dict[str, Any]] = {}
        for keys, specs in ((sort_keys, self._SORT_ARROWS), (scroll_keys, self._SCROLL_ARROWS)):
            for key, spec in zip(keys, specs):
                bindings[key] = {**spec, "label": self._ARROW_LABELS[key]}
        return bindings

    def _special_hotkeys(self) -> dict[int, dict[str, Any]]:
        """Every keycode-addressed hotkey, the swappable arrows included."""
        return {**self._SPECIAL_HOTKEYS, **self._arrow_bindings()}

    # Display order of the hotkey groups in the help overlay.
    _HELP_GROUPS: tuple[str, ...] = (
        "SORT PROCESSES",
        "SELECT PROCESS",
        "TOGGLE VIEW",
        "SHOW/HIDE",
        "MISCELLANEOUS",
    )
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
    # Poll interval used *only* during the startup catch-up window (see
    # ``_startup_catchup_over``). Short enough that the first data-bearing
    # frame lands within a couple of frames of the plugins publishing.
    _STARTUP_POLL_INTERVAL = 0.15
    # Hard ceiling on the startup catch-up window, so a plugin whose
    # ``update()`` never succeeds cannot keep the fast polling alive forever.
    _STARTUP_CATCHUP_TIMEOUT = 5.0

    def __init__(
        self,
        store: StatsStoreV5,
        alerts: GlancesAlerts | None,
        config: GlancesConfigV5,
        registry: list[tuple[str, bool]],
        fields_by_plugin: dict[str, dict[str, dict[str, Any]]],
        refresh_interval: float = 1.0,
        on_quit: Callable[[], None] | None = None,
        full_quicklook: bool = False,
        percpu: bool = False,
        meangpu: bool = False,
        fahrenheit: bool = False,
        hide_public_info: bool = False,
        byte: bool = False,
        diskio_latency: bool = False,
        disable_unicode: bool = False,
        programs: bool = False,
        disable_cursor: bool = False,
        arrow_keys_sort: bool = False,
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
        # Plugin-title colour, see `_init_colors`. ``dark`` (default) is a
        # light amber tuned for the dark backgrounds most terminals use;
        # ``light`` swaps to a dark amber for white backgrounds. A single
        # colour cannot clear 4.6:1 on both, hence the key.
        self._theme = str(self.config.get("outputs", "theme", "dark")).strip().lower()
        self._stop_event = threading.Event()
        # User-toggled view options (percpu / short-name / programs),
        # driven by the hotkey dispatch table. ``programs`` starts from the
        # CLI flag --programs (wired in main_v5.assemble) — the ``j`` hotkey
        # flips it live from there, same pattern as full_quicklook/percpu
        # below. The process sort key is held by the ``glances_processes``
        # engine, not here.
        self._view = ViewState(programs=bool(programs))
        # Quicklook view options. ``_full_quicklook`` is also toggled live by
        # the ``4`` hotkey; ``_percpu`` selects per-core bars inside the
        # quicklook block (distinct from ``_view.show_percpu``, which swaps the
        # whole cpu/percpu TOP block). Seeded from the CLI flags --full-quicklook
        # / --percpu (wired in main_v5.assemble).
        self._full_quicklook = bool(full_quicklook)
        self._percpu = bool(percpu)
        # GPU view options seeded from the CLI flags --meangpu / --fahrenheit.
        # ``_view.meangpu`` forces the gpu renderer into a single mean summary
        # and is flipped live by the ``6`` hotkey, which is why it lives in
        # ViewState rather than beside ``_fahrenheit``; the latter has no key.
        self._view.meangpu = bool(meangpu)
        self._fahrenheit = bool(fahrenheit)
        self._hide_public_info = bool(hide_public_info)
        # Network I/O unit, seeded from --byte and flipped live by the ``b``
        # hotkey. False (default) = bits, matching the v4 default.
        self._view.byte = bool(byte)
        # Disk I/O latency mode, seeded from --diskio-latency, flipped by `L`.
        self._view.diskio_latency = bool(diskio_latency)
        # v4 parity for `--disable-unicode`: when set, renderers must emit
        # pure ASCII. v5 emitted no non-ASCII character at all until the
        # alert block's state glyphs (design §6.5), so this is the first
        # consumer — published as `view["unicode"]` (True = glyphs allowed).
        self._unicode = not bool(disable_unicode)
        # Horizontal rule between sections (header↔top, top↔body). Default
        # ``─`` (box-drawing). ``[outputs] separator=False`` keeps each rule
        # row blank instead, so the vertical rhythm of the layout is
        # preserved (v4 collapses the row; v5 keeps a blank line).
        # ``--disable-unicode`` turns it off whatever the file says: ``─`` is
        # not ASCII, and the command line overrides the configuration file
        # (v4 main.py "Unicode => No separator", d2836579).
        self._separator_enabled = self._unicode and bool(self.config.get("outputs", "separator", True))
        # Vertical scroll offset of the help overlay (rows). Reset to 0 each
        # time the overlay is opened; clamped to the content in ``_paint_help``
        # (which is the only place that knows the terminal height).
        self._help_scroll = 0
        # Process-selection cursor (2.X-b), seeded from --disable-cursor.
        # When off, every cursor key and every key that needs a target is
        # `"ignored"` and no row is decorated -- v4's guard, one flag instead
        # of repeated `and not self.args.disable_cursor` clauses.
        self._cursor_enabled = not bool(disable_cursor)
        # `--arrow-keys-sort` (v4 issue #3385): swaps which arrow pair steps
        # the sort column and which scrolls the command text.
        self._arrow_keys_sort = bool(arrow_keys_sort)
        # How many process rows the LAST painted frame actually drew. The
        # cursor is clamped to it so the selected process is always on
        # screen -- which is what makes `k`'s confirmation trustworthy: it
        # can never name a process the user cannot see (design 5.3).
        # 0 until the first paint, so `DOWN` is inert for exactly one frame.
        self._cursor_max = 0
        # Set by `_handle_key` (which stays pure) when a key needs the
        # terminal: a popup, i.e. curses I/O. `_loop` runs it and clears it.
        self._pending: str | None = None
        # The ordered process items of the frame currently on screen; see
        # `_frame_for_view`.
        self._cursor_items: list[dict[str, Any]] = []

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
        - ``"repaint"`` — a help-overlay key (open / close / scroll) or a
          terminal resize (``curses.KEY_RESIZE``): the caller should repaint
          *immediately*, bypassing the key throttle (the help frame is static
          and cheap to rebuild; a resize must reflow to the new dimensions at
          once).
        - ``"modal"``   — the key needs the terminal (a popup). ``_pending``
          names what to run; the caller calls ``_run_pending`` and repaints.
        - ``"ignored"`` — unmapped key / non-character: no state change.

        Pure (no curses I/O) so it can be unit-tested without a terminal —
        which is exactly why a popup cannot happen here. Same separation v4
        arrives at (its handler sets a flag, ``display()`` draws the popup),
        made deliberate.
        """
        # Terminal resize (SIGWINCH → curses.KEY_RESIZE): force an immediate
        # repaint so the layout reflows to the new dimensions without waiting
        # for the next refresh cycle. Handled before the help check so it works
        # in every mode; it must not close the help overlay.
        if key == curses.KEY_RESIZE:
            return "repaint"

        # While the help overlay is open it captures every key: scrolling and
        # closing only — q / ESC / h close the help instead of quitting.
        if self._view.show_help:
            return self._handle_help_key(key)

        if key == 27:  # ESC always quits (not a printable hotkey).
            return "quit"
        # Keys with no character to be keyed by (arrows) are looked up FIRST:
        # `chr(curses.KEY_UP)` is a real character, so leaving them to the
        # character table would silently shadow whatever letter that is.
        action = self._special_hotkeys().get(key)
        if action is None:
            try:
                ch = chr(key)
            except ValueError:
                return "ignored"
            action = self._HOTKEYS.get(ch)
        if action is None:
            return "ignored"
        # A key that needs a selected process does nothing without a cursor.
        if action.get("cursor") and not self._cursor_enabled:
            return "ignored"
        if "action" in action:
            return self._handle_action(action["action"])
        if "switch" in action:
            attr = action["switch"]
            setattr(self._view, attr, not getattr(self._view, attr))
            return "changed"
        if "hide" in action:
            # v4 SHOW/HIDE parity. The whole tuple flips as one unit, keyed on
            # its FIRST member, so a compound key (`f` → fs+folders) can never
            # land half-hidden however its members were toggled individually
            # beforehand.
            names = action["hide"]
            if names[0] in self._view.hidden_plugins:
                self._view.hidden_plugins.difference_update(names)
            else:
                self._view.hidden_plugins.update(names)
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

    # Verbs that need the terminal, so they are deferred to `_run_pending`
    # rather than executed in this pure function (design 5.4).
    _MODAL_VERBS = frozenset(
        {"kill_process", "nice_increase", "nice_decrease", "extended", "edit_filter", "reset_minmax"}
    )
    # Of those, the ones that CHANGE the process. `e` only looks at it, which
    # is why it is allowed to look at Glances itself (`_selected_process`).
    _MUTATING_VERBS = frozenset({"kill_process", "nice_increase", "nice_decrease"})

    def _handle_action(self, verb: str) -> str:
        """Execute an ``action`` entry's verb. Pure, like its caller."""
        if verb == "quit":
            return "quit"
        if verb == "help":
            self._view.show_help = True
            self._help_scroll = 0
            return "repaint"
        if verb in self._MODAL_VERBS:
            self._pending = verb
            return "modal"
        if verb == "fs_free_space":
            # First press resolves the tri-state against what the fs payload
            # is currently showing, so it always visibly flips -- the same
            # rule the browser's TOGGLE VIEW overrides follow. Read from the
            # store rather than cached at render time: the payload IS the
            # source of truth, and a cache would go stale against a config
            # reload.
            current = self._view.fs_free_space
            if current is None:
                fs = self.store.as_dict().get("fs")
                current = bool(fs.get("free_space")) if isinstance(fs, dict) else False
            self._view.fs_free_space = not current
            return "changed"
        if verb in ("cursor_up", "cursor_down") and self._view.extended:
            # v4 freezes the cursor while extended stats are on
            # (`glances_curses.py:356`), so the block cannot describe a
            # moving target. Press `e` again to move on.
            return "ignored"
        if verb == "cursor_up":
            if self._view.cursor_position == 0:
                return "ignored"
            self._view.cursor_position -= 1
            return "changed"
        if verb == "cursor_down":
            # The ceiling is what the last frame DREW, not how many processes
            # exist: the selection must stay visible (design 5.3).
            if self._view.cursor_position >= self._cursor_max - 1:
                return "ignored"
            self._view.cursor_position += 1
            return "changed"
        if verb in ("sort_prev", "sort_next"):
            self._step_sort(-1 if verb == "sort_prev" else 1)
            return "changed"
        if verb == "command_left":
            if self._view.command_offset == 0:
                return "ignored"
            self._view.command_offset -= 1
            return "changed"
        if verb == "command_right":
            # No ceiling: the longest argument string on screen is not known
            # until the frame is built, and clamping to it would make the key
            # stop working because of a row the user cannot see. Scrolling
            # past the end shows an empty column, which is self-correcting.
            self._view.command_offset += 1
            return "changed"
        if verb == "refresh":
            # v4's `_handle_refresh` (`glances_curses.py:432-433`). Silent by
            # nature: nothing visible happens until the next collection cycle,
            # and a popup on every refresh would be worse than saying nothing.
            try:
                glances_processes.reset_internal_cache()
            except Exception as e:  # pragma: no cover — defensive
                logger.warning("TUI: reset_internal_cache failed: %s", e)
            return "changed"
        if verb == "erase_filter":
            # No popup: erasing is unambiguous and instant. The min/max go
            # with it -- they describe a set of processes that no longer
            # exists, and keeping them would make the next filter start from
            # the previous one's extremes.
            self._set_filter(None)
            return "changed"
        if verb == "full_quicklook":
            # Toggle full-width quicklook: EVERY other TOP block goes, so the
            # row holds quicklook alone
            # (``curses_renderer_v5._FULL_QUICKLOOK_HIDDEN``, a deliberate v4
            # divergence recorded there). A stats-view mutation, so it returns
            # ``"changed"`` like the other view switches.
            self._full_quicklook = not self._full_quicklook
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

    # An escape sequence ncurses handed back unassembled, mapped to the key
    # it stands for. `\x1bOA` is what a terminal sends for Up in APPLICATION
    # cursor mode (terminfo `kcud1`, which ncurses switches on via `smkx`);
    # `\x1b[A` is the NORMAL-mode form. ncurses translates whichever one its
    # terminfo entry lists, and hands the other back byte by byte -- so under
    # tmux, screen, or a TERM whose entry covers only one of the two, an arrow
    # key arrives here as a bare ESC followed by its tail.
    _ESCAPE_SEQUENCES: dict[str, int] = {
        "[A": curses.KEY_UP,
        "OA": curses.KEY_UP,
        "[B": curses.KEY_DOWN,
        "OB": curses.KEY_DOWN,
        # Left and right were absent until these keys were bound: an
        # untranslated `\x1b[C` was swallowed as an unknown sequence and the
        # command column simply did not scroll. Found in a pty, not in a test
        # -- the four horizontal arrows are only as useful as the terminal's
        # encoding is understood.
        "[C": curses.KEY_RIGHT,
        "OC": curses.KEY_RIGHT,
        "[D": curses.KEY_LEFT,
        "OD": curses.KEY_LEFT,
    }
    # Longest tail `_read_key` will drain after an ESC before giving up.
    _ESCAPE_TAIL_MAX = 6

    @staticmethod
    def _unget(key: int) -> None:
        """Push a key back for the next read. A no-op where curses cannot."""
        try:
            curses.ungetch(key)
        except (curses.error, AttributeError):  # pragma: no cover — no terminal
            pass

    def _read_key(self, window) -> int:
        """Read one key from `window`, resolving an escape sequence ncurses did not.

        A bare 27 is ambiguous: the user pressed Esc, OR ncurses is handing
        back a sequence it could not translate, one byte at a time. Telling
        them apart takes exactly one non-blocking read -- a real Esc has
        nothing behind it.

        Getting this wrong is not cosmetic: 27 means QUIT, so an untranslated
        arrow key would exit Glances. That was invisible until 2.X-b bound the
        arrows, but it was never only about arrows -- a mouse report, a
        bracketed paste or an unmapped function key is an escape sequence too,
        and each of them quit Glances.
        """
        key = window.getch()
        if key != 27:
            return key
        # Peek: `nodelay` so a real Esc costs nothing.
        window.nodelay(True)
        try:
            tail = ""
            for _ in range(self._ESCAPE_TAIL_MAX):
                nxt = window.getch()
                if nxt == -1:
                    break
                tail += chr(nxt) if 0 <= nxt < 0x110000 else ""
                resolved = self._ESCAPE_SEQUENCES.get(tail)
                if resolved is not None:
                    return resolved
                # Only `[` (CSI) or `O` (SS3) can start a sequence. Anything
                # else means the Esc was a real Esc and this key is the user's
                # next one, so give it back rather than eat it.
                if len(tail) == 1 and tail not in ("[", "O"):
                    self._unget(nxt)
                    tail = ""
                    break
                # A CSI/SS3 sequence ends at its final byte (0x40-0x7E). Reading
                # past it would swallow real keystrokes -- which in a text field
                # means characters the user typed and never saw.
                if len(tail) > 1 and 0x40 <= nxt <= 0x7E:
                    break
        finally:
            # `nodelay(False)` is `wtimeout(-1)` -- blocking. Both callers
            # re-apply their own `timeout()` before the next read: `_loop` at
            # the top of every iteration, `_popup_input` inside its loop.
            window.nodelay(False)
        # Nothing followed -> a real Esc. Something followed but we do not
        # know it -> swallow it rather than quit or dispatch its tail as
        # separate keystrokes.
        return 27 if not tail else -1

    # ------------------------------------------- popups & process actions

    # How long an informational popup stays up when the user presses nothing.
    _POPUP_INFO_SECONDS = 3.0
    # Longest a confirmation popup blocks in one `getch`, so `stop()` is
    # honoured within that bound instead of waiting for an answer forever.
    _POPUP_GETCH_BLOCK = 0.25
    # Visible width of a text field, and a floor for the popup that holds it.
    _INPUT_FIELD = 40
    _POPUP_MIN_WIDTH = 60

    def _ordered_process_items(self, snapshot: dict[str, Any]) -> list[dict[str, Any]]:
        """The process items in render order, filtered exactly as the
        renderer filters them — so index *i* here is the row the renderer
        draws at *i*."""
        payload = snapshot.get(self._cursor_block_name())
        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, list):
            return []
        return [item for item in data if isinstance(item, dict)]

    def _extended_payload(self) -> dict[str, Any] | None:
        """The engine's accumulated extended stats, or None.

        Read HERE and handed to the renderer through the per-cycle `view`,
        rather than letting the renderer reach for the engine singleton: the
        renderers are pure functions of (payload, fields, view), and this is
        the only way to keep them so. It also keeps the extended stats out of
        the REST payload entirely, which is what the TUI-only decision for
        2.X-b requires (design §8.1).

        The pid guard matters on two cycles: the one after `e` is pressed
        (the engine has not grabbed yet) and the one after the selection
        changes. Showing the previous process' numbers under the new name
        would be worse than showing nothing.
        """
        if not self._view.extended:
            return None
        payload = getattr(glances_processes, "extended_process", None)
        if not isinstance(payload, dict):
            return None
        if payload.get("pid") != getattr(glances_processes, "extended_pid", None):
            return None
        return payload

    def _filter_summary(self) -> dict[str, dict[str, float]] | None:
        """The three aggregate rows v4 draws under a FILTERED process table.

        None when no filter is set — the key's absence is the signal, as it is
        for `extended_process`.

        The sum is computed by the renderer's pure `summarise`; the min/max
        across frames are folded in here, because a pure renderer cannot
        remember. v4 keeps them on the plugin instance instead, which is what
        makes its renderer stateful.

        `_cursor_items` is the list the frame is being built from, so the
        summary describes exactly the rows on screen.
        """
        if glances_processes.process_filter is None:
            return None
        current = summarise(self._cursor_items)
        low, high = self._view.filter_mmm["min"], self._view.filter_mmm["max"]
        for key, value in current.items():
            low[key] = value if key not in low else min(low[key], value)
            high[key] = value if key not in high else max(high[key], value)
        return {"current": current, "min": dict(low), "max": dict(high)}

    def _selected_process(self, *, mutating: bool = True) -> tuple[dict[str, Any] | None, str | None]:
        """Resolve the cursor to a process, or to a reason it cannot be.

        Returns ``(process, None)`` or ``(None, reason)``. Every refusal is a
        sentence the user reads in a popup — an interactive key that silently
        does nothing is the defect this whole path exists to avoid.

        ``mutating=False`` (``e``) drops the own-pid refusal: watching
        Glances' own extended stats is legitimate and harmless, and refusing
        it would be the surprise, not the protection.
        """
        if self._view.programs:
            # v4 resolves the pid from the `processlist` plugin even while the
            # PROGRAM list is on screen (`glances_curses.py:638`, `:641`,
            # `:647`), so it acts on a row other than the one it shows. v5's
            # `programlist` payload carries no pid at all, and reproducing the
            # v4 behaviour would mean reproducing that bug (design 8.3).
            return None, "Not available in the program view.\n\nPress `j` to go back to the process list."
        if self._view.cursor_position >= len(self._cursor_items):
            return None, "No process is selected."
        process = self._cursor_items[self._view.cursor_position]
        pid = process.get("pid")
        if not isinstance(pid, int):
            return None, "The selected process has no PID."
        if mutating and pid == os.getpid():
            # `glances_processes.kill` guards this with a bare `assert`
            # (`processes.py:782`), which `python -O` strips. Check it here,
            # and for every mutating action rather than just for `kill`.
            return None, "That is Glances itself."
        return process, None

    def _step_sort(self, step: int) -> None:
        """Move the process sort one place along v4's own loop.

        `sort_processes_stats_list` (`processes.py:33-34`) is the list v4
        steps through, and the engine is the only holder of the current key —
        so the position is read back from it rather than tracked here, which
        keeps a sort set by `c`/`m`/`u` and one set by the arrows the same
        thing.
        """
        loop = list(sort_processes_stats_list)
        current = getattr(glances_processes, "sort_key", None)
        position = loop.index(current) if current in loop else 0
        try:
            glances_processes.set_sort_key(loop[(position + step) % len(loop)], False)
        except Exception as e:  # pragma: no cover — defensive
            logger.warning("TUI: set_sort_key failed: %s", e)

    def _set_filter(self, pattern: str | None) -> None:
        """Apply a process filter, or clear it, and reset the summary memory.

        The engine's filter is what `get_list()` is filtered by, so this is
        the same property `-f/--process-filter` writes. Global to the
        process — which in v5 means global to the TUI and its exporters and
        to nothing else: `main_v5.assemble` starts either the REST API or the
        TUI, never both, so a filter typed here cannot reach a browser.
        """
        glances_processes.process_filter = pattern
        self._view.filter_mmm = {"min": {}, "max": {}}

    def _run_pending(self, stdscr) -> None:
        """Execute the popup-bearing action `_handle_key` deferred.

        The pid is captured ONCE, before any popup, and the action runs
        against that captured value — never re-resolved through the cursor
        afterwards. The list re-sorts every cycle, so an index resolved after
        a confirmation can address a different process than the one the
        confirmation named (design 5.6).
        """
        verb, self._pending = self._pending, None
        if verb is None:  # pragma: no cover — defensive
            return
        if verb == "edit_filter":
            self._edit_filter(stdscr)
            return
        if verb == "reset_minmax":
            if glances_processes.process_filter is None:
                # v4 reads this flag INSIDE `if process_filter is not None`
                # (`processlist/__init__.py:648-650`), so without a filter the
                # key does nothing at all and says nothing either.
                self._popup_info(stdscr, "No process filter is set.\n\nPress ENTER to set one.")
                return
            self._view.filter_mmm = {"min": {}, "max": {}}
            return
        if verb == "extended" and self._view.extended:
            # Turning it OFF needs no selection at all -- and must not be
            # refused by one, or `e` would be a trap in the program view.
            self._set_extended(None)
            return
        process, refusal = self._selected_process(mutating=verb in self._MUTATING_VERBS)
        if refusal is not None:
            self._popup_info(stdscr, refusal)
            return
        if process is None:  # pragma: no cover — `_selected_process` pairs them
            return
        pid = int(process["pid"])
        name = str(process.get("name") or "?")
        if verb == "extended":
            self._set_extended(pid)
            return
        if verb == "kill_process" and not self._popup_yesno(stdscr, f"Kill {name} (pid {pid})?"):
            return
        self._apply_process_action(stdscr, verb, pid, name)

    def _set_extended(self, pid: int | None) -> None:
        """Turn extended stats on for `pid`, or off when it is None.

        Two divergences from v4, both in `enable_extended` / `disable_extended`
        (`processes.py:210-217`):

        - v4's `enable_extended()` calls `update()` synchronously. From the TUI
          thread that is a second full process collection racing the
          collector's own. Setting the tag costs one refresh interval of
          latency and no race.
        - Turning it OFF also clears `extended_process`, which is what
          actually stops the engine grabbing: the grab is keyed on
          `extended_process` being set (`processes.py:663-669`), not on
          `disable_extended_tag`. v4 leaves it set and keeps paying for it
          after `e` is pressed again; only its renderer stops looking.
        """
        self._view.extended = pid is not None
        glances_processes.extended_pid = pid
        glances_processes.disable_extended_tag = pid is None
        if pid is None:
            glances_processes.extended_process = None

    _FILTER_PROMPT = "Process filter (regex, empty to clear): "
    _FILTER_HELP = (
        "Examples:  python  |  .*python.*  |  name:.*nautilus.*\n           cmdline:.*glances.*  |  username:^root"
    )

    def _edit_filter(self, stdscr) -> None:
        """Prompt for a filter pattern and apply it.

        An invalid regex is REPORTED. `GlancesFilter`'s setter compiles the
        pattern, and on failure sets the filter back to None and writes a log
        line (`glances/filter.py:141-145`) — so in v4 a typo is a keypress
        that does nothing at all, with no feedback anywhere the user is
        looking. Comparing what went in against what came back is the only
        way to tell "cleared" from "rejected" through that API.
        """
        current = getattr(glances_processes, "process_filter_input", None) or ""
        pattern = self._popup_input(stdscr, self._FILTER_PROMPT, current)
        if pattern is None:
            return  # ESC: nothing was touched.
        pattern = pattern.strip()
        self._set_filter(pattern or None)
        if pattern and glances_processes.process_filter is None:
            self._popup_info(stdscr, f"Not a valid filter pattern:\n\n  {pattern}\n\n{self._FILTER_HELP}")

    def _apply_process_action(self, stdscr, verb: str, pid: int, name: str) -> None:
        """Call the engine for `verb` on `pid`, reporting every failure.

        v4 logs a refused nice change and shows nothing (`processes.py:767`,
        `:778`); a TUI user has no log to read, so the key looks broken. Here
        every outcome that is not "it worked" reaches the screen.
        """
        label = f"{name} (pid {pid})"
        try:
            if verb == "kill_process":
                glances_processes.kill(pid)
            elif verb == "nice_increase":
                if not glances_processes.nice_increase(pid):
                    self._popup_info(stdscr, f"Not allowed to renice {label}.")
            elif verb == "nice_decrease":
                if not glances_processes.nice_decrease(pid):
                    self._popup_info(stdscr, f"Not allowed to renice {label}.\n\nLowering a nice value needs root.")
        except psutil.NoSuchProcess:
            self._popup_info(stdscr, f"{label} is already gone.")
        except psutil.AccessDenied:
            self._popup_info(stdscr, f"Not allowed to act on {label}.")
        except Exception as e:  # noqa: BLE001 — psutil raises widely; never kill the TUI over it
            logger.warning("TUI: %s on pid %s failed: %s", verb, pid, e)
            self._popup_info(stdscr, f"Could not act on {label}:\n\n{e}")

    def _popup_window(self, stdscr, message: str, *, extra_rows: int = 0):
        """Draw a centred bordered popup, or return None if it does not fit.

        v4 aborts the same way rather than clipping (`glances_curses.py:1041-1043`).
        `extra_rows` reserves space the caller will draw into itself.
        """
        max_y, max_x = stdscr.getmaxyx()
        lines = message.split("\n")
        width = max((len(line) for line in lines), default=0) + 4
        height = len(lines) + 4 + extra_rows
        if width > max_x or height > max_y:
            logger.info("TUI: popup does not fit (%s)", " ".join(lines))
            return None
        try:
            win = curses.newwin(height, width, (max_y - height) // 2, (max_x - width) // 2)
            win.border()
            for i, line in enumerate(lines):
                win.addnstr(2 + i, 2, line, width - 4)
            win.keypad(True)
            win.refresh()
        except curses.error as e:  # pragma: no cover — terminal-dependent
            logger.warning("TUI: could not draw popup: %s", e)
            return None
        return win

    def _popup_info(self, stdscr, message: str) -> None:
        """Show `message` until the user presses a key, or for a few seconds.

        v4 naps for the whole duration (`glances_curses.py:1060`) and ignores
        both the keyboard and `stop()` while it does.
        """
        win = self._popup_window(stdscr, message)
        if win is None:
            return
        win.timeout(int(self._POPUP_INFO_SECONDS * 1000))
        win.getch()

    # Keys that submit a text field, and keys that erase one character. 127 is
    # DEL, which is what most terminals actually send for Backspace; 8 is
    # ^H, which some still do.
    _INPUT_SUBMIT = (ord("\n"), curses.KEY_ENTER, 10, 13)
    _INPUT_ERASE = (curses.KEY_BACKSPACE, 127, 8)

    def _popup_input(self, stdscr, message: str, value: str = "") -> str | None:
        """Ask for a line of text. Returns it, or None if the user cancelled.

        Own loop rather than `curses.textpad.Textbox`, which v4 wraps in a
        `GlancesTextbox` subclass just to make Enter submit
        (`glances_curses.py:1426-1435`). Textbox has no CANCEL, and cancel is
        the case that matters here: a user who opened the filter prompt by
        accident would otherwise have to clear the field by hand to get back
        to where they were. ESC returns None and nothing is touched.
        """
        width = max(len(message) + self._INPUT_FIELD + 4, self._POPUP_MIN_WIDTH)
        win = self._popup_window(stdscr, message.ljust(width - 4), extra_rows=0)
        if win is None:
            return None
        text = value or ""
        try:
            curses.curs_set(1)
        except curses.error:  # pragma: no cover — terminal-dependent
            pass
        try:
            while not self._stop_event.is_set():
                # Re-applied every pass: `_read_key`'s peek leaves the window
                # blocking, and a blocking read would stop honouring `stop()`.
                win.timeout(int(self._POPUP_GETCH_BLOCK * 1000))
                # Redraw the field each pass: the shown tail is the last
                # `_INPUT_FIELD` characters, so a pattern longer than the box
                # scrolls instead of vanishing off the edge.
                shown = text[-self._INPUT_FIELD :]
                try:
                    win.addnstr(2, 2 + len(message), shown.ljust(self._INPUT_FIELD), self._INPUT_FIELD)
                    win.move(2, 2 + len(message) + len(shown))
                    win.refresh()
                except curses.error:  # pragma: no cover — terminal-dependent
                    return None
                # Through `_read_key`, not `getch`: an untranslated arrow
                # key arrives as a bare 27 here too, and in a text field
                # cancelling on it would throw away what the user typed. Same
                # defect the main loop had, and the same one line of fix.
                key = self._read_key(win)
                if key == -1:
                    continue
                if key == 27:
                    return None
                if key in self._INPUT_SUBMIT:
                    return text
                if key in self._INPUT_ERASE:
                    text = text[:-1]
                    continue
                if 32 <= key < 127:
                    text += chr(key)
            return None
        finally:
            try:
                curses.curs_set(0)
            except curses.error:  # pragma: no cover — terminal-dependent
                pass

    def _popup_yesno(self, stdscr, message: str) -> bool:
        """Ask for confirmation. Anything but an explicit yes is a no."""
        win = self._popup_window(stdscr, f"{message}\n\nConfirm ([y]es / [n]o): ")
        if win is None:
            # A terminal too small to ask in is a terminal too small to
            # destroy something from.
            return False
        win.timeout(int(self._POPUP_GETCH_BLOCK * 1000))
        while not self._stop_event.is_set():
            key = win.getch()
            if key in (ord("y"), ord("Y")):
                return True
            if key in (ord("n"), ord("N"), 27, ord("q")):
                return False
        return False

    # ----------------------------------------------------------- run loop

    def run(self) -> None:
        try:
            _safe_curses_wrapper(self._loop)
        except Exception as e:  # pragma: no cover — defensive
            logger.warning("TUI v5 crashed: %s", e)

    def _loop(self, stdscr) -> None:
        _init_colors(self._theme)
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
            # Startup catch-up: the frame just painted was built *before* the
            # scheduler ran a single plugin update, so it carries headers and
            # no stats. Until every displayed plugin has published (or the
            # timeout fires) poll the store's publication counter and repaint
            # the moment data lands — otherwise that empty frame would be held
            # for a whole ``refresh_interval``. Closed for good afterwards:
            # steady-state cadence is unchanged.
            last_revision = self.store.revision
            startup_deadline = now + max(self._STARTUP_CATCHUP_TIMEOUT, 2 * self.refresh_interval)
            in_startup = not self._startup_catchup_over(now, startup_deadline)
            while not self._stop_event.is_set():
                now = time.monotonic()
                next_regular = last_paint + self.refresh_interval
                next_change = last_change_paint + self._MIN_KEY_REPAINT_INTERVAL if dirty else float("inf")
                block = max(0.0, min(min(next_regular, next_change) - now, self._MAX_GETCH_BLOCK))
                if in_startup:
                    block = min(block, self._STARTUP_POLL_INTERVAL)
                stdscr.timeout(int(block * 1000))

                key = self._read_key(stdscr)
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
                    if result == "modal":
                        # A popup: curses I/O, so it happens here and not in
                        # the pure `_handle_key`. Repaint unconditionally
                        # afterwards -- the popup window has to be erased
                        # whatever the user chose.
                        self._run_pending(stdscr)
                        self._repaint(stdscr)
                        now = time.monotonic()
                        last_paint = now
                        last_change_paint = now - self._MIN_KEY_REPAINT_INTERVAL
                        dirty = False
                        continue
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
                data_due = in_startup and self.store.revision != last_revision
                if regular_due or change_due or data_due:
                    last_revision = self.store.revision
                    self._repaint(stdscr)
                    last_paint = now
                    if change_due:
                        last_change_paint = now
                    dirty = False
                if in_startup and self._startup_catchup_over(now, startup_deadline):
                    in_startup = False
        finally:
            # `curses.endwin()` doesn't reliably restore cursor visibility
            # on every terminal — if we hid it, restore it ourselves so the
            # shell prompt that follows shows a blinking cursor.
            if cursor_was_hidden:
                try:
                    curses.curs_set(1)
                except curses.error:
                    pass

    def _startup_catchup_over(self, now: float, deadline: float) -> bool:
        """Return True when the startup catch-up window must close.

        It closes as soon as every plugin the TUI displays has published at
        least once, or on ``deadline`` — a plugin whose ``update()`` keeps
        failing (or a platform where it yields nothing) must not keep the fast
        polling alive for the whole session.
        """
        if now >= deadline:
            return True
        published = set(self.store.keys())
        return all(name in published for name, _ in self.registry)

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
            max_y, max_x = stdscr.getmaxyx()
            frame = self._build_fitted_frame(max_x, max_y)
            self._note_cursor_bound(frame)
            self._paint(stdscr, frame)
        stdscr.refresh()

    # Name of the process block the cursor addresses, per view mode. `j`
    # swaps which of the two is in the frame (`_frame_for_view`), and the
    # cursor follows whichever is actually drawn.
    def _cursor_block_name(self) -> str:
        return "programlist" if self._view.programs else "processlist"

    def _note_cursor_bound(self, frame: Frame) -> None:
        """Record how many process rows the frame drew, and clamp into it.

        The renderer is the authority: only it knows what the vertical-fit
        pass left room for. Row 0 of the block is the column header, so the
        item count is ``len(rows) - 1``.

        Clamping HERE as well as in ``_handle_key`` is not belt-and-braces:
        the terminal can shrink (or an alert can claim rows) under a cursor
        that never moved, and a stale index would decorate nothing while
        `k` still resolved it.
        """
        # The pin can end without the TUI asking: the pinned process exits and
        # the engine forgets it (`processes.py`, `extended_seen`). Re-sync, or
        # `e` would leave the cursor frozen on a block that is no longer drawn
        # and the next `e` would UNpin something already gone.
        if self._view.extended and glances_processes.extended_pid is None:
            self._view.extended = False

        block = next((b for b in frame.right if b.name == self._cursor_block_name()), None)
        self._cursor_max = max(0, len(block.rows) - 1) if block is not None else 0
        if self._view.cursor_position >= self._cursor_max:
            self._view.cursor_position = max(0, self._cursor_max - 1)
            self._repin_extended()

    def _repin_extended(self) -> None:
        """Keep the `e` block describing the row that is underlined.

        `e` freezes the cursor, so nothing the USER does can separate the two.
        A shrink can: the extended block spends four rows of the process
        list's budget, so turning it on near the bottom of a short terminal
        pulls the clamp down under a cursor that never moved — and then the
        pinned block and the underlined row name different processes, with
        `k` following the underline. Re-pinning keeps the one invariant that
        matters: what is described is what is selected.
        """
        if not self._view.extended:
            return
        if self._view.cursor_position >= len(self._cursor_items):
            return
        pid = self._cursor_items[self._view.cursor_position].get("pid")
        if isinstance(pid, int) and pid != glances_processes.extended_pid:
            self._set_extended(pid)

    # ----------------------------------------------------------- helpers

    # Default terminal width used when ``_build_frame`` is called without an
    # explicit one (unit tests that exercise frame assembly headless).
    _DEFAULT_MAX_X = 80

    def _build_frame(self, max_x: int | None = None) -> Frame:
        if max_x is None:
            max_x = self._DEFAULT_MAX_X
        return self._frame_for_view(self._build_view(max_x))

    def _frame_for_view(self, view: dict[str, Any]) -> Frame:
        """Build a :class:`Frame` from a fully-assembled ``view`` dict.

        Pure with respect to the view: the same ``view`` always yields an
        equivalent frame (modulo the live store snapshot), so the fitted-frame
        loop can call it repeatedly with escalating degradation flags to
        measure the resulting TOP-row width.
        """
        snapshot = self.store.as_dict()
        # Re-sort the process collections by the engine's *current* sort key
        # so a key change is reflected on the very next repaint, without
        # waiting for the engine's next update cycle to re-sort the store.
        self._apply_live_sort(snapshot)
        # The ordered list the process block is about to render, kept so that
        # `k` / `+` / `-` resolve the cursor against THE FRAME ON SCREEN and
        # not against a fresher snapshot taken at keypress time. Between a
        # paint and a keypress the collector may have published a differently
        # ordered list; resolving an index against that one would act on a
        # process other than the underlined row (design 5.6).
        self._cursor_items = self._ordered_process_items(snapshot)
        history = self.alerts.get_history() if self.alerts is not None else []
        # Distinguish "still in warmup" (alerts cannot fire yet) from "truly
        # empty history" — the alert block shows different placeholders for
        # the two cases.
        initializing = self.alerts.is_initializing() if self.alerts is not None else False
        ongoing = self.alerts.get_ongoing() if self.alerts is not None else {}
        # When each active alert started. `_history` is bounded, so a
        # long-running alert loses its own opening event; without this the
        # block renders its start as `--:--:--`.
        ongoing_since = self.alerts.get_ongoing_since() if self.alerts is not None else {}
        # The accumulated top processes of each active alert. Same
        # ring-buffer argument as `ongoing_since`: the engine outlives the
        # history entry that carries them.
        ongoing_top = self.alerts.get_ongoing_top() if self.alerts is not None else {}
        frame = build_frame(
            store_snapshot=snapshot,
            fields_by_plugin=self.fields_by_plugin,
            registry=self.registry,
            alerts_history=history,
            alerts_ongoing=ongoing,
            alerts_ongoing_since=ongoing_since,
            alerts_ongoing_top=ongoing_top,
            alerts_initializing=initializing,
            view=view,
        )
        # CPU ↔ perCPU mutual exclusion (v4 parity, hotkey '1').
        hidden_top = "cpu" if self._view.show_percpu else "percpu"
        frame.top = [b for b in frame.top if b.name != hidden_top]
        # Threads ↔ programs mutual exclusion (v4 parity, hotkey 'j'):
        # show exactly one of processlist / programlist.
        hidden_right = "processlist" if self._view.programs else "programlist"
        frame.right = [b for b in frame.right if b.name != hidden_right]
        return frame

    def _top_fits(self, frame: Frame, max_x: int) -> bool:
        """True iff the painter can lay the TOP row out without clipping.

        Mirrors ``_paint_top_row``'s fit test exactly: the row fits when the
        sum of the block widths plus the minimum inter-block gaps is within
        ``max_x``. An empty TOP row trivially fits.
        """
        widths = [b.width for b in frame.top]
        if not widths:
            return True
        return sum(widths) + (len(widths) - 1) * self._TOP_GAP_MIN <= max_x

    def _header_fits(self, frame: Frame, max_x: int) -> bool:
        """True iff the header row (system … ip … uptime … now) fits ``max_x``.

        Mirrors ``_paint_header``'s layout: the blocks plus one ``_HEADER_GAP``
        between each must be within ``max_x`` — the same requirement whether a
        block is packed left or right-aligned. An empty or single-block header
        trivially fits.
        """
        widths = [b.width for b in frame.header]
        if len(widths) <= 1:
            return True
        return sum(widths) + (len(widths) - 1) * self._HEADER_GAP <= max_x

    def _build_fitted_frame(self, max_x: int, max_y: int | None = None) -> Frame:
        """Build the frame, degrading the TOP row (a→f) until it fits ``max_x``.

        Measure-driven (not threshold-driven): rebuilds the pure, cheap frame
        with one extra degradation flag at a time and re-measures the real
        ``PluginBlock.width`` until ``_top_fits`` is satisfied. Wide terminals
        take the early return (one ``build_frame`` call, byte-identical output).
        Full-quicklook mode already owns the whole width via its own
        sibling-hiding, so it is exempt from the cascade.

        The vertical fit (``_fit_right_column``) runs LAST, on both return
        paths: the body height it budgets against depends on the TOP row
        height, which the horizontal cascade above is free to change.
        ``max_y is None`` skips it entirely (headless callers that only care
        about the width fit).
        """
        view = self._build_view(max_x)
        frame = self._frame_for_view(view)
        if self._full_quicklook:
            frame = self._fit_full_quicklook(view, frame, max_x)
        if self._full_quicklook or self._top_fits(frame, max_x):
            frame = self._fit_header(view, frame, max_x)
            frame = self._fit_right_width(view, frame, max_x)
            return frame if max_y is None else self._fit_right_column(view, frame, max_y)
        for key, val in _DEGRADE_STEPS:
            view[key] = val
            frame = self._frame_for_view(view)
            if self._top_fits(frame, max_x):
                break
        frame = self._fit_header(view, frame, max_x)
        frame = self._fit_right_width(view, frame, max_x)
        return frame if max_y is None else self._fit_right_column(view, frame, max_y)

    # v4 spacing between TOP plugins (`space_between_column`), kept around the
    # siblings full-quicklook mode leaves on the row.
    _FULL_QUICKLOOK_GAP = 3

    def _fit_full_quicklook(self, view: dict[str, Any], frame: Frame, max_x: int) -> Frame:
        """Size the full-quicklook bars from the room the TOP row actually leaves.

        `_build_view`'s provisional `max_x - 8` guesses the label/bracket
        overhead; this measures it on the provisional frame instead, so the
        bars end exactly at the right edge rather than 'about there'. One
        rebuild settles it.

        `_FULL_QUICKLOOK_HIDDEN` now takes every sibling off the row, so
        `others` is normally empty and the subtraction is a no-op — it is kept
        because the sibling set is derived from `TOP_SLOT`, and a plugin
        deliberately exempted from the mode later would land here with its
        spacing correctly accounted for.
        """
        quicklook = next((b for b in frame.top if b.name == "quicklook"), None)
        if quicklook is None:
            return frame
        others = [b.width for b in frame.top if b is not quicklook]
        overhead = quicklook.width - view["quicklook_width"]
        bar_width = max_x - sum(others) - len(others) * self._FULL_QUICKLOOK_GAP - overhead
        view["quicklook_width"] = max(20, bar_width)
        return self._frame_for_view(view)

    def _fit_header(self, view: dict[str, Any], frame: Frame, max_x: int) -> Frame:
        """Degrade the header row (system … ip … uptime … now) until it fits ``max_x``.

        Independent of the TOP-row degrade above: measures the real header
        block widths and applies the cumulative ``_HEADER_DEGRADE_STEPS``
        (hide cloud → drop ip location → drop OS info → hide now → hide ip →
        hide uptime) until ``_header_fits``. Wide terminals take the early
        return (no extra rebuild); the header and TOP degrade flags coexist in
        the same ``view``.
        """
        if self._header_fits(frame, max_x):
            return frame
        for key, val in _HEADER_DEGRADE_STEPS:
            view[key] = val
            frame = self._frame_for_view(view)
            if self._header_fits(frame, max_x):
                break
        return frame

    def _fit_right_width(self, view: dict[str, Any], frame: Frame, max_x: int) -> Frame:
        """Tell the RIGHT-column renderers the width they will be painted at.

        The right sidebar is painted at
        ``right_width = max_x - left_width - _SIDEBAR_SEPARATOR_GAP`` (mirrors
        ``_paint``). Feeding that as ``view["right_width"]`` lets the
        processlist drop low-priority columns to keep ``Command`` readable,
        and lets the alert block pick a grid that fits (design §6.1).

        ``left_width`` depends only on ``frame.left`` natural widths — NOT on
        any right-column renderer's own columns. ``_build_view`` never seeds a
        prior ``right_width``, so the comparison below is always a change and
        this extra rebuild fires on every repaint, not just on resize — it is
        cheap and pure (idempotent), but unlike ``_fit_right_column`` it does
        not short-circuit on an unchanged value. Seeding a cached width into
        ``view`` the way ``row_budget`` is seeded (see ``_PREFIT_ROW_BUDGET``)
        is what would let it do so.
        """
        if not frame.right:
            return frame
        _, _, right_width = self._body_columns(frame, max_x)
        if right_width and view.get("right_width") != right_width:
            view["right_width"] = right_width
            frame = self._frame_for_view(view)
        return frame

    # RIGHT-column blocks whose height the vertical budget controls. Anything
    # else in the column (currently `processcount`) is non-elastic.
    _ELASTIC_RIGHT = frozenset({"vms", "containers", "processlist", "programlist", "alert", "amps"})

    def _fit_right_column(self, view: dict[str, Any], frame: Frame, max_y: int) -> Frame:
        """Give each RIGHT-column block the number of rows the terminal height
        allows, then rebuild once if that changes anything.

        Mirrors ``_fit_right_width`` on the vertical axis: the plan is
        computed by the pure ``plan_right_column`` solver from the real item
        counts (``PluginBlock.data_count``), so a single rebuild settles it.
        """
        _, body_height = self._body_geometry(frame, max_y)
        if body_height <= 0:
            return frame

        by_name = {b.name: b for b in frame.right}

        def count(name: str) -> int:
            block = by_name.get(name)
            return block.data_count or 0 if block else 0

        # processlist and programlist are mutually exclusive — exactly one is
        # in the frame at any time (see `_frame_for_view`).
        n_processes = count("processlist") or count("programlist")
        plan = plan_right_column(
            body_height=body_height,
            static_heights={b.name: b.height for b in frame.right if b.name not in self._ELASTIC_RIGHT},
            amps_height=by_name["amps"].height if "amps" in by_name else 0,
            n_vms=count("vms"),
            n_containers=count("containers"),
            n_processes=n_processes,
            n_alerts=count("alert"),
            n_ongoing=by_name["alert"].data_pinned if "alert" in by_name else 0,
            # The `e` block and the filtered summary sit inside the process
            # block but cost rows the solver's "one line per data row" model
            # does not know about.
            process_extra_rows=process_extra_rows(view),
        )

        current = view.get("row_budget") or {}

        # Compare the EFFECTIVE row counts, not the raw quotas: a quota above
        # the item count renders exactly the same block, and rebuilding for
        # that would cost one extra frame on every single cycle.
        def effective(budget: dict[str, int], name: str) -> int:
            available = count(name) if name != "amps" else (by_name["amps"].height if "amps" in by_name else 0)
            quota = budget.get(name)
            return available if quota is None else min(available, quota)

        names = set(plan) | set(current)
        if all(effective(plan, n) == effective(current, n) for n in names):
            return frame

        view["row_budget"] = plan
        return self._frame_for_view(view)

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

    # Compact-mode target width (cells) for the quicklook bars — a single
    # TOP-slot column. Full mode widens them to (almost) the whole terminal.
    _QUICKLOOK_COMPACT_WIDTH = 38

    # Pre-fit row budget: a cost bound only. The vertical fit pass replaces it
    # with the exact, height-driven budget — but without it the first frame of
    # every cycle would render every process and every container just to throw
    # the rows away.
    _PREFIT_ROW_BUDGET = {
        "vms": 10,
        "containers": 10,
        "processlist": 20,
        "programlist": 20,
        "alert": 10,
    }

    def _build_view(self, max_x: int) -> dict[str, Any]:
        """Assemble the per-cycle ``view`` dict passed to ``build_frame``.

        Extends ``_render_view`` (process switches + engine sort) with the
        quicklook keys consumed by ``build_frame`` (``full_quicklook``
        hides TOP siblings) and the quicklook renderer (``percpu`` draws
        per-core bars, ``quicklook_width`` sizes them). ``max_x`` is the
        terminal width, known only at paint time."""
        view = self._render_view()
        view["full_quicklook"] = self._full_quicklook
        view["percpu"] = self._percpu
        view["meangpu"] = self._view.meangpu
        view["fahrenheit"] = self._fahrenheit
        view["hide_public_info"] = self._hide_public_info
        view["byte"] = self._view.byte
        view["diskio_iops"] = self._view.diskio_iops
        view["diskio_latency"] = self._view.diskio_latency
        view["load_irix"] = self._view.load_irix
        view["network_sum"] = self._view.network_sum
        view["network_cumul"] = self._view.network_cumul
        # Only published when the viewer has pressed `F`; absent means the fs
        # renderer keeps reading its payload metadata.
        if self._view.fs_free_space is not None:
            view["fs_free_space"] = self._view.fs_free_space
        # Published only when the cursor is enabled, so `--disable-cursor`
        # reaches the renderer as an ABSENT key -- the same "no key, no
        # decoration" path export and the tests already take.
        if self._cursor_enabled:
            view["cursor_position"] = self._view.cursor_position
        view["command_offset"] = self._view.command_offset
        extended = self._extended_payload()
        if extended is not None:
            view["extended_process"] = extended
        summary = self._filter_summary()
        if summary is not None:
            view["filter_summary"] = summary
        view["unicode"] = self._unicode
        # The user's own SHOW/HIDE set. A frozenset, so the per-cycle view
        # cannot be a back door onto the live ViewState (the fit loops copy
        # and mutate `view` freely).
        view["user_hidden"] = frozenset(self._view.hidden_plugins)
        # Full mode: bars span (almost) the whole width; compact: a column.
        view["quicklook_width"] = max(20, max_x - 8) if self._full_quicklook else self._QUICKLOOK_COMPACT_WIDTH
        view["row_budget"] = dict(self._PREFIT_ROW_BUDGET)
        return view

    # ----------------------------------------------------------- paint

    # Sidebar split spacing (left ↔ right column gap below the top row).
    _SIDEBAR_SEPARATOR_GAP = 2
    # Minimum gap between two adjacent top-row blocks when the terminal
    # is too narrow to distribute extra space — fallback only.
    _TOP_GAP_MIN = 1

    def _body_geometry(self, frame: Frame, max_y: int) -> tuple[int, int]:
        """Return ``(body_y0, body_height)`` — the region below the top row.

        Single source of truth shared by the painter and by the vertical fit
        pass: the RIGHT column budget is computed against the very same
        height the painter will honour.

        Note: it measures DECLARED block heights, while ``_paint_header`` and
        ``_paint_top_row`` return PAINTED heights. The two diverge only when a
        header or top block is skipped for lack of width, and the error
        direction is safe: the body then starts lower than it had to, leaving a
        blank band — never an overlap.
        """
        header_height = max((b.height for b in frame.header), default=0)
        y = header_height + (1 if header_height else 0)
        top_height = max((b.height for b in frame.top), default=0)
        y += top_height + (1 if top_height else 0)
        return (y, max(0, max_y - y))

    def _paint(self, stdscr, frame: Frame) -> None:
        """Lay out the frame on the terminal, mirroring v4:

        header line        (hostname/OS ...... Uptime  Now)  row 0
        <separator line>
        top blocks         (cpu | mem | load | ...)  side-by-side
        <separator line>
        left blocks         right blocks              two vertical columns
        """
        stdscr.erase()
        max_y, max_x = stdscr.getmaxyx()

        # 0. Header line (system flush-left, uptime flush-right).
        header_height = self._paint_header(stdscr, frame.header, 0, max_x)

        # 0b. Separator between the header and the top row (v4 parity). The
        # row is always reserved when a header is present — with separators
        # disabled it stays blank rather than collapsing.
        top_y0 = header_height
        if header_height > 0 and top_y0 < max_y:
            self._paint_separator(stdscr, top_y0, 0, max_x)
            top_y0 += 1

        # 1. Top row, below the header (and its separator).
        top_height = self._paint_top_row(stdscr, frame.top, top_y0, max_x)

        # 2. Separator under the top row (if any top content was painted).
        if top_height > 0 and top_y0 + top_height < max_y:
            self._paint_separator(stdscr, top_y0 + top_height, 0, max_x)

        # 3. Below the top row: left + right sidebars side-by-side. The
        # geometry comes from `_body_geometry` so the painter and the vertical
        # fit pass can never disagree on the available height.
        body_y0, body_height = self._body_geometry(frame, max_y)
        if body_height > 0:
            left_width, right_x, right_width = self._body_columns(frame, max_x)

            self._paint_sidebar(stdscr, frame.left, body_y0, 0, left_width, body_height)
            self._paint_sidebar(stdscr, frame.right, body_y0, right_x, right_width, body_height)

    @staticmethod
    def _sidebar_split(frame: Frame, max_x: int) -> int:
        """Width allocated to the left sidebar — bounded like v4
        (`_left_sidebar_min_width=23`, `_left_sidebar_max_width=34`).

        An EMPTY left column takes no width at all. v4's minimum is a floor
        for a column that HAS content, not a reservation: without this guard
        the 23-column floor applied to an absent sidebar, so hiding it (`2`,
        or its plugins one by one) left a blank 23-column band and the right
        column stayed exactly where it was.
        """
        if not frame.left:
            return 0
        natural = max((b.width for b in frame.left), default=0)
        # +2 for breathing room, mirroring v4's column gap.
        natural = max(natural + 2, 23)
        return min(natural, 34, max(1, max_x // 2))

    def _body_columns(self, frame: Frame, max_x: int) -> tuple[int, int, int]:
        """``(left_width, right_x, right_width)`` for the body's two columns.

        Single source of truth for the painter and for ``_fit_right_width``,
        so the width the right-column renderers are TOLD can never differ
        from the width they are painted at. The inter-column gap exists only
        when there is a left column to separate from.
        """
        left_width = self._sidebar_split(frame, max_x)
        right_x = left_width + self._SIDEBAR_SEPARATOR_GAP if left_width else 0
        return left_width, right_x, max(0, max_x - right_x)

    # Horizontal gap between two adjacent header blocks, in either alignment
    # group (v4 parity: `space_between_column = 3` between system and ip).
    _HEADER_GAP = 3

    def _paint_header(self, stdscr, blocks: list[PluginBlock], y0: int, max_x: int) -> int:
        """Paint the header line (v4 parity): the blocks of `HEADER_SLOT_LEFT`
        packed from the left edge, the blocks of `HEADER_SLOT_RIGHT`
        right-aligned as one group (v4 paints `system … ip … uptime` this way,
        `glances_curses.py` `__display_top`; v5 appends `now` at the far right).
        Returns the header height (0 when empty, else the tallest block
        painted — normally 1).

        The layout is generic (not ip- or now-specific): slot membership and
        order are owned by `HEADER_SLOT_*`; this painter just lays out whatever
        blocks it is handed without overlapping them. With a single right-group
        block the geometry reduces to the plain flush-right case.
        """
        if not blocks:
            return 0
        left_blocks = [b for b in blocks if b.name not in HEADER_SLOT_RIGHT]
        right_blocks = [b for b in blocks if b.name in HEADER_SLOT_RIGHT]
        height = 0
        # Left group: packed from x=0, each block separated by `_HEADER_GAP`.
        # Stop if we run past the right edge.
        x = 0
        for i, block in enumerate(left_blocks):
            if i:
                x += self._HEADER_GAP
            if x >= max_x:
                break
            self._paint_block(stdscr, block, y0, x, max(1, max_x - x), fit_to_term=False)
            height = max(height, block.height)
            x += block.width
        if not right_blocks:
            return height
        # Right group: right-aligned as a whole, but never overlapping the
        # left-packed blocks. `x` is 0 when the left group is empty, in which
        # case the group is free to start at the natural right-aligned offset.
        group_width = sum(b.width for b in right_blocks) + (len(right_blocks) - 1) * self._HEADER_GAP
        right_x = max_x - group_width
        if left_blocks:
            right_x = max(x + 1, right_x)
        for block in right_blocks:
            if right_x >= max_x:
                break
            self._paint_block(stdscr, block, y0, right_x, max(1, max_x - right_x), fit_to_term=False)
            height = max(height, block.height)
            right_x += block.width + self._HEADER_GAP
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
            # A zero-row block (e.g. `amps` with every `[amp_*]` section
            # disabled) must not cost a blank line — v4 parity
            # (`glances_curses.py:1230` returns 0 for an empty plugin).
            if not block.rows:
                continue
            if y >= end_y:
                break
            max_h = end_y - y
            painted = self._sidebar_block(block, max_h)
            if painted is None:
                # Dropped for lack of room. Leave `y` where it is: the line it
                # would have wasted on a lonely header goes to the next block.
                continue
            self._paint_block(stdscr, painted, y, x0, width, fit_to_term=True, max_height=max_h)
            # Advance by the number of rows actually painted (capped to the
            # remaining vertical room) plus one blank line. `_paint_block`
            # returns the width painted, not the height — using `block.height`
            # directly mirrors `_paint_top_row` and avoids the old bug where
            # the row width was added to `y` (visible as a large empty band
            # between two sidebar blocks).
            y += min(block.height, max_h) + 1

    @staticmethod
    def _sidebar_block(block: PluginBlock, max_h: int) -> PluginBlock | None:
        """Return `block` as it must be painted in `max_h` rows, or None to drop it.

        The LEFT sidebar has no vertical fit pass: a block that outgrows the
        remaining room is simply cut at `max_h` by `_paint_block`, silently
        hiding items. A block whose renderer marks its item rows
        (``Row.item_start``) gets the count folded into its header cell —
        "SENSORS 5/7" — so the cut is visible, and is dropped outright when not
        one item survives the cut ("SENSORS 0/18" is a header carrying no
        information). Blocks with no marked row (scalar plugins,
        `connections`) are returned untouched, cut included.

        RIGHT-column blocks never reach the cut: they truncate themselves
        against `row_budget` and build their own counter (containers, vms).
        """
        if block.height <= max_h:
            return block
        total = sum(1 for r in block.rows if r.item_start)
        # No marked row, or no header row to host the counter (`ports` is
        # deliberately title-less — it reads as a continuation of `network`).
        if not total or block.rows[0].item_start:
            return block
        shown = sum(1 for r in block.rows[:max_h] if r.item_start)
        if not shown:
            return None
        header, *rest = block.rows
        return replace(block, rows=[with_truncation_counter(header, shown, total), *rest])

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
            # Cell text carries untrusted strings (cmdlines, container names,
            # SSIDs): a raw "\n" makes curses jump to the next line (#1692).
            text = cell.text[: limit - x].translate(_CONTROL_CHARS_TO_SPACE)
            attr = _attr_for(cell)
            try:
                stdscr.addstr(y, x, text, attr)
            except curses.error:
                break
            x += len(text)
        return max(0, x - x0)

    # Horizontal rule glyph (U+2500 BOX DRAWINGS LIGHT HORIZONTAL) — v4 parity
    # (v4 paints curses.ACS_HLINE, which renders as the same ─).
    _SEPARATOR_CHAR = "─"

    def _paint_separator(self, stdscr, y: int, x0: int, width: int) -> None:
        """Paint a horizontal rule at row ``y``.

        Default: a ``─`` rule spanning the width. When ``[outputs]
        separator`` is False the rule is suppressed — the caller still
        reserves the row, so it renders as a blank line.
        """
        if not self._separator_enabled:
            return
        try:
            stdscr.addstr(y, x0, self._SEPARATOR_CHAR * max(0, width))
        except curses.error:
            pass

    # ----------------------------------------------------------- help overlay

    def _help_lines(self) -> list[Row]:
        """Build the help body as a single column of display rows.

        Generated straight from the dispatch tables so the overlay documents
        *every* key the TUI actually responds to — add a hotkey and it shows
        up here automatically, with no second list to keep in sync (CLAUDE.md
        "extensibilité sans modification du cœur").

        BOTH tables: ``_HOTKEYS`` keyed by character, and ``_SPECIAL_HOTKEYS``
        keyed by curses keycode for the keys that have no character (the
        arrows and ENTER), which print the ``label`` they carry. An entry with
        no ``desc`` is an alias of one that has it (``curses.KEY_ENTER`` beside
        ``10``) and is deliberately not listed twice.

        Each group is a bold header followed by one ``  k  description`` row
        per key, with a blank spacer line between groups.
        """
        labelled: list[tuple[str, dict[str, Any]]] = [
            *self._HOTKEYS.items(),
            *((spec["label"], spec) for spec in self._special_hotkeys().values() if spec.get("desc")),
        ]
        lines: list[Row] = []
        for group in self._HELP_GROUPS:
            keys = [(k, spec) for k, spec in labelled if spec.get("group") == group]
            if not keys:
                continue
            if lines:
                lines.append(Row(cells=[Cell(text="")]))  # spacer between groups
            lines.append(Row(cells=[Cell(text=group, color=ColorRole.HEADER)]))
            for k, spec in keys:
                lines.append(Row(cells=[Cell(text=f"  {k:>4}  {spec.get('desc', '')}")]))
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
        # Same four levels as `levels`, rendered as the highlighted badge so
        # the user can tell the two apart side by side. The `Alert` sample
        # lives here rather than in `decorations` — it IS this decoration.
        prominent = Row(
            cells=[
                Cell(text="OK", color=ColorRole.OK, prominent=True),
                Cell(text="CAREFUL", color=ColorRole.CAREFUL, prominent=True),
                Cell(text="WARNING", color=ColorRole.WARNING, prominent=True),
                Cell(text="CRITICAL", color=ColorRole.CRITICAL, prominent=True),
                Cell(text="= same, highlighted: an event is ongoing"),
            ]
        )
        decorations = Row(
            cells=[
                Cell(text="Title", color=ColorRole.HEADER),
                Cell(text="Sort", color=ColorRole.DEFAULT, bold=True, underline=True),
                Cell(text="= section title / active sort column"),
            ]
        )
        return [levels, prominent, decorations]

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


def _init_colors(theme: str = "dark") -> None:
    try:
        if not curses.has_colors():
            return
        curses.start_color()
        try:
            curses.use_default_colors()
        except curses.error:
            pass
        colors = getattr(curses, "COLORS", 8)
        # Plugin titles. A foreground readable on BOTH a black and a white
        # background peaks at 4.58:1 (equal-contrast luminance L=0.179), so
        # no single value serves both. The shade is therefore a user choice:
        #   dark  (default) COLOR_WHITE, bold — v4's TITLE decoration, and
        #                   what every existing deployment already renders.
        #   light           grey 236 #303030 — ~13:1 on white, the mirror
        #                   image of bold-white-on-dark. A cube index, so no
        #                   terminal theme can redefine it.
        if theme == "light":
            header_color = 236 if colors >= 256 else curses.COLOR_BLACK
        else:
            header_color = curses.COLOR_WHITE
        # Foreground pairs (used by default for coloured text on the
        # terminal's native background). These four keep the terminal's own
        # ANSI palette on purpose: they paint on the terminal's background,
        # and a theme calibrates its palette to be readable on it.
        pairs = [
            (ColorRole.OK, curses.COLOR_GREEN),
            (ColorRole.CAREFUL, curses.COLOR_BLUE),
            (ColorRole.WARNING, curses.COLOR_MAGENTA),
            (ColorRole.CRITICAL, curses.COLOR_RED),
            (ColorRole.HEADER, header_color),
        ]
        for i, (role, color) in enumerate(pairs, start=1):
            try:
                curses.init_pair(i, color, -1)
            except curses.error:
                curses.init_pair(i, color, curses.COLOR_BLACK)
            _COLOR_PAIRS[role] = curses.color_pair(i)
        _COLOR_PAIRS[ColorRole.DEFAULT] = curses.color_pair(0)

        # Reverse pairs — the filled "badge" used by prominent cells (v4
        # ``*_LOG`` decoration parity). A_REVERSE alone would inherit the
        # terminal's default foreground, so each pair is defined explicitly.
        #
        # The badge paints its own background, so it must NOT rely on ANSI
        # colours 0-15: themes (Catppuccin, Solarized, Gruvbox, Tokyo Night…)
        # redefine those, and their luminance is unknowable without querying
        # the terminal. Under Catppuccin Mocha, ANSI "red" is #f38ba8 — a
        # light pink — so white-on-red collapses to ~2:1.
        #
        # Cube indices 16-255 are fixed by the spec and left alone by those
        # themes. Painting the badge in absolute colours makes its contrast
        # deterministic whatever the theme AND whatever the terminal
        # background: black on a light cube colour, >= 11:1 on every level.
        # Foreground 16 (not 0) is deliberate — A_BOLD brightens colours 0-7
        # on many terminals, which would turn black into mid-gray.
        if colors >= 256:
            reverse_pairs = [
                (ColorRole.OK, 16, 120),  # #87ffaf  ~16.8:1
                (ColorRole.CAREFUL, 16, 117),  # #87d7ff  ~13.6:1
                (ColorRole.WARNING, 16, 183),  # #d7afff  ~11.4:1
                (ColorRole.CRITICAL, 16, 210),  # #ffafaf  ~12.0:1
            ]
        else:
            # No absolute palette available. Best effort against the DEFAULT
            # xterm luminance: green is its only light background. On a
            # 16-colour terminal running a themed palette this stays
            # imperfect — that case needs an OSC 4 query we deliberately
            # avoid (fragile under tmux, and a startup risk).
            white = 15 if colors >= 16 else curses.COLOR_WHITE
            reverse_pairs = [
                (ColorRole.OK, curses.COLOR_BLACK, curses.COLOR_GREEN),
                (ColorRole.CAREFUL, white, curses.COLOR_BLUE),
                (ColorRole.WARNING, white, curses.COLOR_MAGENTA),
                (ColorRole.CRITICAL, white, curses.COLOR_RED),
            ]
        for j, (role, fg, bg) in enumerate(reverse_pairs, start=len(pairs) + 1):
            try:
                curses.init_pair(j, fg, bg)
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
        # Bold the badge: on an 8-colour terminal this is what promotes the
        # light-gray foreground to true white; elsewhere it just thickens the
        # glyphs, which helps on a saturated background either way.
        attr |= curses.A_BOLD
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

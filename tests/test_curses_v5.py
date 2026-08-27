"""Glances v5 — smoke tests for the curses TUI thread.

The thread is fully exercised under a mocked `curses` module so the suite
runs headless. The visual layer (color attributes, addstr placement) is
checked through assertions on the mock; logic is tested via the pure
renderer in test_curses_renderer_v5.
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------- fixtures


@pytest.fixture
def fake_store():
    store = MagicMock()
    store.as_dict.return_value = {
        "mem": {
            "total": 16_000_000_000,
            "available": 8_000_000_000,
            "percent": 72.0,
            "_levels": {"percent": {"level": "warning", "prominent": True}},
        },
    }
    return store


@pytest.fixture
def fake_alerts():
    alerts = MagicMock()
    alerts.get_history.return_value = []
    alerts.get_ongoing.return_value = {}
    alerts.get_ongoing_since.return_value = {}
    return alerts


@pytest.fixture
def fake_config():
    cfg = MagicMock()
    cfg.get.side_effect = lambda section, key, default=None: default
    return cfg


# ---------------------------------------------------------------- lifecycle


def test_tui_v5_can_start_and_stop_without_curses(monkeypatch, fake_store, fake_alerts, fake_config):
    """The thread enters its loop and exits cleanly when stop() is called."""
    from glances.outputs import glances_curses_v5 as tui_mod

    fake_stdscr = MagicMock()
    fake_stdscr.getmaxyx.return_value = (24, 80)
    fake_stdscr.getch.return_value = -1
    monkeypatch.setattr(tui_mod, "_safe_curses_wrapper", lambda fn: fn(fake_stdscr))

    fake_registry = [("mem", False)]
    fake_fields = {"mem": {"percent": {"unit": "percent", "label": "MEM", "watched": True, "prominent": True}}}

    tui = tui_mod.TuiV5(
        store=fake_store,
        alerts=fake_alerts,
        config=fake_config,
        registry=fake_registry,
        fields_by_plugin=fake_fields,
        refresh_interval=0.01,
    )

    tui.start()
    time.sleep(0.05)
    tui.stop()
    tui.join(timeout=1.0)
    assert not tui.is_alive()


def test_tui_v5_calls_addstr_for_rendered_cells(monkeypatch, fake_store, fake_alerts, fake_config):
    """The thread paints something onto stdscr each cycle."""
    from glances.outputs import glances_curses_v5 as tui_mod

    fake_stdscr = MagicMock()
    fake_stdscr.getmaxyx.return_value = (24, 80)
    fake_stdscr.getch.return_value = -1

    def record_wrapper(fn):
        fn(fake_stdscr)

    monkeypatch.setattr(tui_mod, "_safe_curses_wrapper", record_wrapper)

    registry = [("mem", False)]
    fields = {"mem": {"percent": {"unit": "percent", "label": "MEM", "watched": True, "prominent": True}}}

    tui = tui_mod.TuiV5(
        store=fake_store,
        alerts=fake_alerts,
        config=fake_config,
        registry=registry,
        fields_by_plugin=fields,
        refresh_interval=0.01,
    )
    tui.start()
    time.sleep(0.05)
    tui.stop()
    tui.join(timeout=1.0)

    addstr_calls = list(fake_stdscr.addstr.call_args_list)
    assert addstr_calls, "addstr was never called"
    flat = " ".join(str(args) for args in addstr_calls)
    assert "MEM" in flat


def test_paint_sidebar_advances_y_by_block_height_plus_one_blank_line(fake_store, fake_alerts, fake_config):
    """Regression: ``_paint_sidebar`` used to pass the return of
    ``_paint_block`` (the WIDTH painted, ~34 chars) as a height, leaving a
    huge gap between sidebar blocks (network → fs would skip ~35 lines).
    The fix advances ``y`` by ``block.height + 1`` instead — one blank
    line between blocks, matching v4 sidebar layout.
    """
    from glances.outputs import glances_curses_v5 as tui_mod
    from glances.outputs.curses_renderer_v5 import Cell, PluginBlock, Row

    tui = tui_mod.TuiV5(
        store=fake_store,
        alerts=fake_alerts,
        config=fake_config,
        registry=[],
        fields_by_plugin={},
        refresh_interval=0.01,
    )

    # Two blocks of distinct, known heights.
    block_a = PluginBlock(
        name="network",
        rows=[Row(cells=[Cell(text="NETWORK")]), Row(cells=[Cell(text="eth0")])],
    )  # height = 2
    block_b = PluginBlock(
        name="fs",
        rows=[Row(cells=[Cell(text="FILE SYS")]), Row(cells=[Cell(text="/")])],
    )  # height = 2

    fake_stdscr = MagicMock()
    tui._paint_sidebar(fake_stdscr, [block_a, block_b], y0=5, x0=0, width=34, height=20)

    # Collect every (y, text) addstr call.
    rows_painted = [(call.args[0], call.args[2]) for call in fake_stdscr.addstr.call_args_list]
    # Block A rendered at y=5, y=6. Block B at y=5+2+1=8, y=9. y=7 must be empty.
    ys = sorted({y for y, _ in rows_painted})
    assert ys == [5, 6, 8, 9], f"unexpected y-coordinates: {ys}"
    # And there's no row painted at y=7 (the blank separator line).
    assert all(y != 7 for y, _ in rows_painted)


def test_paint_sidebar_skips_zero_row_block(fake_store, fake_alerts, fake_config):
    """Regression: a zero-row block (e.g. ``amps`` when every ``[amp_*]``
    section is disabled — every shipped default) used to still cost one
    blank line via the unconditional ``y += min(block.height, max_h) + 1``.
    That left a stray blank line between ``processcount`` and
    ``processlist`` on every default install. A block with no rows must be
    skipped entirely: it neither paints nor advances ``y``.
    """
    from glances.outputs import glances_curses_v5 as tui_mod
    from glances.outputs.curses_renderer_v5 import Cell, PluginBlock, Row

    tui = tui_mod.TuiV5(
        store=fake_store,
        alerts=fake_alerts,
        config=fake_config,
        registry=[],
        fields_by_plugin={},
        refresh_interval=0.01,
    )

    block_a = PluginBlock(
        name="processcount",
        rows=[Row(cells=[Cell(text="PROCESSCOUNT")])],
    )  # height = 1
    block_empty = PluginBlock(name="amps", rows=[])  # height = 0 — must be skipped
    block_b = PluginBlock(
        name="processlist",
        rows=[Row(cells=[Cell(text="PROCESSLIST")])],
    )  # height = 1

    fake_stdscr = MagicMock()
    tui._paint_sidebar(fake_stdscr, [block_a, block_empty, block_b], y0=5, x0=0, width=34, height=20)

    rows_painted = [(call.args[0], call.args[2]) for call in fake_stdscr.addstr.call_args_list]
    ys = sorted({y for y, _ in rows_painted})
    # Block A at y=5. No line reserved for the empty block: block B follows
    # directly at y=5+1+1=7 (one blank separator line), not y=8 or beyond.
    assert ys == [5, 7], f"unexpected y-coordinates: {ys}"


def test_tui_v5_quit_on_q_key(monkeypatch, fake_store, fake_alerts, fake_config):
    """Pressing 'q' triggers stop()."""
    from glances.outputs import glances_curses_v5 as tui_mod

    fake_stdscr = MagicMock()
    fake_stdscr.getmaxyx.return_value = (24, 80)
    fake_stdscr.getch.side_effect = [ord("q"), -1, -1]

    monkeypatch.setattr(tui_mod, "_safe_curses_wrapper", lambda fn: fn(fake_stdscr))

    tui = tui_mod.TuiV5(
        store=fake_store,
        alerts=fake_alerts,
        config=fake_config,
        registry=[("mem", False)],
        fields_by_plugin={"mem": {}},
        refresh_interval=0.01,
    )
    tui.start()
    tui.join(timeout=1.0)
    assert not tui.is_alive()
    assert tui._stop_event.is_set()


def test_attr_for_prominent_ok_uses_reverse():
    """A prominent cell with OK level renders with background highlight."""
    import curses

    from glances.outputs.curses_renderer_v5 import Cell, ColorRole
    from glances.outputs.glances_curses_v5 import _attr_for

    cell = Cell(text="50%", color=ColorRole.OK, prominent=True)
    attr = _attr_for(cell)
    assert attr & curses.A_REVERSE


def test_attr_for_prominent_warning_uses_reverse():
    import curses

    from glances.outputs.curses_renderer_v5 import Cell, ColorRole
    from glances.outputs.glances_curses_v5 import _attr_for

    cell = Cell(text="80%", color=ColorRole.WARNING, prominent=True)
    attr = _attr_for(cell)
    assert attr & curses.A_REVERSE


def test_attr_for_non_prominent_warning_does_not_use_reverse():
    """Non-prominent cells never get A_REVERSE, even at WARNING/CRITICAL."""
    import curses

    from glances.outputs.curses_renderer_v5 import Cell, ColorRole
    from glances.outputs.glances_curses_v5 import _attr_for

    cell = Cell(text="80%", color=ColorRole.WARNING, prominent=False)
    attr = _attr_for(cell)
    assert not (attr & curses.A_REVERSE)


def test_attr_for_prominent_default_color_stays_plain():
    """`prominent` only matters when an alert level is set."""
    import curses

    from glances.outputs.curses_renderer_v5 import Cell, ColorRole
    from glances.outputs.glances_curses_v5 import _attr_for

    cell = Cell(text="—", color=ColorRole.DEFAULT, prominent=True)
    attr = _attr_for(cell)
    assert not (attr & curses.A_REVERSE)


def test_attr_for_explicit_bold_flag_applies_a_bold():
    """A non-HEADER cell with `bold=True` still gets A_BOLD (used for
    alert-coloured plugin titles)."""
    import curses

    from glances.outputs.curses_renderer_v5 import Cell, ColorRole
    from glances.outputs.glances_curses_v5 import _attr_for

    cell = Cell(text="MEM", color=ColorRole.CRITICAL, bold=True)
    attr = _attr_for(cell)
    assert attr & curses.A_BOLD


def test_attr_for_header_is_bold_without_explicit_flag():
    """Backwards compat: HEADER role implies bold even without `bold=True`."""
    import curses

    from glances.outputs.curses_renderer_v5 import Cell, ColorRole
    from glances.outputs.glances_curses_v5 import _attr_for

    cell = Cell(text="MEM", color=ColorRole.HEADER)
    attr = _attr_for(cell)
    assert attr & curses.A_BOLD


def test_attr_for_prominent_uses_dedicated_reverse_pair_when_available(monkeypatch):
    """When `_init_colors` has populated `_COLOR_PAIRS_REVERSE`, prominent
    cells use the dedicated white-on-colour pair instead of A_REVERSE on
    the foreground pair — matching v4 readability for *_LOG decorations."""
    from glances.outputs.curses_renderer_v5 import Cell, ColorRole
    from glances.outputs.glances_curses_v5 import _attr_for

    # Inject sentinel attr values into the module-level dicts so we can
    # observe which path `_attr_for` took.
    monkeypatch.setattr("glances.outputs.glances_curses_v5._COLOR_PAIRS", {ColorRole.WARNING: 0xCAFE})
    monkeypatch.setattr(
        "glances.outputs.glances_curses_v5._COLOR_PAIRS_REVERSE",
        {ColorRole.WARNING: 0xBEEF},
    )

    cell = Cell(text="80%", color=ColorRole.WARNING, prominent=True)
    attr = _attr_for(cell)
    # The reverse-pair sentinel is in the attr.
    assert attr & 0xBEEF == 0xBEEF
    # The foreground-pair sentinel is NOT used.
    assert not (attr & 0xCAFE == 0xCAFE)


def test_top_row_gaps_evenly_distributes_remaining_space(fake_store, fake_alerts, fake_config):
    """3 blocks of widths [10, 15, 12] in a 60-col terminal:
    total=37, available=23, 2 gaps → 12 + 11 (extra char to the leftmost).
    First block flush-left; last block's right edge at column 59."""
    from glances.outputs import glances_curses_v5 as tui_mod

    tui = tui_mod.TuiV5(
        store=fake_store,
        alerts=fake_alerts,
        config=fake_config,
        registry=[],
        fields_by_plugin={},
        refresh_interval=0.01,
    )
    gaps = tui._top_row_gaps([10, 15, 12], max_x=60)
    assert sum(gaps) + 10 + 15 + 12 == 60
    assert gaps == [12, 11]


def test_top_row_gaps_handles_single_block(fake_store, fake_alerts, fake_config):
    """One block alone has no gaps (and is flush-left)."""
    from glances.outputs import glances_curses_v5 as tui_mod

    tui = tui_mod.TuiV5(
        store=fake_store,
        alerts=fake_alerts,
        config=fake_config,
        registry=[],
        fields_by_plugin={},
        refresh_interval=0.01,
    )
    assert tui._top_row_gaps([20], max_x=80) == []


def test_top_row_gaps_handles_empty_input(fake_store, fake_alerts, fake_config):
    from glances.outputs import glances_curses_v5 as tui_mod

    tui = tui_mod.TuiV5(
        store=fake_store,
        alerts=fake_alerts,
        config=fake_config,
        registry=[],
        fields_by_plugin={},
        refresh_interval=0.01,
    )
    assert tui._top_row_gaps([], max_x=80) == []


def test_top_row_gaps_falls_back_to_min_gap_when_no_room(fake_store, fake_alerts, fake_config):
    """When the terminal is narrower than the natural content + min gaps,
    every gap collapses to the minimum so curses can clip the overflow
    rather than overlap blocks."""
    from glances.outputs import glances_curses_v5 as tui_mod

    tui = tui_mod.TuiV5(
        store=fake_store,
        alerts=fake_alerts,
        config=fake_config,
        registry=[],
        fields_by_plugin={},
        refresh_interval=0.01,
    )
    # 3 blocks of widths [30, 30, 30] in 50 cols — way too narrow.
    gaps = tui._top_row_gaps([30, 30, 30], max_x=50)
    assert gaps == [tui_mod.TuiV5._TOP_GAP_MIN, tui_mod.TuiV5._TOP_GAP_MIN]


def test_top_row_gaps_distributes_evenly_when_remainder_is_zero(fake_store, fake_alerts, fake_config):
    """If available % n_gaps == 0, every gap is identical."""
    from glances.outputs import glances_curses_v5 as tui_mod

    tui = tui_mod.TuiV5(
        store=fake_store,
        alerts=fake_alerts,
        config=fake_config,
        registry=[],
        fields_by_plugin={},
        refresh_interval=0.01,
    )
    # 4 blocks [10, 10, 10, 10] = 40; 80 - 40 = 40 / 3 gaps = 13 r1 (one extra)
    # Pick an exact divisor: 3 gaps and available=30 → 10/10/10
    gaps = tui._top_row_gaps([10, 10, 10, 10], max_x=70)
    assert gaps == [10, 10, 10]


def test_attr_for_prominent_falls_back_to_reverse_when_pair_unallocated(monkeypatch):
    """If the white-on-colour pair couldn't be allocated (limited
    palette), `_attr_for` falls back to A_REVERSE on the foreground
    pair so the cell is still visibly highlighted."""
    import curses

    from glances.outputs.curses_renderer_v5 import Cell, ColorRole
    from glances.outputs.glances_curses_v5 import _attr_for

    monkeypatch.setattr("glances.outputs.glances_curses_v5._COLOR_PAIRS_REVERSE", {})

    cell = Cell(text="80%", color=ColorRole.WARNING, prominent=True)
    attr = _attr_for(cell)
    assert attr & curses.A_REVERSE


def test_tui_v5_default_top_shows_cpu_not_percpu(monkeypatch, fake_store, fake_alerts, fake_config):
    """At startup, cpu is in the top slot and percpu is hidden (v4 default)."""
    from glances.outputs import glances_curses_v5 as tui_mod

    fake_store.as_dict.return_value = {
        "cpu": {"total": 5.0, "_levels": {}},
        "percpu": {"data": [{"cpu_number": 0, "total": 5.0}], "_levels": {}},
    }
    tui = tui_mod.TuiV5(
        store=fake_store,
        alerts=fake_alerts,
        config=fake_config,
        registry=[("cpu", False), ("percpu", True)],
        fields_by_plugin={
            "cpu": {"total": {"unit": "percent", "watched": True, "label": "CPU"}},
            "percpu": {"cpu_number": {"unit": "number", "primary_key": True}},
        },
        refresh_interval=0.01,
    )
    frame = tui._build_frame()
    top_names = [b.name for b in frame.top]
    assert "cpu" in top_names
    assert "percpu" not in top_names


def test_tui_v5_toggle_swaps_cpu_for_percpu(monkeypatch, fake_store, fake_alerts, fake_config):
    """Once `_view.show_percpu` flips True, the top slot exposes percpu instead of cpu."""
    from glances.outputs import glances_curses_v5 as tui_mod

    fake_store.as_dict.return_value = {
        "cpu": {"total": 5.0, "_levels": {}},
        "percpu": {"data": [{"cpu_number": 0, "total": 5.0}], "_levels": {}},
    }
    tui = tui_mod.TuiV5(
        store=fake_store,
        alerts=fake_alerts,
        config=fake_config,
        registry=[("cpu", False), ("percpu", True)],
        fields_by_plugin={
            "cpu": {"total": {"unit": "percent", "watched": True, "label": "CPU"}},
            "percpu": {"cpu_number": {"unit": "number", "primary_key": True}},
        },
        refresh_interval=0.01,
    )
    tui._view.show_percpu = True
    frame = tui._build_frame()
    top_names = [b.name for b in frame.top]
    assert "percpu" in top_names
    assert "cpu" not in top_names


def test_tui_v5_hotkey_1_toggles_percpu(monkeypatch, fake_store, fake_alerts, fake_config):
    """Pressing '1' flips `_view.show_percpu`."""
    from glances.outputs import glances_curses_v5 as tui_mod

    fake_stdscr = MagicMock()
    fake_stdscr.getmaxyx.return_value = (24, 80)
    # Sequence: one '1' keypress to toggle, then a 'q' to exit.
    fake_stdscr.getch.side_effect = [ord("1"), ord("q"), -1, -1]
    monkeypatch.setattr(tui_mod, "_safe_curses_wrapper", lambda fn: fn(fake_stdscr))

    tui = tui_mod.TuiV5(
        store=fake_store,
        alerts=fake_alerts,
        config=fake_config,
        registry=[("mem", False)],
        fields_by_plugin={"mem": {}},
        refresh_interval=0.01,
    )
    assert tui._view.show_percpu is False
    tui.start()
    tui.join(timeout=1.0)
    # After one '1' press, the flag was flipped — the thread exits on 'q'
    # but the flag retains the toggled value.
    assert tui._view.show_percpu is True


class _FakeEngine:
    """Minimal ``glances_processes`` stand-in recording sort-key changes."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, bool]] = []
        self.sort_key = "cpu_percent"
        self.auto_sort = False

    def set_sort_key(self, key, auto) -> None:
        self.calls.append((key, auto))
        self.sort_key = "cpu_percent" if key == "auto" else key
        self.auto_sort = (key == "auto") or auto


def _make_tui(tui_mod, fake_store, fake_alerts, fake_config, **kw):
    return tui_mod.TuiV5(
        store=fake_store,
        alerts=fake_alerts,
        config=fake_config,
        registry=kw.get("registry", [("mem", False)]),
        fields_by_plugin=kw.get("fields_by_plugin", {"mem": {}}),
        refresh_interval=0.01,
    )


def test_tui_v5_handle_key_quit(fake_store, fake_alerts, fake_config):
    """`q` and ESC request shutdown; any other key does not."""
    from glances.outputs import glances_curses_v5 as tui_mod

    tui = _make_tui(tui_mod, fake_store, fake_alerts, fake_config)
    assert tui._handle_key(ord("q")) == "quit"
    assert tui._handle_key(27) == "quit"
    assert tui._handle_key(ord("z")) == "ignored"


def test_tui_v5_key_4_toggles_full_quicklook(fake_store, fake_alerts, fake_config):
    """Pressing '4' flips `_full_quicklook` (off → on → off), v4 parity."""
    from glances.outputs import glances_curses_v5 as tui_mod

    tui = _make_tui(tui_mod, fake_store, fake_alerts, fake_config)
    assert tui._full_quicklook is False
    assert tui._handle_key(ord("4")) == "changed"
    assert tui._full_quicklook is True
    assert tui._handle_key(ord("4")) == "changed"
    assert tui._full_quicklook is False


def test_tui_v5_cli_flags_seed_quicklook_state(fake_store, fake_alerts, fake_config):
    """`--full-quicklook` / `--percpu` reach the TUI via the constructor params
    (wired in main_v5.assemble) instead of being parsed-but-dropped dead code."""
    from glances.outputs import glances_curses_v5 as tui_mod

    tui = tui_mod.TuiV5(
        store=fake_store,
        alerts=fake_alerts,
        config=fake_config,
        registry=[("mem", False)],
        fields_by_plugin={"mem": {}},
        refresh_interval=0.01,
        full_quicklook=True,
        percpu=True,
    )
    assert tui._full_quicklook is True
    assert tui._percpu is True

    # Default construction (no flags) keeps both off (v4 defaults).
    default_tui = tui_mod.TuiV5(
        store=fake_store,
        alerts=fake_alerts,
        config=fake_config,
        registry=[("mem", False)],
        fields_by_plugin={"mem": {}},
        refresh_interval=0.01,
    )
    assert default_tui._full_quicklook is False
    assert default_tui._percpu is False


def test_tui_v5_build_view_carries_quicklook_flags(fake_store, fake_alerts, fake_config):
    """The assembled view dict carries `full_quicklook`, `percpu`, and an int
    `quicklook_width` for the renderer / build_frame to consume."""
    from glances.outputs import glances_curses_v5 as tui_mod

    tui = _make_tui(tui_mod, fake_store, fake_alerts, fake_config)
    tui._full_quicklook = True
    tui._percpu = True
    view = tui._build_view(max_x=120)
    assert view["full_quicklook"] is True
    assert view["percpu"] is True
    assert isinstance(view["quicklook_width"], int)
    # Full mode widens the bars to (almost) the whole terminal.
    assert view["quicklook_width"] == max(20, 120 - 8)
    # Compact mode falls back to a single-column width.
    tui._full_quicklook = False
    assert tui._build_view(max_x=120)["quicklook_width"] == tui_mod.TuiV5._QUICKLOOK_COMPACT_WIDTH


def test_build_view_seeds_meangpu_and_fahrenheit(fake_store, fake_alerts, fake_config):
    """`--meangpu` / `--fahrenheit` reach the view dict via the constructor
    params (wired in main_v5.assemble), consumed by the gpu renderer."""
    from glances.outputs import glances_curses_v5 as tui_mod

    tui = tui_mod.TuiV5(
        store=fake_store,
        alerts=fake_alerts,
        config=fake_config,
        registry=[("mem", False)],
        fields_by_plugin={"mem": {}},
        refresh_interval=0.01,
        meangpu=True,
        fahrenheit=True,
    )
    assert tui._meangpu is True
    assert tui._fahrenheit is True
    view = tui._build_view(max_x=200)
    assert view["meangpu"] is True
    assert view["fahrenheit"] is True


def test_build_view_meangpu_fahrenheit_default_false(fake_store, fake_alerts, fake_config):
    from glances.outputs import glances_curses_v5 as tui_mod

    tui = _make_tui(tui_mod, fake_store, fake_alerts, fake_config)
    assert tui._meangpu is False
    assert tui._fahrenheit is False
    view = tui._build_view(max_x=200)
    assert view["meangpu"] is False
    assert view["fahrenheit"] is False


def test_build_view_carries_byte_flag(fake_store, fake_alerts, fake_config):
    """`--byte` reaches the view dict via the constructor param (wired in
    main_v5.assemble), consumed by the containers renderer."""
    from glances.outputs import glances_curses_v5 as tui_mod

    tui = tui_mod.TuiV5(
        store=fake_store,
        alerts=fake_alerts,
        config=fake_config,
        registry=[("mem", False)],
        fields_by_plugin={"mem": {}},
        refresh_interval=0.01,
        byte=True,
    )
    assert tui._byte is True
    view = tui._build_view(max_x=200)
    assert view["byte"] is True


def test_build_view_byte_defaults_false(fake_store, fake_alerts, fake_config):
    from glances.outputs import glances_curses_v5 as tui_mod

    tui = _make_tui(tui_mod, fake_store, fake_alerts, fake_config)
    assert tui._byte is False
    view = tui._build_view(max_x=200)
    assert view["byte"] is False


def test_build_view_allows_unicode_by_default(fake_store, fake_alerts, fake_config):
    from glances.outputs import glances_curses_v5 as tui_mod

    tui = _make_tui(tui_mod, fake_store, fake_alerts, fake_config)
    assert tui._build_view(max_x=100)["unicode"] is True


def test_build_view_forbids_unicode_when_disable_unicode_is_set(fake_store, fake_alerts, fake_config):
    """--disable-unicode must reach the renderers, v4 parity."""
    from glances.outputs import glances_curses_v5 as tui_mod

    tui = tui_mod.TuiV5(
        store=fake_store,
        alerts=fake_alerts,
        config=fake_config,
        registry=[("mem", False)],
        fields_by_plugin={"mem": {}},
        refresh_interval=0.01,
        disable_unicode=True,
    )
    assert tui._build_view(max_x=100)["unicode"] is False


def test_tui_v5_full_quicklook_hides_siblings_end_to_end(fake_store, fake_alerts, fake_config):
    """End-to-end: with `_full_quicklook` on, `_build_frame(max_x)` drives the
    real chain (_build_view → build_frame) and the hidden TOP siblings
    (cpu/mem) vanish while quicklook stays. Proves the flag flows all the way
    through, not just the literal-view shortcut. v4 parity: `load` stays."""
    from glances.outputs import glances_curses_v5 as tui_mod

    fake_store.as_dict.return_value = {
        "quicklook": {"cpu": 12.0, "_levels": {}},
        "cpu": {"total": 5.0, "_levels": {}},
        "mem": {"percent": 72.0, "_levels": {}},
        "load": {"min1": 0.5, "_levels": {}},
    }
    tui = _make_tui(
        tui_mod,
        fake_store,
        fake_alerts,
        fake_config,
        registry=[
            ("quicklook", False),
            ("cpu", False),
            ("mem", False),
            ("load", False),
        ],
        fields_by_plugin={
            "quicklook": {"cpu": {"unit": "percent", "label": "CPU", "watched": True}},
            "cpu": {"total": {"unit": "percent", "label": "CPU", "watched": True}},
            "mem": {"percent": {"unit": "percent", "label": "MEM", "watched": True}},
            "load": {"min1": {"unit": "number", "label": "1 min", "watched": True}},
        },
    )

    tui._full_quicklook = True
    frame = tui._build_frame(max_x=120)
    top_names = [b.name for b in frame.top]
    assert "quicklook" in top_names
    assert "load" in top_names  # v4 parity: load is NOT a hidden sibling
    assert "cpu" not in top_names
    assert "mem" not in top_names


def test_tui_v5_sort_hotkeys_drive_engine(monkeypatch, fake_store, fake_alerts, fake_config):
    """Manual sort keys set the engine key with auto=False; 'a' enables auto."""
    from glances.outputs import glances_curses_v5 as tui_mod

    engine = _FakeEngine()
    monkeypatch.setattr(tui_mod, "glances_processes", engine)
    tui = _make_tui(tui_mod, fake_store, fake_alerts, fake_config)

    for ch, expected in [
        ("c", "cpu_percent"),
        ("m", "memory_percent"),
        ("i", "io_counters"),
        ("t", "cpu_times"),
        ("p", "name"),
        ("u", "username"),
        ("o", "cpu_num"),
    ]:
        assert tui._handle_key(ord(ch)) == "changed"
        assert engine.calls[-1] == (expected, False)

    assert tui._handle_key(ord("a")) == "changed"
    assert engine.calls[-1] == ("auto", True)
    assert engine.auto_sort is True


def test_tui_v5_switch_hotkeys_toggle_view(fake_store, fake_alerts, fake_config):
    """`/` toggles short-name, `j` toggles the programs view."""
    from glances.outputs import glances_curses_v5 as tui_mod

    tui = _make_tui(tui_mod, fake_store, fake_alerts, fake_config)
    assert tui._view.process_short_name is True
    assert tui._handle_key(ord("/")) == "changed"
    assert tui._view.process_short_name is False

    assert tui._view.programs is False
    assert tui._handle_key(ord("j")) == "changed"
    assert tui._view.programs is True


def test_tui_v5_unknown_key_is_noop(fake_store, fake_alerts, fake_config):
    """An unmapped key leaves view state untouched and does not quit."""
    from glances.outputs import glances_curses_v5 as tui_mod

    tui = _make_tui(tui_mod, fake_store, fake_alerts, fake_config)
    before = (tui._view.show_percpu, tui._view.process_short_name, tui._view.programs)
    assert tui._handle_key(ord("Z")) == "ignored"
    after = (tui._view.show_percpu, tui._view.process_short_name, tui._view.programs)
    assert before == after


def test_key_resize_forces_immediate_repaint(fake_store, fake_alerts, fake_config):
    """A terminal resize (curses.KEY_RESIZE) routes through the immediate
    repaint path so the layout reflows to the new dimensions at once."""
    import curses

    from glances.outputs import glances_curses_v5 as tui_mod

    tui = _make_tui(tui_mod, fake_store, fake_alerts, fake_config)
    assert tui._handle_key(curses.KEY_RESIZE) == "repaint"


def test_key_resize_repaints_with_help_open_without_closing_it(fake_store, fake_alerts, fake_config):
    """A resize while the help overlay is open repaints immediately but must
    NOT close the overlay (resize is handled before the help check)."""
    import curses

    from glances.outputs import glances_curses_v5 as tui_mod

    tui = _make_tui(tui_mod, fake_store, fake_alerts, fake_config)
    tui._view.show_help = True
    assert tui._handle_key(curses.KEY_RESIZE) == "repaint"
    assert tui._view.show_help is True  # resize must NOT close the help overlay


def test_tui_v5_programs_toggle_hides_one_list(fake_store, fake_alerts, fake_config):
    """`j` shows exactly one of processlist / programlist in the right slot."""
    from glances.outputs import glances_curses_v5 as tui_mod

    fake_store.as_dict.return_value = {
        "processlist": {"data": [{"pid": 1}], "_levels": {}},
        "programlist": {"data": [{"pid": 2}], "_levels": {}},
    }
    tui = _make_tui(
        tui_mod,
        fake_store,
        fake_alerts,
        fake_config,
        registry=[("processlist", True), ("programlist", True)],
        fields_by_plugin={"processlist": {}, "programlist": {}},
    )
    # Default (threads view): programlist hidden, processlist shown.
    names = [b.name for b in tui._build_frame().right]
    assert "processlist" in names
    assert "programlist" not in names
    # Programs view: the reverse.
    tui._view.programs = True
    names = [b.name for b in tui._build_frame().right]
    assert "programlist" in names
    assert "processlist" not in names


def test_tui_v5_render_view_snapshots_engine_sort(monkeypatch, fake_store, fake_alerts, fake_config):
    """`_render_view` exposes engine sort key + view switches to renderers."""
    from glances.outputs import glances_curses_v5 as tui_mod

    engine = _FakeEngine()
    engine.sort_key = "memory_percent"
    engine.auto_sort = True
    monkeypatch.setattr(tui_mod, "glances_processes", engine)
    tui = _make_tui(tui_mod, fake_store, fake_alerts, fake_config)
    tui._view.process_short_name = False
    tui._view.programs = True

    view = tui._render_view()
    assert view["sort_key"] == "memory_percent"
    assert view["auto_sort"] is True
    assert view["process_short_name"] is False
    assert view["programs"] is True


def test_tui_v5_repaint_decision_guard_rail(fake_store, fake_alerts, fake_config):
    """A pending key change repaints at most once per `_MIN_KEY_REPAINT_INTERVAL`
    (the guard-rail), measured from the last key-driven repaint."""
    from glances.outputs import glances_curses_v5 as tui_mod

    tui = _make_tui(tui_mod, fake_store, fake_alerts, fake_config)
    interval = tui._MIN_KEY_REPAINT_INTERVAL

    # A change 0.5 s after the last key repaint → throttled (not yet due).
    _, change_due = tui._repaint_decision(
        now=100.0, last_paint=100.0, last_change_paint=100.0 - 0.5 * interval, dirty=True
    )
    assert change_due is False

    # A change a full interval later → due.
    _, change_due = tui._repaint_decision(now=100.0, last_paint=100.0, last_change_paint=100.0 - interval, dirty=True)
    assert change_due is True

    # No pending change → never change-due regardless of elapsed time.
    _, change_due = tui._repaint_decision(now=100.0, last_paint=100.0, last_change_paint=0.0, dirty=False)
    assert change_due is False


def test_tui_v5_repaint_decision_regular_cadence(fake_store, fake_alerts, fake_config):
    """Regular cadence is independent of key changes."""
    from glances.outputs import glances_curses_v5 as tui_mod

    tui = _make_tui(tui_mod, fake_store, fake_alerts, fake_config)
    # last paint older than refresh_interval → regular due.
    regular_due, _ = tui._repaint_decision(
        now=100.0, last_paint=100.0 - tui.refresh_interval, last_change_paint=100.0, dirty=False
    )
    assert regular_due is True
    # last paint just now → not due.
    regular_due, _ = tui._repaint_decision(now=100.0, last_paint=100.0, last_change_paint=0.0, dirty=False)
    assert regular_due is False


# ------------------------------------------------------- startup catch-up


class _CatchupStore:
    """Minimal stand-in exposing exactly what the TUI consumes from the store:
    `revision`, `keys()` and `as_dict()`. Starts empty, like the real store
    does while the scheduler has not run a single plugin update yet."""

    _PAYLOAD = {
        "total": 16_000_000_000,
        "available": 8_000_000_000,
        "percent": 72.0,
    }

    def __init__(self) -> None:
        self._published: dict[str, dict] = {}
        self._revision = 0

    @property
    def revision(self) -> int:
        return self._revision

    def keys(self) -> list[str]:
        return list(self._published)

    def as_dict(self) -> dict:
        return dict(self._published)

    def publish(self, name: str) -> None:
        self._published[name] = dict(self._PAYLOAD)
        self._revision += 1


class _FakeScreen:
    """`getch` never returns a key; it drives the loop and fires callbacks at
    chosen iterations so a test can make data land at a precise moment."""

    def __init__(self, stop_event, at_iteration: dict, max_polls: int = 30) -> None:
        self._stop = stop_event
        self._at = at_iteration
        self._max = max_polls
        self.calls = 0
        self.blocks: list[float] = []

    def timeout(self, ms: int) -> None:
        self.blocks.append(ms / 1000.0)

    def getch(self) -> int:
        self.calls += 1
        time.sleep(0.01)
        cb = self._at.get(self.calls)
        if cb is not None:
            cb()
        if self.calls >= self._max:
            self._stop.set()
        return -1

    def getmaxyx(self) -> tuple[int, int]:
        return (50, 200)

    def refresh(self) -> None:
        pass


def _make_catchup_tui(tui_mod, store, fake_alerts, fake_config, registry, refresh_interval=30.0):
    return tui_mod.TuiV5(
        store=store,
        alerts=fake_alerts,
        config=fake_config,
        registry=registry,
        fields_by_plugin={name: {} for name, _ in registry},
        refresh_interval=refresh_interval,
    )


def test_tui_v5_startup_catchup_over_when_every_registry_plugin_published(fake_alerts, fake_config):
    """The catch-up window closes as soon as every displayed plugin published."""
    from glances.outputs import glances_curses_v5 as tui_mod

    store = _CatchupStore()
    tui = _make_catchup_tui(tui_mod, store, fake_alerts, fake_config, [("mem", False), ("cpu", False)])

    assert tui._startup_catchup_over(now=0.0, deadline=100.0) is False
    store.publish("mem")
    assert tui._startup_catchup_over(now=0.0, deadline=100.0) is False
    store.publish("cpu")
    assert tui._startup_catchup_over(now=0.0, deadline=100.0) is True


def test_tui_v5_startup_catchup_over_on_deadline(fake_alerts, fake_config):
    """A plugin that never publishes (permanently failing `update()`) must not
    keep the fast startup polling alive forever."""
    from glances.outputs import glances_curses_v5 as tui_mod

    store = _CatchupStore()
    tui = _make_catchup_tui(tui_mod, store, fake_alerts, fake_config, [("mem", False)])

    assert tui._startup_catchup_over(now=99.0, deadline=100.0) is False
    assert tui._startup_catchup_over(now=100.0, deadline=100.0) is True


def test_tui_v5_repaints_as_soon_as_plugins_publish_at_startup(monkeypatch, fake_alerts, fake_config):
    """Regression: the first frame is painted before the scheduler has run, so
    it carries no stats. Without the catch-up window the TUI held that empty
    frame for a full `refresh_interval` — first stats landed ~2 s late."""
    from glances.outputs import glances_curses_v5 as tui_mod

    monkeypatch.setattr(tui_mod, "_init_colors", lambda theme: None)
    store = _CatchupStore()
    tui = _make_catchup_tui(tui_mod, store, fake_alerts, fake_config, [("mem", False)])

    paints: list[float] = []
    monkeypatch.setattr(tui, "_repaint", lambda scr: paints.append(time.monotonic()))

    screen = _FakeScreen(tui._stop_event, at_iteration={1: lambda: store.publish("mem")})
    tui._loop(screen)

    # Initial (empty) frame + one triggered by the publication.
    assert len(paints) == 2
    # Repainted promptly, nowhere near the 30 s regular cadence.
    assert paints[1] - paints[0] < 1.0


def test_tui_v5_no_extra_repaint_once_startup_catchup_closed(monkeypatch, fake_alerts, fake_config):
    """Steady state is untouched: after the window closes, a new publication
    does NOT force a repaint — the regular cadence stays in charge."""
    from glances.outputs import glances_curses_v5 as tui_mod

    monkeypatch.setattr(tui_mod, "_init_colors", lambda theme: None)
    store = _CatchupStore()
    tui = _make_catchup_tui(tui_mod, store, fake_alerts, fake_config, [("mem", False)])

    paints: list[float] = []
    monkeypatch.setattr(tui, "_repaint", lambda scr: paints.append(time.monotonic()))

    screen = _FakeScreen(
        tui._stop_event,
        at_iteration={
            1: lambda: store.publish("mem"),  # closes the window
            5: lambda: store.publish("mem"),  # republication, window already closed
            9: lambda: store.publish("mem"),
        },
    )
    tui._loop(screen)

    assert len(paints) == 2  # initial + the single catch-up repaint


def test_tui_v5_startup_polling_stops_after_catchup(monkeypatch, fake_alerts, fake_config):
    """The fast startup poll must not survive the window — once closed, the
    `getch` block returns to the normal `_MAX_GETCH_BLOCK` ceiling."""
    from glances.outputs import glances_curses_v5 as tui_mod

    monkeypatch.setattr(tui_mod, "_init_colors", lambda theme: None)
    store = _CatchupStore()
    tui = _make_catchup_tui(tui_mod, store, fake_alerts, fake_config, [("mem", False)])
    monkeypatch.setattr(tui, "_repaint", lambda scr: None)

    screen = _FakeScreen(tui._stop_event, at_iteration={1: lambda: store.publish("mem")}, max_polls=6)
    tui._loop(screen)

    assert screen.blocks[0] == pytest.approx(tui._STARTUP_POLL_INTERVAL)
    assert screen.blocks[-1] == pytest.approx(tui._MAX_GETCH_BLOCK)


def test_tui_v5_live_sort_reorders_by_engine_key(monkeypatch, fake_store, fake_alerts, fake_config):
    """`_apply_live_sort` reorders process data by the engine's current key so
    a sort hotkey is reflected on the next repaint (not the next engine tick)."""
    from glances.outputs import glances_curses_v5 as tui_mod

    engine = _FakeEngine()
    engine.sort_key = "memory_percent"  # reverse=True default
    monkeypatch.setattr(tui_mod, "glances_processes", engine)
    tui = _make_tui(tui_mod, fake_store, fake_alerts, fake_config)

    snapshot = {
        "processlist": {
            "data": [
                {"pid": 1, "cpu_percent": 90.0, "memory_percent": 1.0, "name": "a"},
                {"pid": 2, "cpu_percent": 1.0, "memory_percent": 90.0, "name": "b"},
            ],
            "_levels": {},
        }
    }
    tui._apply_live_sort(snapshot)
    pids = [p["pid"] for p in snapshot["processlist"]["data"]]
    assert pids == [2, 1]  # memory_percent descending


def test_tui_v5_live_sort_does_not_mutate_store_payload(monkeypatch, fake_store, fake_alerts, fake_config):
    """The shallow store snapshot must not be mutated — the entry is replaced
    by a fresh dict with a freshly sorted list, leaving the original intact."""
    from glances.outputs import glances_curses_v5 as tui_mod

    engine = _FakeEngine()
    engine.sort_key = "memory_percent"
    monkeypatch.setattr(tui_mod, "glances_processes", engine)
    tui = _make_tui(tui_mod, fake_store, fake_alerts, fake_config)

    original_payload = {
        "data": [
            {"pid": 1, "cpu_percent": 90.0, "memory_percent": 1.0, "name": "a"},
            {"pid": 2, "cpu_percent": 1.0, "memory_percent": 90.0, "name": "b"},
        ],
        "_levels": {},
    }
    original_data = original_payload["data"]
    snapshot = {"processlist": original_payload}
    tui._apply_live_sort(snapshot)
    # Snapshot entry replaced (not the same object) but the original payload
    # and its list keep their original order.
    assert snapshot["processlist"] is not original_payload
    assert [p["pid"] for p in original_data] == [1, 2]


def test_tui_v5_live_sort_noop_without_key(monkeypatch, fake_store, fake_alerts, fake_config):
    from glances.outputs import glances_curses_v5 as tui_mod

    engine = _FakeEngine()
    engine.sort_key = None
    monkeypatch.setattr(tui_mod, "glances_processes", engine)
    tui = _make_tui(tui_mod, fake_store, fake_alerts, fake_config)

    payload = {"data": [{"pid": 1, "cpu_percent": 1.0, "memory_percent": 1.0, "name": "a"}], "_levels": {}}
    snapshot = {"processlist": payload}
    tui._apply_live_sort(snapshot)
    assert snapshot["processlist"] is payload  # untouched


# ---------------------------------------------------------------- help overlay


def test_tui_v5_every_hotkey_is_documented(fake_store, fake_alerts, fake_config):
    """Req #1 (exhaustiveness): every dispatched key carries a help group +
    description, and the group is one the overlay actually renders. Guards
    against adding a hotkey without documenting it."""
    from glances.outputs import glances_curses_v5 as tui_mod

    for key, spec in tui_mod.TuiV5._HOTKEYS.items():
        assert spec.get("desc"), f"hotkey {key!r} has no help description"
        assert spec.get("group") in tui_mod.TuiV5._HELP_GROUPS, f"hotkey {key!r} has an unknown help group"


def test_tui_v5_help_lines_cover_all_hotkeys(fake_store, fake_alerts, fake_config):
    """The generated help body mentions every hotkey from the dispatch table
    (single source of truth → no drift)."""
    from glances.outputs import glances_curses_v5 as tui_mod

    tui = _make_tui(tui_mod, fake_store, fake_alerts, fake_config)
    rendered = "\n".join(cell.text for row in tui._help_lines() for cell in row.cells)
    for key in tui_mod.TuiV5._HOTKEYS:
        assert f" {key} " in f" {rendered} " or f"{key:>2}" in rendered, f"{key!r} missing from help body"
    # Group headers present.
    for group in tui_mod.TuiV5._HELP_GROUPS:
        assert group in rendered


def test_tui_v5_h_key_opens_help(fake_store, fake_alerts, fake_config):
    """Pressing 'h' opens the overlay and asks for an immediate repaint."""
    from glances.outputs import glances_curses_v5 as tui_mod

    tui = _make_tui(tui_mod, fake_store, fake_alerts, fake_config)
    assert tui._view.show_help is False
    assert tui._handle_key(ord("h")) == "repaint"
    assert tui._view.show_help is True
    assert tui._help_scroll == 0


def test_tui_v5_help_close_keys_return_to_stats(fake_store, fake_alerts, fake_config):
    """While help is open, q / ESC / h all close it (and never quit)."""
    from glances.outputs import glances_curses_v5 as tui_mod

    for closing in (ord("q"), 27, ord("h")):
        tui = _make_tui(tui_mod, fake_store, fake_alerts, fake_config)
        tui._view.show_help = True
        assert tui._handle_key(closing) == "repaint"
        assert tui._view.show_help is False


def test_tui_v5_help_swallows_stats_hotkeys(monkeypatch, fake_store, fake_alerts, fake_config):
    """An open overlay captures all input: a sort key does NOT reach the
    engine, and the app does not quit on a non-close key."""
    from glances.outputs import glances_curses_v5 as tui_mod

    engine = _FakeEngine()
    monkeypatch.setattr(tui_mod, "glances_processes", engine)
    tui = _make_tui(tui_mod, fake_store, fake_alerts, fake_config)
    tui._view.show_help = True

    assert tui._handle_key(ord("c")) == "ignored"  # 'c' is not a help-nav key
    assert engine.calls == []  # never reached the sort engine
    assert tui._view.show_help is True  # still open


def test_tui_v5_help_scroll_keys(fake_store, fake_alerts, fake_config):
    """Arrow / vim / page keys move the scroll offset; up is floored at 0."""
    import curses

    from glances.outputs import glances_curses_v5 as tui_mod

    tui = _make_tui(tui_mod, fake_store, fake_alerts, fake_config)
    tui._view.show_help = True

    assert tui._handle_key(curses.KEY_DOWN) == "repaint"
    assert tui._help_scroll == 1
    assert tui._handle_key(ord("j")) == "repaint"
    assert tui._help_scroll == 2
    assert tui._handle_key(curses.KEY_UP) == "repaint"
    assert tui._help_scroll == 1
    # Up past the top floors at 0.
    tui._handle_key(curses.KEY_UP)
    tui._handle_key(curses.KEY_UP)
    assert tui._help_scroll == 0
    # Page down jumps by the page step.
    assert tui._handle_key(curses.KEY_NPAGE) == "repaint"
    assert tui._help_scroll == tui._HELP_PAGE_STEP
    # Home returns to the top.
    assert tui._handle_key(curses.KEY_HOME) == "repaint"
    assert tui._help_scroll == 0


def test_tui_v5_paint_help_renders_title_and_keys(fake_store, fake_alerts, fake_config):
    """`_paint_help` paints the title and at least one documented key."""
    from glances.outputs import glances_curses_v5 as tui_mod

    tui = _make_tui(tui_mod, fake_store, fake_alerts, fake_config)
    fake_stdscr = MagicMock()
    fake_stdscr.getmaxyx.return_value = (24, 80)
    tui._paint_help(fake_stdscr)

    flat = " ".join(str(call) for call in fake_stdscr.addstr.call_args_list)
    assert "Glances" in flat
    assert "help" in flat
    assert "SORT PROCESSES" in flat
    assert "Quit Glances" in flat


def test_tui_v5_help_shows_config_file(fake_store, fake_alerts):
    """The overlay shows the configuration file actually in use (v4 parity)."""
    from pathlib import Path

    from glances.outputs import glances_curses_v5 as tui_mod

    cfg = MagicMock()
    cfg.loaded_sources = [Path("/etc/glances/glances.conf")]
    tui = _make_tui(tui_mod, fake_store, fake_alerts, cfg)
    fake_stdscr = MagicMock()
    fake_stdscr.getmaxyx.return_value = (30, 100)
    tui._paint_help(fake_stdscr)

    flat = " ".join(str(call) for call in fake_stdscr.addstr.call_args_list)
    assert "Configuration file:" in flat
    assert "/etc/glances/glances.conf" in flat


def test_tui_v5_help_config_file_defaults_note_when_none(fake_store, fake_alerts):
    """No config file loaded → a clear 'built-in defaults' note, not a crash."""
    from glances.outputs import glances_curses_v5 as tui_mod

    cfg = MagicMock()
    cfg.loaded_sources = []
    tui = _make_tui(tui_mod, fake_store, fake_alerts, cfg)
    assert "(none" in tui._loaded_config_path()


def test_tui_v5_help_config_path_is_defensive(fake_store, fake_alerts):
    """A config object without `loaded_sources` must not crash the overlay."""
    from glances.outputs import glances_curses_v5 as tui_mod

    class _NoSources:
        def get(self, section, key, default=None):
            return default

        @property
        def loaded_sources(self):
            raise AttributeError("nope")

    tui = _make_tui(tui_mod, fake_store, fake_alerts, _NoSources())
    assert tui._loaded_config_path() == ""


def test_tui_v5_help_shows_doc_link(fake_store, fake_alerts, fake_config):
    """The overlay links to the readthedocs interactive-commands page."""
    from glances.outputs import glances_curses_v5 as tui_mod

    tui = _make_tui(tui_mod, fake_store, fake_alerts, fake_config)
    fake_stdscr = MagicMock()
    fake_stdscr.getmaxyx.return_value = (30, 100)
    tui._paint_help(fake_stdscr)

    flat = " ".join(str(call) for call in fake_stdscr.addstr.call_args_list)
    assert "https://glances.readthedocs.io/en/latest/cmds.html#interactive-commands" in flat


def test_tui_v5_help_shows_color_binding(fake_store, fake_alerts, fake_config):
    """The colour-binding legend documents the v5 palette + decorations."""
    from glances.outputs import glances_curses_v5 as tui_mod

    tui = _make_tui(tui_mod, fake_store, fake_alerts, fake_config)
    fake_stdscr = MagicMock()
    fake_stdscr.getmaxyx.return_value = (30, 100)
    tui._paint_help(fake_stdscr)

    flat = " ".join(str(call) for call in fake_stdscr.addstr.call_args_list)
    assert "Color binding:" in flat
    for sample in ("OK", "CAREFUL", "WARNING", "CRITICAL", "Title", "Sort"):
        assert sample in flat
    # The four severities appear twice: plain, then as the highlighted badge.
    assert flat.count("'CRITICAL'") == 2
    assert "an event is ongoing" in flat


def test_tui_v5_help_color_rows_use_real_attributes(fake_store, fake_alerts, fake_config):
    """Each legend sample carries the actual ColorRole / decoration so it
    renders in the colour it documents."""
    from glances.outputs import glances_curses_v5 as tui_mod
    from glances.outputs.curses_renderer_v5 import ColorRole

    tui = _make_tui(tui_mod, fake_store, fake_alerts, fake_config)
    levels, prominent, decorations = tui._help_color_rows()
    by_text = {c.text: c for c in levels.cells}
    assert by_text["OK"].color is ColorRole.OK
    assert by_text["CRITICAL"].color is ColorRole.CRITICAL
    # The plain severity row must NOT be highlighted — it is the counterpart
    # the `prominent` row is meant to contrast with.
    assert all(c.prominent is False for c in levels.cells)
    deco = {c.text: c for c in decorations.cells}
    assert deco["Sort"].underline is True


def test_tui_v5_help_documents_the_prominent_badge(fake_store, fake_alerts, fake_config):
    """The legend carries a row showing every severity as a highlighted badge,
    so the `prominent` decoration is discoverable rather than folk knowledge."""
    from glances.outputs import glances_curses_v5 as tui_mod
    from glances.outputs.curses_renderer_v5 import ColorRole

    tui = _make_tui(tui_mod, fake_store, fake_alerts, fake_config)
    _, prominent, _ = tui._help_color_rows()
    samples = {c.text: c for c in prominent.cells if c.prominent}
    assert set(samples) == {"OK", "CAREFUL", "WARNING", "CRITICAL"}
    assert samples["OK"].color is ColorRole.OK
    assert samples["CRITICAL"].color is ColorRole.CRITICAL


def test_tui_v5_paint_help_clamps_scroll_and_shows_footer(fake_store, fake_alerts, fake_config):
    """On a terminal too short for the whole list, an over-scroll is clamped
    and the scroll footer is shown."""
    from glances.outputs import glances_curses_v5 as tui_mod

    tui = _make_tui(tui_mod, fake_store, fake_alerts, fake_config)
    fake_stdscr = MagicMock()
    # Tiny + narrow → single column, content overflows vertically.
    fake_stdscr.getmaxyx.return_value = (8, 30)
    tui._help_scroll = 999  # absurd over-scroll
    tui._paint_help(fake_stdscr)

    # Clamped to a sane bound (< total rows).
    assert tui._help_scroll < 999
    flat = " ".join(str(call) for call in fake_stdscr.addstr.call_args_list)
    assert "more" in flat  # the scroll footer was painted


def test_tui_v5_paint_help_no_footer_when_everything_fits(fake_store, fake_alerts, fake_config):
    """A roomy terminal shows the whole help with no scroll footer."""
    from glances.outputs import glances_curses_v5 as tui_mod

    tui = _make_tui(tui_mod, fake_store, fake_alerts, fake_config)
    fake_stdscr = MagicMock()
    fake_stdscr.getmaxyx.return_value = (40, 120)
    tui._paint_help(fake_stdscr)

    flat = " ".join(str(call) for call in fake_stdscr.addstr.call_args_list)
    assert "more" not in flat  # nothing to scroll → no footer


def test_tui_v5_repaint_uses_help_when_open(fake_store, fake_alerts, fake_config):
    """`_repaint` paints the help overlay (not the stats frame) when open."""
    from glances.outputs import glances_curses_v5 as tui_mod

    tui = _make_tui(tui_mod, fake_store, fake_alerts, fake_config)
    tui._view.show_help = True
    fake_stdscr = MagicMock()
    fake_stdscr.getmaxyx.return_value = (24, 80)
    tui._repaint(fake_stdscr)

    flat = " ".join(str(call) for call in fake_stdscr.addstr.call_args_list)
    assert "Glances" in flat and "help" in flat


def test_tui_v5_q_key_fires_on_quit_callback(monkeypatch, fake_store, fake_alerts, fake_config):
    """Pressing 'q' fires the on_quit callback so the main loop can shut down."""
    from glances.outputs import glances_curses_v5 as tui_mod

    fake_stdscr = MagicMock()
    fake_stdscr.getmaxyx.return_value = (24, 80)
    fake_stdscr.getch.side_effect = [ord("q"), -1, -1]

    monkeypatch.setattr(tui_mod, "_safe_curses_wrapper", lambda fn: fn(fake_stdscr))

    fired: list[bool] = []
    tui = tui_mod.TuiV5(
        store=fake_store,
        alerts=fake_alerts,
        config=fake_config,
        registry=[("mem", False)],
        fields_by_plugin={"mem": {}},
        refresh_interval=0.01,
        on_quit=lambda: fired.append(True),
    )
    tui.start()
    tui.join(timeout=1.0)
    assert fired == [True]


# ---------------------------------------------------------------- header line


def test_paint_header_places_first_left_and_last_right(fake_store, fake_alerts, fake_config):
    """Header: first block flush-left at x=0; last block's right edge near max_x."""
    from glances.outputs import glances_curses_v5 as tui_mod
    from glances.outputs.curses_renderer_v5 import Cell, PluginBlock, Row

    tui = tui_mod.TuiV5(
        store=fake_store,
        alerts=fake_alerts,
        config=fake_config,
        registry=[],
        fields_by_plugin={},
        refresh_interval=0.01,
    )
    left = PluginBlock(name="system", rows=[Row(cells=[Cell(text="myhost Ubuntu")])])
    right = PluginBlock(name="uptime", rows=[Row(cells=[Cell(text="Uptime: 3d04h")])])

    fake_stdscr = MagicMock()
    height = tui._paint_header(fake_stdscr, [left, right], y0=0, max_x=80)

    assert height == 1
    calls = [(c.args[0], c.args[1], c.args[2]) for c in fake_stdscr.addstr.call_args_list]
    # Left block at x=0.
    assert any(y == 0 and x == 0 and "myhost" in text for (y, x, text) in calls)
    # Right block flush-right: its x is max_x - width("Uptime: 3d04h").
    expected_right_x = 80 - len("Uptime: 3d04h")
    assert any(y == 0 and x == expected_right_x and "Uptime" in text for (y, x, text) in calls)


def test_paint_header_two_blocks_unchanged(fake_store, fake_alerts, fake_config):
    """REGRESSION GUARD: the 2-block path (system/uptime, no middle block)
    must stay byte-for-byte equivalent to the pre-ip painter behaviour.
    """
    from glances.outputs import glances_curses_v5 as tui_mod
    from glances.outputs.curses_renderer_v5 import Cell, PluginBlock, Row

    tui = tui_mod.TuiV5(
        store=fake_store,
        alerts=fake_alerts,
        config=fake_config,
        registry=[],
        fields_by_plugin={},
        refresh_interval=0.01,
    )
    left = PluginBlock(name="system", rows=[Row(cells=[Cell(text="myhost Ubuntu")])])
    right = PluginBlock(name="uptime", rows=[Row(cells=[Cell(text="Uptime: 3d04h")])])

    fake_stdscr = MagicMock()
    height = tui._paint_header(fake_stdscr, [left, right], y0=0, max_x=80)

    assert height == 1
    calls = [(c.args[0], c.args[1], c.args[2]) for c in fake_stdscr.addstr.call_args_list]
    assert any(y == 0 and x == 0 and "myhost" in text for (y, x, text) in calls)
    expected_right_x = 80 - len("Uptime: 3d04h")
    assert any(y == 0 and x == expected_right_x and "Uptime" in text for (y, x, text) in calls)


def test_paint_header_packs_middle_block_between_first_and_last(fake_store, fake_alerts, fake_config):
    """Header with 3 blocks (system/ip/uptime): first flush-left, middle
    packed after it, last flush-right — v4 parity (`system … ip … uptime`).
    """
    from glances.outputs import glances_curses_v5 as tui_mod
    from glances.outputs.curses_renderer_v5 import Cell, ColorRole, PluginBlock, Row

    tui = tui_mod.TuiV5(
        store=fake_store,
        alerts=fake_alerts,
        config=fake_config,
        registry=[],
        fields_by_plugin={},
        refresh_interval=0.01,
    )
    system = PluginBlock(name="system", rows=[Row(cells=[Cell(text="myhost Ubuntu")])])
    ip = PluginBlock(
        name="ip",
        rows=[Row(cells=[Cell(text="IP", color=ColorRole.HEADER), Cell(text="192.168.1.10/24")])],
    )
    uptime = PluginBlock(name="uptime", rows=[Row(cells=[Cell(text="Uptime: 3d04h")])])

    fake_stdscr = MagicMock()
    max_x = 120
    height = tui._paint_header(fake_stdscr, [system, ip, uptime], y0=0, max_x=max_x)

    assert height == 1
    calls = [(c.args[0], c.args[1], c.args[2]) for c in fake_stdscr.addstr.call_args_list]
    uptime_x = max_x - len("Uptime: 3d04h")

    # First block flush-left.
    assert any(y == 0 and x == 0 and "myhost" in text for (y, x, text) in calls)
    # Middle block (ip) painted after the first block and before the
    # flush-right last block.
    assert any(
        y == 0 and system.width < x < uptime_x and ("IP" in text or "192.168.1.10" in text) for (y, x, text) in calls
    )
    # Last block flush-right.
    assert any(y == 0 and x == uptime_x and "Uptime" in text for (y, x, text) in calls)


def test_paint_header_right_aligns_uptime_and_now_as_a_group(fake_store, fake_alerts, fake_config):
    """Header with 4 blocks: `system`/`ip` packed left, `uptime`/`now`
    right-aligned as one group with `now` flush against the right edge.
    """
    from glances.outputs import glances_curses_v5 as tui_mod
    from glances.outputs.curses_renderer_v5 import Cell, ColorRole, PluginBlock, Row

    tui = tui_mod.TuiV5(
        store=fake_store,
        alerts=fake_alerts,
        config=fake_config,
        registry=[],
        fields_by_plugin={},
        refresh_interval=0.01,
    )
    system = PluginBlock(name="system", rows=[Row(cells=[Cell(text="myhost Ubuntu")])])
    ip = PluginBlock(
        name="ip",
        rows=[Row(cells=[Cell(text="IP", color=ColorRole.HEADER), Cell(text="192.168.1.10/24")])],
    )
    uptime = PluginBlock(name="uptime", rows=[Row(cells=[Cell(text="Uptime: 3d04h")])])
    now = PluginBlock(name="now", rows=[Row(cells=[Cell(text="2026-07-25 11:30:00")])])

    fake_stdscr = MagicMock()
    max_x = 120
    height = tui._paint_header(fake_stdscr, [system, ip, uptime, now], y0=0, max_x=max_x)

    assert height == 1
    calls = [(c.args[0], c.args[1], c.args[2]) for c in fake_stdscr.addstr.call_args_list]
    now_x = max_x - now.width
    uptime_x = now_x - tui._HEADER_GAP - uptime.width

    # Left group.
    assert any(y == 0 and x == 0 and "myhost" in text for (y, x, text) in calls)
    assert any(
        y == 0 and system.width < x < uptime_x and ("IP" in text or "192.168.1.10" in text) for (y, x, text) in calls
    )
    # Right group: uptime then now, now's right edge exactly at max_x.
    assert any(y == 0 and x == uptime_x and "Uptime" in text for (y, x, text) in calls)
    assert any(y == 0 and x == now_x and "2026-07-25 11:30:00" in text for (y, x, text) in calls)


def test_paint_header_right_group_never_overlaps_the_left_group(fake_store, fake_alerts, fake_config):
    """On a terminal too narrow for both groups the right group is pushed past
    the left-packed blocks rather than painted over them."""
    from glances.outputs import glances_curses_v5 as tui_mod
    from glances.outputs.curses_renderer_v5 import Cell, PluginBlock, Row

    tui = tui_mod.TuiV5(
        store=fake_store,
        alerts=fake_alerts,
        config=fake_config,
        registry=[],
        fields_by_plugin={},
        refresh_interval=0.01,
    )
    system = PluginBlock(name="system", rows=[Row(cells=[Cell(text="myhost Ubuntu 24.04 LTS 64bit")])])
    uptime = PluginBlock(name="uptime", rows=[Row(cells=[Cell(text="Uptime: 3d04h")])])
    now = PluginBlock(name="now", rows=[Row(cells=[Cell(text="2026-07-25 11:30:00")])])

    fake_stdscr = MagicMock()
    max_x = 40  # smaller than system.width + uptime.width + gap + now.width
    tui._paint_header(fake_stdscr, [system, uptime, now], y0=0, max_x=max_x)

    calls = [(c.args[0], c.args[1], c.args[2]) for c in fake_stdscr.addstr.call_args_list]
    painted_x = [x for (y, x, text) in calls if y == 0 and "Uptime" in text]
    assert painted_x, "uptime must still be painted"
    assert all(x > system.width for x in painted_x)


def test_paint_header_empty_returns_zero(fake_store, fake_alerts, fake_config):
    from glances.outputs import glances_curses_v5 as tui_mod

    tui = tui_mod.TuiV5(
        store=fake_store,
        alerts=fake_alerts,
        config=fake_config,
        registry=[],
        fields_by_plugin={},
        refresh_interval=0.01,
    )
    assert tui._paint_header(MagicMock(), [], y0=0, max_x=80) == 0


def test_paint_shifts_top_row_below_header(fake_store, fake_alerts, fake_config):
    """When a header is present, a separator sits at y=1 and the top row at y=2."""
    from glances.outputs import glances_curses_v5 as tui_mod
    from glances.outputs.curses_renderer_v5 import Cell, Frame, PluginBlock, Row

    tui = tui_mod.TuiV5(
        store=fake_store,
        alerts=fake_alerts,
        config=fake_config,
        registry=[],
        fields_by_plugin={},
        refresh_interval=0.01,
    )
    frame = Frame(
        header=[PluginBlock(name="system", rows=[Row(cells=[Cell(text="myhost")])])],
        top=[PluginBlock(name="cpu", rows=[Row(cells=[Cell(text="CPU 5%")])])],
    )
    fake_stdscr = MagicMock()
    fake_stdscr.getmaxyx.return_value = (24, 80)
    tui._paint(fake_stdscr, frame)

    calls = [(c.args[0], c.args[2]) for c in fake_stdscr.addstr.call_args_list]
    # Header on row 0, separator (─) on row 1, CPU top-row on row 2.
    assert any(y == 0 and "myhost" in text for (y, text) in calls)
    assert any(y == 1 and "─" in text for (y, text) in calls)
    assert any(y == 2 and "CPU" in text for (y, text) in calls)


def test_separator_default_enabled_uses_box_drawing_char(fake_store, fake_alerts, fake_config):
    """Default separator glyph is ─ (U+2500), not the ASCII hyphen."""
    from glances.outputs import glances_curses_v5 as tui_mod

    tui = tui_mod.TuiV5(
        store=fake_store,
        alerts=fake_alerts,
        config=fake_config,
        registry=[],
        fields_by_plugin={},
        refresh_interval=0.01,
    )
    assert tui._separator_enabled is True
    fake_stdscr = MagicMock()
    tui._paint_separator(fake_stdscr, y=3, x0=0, width=20)
    drawn = [c.args[2] for c in fake_stdscr.addstr.call_args_list]
    assert any("─" in text for text in drawn)
    # The old ASCII-hyphen rule must be gone.
    assert not any(set(text) == {"-"} for text in drawn)


def test_separator_disabled_paints_nothing(fake_store, fake_alerts):
    """[outputs] separator=False → _paint_separator draws no glyph."""
    from glances.outputs import glances_curses_v5 as tui_mod

    cfg = MagicMock()
    cfg.get.side_effect = lambda section, key, default=None: (
        False if (section, key) == ("outputs", "separator") else default
    )
    tui = tui_mod.TuiV5(
        store=fake_store,
        alerts=fake_alerts,
        config=cfg,
        registry=[],
        fields_by_plugin={},
        refresh_interval=0.01,
    )
    assert tui._separator_enabled is False
    fake_stdscr = MagicMock()
    tui._paint_separator(fake_stdscr, y=3, x0=0, width=20)
    fake_stdscr.addstr.assert_not_called()


def test_separator_disabled_renders_blank_line(fake_store, fake_alerts):
    """[outputs] separator=False → separator rows are blank, layout preserved.

    The top row still lands at y=2 (header y=0, blank separator y=1), so the
    vertical rhythm matches the enabled case — only the ─ glyph disappears."""
    from glances.outputs import glances_curses_v5 as tui_mod
    from glances.outputs.curses_renderer_v5 import Cell, Frame, PluginBlock, Row

    cfg = MagicMock()
    cfg.get.side_effect = lambda section, key, default=None: (
        False if (section, key) == ("outputs", "separator") else default
    )
    tui = tui_mod.TuiV5(
        store=fake_store,
        alerts=fake_alerts,
        config=cfg,
        registry=[],
        fields_by_plugin={},
        refresh_interval=0.01,
    )
    frame = Frame(
        header=[PluginBlock(name="system", rows=[Row(cells=[Cell(text="myhost")])])],
        top=[PluginBlock(name="cpu", rows=[Row(cells=[Cell(text="CPU 5%")])])],
    )
    fake_stdscr = MagicMock()
    fake_stdscr.getmaxyx.return_value = (24, 80)
    tui._paint(fake_stdscr, frame)

    calls = [(c.args[0], c.args[2]) for c in fake_stdscr.addstr.call_args_list]
    # No box-drawing rule anywhere.
    assert not any("─" in text for (_y, text) in calls)
    # But the blank separator row is still reserved: top row remains at y=2.
    assert any(y == 0 and "myhost" in text for (y, text) in calls)
    assert any(y == 2 and "CPU" in text for (y, text) in calls)


# ------------------------------------------------- TOP-row responsive degrade


# Realistic TOP set (quicklook / cpu / mem / memswap / load) with representative
# payloads + fields lifted from the per-plugin render-curses tests, so the
# measured PluginBlock widths are real and the degradation cascade actually
# triggers at a narrow ``max_x``. Driving the real renderers (not mocks) is the
# whole point: the fitted-frame loop keys on ``PluginBlock.width``, which only
# means something when the blocks carry real content. With this set the natural
# TOP width is ~144 cols, so a 120-col terminal forces degradation while a
# 400-col one takes the no-degradation early return.
_TOP_PAYLOADS = {
    "quicklook": {
        "cpu": 20.0,
        "mem": 42.0,
        "swap": 10.0,
        "load": 25.0,
        "_levels": {
            "cpu": {"level": "ok", "prominent": True},
            "mem": {"level": "ok", "prominent": True},
            "load": {"level": "ok", "prominent": True},
        },
    },
    "cpu": {
        "total": 4.5,
        "user": 3.8,
        "system": 0.7,
        "idle": 95.5,
        "nice": 0.0,
        "iowait": 0.5,
        "irq": 0.0,
        "steal": 0.0,
        "guest": 0.1,
        "ctx_switches": 6727.5,
        "interrupts": 3000.4,
        "soft_interrupts": 1782.5,
        "_levels": {"total": {"level": "ok", "prominent": True}},
    },
    "mem": {
        "total": 16_421_208_064,
        "available": 7_691_833_344,
        "percent": 53.2,
        "used": 8_729_374_720,
        "free": 2_740_531_200,
        "active": 6_184_337_408,
        "inactive": 4_744_855_552,
        "buffers": 194_555_904,
        "cached": 4_538_667_008,
        "_levels": {"percent": {"level": "careful", "prominent": True}},
    },
    "memswap": {
        "total": 16 * 1024**3,
        "used": 4 * 1024**3,
        "free": 12 * 1024**3,
        "percent": 25.0,
        "sin": 100_000.0,
        "sout": 0.0,
        "_levels": {"percent": {"level": "ok", "prominent": True}},
    },
    "load": {
        "min1": 0.857,
        "min5": 0.716,
        "min15": 0.801,
        "cpucore": 16,
        "_levels": {"min15": {"level": "ok", "prominent": True}},
    },
}

_TOP_FIELDS = {
    "quicklook": {
        "cpu": {"unit": "percent"},
        "mem": {"unit": "percent"},
        "load": {"unit": "percent"},
    },
    "cpu": {
        "total": {"unit": "percent", "watched": True, "prominent": True, "label": "CPU"},
        "user": {"unit": "percent"},
        "system": {"unit": "percent"},
        "idle": {"unit": "percent"},
        "nice": {"unit": "percent"},
        "iowait": {"unit": "percent"},
        "irq": {"unit": "percent"},
        "steal": {"unit": "percent"},
        "guest": {"unit": "percent"},
        "ctx_switches": {"unit": "number", "rate": True, "short_name": "ctx_sw"},
        "interrupts": {"unit": "number", "rate": True, "short_name": "inter"},
        "soft_interrupts": {"unit": "number", "rate": True, "short_name": "sw_int"},
    },
    "mem": {
        "total": {"unit": "bytes", "label": "total"},
        "available": {"unit": "bytes", "label": "avail"},
        "percent": {"unit": "percent", "label": "MEM", "watched": True, "prominent": True},
        "used": {"unit": "bytes", "label": "used"},
        "free": {"unit": "bytes", "label": "free"},
        "active": {"unit": "bytes", "label": "active"},
        "inactive": {"unit": "bytes", "label": "inactive"},
        "buffers": {"unit": "bytes", "label": "buffers"},
        "cached": {"unit": "bytes", "label": "cached"},
    },
    "memswap": {
        "total": {"unit": "bytes"},
        "used": {"unit": "bytes"},
        "free": {"unit": "bytes"},
        "percent": {"unit": "percent", "watched": True, "prominent": True},
        "sin": {"unit": "bytespers", "rate": True},
        "sout": {"unit": "bytespers", "rate": True},
    },
    "load": {
        "min1": {"unit": "float", "label": "1 min", "watched": True},
        "min5": {"unit": "float", "label": "5 min", "watched": True, "prominent": True},
        "min15": {"unit": "float", "label": "15 min", "watched": True, "prominent": True},
        "cpucore": {"unit": "number", "internal": True},
    },
}


@pytest.fixture
def make_tui_with_top(fake_alerts, fake_config):
    """Build a ``TuiV5`` whose registry is a full, realistic TOP set.

    The store snapshot and fields drive the real cpu/mem/quicklook/memswap/load
    curses renderers, so ``PluginBlock.width`` reflects genuine content and the
    measure-driven cascade behaves as it would on a real terminal.
    """
    from glances.outputs import glances_curses_v5 as tui_mod

    def _factory():
        store = MagicMock()
        store.as_dict.return_value = {name: dict(p) for name, p in _TOP_PAYLOADS.items()}
        alerts = MagicMock()
        alerts.get_history.return_value = []
        alerts.get_ongoing.return_value = {}
        alerts.get_ongoing_since.return_value = {}
        alerts.is_initializing.return_value = False
        return tui_mod.TuiV5(
            store=store,
            alerts=alerts,
            config=fake_config,
            registry=[
                ("quicklook", False),
                ("cpu", False),
                ("mem", False),
                ("memswap", False),
                ("load", False),
            ],
            fields_by_plugin={name: dict(f) for name, f in _TOP_FIELDS.items()},
            refresh_interval=0.01,
        )

    return _factory


def test_degrade_steps_order():
    """The cascade order is the maintainer's v4 spec a→g, exported as a list."""
    from glances.outputs.glances_curses_v5 import _DEGRADE_STEPS

    assert _DEGRADE_STEPS == [
        ("mem_cols", 1),
        ("cpu_cols", 2),
        ("cpu_cols", 1),
        ("quicklook_freq_only", True),
        ("hide_quicklook", True),
        ("hide_memswap", True),
        ("hide_gpu", True),
    ]


def test_wide_terminal_no_degradation(make_tui_with_top):
    """A roomy terminal keeps every TOP plugin at full width (no degradation)."""
    tui = make_tui_with_top()
    natural = tui._build_frame(max_x=400)
    fitted = tui._build_fitted_frame(max_x=400)
    # All TOP plugins present.
    assert {"quicklook", "cpu", "mem", "memswap", "load"} <= {b.name for b in fitted.top}
    # Byte-for-byte the same widths as the non-degraded frame (early return).
    assert [b.width for b in fitted.top] == [b.width for b in natural.top]


def test_narrow_terminal_drops_load_never(make_tui_with_top):
    """A narrow terminal degrades cols / blocks but never clips LOAD, and the
    resulting TOP row actually fits ``max_x`` (the painter's own fit test)."""
    tui = make_tui_with_top()
    # Sanity: the natural row genuinely overflows 120 cols, so the cascade runs.
    natural = tui._build_frame(max_x=120)
    nat_w = [b.width for b in natural.top]
    assert sum(nat_w) + max(0, len(nat_w) - 1) * tui._TOP_GAP_MIN > 120

    frame = tui._build_fitted_frame(max_x=120)
    names = {b.name for b in frame.top}
    # LOAD must survive (the whole point of the cascade).
    assert "load" in names
    # The fitted top row must actually fit, mirroring the painter's fit rule.
    widths = [b.width for b in frame.top]
    assert sum(widths) + max(0, len(widths) - 1) * tui._TOP_GAP_MIN <= 120
    assert tui._top_fits(frame, 120) is True


def test_extreme_narrow_keeps_protected_blocks(make_tui_with_top):
    """Limit behaviour: an absurdly narrow ``max_x`` the cascade can never
    satisfy must not raise or loop forever. The cascade exhausts its hide
    steps (quicklook / memswap gone) but the protected blocks cpu/mem/load
    always survive — LOAD is protected by design, so the minimal degraded row
    can still exceed ``max_x`` (and curses clips). This documents that
    intended residual."""
    tui = make_tui_with_top()
    frame = tui._build_fitted_frame(max_x=20)
    names = {b.name for b in frame.top}
    # Protected blocks never hidden, even when the row cannot fit.
    assert {"cpu", "mem", "load"} <= names
    # The cascade exhausted its hide steps.
    assert "quicklook" not in names
    assert "memswap" not in names


# ------------------------------------------- RIGHT-sidebar processlist width
#
# The processlist block is painted in the RIGHT sidebar at
# ``right_width = max_x - left_width - _SIDEBAR_SEPARATOR_GAP``. ``TuiV5``
# computes that width and feeds it to the renderer as ``view["right_width"]``
# so it can drop low-priority columns to keep ``Command`` readable. A wide
# terminal leaves enough room for all 13 columns; a narrow one forces a drop.
# A realistic processlist payload + at least one LEFT plugin (network) make the
# sidebar split non-trivial, so the measured ``left_width`` is genuine.

# Realistic processlist payload + fields, lifted from
# ``tests/test_plugin_processlist_render_curses_v5.py`` so the real renderer
# produces genuine column widths.
_PROC_FIELDS = {
    "pid": {"unit": "number", "primary_key": True},
    "name": {"unit": "string"},
    "username": {"unit": "string"},
    "status": {"unit": "string", "watched": True, "threshold_type": "categorical"},
    "nice": {"unit": "number", "watched": True, "threshold_type": "categorical"},
    "num_threads": {"unit": "number"},
    "cpu_percent": {"unit": "percent", "watched": True, "prominent": False},
    "memory_percent": {"unit": "percent", "watched": True, "prominent": False},
    "cmdline": {"unit": "list"},
    "cpu_num": {"unit": "number"},
    "memory_info": {"unit": "byte", "internal": True},
    "io_counters": {"unit": "byte", "internal": True},
    "time_since_update": {"unit": "second", "internal": True},
}


def _proc(**overrides):
    base = {
        "pid": 1234,
        "name": "python3",
        "username": "alice",
        "status": "S",
        "nice": 0,
        "num_threads": 4,
        "cpu_percent": 12.5,
        "memory_percent": 3.1,
        "cmdline": ["python3", "myscript.py"],
        "cpu_num": 2,
        "memory_info": {"rss": 32 * 1024**2, "vms": 120 * 1024**2},
        "io_counters": [0, 0, 0, 0, 1],
        "cpu_times": {"user": 1.0, "system": 0.5},
        "time_since_update": 1.0,
    }
    base.update(overrides)
    return base


_BODY_PAYLOADS = {
    "processlist": {
        "data": [
            _proc(pid=1, cpu_percent=78.4, memory_percent=12.5, name="hot"),
            _proc(pid=42, cpu_percent=12.5, memory_percent=3.1, name="med"),
            _proc(pid=512, cpu_percent=0.5, memory_percent=0.2, username="root", name="sshd"),
        ],
        "_levels": {},
    },
    "network": {
        "data": [
            {"interface_name": "eth0", "bytes_recv": 1000, "bytes_sent": 500, "is_up": True, "time_since_update": 1.0},
            {"interface_name": "lo", "bytes_recv": 0, "bytes_sent": 0, "is_up": True, "time_since_update": 1.0},
        ],
        "_levels": {},
    },
}

_BODY_FIELDS = {
    "processlist": _PROC_FIELDS,
    "network": {
        "interface_name": {"unit": "string", "primary_key": True},
        "bytes_recv": {"unit": "bytespers", "rate": True, "watched": True},
        "bytes_sent": {"unit": "bytespers", "rate": True, "watched": True},
    },
}


@pytest.fixture
def make_tui_with_body(fake_alerts, fake_config):
    """Build a ``TuiV5`` with a realistic body: ``processlist`` in the RIGHT
    slot and ``network`` in the LEFT slot, so the sidebar split is non-trivial
    and the right-sidebar width fed to the processlist renderer is genuine.
    """
    from glances.outputs import glances_curses_v5 as tui_mod

    def _factory():
        store = MagicMock()
        store.as_dict.return_value = {name: dict(p) for name, p in _BODY_PAYLOADS.items()}
        alerts = MagicMock()
        alerts.get_history.return_value = []
        alerts.get_ongoing.return_value = {}
        alerts.get_ongoing_since.return_value = {}
        alerts.is_initializing.return_value = False
        return tui_mod.TuiV5(
            store=store,
            alerts=alerts,
            config=fake_config,
            registry=[
                ("network", False),
                ("processlist", True),
            ],
            fields_by_plugin={name: dict(f) for name, f in _BODY_FIELDS.items()},
            refresh_interval=0.01,
        )

    return _factory


def test_right_width_passed_and_narrows_columns(make_tui_with_body):
    """A narrow terminal: the right sidebar is small, so the processlist
    renderer drops columns (fewer than the full 13 header cells) while always
    keeping ``Command``."""
    tui = make_tui_with_body()
    frame = tui._build_fitted_frame(max_x=95)
    proc = next(b for b in frame.right if b.name == "processlist")
    header = proc.rows[0]
    assert len(header.cells) < 13
    assert any("Command" in c.text for c in header.cells)


def test_wide_terminal_keeps_all_proclist_columns(make_tui_with_body):
    """A roomy terminal leaves the right sidebar wide enough for every
    column — all 13 header cells survive."""
    tui = make_tui_with_body()
    frame = tui._build_fitted_frame(max_x=400)
    proc = next(b for b in frame.right if b.name == "processlist")
    assert len(proc.rows[0].cells) == 13


def test_right_width_is_published_even_without_a_processlist_block(fake_alerts, fake_config):
    """The alert block always exists in the RIGHT column, so the width hint
    must not be gated on a processlist block being present."""
    from unittest.mock import MagicMock

    store = MagicMock()
    store.as_dict.return_value = {}
    alerts = MagicMock()
    alerts.get_history.return_value = []
    alerts.is_initializing.return_value = False
    alerts.get_ongoing.return_value = {}
    alerts.get_ongoing_since.return_value = {}
    tui = _tui_with(store, alerts, fake_config, [], {})

    frame = tui._build_fitted_frame(max_x=100, max_y=40)
    assert [b.name for b in frame.right] == ["alert"]  # no processlist block present
    view = tui._build_view(100)
    tui._fit_right_width(view, frame, 100)
    assert isinstance(view["right_width"], int)
    assert view["right_width"] > 0


def test_right_width_is_not_published_when_the_right_column_is_empty(fake_alerts, fake_config):
    from unittest.mock import MagicMock

    from glances.outputs.curses_renderer_v5 import Frame

    store = MagicMock()
    store.as_dict.return_value = {}
    tui = _tui_with(store, fake_alerts, fake_config, [], {})
    view = tui._build_view(100)
    empty = Frame(header=[], top=[], left=[], right=[])
    tui._fit_right_width(view, empty, 100)
    assert "right_width" not in view


def test_only_right_width_key_is_published(make_tui_with_body):
    """One mechanism, one name — the retired processlist-only key is gone.

    Built from two literal fragments (rather than the name itself) so this
    regression test does not itself reintroduce the retired key into the
    codebase."""
    tui = make_tui_with_body()
    view = tui._build_view(100)
    frame = tui._build_fitted_frame(max_x=100, max_y=40)
    tui._fit_right_width(view, frame, 100)
    retired_key = "proclist" + "_width"
    assert retired_key not in view
    assert view["right_width"] > 0


def test_alert_block_still_renders_last_in_the_right_column(make_tui_with_body):
    """§11 — moving the append before the sort must not move the block."""
    tui = make_tui_with_body()
    frame = tui._build_fitted_frame(max_x=120, max_y=45)
    assert frame.right[-1].name == "alert"


def test_alert_block_is_appended_exactly_once(make_tui_with_body):
    tui = make_tui_with_body()
    frame = tui._build_fitted_frame(max_x=120, max_y=45)
    assert [b.name for b in frame.right].count("alert") == 1


def test_alert_block_never_overflows_the_right_column(make_tui_with_body):
    """No emitted row exceeds the painted block width, at any terminal size.

    ``make_tui_with_body``'s default alerts stub is empty history / no
    ongoing alerts, which collapses the block to the 1-row placeholder and
    never exercises the grid at all. Give it 20 ongoing (fully-evicted, no
    matching history) incidents so the grid genuinely renders, and compare
    against the real painted width (``view["right_width"]``), not ``max_x``
    — the alert block is only one of several blocks sharing the row.
    """
    tui = make_tui_with_body()
    tui.alerts.get_history.return_value = []
    tui.alerts.get_ongoing.return_value = {("cpu", f"core{i}", "total"): "warning" for i in range(20)}
    tui.alerts.get_ongoing_since.return_value = {}
    for max_x in (80, 96, 120, 200):
        view = tui._build_view(max_x)
        frame = tui._build_fitted_frame(max_x=max_x, max_y=45)
        frame = tui._fit_right_width(view, frame, max_x)
        block = next(b for b in frame.right if b.name == "alert")
        assert len(block.rows) > 1, "grid did not actually render"
        assert block.width <= view["right_width"]


def test_right_width_rebuild_fires_every_repaint_not_just_on_resize(make_tui_with_body, monkeypatch):
    """Pins CURRENT behaviour — does not endorse it.

    ``_build_view`` never seeds a prior ``right_width`` into the view it
    returns, so ``_fit_right_width``'s "did the value change" check is always
    true and its extra ``build_frame`` call fires on EVERY repaint, even at
    an unchanged width — unlike ``_fit_right_column``'s cached
    ``row_budget``, which short-circuits once the plan stops changing. If
    width caching is added later to close this gap, the call counts below
    will drop and this test must be updated deliberately, not silently."""
    from glances.outputs import glances_curses_v5 as tui_mod

    tui = make_tui_with_body()
    calls = []
    original_build_frame = tui_mod.build_frame

    def spy(*args, **kwargs):
        calls.append(1)
        return original_build_frame(*args, **kwargs)

    monkeypatch.setattr(tui_mod, "build_frame", spy)

    tui._build_fitted_frame(max_x=95)
    first_frame_calls = len(calls)
    calls.clear()
    tui._build_fitted_frame(max_x=95)  # same width again — no resize
    second_frame_calls = len(calls)

    # Both frames pay the extra rebuild — the count does NOT drop to 1 on the
    # second, unchanged-width call. This is the exact defect the review found.
    assert first_frame_calls == 2
    assert second_frame_calls == 2


def test_hide_gpu_is_last_cascade_step():
    from glances.outputs.glances_curses_v5 import _DEGRADE_STEPS

    keys = [k for k, _ in _DEGRADE_STEPS]
    assert keys[-1] == "hide_gpu"
    # Ordering contract: gpu hidden only after quicklook + memswap.
    assert keys.index("hide_memswap") < keys.index("hide_gpu")


def test_fit_header_progressively_degrades(fake_store, fake_alerts, fake_config):
    """Header line (system … ip … uptime) degrades in the maintainer order as
    the terminal narrows: full → drop system OS-info → hide ip → hide uptime.

    Thresholds are computed from the real block widths so the test does not
    hardcode fragile pixel counts; it asserts which level ``_build_fitted_frame``
    settles on at each straddled width."""
    from glances.outputs import glances_curses_v5 as tui_mod

    fake_store.as_dict.return_value = {
        "system": {"hostname": "host", "hr_name": "Ubuntu 24.04 64bit / Linux 6.17", "_levels": {}},
        "ip": {"address": "192.168.1.100", "mask_cidr": 24, "_levels": {}},
        "uptime": {"seconds": 3600, "_levels": {}},
    }
    tui = tui_mod.TuiV5(
        store=fake_store,
        alerts=fake_alerts,
        config=fake_config,
        registry=[("system", False), ("ip", False), ("uptime", False)],
        fields_by_plugin={
            "system": {"hostname": {"unit": "string"}, "hr_name": {"unit": "string"}},
            "ip": {"address": {"unit": "string"}, "mask_cidr": {"unit": "number"}},
            "uptime": {"seconds": {"unit": "seconds"}},
        },
        refresh_interval=0.01,
    )

    def _flat(block):
        return " ".join(c.text for r in block.rows for c in r.cells)

    gap = tui_mod.TuiV5._HEADER_GAP

    # Measure real widths at a very wide terminal (level 0 — everything shown).
    wide = tui._build_fitted_frame(1000)
    assert [b.name for b in wide.header] == ["system", "ip", "uptime"]
    w = {b.name: b.width for b in wide.header}
    assert "Ubuntu" in _flat(next(b for b in wide.header if b.name == "system"))

    # Short-system width (hostname only) via the hide_os_info view.
    short_view = {**tui._build_view(1000), "hide_os_info": True}
    w_sys_short = next(b.width for b in tui._frame_for_view(short_view).header if b.name == "system")

    # Level 1 — too narrow for the OS-info, but short system + ip + uptime fit.
    f1 = tui._build_fitted_frame(w_sys_short + gap + w["ip"] + gap + w["uptime"])
    assert [b.name for b in f1.header] == ["system", "ip", "uptime"]
    assert "Ubuntu" not in _flat(next(b for b in f1.header if b.name == "system"))

    # Level 2 — ip dropped (only short system + uptime fit).
    f2 = tui._build_fitted_frame(w_sys_short + gap + w["uptime"])
    assert [b.name for b in f2.header] == ["system", "uptime"]

    # Level 3 — uptime dropped too (only the hostname survives).
    f3 = tui._build_fitted_frame(w_sys_short)
    assert [b.name for b in f3.header] == ["system"]


def test_now_is_the_first_header_block_dropped(fake_store, fake_alerts, fake_config):
    """`now` is the least prioritary header block: as soon as the terminal is
    too narrow for the four blocks it goes first, leaving the v4
    `system … ip … uptime` banner (OS-info included) intact."""
    from glances.outputs import glances_curses_v5 as tui_mod

    fake_store.as_dict.return_value = {
        "system": {"hostname": "host", "hr_name": "Ubuntu 24.04 64bit / Linux 6.17", "_levels": {}},
        "ip": {"address": "192.168.1.100", "mask_cidr": 24, "_levels": {}},
        "uptime": {"seconds": 3600, "_levels": {}},
        "now": {"custom": "2026-07-25 11:30:00 CEST", "iso": "2026-07-25T11:30:00+02:00", "_levels": {}},
    }
    tui = tui_mod.TuiV5(
        store=fake_store,
        alerts=fake_alerts,
        config=fake_config,
        registry=[("system", False), ("ip", False), ("uptime", False), ("now", False)],
        fields_by_plugin={
            "system": {"hostname": {"unit": "string"}, "hr_name": {"unit": "string"}},
            "ip": {"address": {"unit": "string"}, "mask_cidr": {"unit": "number"}},
            "uptime": {"seconds": {"unit": "seconds"}},
            "now": {"custom": {"unit": "string"}, "iso": {"unit": "string"}},
        },
        refresh_interval=0.01,
    )
    gap = tui_mod.TuiV5._HEADER_GAP

    # Wide terminal: the four blocks, now last.
    wide = tui._build_fitted_frame(1000)
    assert [b.name for b in wide.header] == ["system", "ip", "uptime", "now"]
    w = {b.name: b.width for b in wide.header}

    # One char short of the full banner → `now` is dropped, nothing else.
    narrow = tui._build_fitted_frame(w["system"] + gap + w["ip"] + gap + w["uptime"] + gap + w["now"] - 1)
    assert [b.name for b in narrow.header] == ["system", "ip", "uptime"]
    system_text = " ".join(c.text for r in next(b for b in narrow.header if b.name == "system").rows for c in r.cells)
    assert "Ubuntu" in system_text  # OS-info still there: degraded one notch only


def test_cloud_is_dropped_before_now_ip_and_uptime(fake_store, fake_alerts, fake_config):
    """`cloud` is opt-in: it must be the first block sacrificed under width
    pressure, so enabling it never costs the user information (ip, uptime,
    now) that was already on screen before cloud was turned on."""
    from glances.outputs import glances_curses_v5 as tui_mod

    fake_store.as_dict.return_value = {
        "system": {"hostname": "host", "hr_name": "Ubuntu 24.04 64bit / Linux 6.17", "_levels": {}},
        "ip": {"address": "192.168.1.100", "mask_cidr": 24, "_levels": {}},
        "uptime": {"seconds": 3600, "_levels": {}},
        "cloud": {"platform": "OpenStack", "type": "gold", "name": "my-vm", "region": "eu-west-1a", "_levels": {}},
        "now": {"custom": "2026-07-25 11:30:00 CEST", "iso": "2026-07-25T11:30:00+02:00", "_levels": {}},
    }
    tui = tui_mod.TuiV5(
        store=fake_store,
        alerts=fake_alerts,
        config=fake_config,
        registry=[
            ("system", False),
            ("ip", False),
            ("uptime", False),
            ("cloud", False),
            ("now", False),
        ],
        fields_by_plugin={
            "system": {"hostname": {"unit": "string"}, "hr_name": {"unit": "string"}},
            "ip": {"address": {"unit": "string"}, "mask_cidr": {"unit": "number"}},
            "uptime": {"seconds": {"unit": "seconds"}},
            "cloud": {"platform": {"unit": "string"}},
            "now": {"custom": {"unit": "string"}, "iso": {"unit": "string"}},
        },
        refresh_interval=0.01,
    )
    gap = tui_mod.TuiV5._HEADER_GAP

    # Wide terminal: all five blocks, cloud between uptime and now.
    wide = tui._build_fitted_frame(1000)
    assert [b.name for b in wide.header] == ["system", "ip", "uptime", "cloud", "now"]
    w = {b.name: b.width for b in wide.header}

    # One char short of the full banner → cloud is dropped first, `now`
    # (and everything before it) survives untouched.
    narrow = tui._build_fitted_frame(
        w["system"] + gap + w["ip"] + gap + w["uptime"] + gap + w["cloud"] + gap + w["now"] - 1
    )
    assert [b.name for b in narrow.header] == ["system", "ip", "uptime", "now"]


def test_hide_cloud_is_the_first_header_cascade_step():
    """`cloud` is opt-in: turning it on must never degrade information that
    was already on screen, so it is sacrificed before everything else —
    including `now`, the next-least-prioritary block."""
    from glances.outputs.glances_curses_v5 import _HEADER_DEGRADE_STEPS

    keys = [k for k, _ in _HEADER_DEGRADE_STEPS]
    assert keys[0] == "hide_cloud"
    assert keys[1] == "hide_now"
    # Ordering contract: uptime stays the last resort.
    assert keys[-1] == "hide_uptime"


def test_attr_for_prominent_badge_is_bold():
    """The prominent badge is always bold — on an 8-colour terminal that is
    what promotes the light-gray foreground (colour 7) to true white."""
    import curses

    from glances.outputs.curses_renderer_v5 import Cell, ColorRole
    from glances.outputs.glances_curses_v5 import _attr_for

    cell = Cell(text="92.0", color=ColorRole.CRITICAL, prominent=True)
    assert _attr_for(cell) & curses.A_BOLD


def _badge_pairs(monkeypatch, colors: int) -> dict:
    """Run `_init_colors` against a fake curses and return {role: (fg, bg)}."""
    import curses

    calls: dict[int, tuple[int, int]] = {}
    monkeypatch.setattr(curses, "has_colors", lambda: True)
    monkeypatch.setattr(curses, "start_color", lambda: None)
    monkeypatch.setattr(curses, "use_default_colors", lambda: None)
    monkeypatch.setattr(curses, "COLORS", colors, raising=False)
    monkeypatch.setattr(curses, "init_pair", lambda n, fg, bg: calls.__setitem__(n, (fg, bg)))
    monkeypatch.setattr(curses, "color_pair", lambda n: n)
    monkeypatch.setattr("glances.outputs.glances_curses_v5._COLOR_PAIRS", {})
    monkeypatch.setattr("glances.outputs.glances_curses_v5._COLOR_PAIRS_REVERSE", {})

    from glances.outputs.glances_curses_v5 import _init_colors

    _init_colors()

    from glances.outputs.glances_curses_v5 import _COLOR_PAIRS_REVERSE as reverse

    return {role: calls[pair] for role, pair in reverse.items()}


def test_init_colors_badge_uses_theme_proof_cube_colours(monkeypatch):
    """The badge must paint itself in ABSOLUTE cube colours (>= 16).

    Themes redefine ANSI 0-15, so a badge built on them has unknowable
    contrast: under Catppuccin Mocha, ANSI red is the light pink #f38ba8 and
    white-on-red collapses to ~2:1. Indices 16-255 are spec-fixed, keeping the
    badge >= 11:1 whatever the theme. Foreground 16 rather than 0 because
    A_BOLD brightens 0-7 into mid-gray on many terminals.
    """
    from glances.outputs.curses_renderer_v5 import ColorRole

    fg_bg = _badge_pairs(monkeypatch, 256)

    assert fg_bg == {
        ColorRole.OK: (16, 120),
        ColorRole.CAREFUL: (16, 117),
        ColorRole.WARNING: (16, 183),
        ColorRole.CRITICAL: (16, 210),
    }
    assert all(bg >= 16 for _, bg in fg_bg.values())  # never a themed ANSI slot


def test_init_colors_badge_falls_back_on_16_colour_terminals(monkeypatch):
    """Below 256 colours there is no absolute palette — fall back to ANSI
    without crashing, picking the foreground by DEFAULT xterm luminance."""
    import curses

    from glances.outputs.curses_renderer_v5 import ColorRole

    fg_bg = _badge_pairs(monkeypatch, 16)

    # Green is the only light background in the default palette.
    assert fg_bg[ColorRole.OK] == (curses.COLOR_BLACK, curses.COLOR_GREEN)
    # The dark ones get true white (15), not the light-gray colour 7.
    assert fg_bg[ColorRole.CRITICAL] == (15, curses.COLOR_RED)


def _header_color(monkeypatch, colors: int, theme: str = "dark") -> int:
    """Run `_init_colors` against a fake curses and return the HEADER fg."""
    import curses

    from glances.outputs.curses_renderer_v5 import ColorRole

    calls: dict[int, tuple[int, int]] = {}
    monkeypatch.setattr(curses, "has_colors", lambda: True)
    monkeypatch.setattr(curses, "start_color", lambda: None)
    monkeypatch.setattr(curses, "use_default_colors", lambda: None)
    monkeypatch.setattr(curses, "COLORS", colors, raising=False)
    monkeypatch.setattr(curses, "init_pair", lambda n, fg, bg: calls.__setitem__(n, (fg, bg)))
    monkeypatch.setattr(curses, "color_pair", lambda n: n)
    monkeypatch.setattr("glances.outputs.glances_curses_v5._COLOR_PAIRS", {})
    monkeypatch.setattr("glances.outputs.glances_curses_v5._COLOR_PAIRS_REVERSE", {})

    from glances.outputs.glances_curses_v5 import _init_colors

    _init_colors(theme)

    from glances.outputs.glances_curses_v5 import _COLOR_PAIRS as fg_pairs

    return calls[fg_pairs[ColorRole.HEADER]][0]


def test_init_colors_header_default_theme_is_unchanged(monkeypatch):
    """The default MUST stay v4's bold white — every existing deployment
    renders it, and `theme` exists to add an option, not to move the default."""
    import curses

    assert _header_color(monkeypatch, 256) == curses.COLOR_WHITE
    assert _header_color(monkeypatch, 16) == curses.COLOR_WHITE


def test_init_colors_header_light_theme_is_dark_grey(monkeypatch):
    """`theme=light` mirrors the default for a white background: ~13:1 instead
    of the ~1.2:1 bold white lands at. Cube index, so no theme redefines it."""
    import curses

    assert _header_color(monkeypatch, 256, "light") == 236  # #303030
    assert _header_color(monkeypatch, 256, "light") >= 16  # never a themable ANSI slot
    assert _header_color(monkeypatch, 16, "light") == curses.COLOR_BLACK  # fallback


def test_init_colors_header_unknown_theme_falls_back_to_dark(monkeypatch):
    """An unrecognised `theme=` value must not break the TUI — treat it as dark."""
    import curses

    assert _header_color(monkeypatch, 256, "solarized-mocha") == curses.COLOR_WHITE


def test_tui_v5_reads_theme_from_config(fake_store, fake_alerts):
    """`[outputs] theme` reaches `_init_colors`, normalised (case/whitespace)."""
    from unittest.mock import MagicMock

    from glances.outputs import glances_curses_v5 as tui_mod

    cfg = MagicMock()
    cfg.get.side_effect = lambda section, key, default=None: "  LIGHT  " if key == "theme" else default
    tui = _make_tui(tui_mod, fake_store, fake_alerts, cfg)
    assert tui._theme == "light"


def test_tui_v5_theme_defaults_to_dark(fake_store, fake_alerts, fake_config):
    """No config key → dark, so an unconfigured user keeps the majority case."""
    from glances.outputs import glances_curses_v5 as tui_mod

    tui = _make_tui(tui_mod, fake_store, fake_alerts, fake_config)
    assert tui._theme == "dark"


# ------------------------------------------- RIGHT column vertical fit (body geometry)


def _tui_with(store, alerts, config, registry, fields):
    from glances.outputs import glances_curses_v5 as tui_mod

    return tui_mod.TuiV5(
        store=store,
        alerts=alerts,
        config=config,
        registry=registry,
        fields_by_plugin=fields,
        refresh_interval=0.01,
    )


def test_body_geometry_matches_what_paint_computes(fake_store, fake_alerts, fake_config):
    """The fitter and the painter must share EXACTLY the same geometry."""
    from glances.outputs.curses_renderer_v5 import Cell, Frame, PluginBlock, Row

    tui = _tui_with(fake_store, fake_alerts, fake_config, [], {})
    frame = Frame()
    frame.header.append(PluginBlock(name="system", rows=[Row(cells=[Cell(text="host")])]))
    frame.top.append(PluginBlock(name="cpu", rows=[Row(cells=[Cell(text="CPU")]) for _ in range(4)]))

    body_y0, body_height = tui._body_geometry(frame, 40)
    # header(1) + sep(1) + top(4) + sep(1)
    assert body_y0 == 7
    assert body_height == 33


def test_body_geometry_without_header_or_top(fake_store, fake_alerts, fake_config):
    from glances.outputs.curses_renderer_v5 import Frame

    tui = _tui_with(fake_store, fake_alerts, fake_config, [], {})
    assert tui._body_geometry(Frame(), 24) == (0, 24)


def test_tall_terminal_shows_more_than_twenty_processes(fake_alerts, fake_config):
    """Main rule: the processlist fills the terminal vertically."""
    from unittest.mock import MagicMock

    procs = [
        {
            "pid": 100 + i,
            "name": f"p{i}",
            "cmdline": [f"p{i}"],
            "cpu_percent": 1.0,
            "memory_percent": 1.0,
            "username": "root",
            "num_threads": 1,
            "nice": 0,
            "status": "S",
            "memory_info": {"vms": 1024, "rss": 512},
        }
        for i in range(300)
    ]
    store = MagicMock()
    store.as_dict.return_value = {"processlist": {"data": procs, "_levels": {}}}

    tui = _tui_with(store, fake_alerts, fake_config, [("processlist", True)], {"processlist": {}})
    frame = tui._build_fitted_frame(200, 80)
    block = [b for b in frame.right if b.name == "processlist"][0]
    assert block.height > 21


def test_short_terminal_keeps_the_alert_block_visible(fake_alerts, fake_config):
    """Fixed regression: the alert block must no longer be squeezed out."""
    from unittest.mock import MagicMock

    procs = [
        {
            "pid": 100 + i,
            "name": f"p{i}",
            "cmdline": [f"p{i}"],
            "cpu_percent": 1.0,
            "memory_percent": 1.0,
            "username": "root",
            "num_threads": 1,
            "nice": 0,
            "status": "S",
            "memory_info": {"vms": 1024, "rss": 512},
        }
        for i in range(300)
    ]
    store = MagicMock()
    store.as_dict.return_value = {"processlist": {"data": procs, "_levels": {}}}
    fake_alerts.get_history.return_value = [
        {
            "ts": f"2026-08-05T10:{i:02d}:00+00:00",
            "plugin": "cpu",
            "key": None,
            "field": "total",
            "level": "warning",
            "previous_level": "ok",
        }
        for i in range(20)
    ]

    tui = _tui_with(store, fake_alerts, fake_config, [("processlist", True)], {"processlist": {}})
    frame = tui._build_fitted_frame(200, 24)
    _, body_height = tui._body_geometry(frame, 24)

    total = sum(b.height for b in frame.right if b.rows)
    total += max(0, len([b for b in frame.right if b.rows]) - 1)
    assert total <= body_height, "the right column overflows the body"
    assert any(b.name == "alert" and b.rows for b in frame.right)


@pytest.mark.parametrize(
    ("max_x", "expect_degradation"),
    [(200, False), (120, True)],
    ids=["wide-early-return", "narrow-after-degradation"],
)
def test_right_column_never_overflows_across_heights(fake_alerts, fake_config, max_x, expect_degradation):
    """Invariant: whatever the height, the plan fits inside the body.

    Parametrised over the TWO return paths of ``_build_fitted_frame``: the wide
    terminal takes the early return (the TOP row already fits), the narrow one
    only returns after the horizontal degradation cascade has run. The vertical
    fit must hold on both, since the body height it budgets against depends on
    the TOP-row height the cascade is free to change.
    """
    from unittest.mock import MagicMock

    procs = [
        {
            "pid": 100 + i,
            "name": f"p{i}",
            "cmdline": [f"p{i}"],
            "cpu_percent": 1.0,
            "memory_percent": 1.0,
            "username": "root",
            "num_threads": 1,
            "nice": 0,
            "status": "S",
            "memory_info": {"vms": 1024, "rss": 512},
        }
        for i in range(300)
    ]
    containers = [
        {
            "name": f"ctr{i}",
            "status": "running",
            "cpu_percent": 1.0,
            "memory_usage_no_cache": 1024,
            "memory_limit": 4096,
        }
        for i in range(25)
    ]
    store = MagicMock()
    store.as_dict.return_value = {
        "processlist": {"data": procs, "_levels": {}},
        "containers": {"data": containers, "_levels": {}, "disable_stats": []},
        **{name: dict(p) for name, p in _TOP_PAYLOADS.items()},
    }
    # A populated, still-ongoing alert history — not `[]` — so the grid
    # actually renders (title + column-header + incident rows) at every
    # swept height, instead of collapsing to the single-row "no alert"
    # line. Distinct `field`s so each event opens its own incident
    # (`_derive_incidents` groups by `(plugin, key, field)`).
    alert_history = [
        {
            "ts": f"2026-08-05T10:{i:02d}:00+00:00",
            "plugin": "cpu",
            "key": None,
            "field": f"metric{i}",
            "level": "warning",
            "previous_level": "ok",
        }
        for i in range(30)
    ]
    fake_alerts.get_history.return_value = alert_history
    fake_alerts.get_ongoing.return_value = {("cpu", None, f"metric{i}"): "warning" for i in range(30)}
    fake_alerts.get_ongoing_since.return_value = {}

    tui = _tui_with(
        store,
        fake_alerts,
        fake_config,
        [
            ("quicklook", False),
            ("cpu", False),
            ("mem", False),
            ("memswap", False),
            ("load", False),
            ("processlist", True),
            ("containers", True),
        ],
        {"processlist": {}, "containers": {}, **{name: dict(f) for name, f in _TOP_FIELDS.items()}},
    )

    # Which return path does ``_build_fitted_frame`` take at this width? The
    # early one iff the natural TOP row already fits (mirrors ``_top_fits``).
    natural = tui._build_frame(max_x=max_x)
    nat_w = [b.width for b in natural.top]
    assert nat_w, "the registry must produce a real TOP row"
    overflows = sum(nat_w) + max(0, len(nat_w) - 1) * tui._TOP_GAP_MIN > max_x
    assert overflows is expect_degradation, f"max_x={max_x} does not exercise the intended return path"

    # The TOP row eats rows off the top, so sweep ``max_y`` relative to it and
    # cover the very same body heights (12→80) on both paths.
    offset, _ = tui._body_geometry(tui._build_fitted_frame(max_x, 200), 200)
    for body in range(12, 81):
        max_y = body + offset
        frame = tui._build_fitted_frame(max_x, max_y)
        _, body_height = tui._body_geometry(frame, max_y)
        assert body_height == body, f"unexpected body height at max_y={max_y}"
        visible = [b for b in frame.right if b.rows]
        total = sum(b.height for b in visible) + max(0, len(visible) - 1)
        assert total <= body_height, f"overflow at max_y={max_y}: {total} > {body_height}"

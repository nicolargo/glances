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
        "percpu": {"data": [], "_levels": {}},
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
        "percpu": {"data": [], "_levels": {}},
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


def test_tui_v5_programs_toggle_hides_one_list(fake_store, fake_alerts, fake_config):
    """`j` shows exactly one of processlist / programlist in the right slot."""
    from glances.outputs import glances_curses_v5 as tui_mod

    fake_store.as_dict.return_value = {
        "processlist": {"data": [], "_levels": {}},
        "programlist": {"data": [], "_levels": {}},
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
    for sample in ("OK", "CAREFUL", "WARNING", "CRITICAL", "Title", "Sort", "Alert"):
        assert sample in flat


def test_tui_v5_help_color_rows_use_real_attributes(fake_store, fake_alerts, fake_config):
    """Each legend sample carries the actual ColorRole / decoration so it
    renders in the colour it documents."""
    from glances.outputs import glances_curses_v5 as tui_mod
    from glances.outputs.curses_renderer_v5 import ColorRole

    tui = _make_tui(tui_mod, fake_store, fake_alerts, fake_config)
    levels, decorations = tui._help_color_rows()
    by_text = {c.text: c for c in levels.cells}
    assert by_text["OK"].color is ColorRole.OK
    assert by_text["CRITICAL"].color is ColorRole.CRITICAL
    deco = {c.text: c for c in decorations.cells}
    assert deco["Sort"].underline is True
    assert deco["Alert"].prominent is True


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
    """When a header is present, the top row starts at y=1, not y=0."""
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
    # Header on row 0, CPU top-row on row 1.
    assert any(y == 0 and "myhost" in text for (y, text) in calls)
    assert any(y == 1 and "CPU" in text for (y, text) in calls)

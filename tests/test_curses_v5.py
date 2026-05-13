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
    """Once `_show_percpu` flips True, the top slot exposes percpu instead of cpu."""
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
    tui._show_percpu = True
    frame = tui._build_frame()
    top_names = [b.name for b in frame.top]
    assert "percpu" in top_names
    assert "cpu" not in top_names


def test_tui_v5_hotkey_1_toggles_percpu(monkeypatch, fake_store, fake_alerts, fake_config):
    """Pressing '1' flips `_show_percpu`."""
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
    assert tui._show_percpu is False
    tui.start()
    tui.join(timeout=1.0)
    # After one '1' press, the flag was flipped — the thread exits on 'q'
    # but the flag retains the toggled value.
    assert tui._show_percpu is True


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

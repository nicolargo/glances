"""The engine's extended-stats selection, by PID (v5) and by position (v4).

v4's curses UI pushes its cursor POSITION into the engine through `set_args`.
v5's TUI does not hand the engine an argparse namespace at all — and a
position is the wrong handle regardless: the list is re-sorted on every cycle,
so position 3 names a different process from one refresh to the next and the
extended block would describe a moving target.
"""

import pytest

from glances.processes import GlancesProcesses


@pytest.fixture
def processes():
    return GlancesProcesses()


def test_no_pid_is_selected_by_default(processes):
    """v4's path must be untouched by v5's addition: with `extended_pid`
    unset, `is_extended_pid` never claims anything."""
    assert processes.extended_pid is None
    assert processes.is_extended_pid(1234) is False
    assert processes.is_extended_pid(None) is False


def test_the_pinned_pid_is_selected(processes):
    processes.extended_pid = 1234
    assert processes.is_extended_pid(1234) is True
    assert processes.is_extended_pid(1235) is False


def test_a_process_without_a_pid_is_never_selected(processes):
    """The loop calls this with `proc.get('pid')`, which can be None."""
    processes.extended_pid = 1234
    assert processes.is_extended_pid(None) is False


def test_position_selection_is_inert_without_args(processes):
    """v5 never calls `set_args`, so v4's position path is a constant False —
    which is why `e` did nothing in v5 before 2.X-b3: not an oversight in the
    key table, an absence of wiring."""
    assert processes.args is None
    assert processes.is_selected_extended_process(0) is False


def test_the_update_loop_actually_uses_the_pinned_pid():
    """Testing `is_extended_pid` alone proves nothing about the loop — the
    same gap that let an arrow key quit Glances in 2.X-b1. This drives the
    real `update()` and asserts the extended stats landed on the pid asked
    for, which cannot happen if the loop never consults it."""
    import os

    engine = GlancesProcesses()
    engine.extended_pid = os.getpid()
    engine.disable_extended_tag = False
    engine.update()

    assert engine.extended_process is not None
    assert engine.extended_process["pid"] == os.getpid()
    # The grab really happened, rather than the raw process dict being stored.
    assert engine.extended_process.get("extended_stats") is True
    assert "cpu_min" in engine.extended_process


def test_no_pin_means_no_extended_grab():
    """v4's behaviour, unchanged: without a selection the engine does not pay
    for extended stats on anybody."""
    engine = GlancesProcesses()
    engine.disable_extended_tag = False
    engine.update()

    assert engine.extended_process is None

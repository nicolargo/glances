"""The engine's extended-stats selection, by PID (v5) and by position (v4).

v4's curses UI pushes its cursor POSITION into the engine through `set_args`.
v5's TUI does not hand the engine an argparse namespace at all — and a
position is the wrong handle regardless: the list is re-sorted on every cycle,
so position 3 names a different process from one refresh to the next and the
extended block would describe a moving target.
"""

import psutil
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


def test_a_pinned_process_that_exits_is_forgotten(monkeypatch):
    """Found in a real browser, not in a test: pin a process, let it exit, and
    the block stays on screen showing its last numbers forever.

    Nothing in the update loop runs again for a pid that has left the list, so
    `extended_process` is never refreshed and never cleared — and it still
    carries `extended_stats: True`. v4 has the same defect, from the same
    lines. The PIN goes with it: a pin on a dead pid can never come back, and
    leaving it set keeps the TUI's cursor frozen on a block it no longer draws.
    """
    engine = GlancesProcesses()
    engine.extended_pid = 4242
    engine.extended_process = {"pid": 4242, "name": "gone", "extended_stats": True, "cpu_max": 9.0}

    # A cycle in which 4242 is not among the running processes. The dicts
    # carry what the rest of `update()` reads, so the assertion below is about
    # the pin and not about a KeyError somewhere downstream.
    def _one_process(attrs):
        return [
            {
                "pid": 1,
                "name": "init",
                "cmdline": ["/sbin/init"],
                "cpu_percent": 0.0,
                "memory_percent": 0.0,
                "memory_info": {"rss": 0, "vms": 0},
                "status": "S",
                "num_threads": 1,
                "nice": 0,
                "username": "root",
                "cpu_times": {"user": 0.0, "system": 0.0},
                "io_counters": [0, 0, 0, 0, 0],
                "gids": {"real": 0},
            }
        ]

    monkeypatch.setattr(engine, "build_process_list", _one_process)

    engine.update()

    assert engine.extended_process is None
    assert engine.extended_pid is None


def test_a_pinned_process_that_is_still_running_is_kept(monkeypatch):
    """The guard above must not fire on the ordinary case."""
    import os

    engine = GlancesProcesses()
    engine.extended_pid = os.getpid()
    engine.disable_extended_tag = False
    engine.update()

    assert engine.extended_pid == os.getpid()
    assert engine.extended_process is not None


class _SwapProc:
    def __init__(self, raises=None, swap=0):
        self._raises = raises
        self._swap = swap

    def memory_maps(self):
        if self._raises is not None:
            raise self._raises
        return [type("m", (), {"swap": self._swap})()]


@pytest.mark.parametrize("error", [KeyError("issue #1551"), psutil.NoSuchProcess(1)])
def test_a_failed_swap_read_reports_no_figure_rather_than_raising(error, processes):
    """The handler used to `pass`, leaving `memory_swap` UNBOUND — so the
    return below raised `UnboundLocalError` instead of saying "no figure".

    Unreachable until 2.X-b3: nothing but `e` calls `set_extended_stats`, and
    the two ways in are a process that exits mid-grab and issue #1551. Pinning
    a short-lived process is exactly the first.
    """
    swap = processes._GlancesProcesses__get_extended_memory_swap(_SwapProc(raises=error))
    assert swap is None


def test_a_readable_process_still_reports_its_swap(processes):
    """The guard above must not swallow the ordinary answer."""
    assert processes._GlancesProcesses__get_extended_memory_swap(_SwapProc(swap=4096)) == 4096


def test_access_denied_reports_no_figure_too(processes):
    """Already handled before this chantier; pinned here so the three paths
    are one decision rather than two guarded and one not."""
    assert processes._GlancesProcesses__get_extended_memory_swap(_SwapProc(raises=psutil.AccessDenied(1))) is None

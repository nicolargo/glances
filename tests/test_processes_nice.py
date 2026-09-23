"""Whether a renice was accepted has to be answerable, not just loggable.

`nice_increase` / `nice_decrease` are called by both UIs. v4's curses code
ignores the return and lets a refusal live in the log — where a TUI user
cannot see it, so the key looks broken. The v5 TUI puts the refusal on
screen, which it can only do if the engine says what happened.
"""

import psutil
import pytest

from glances.processes import GlancesProcesses


@pytest.fixture
def processes():
    return GlancesProcesses()


class _Proc:
    def __init__(self, value=0, refuse=False):
        self.value = value
        self.refuse = refuse

    def nice(self, new=None):
        """psutil's own getter/setter shape: no argument reads, an argument writes."""
        if new is None:
            return self.value
        if self.refuse:
            raise psutil.AccessDenied(1234)
        self.value = new
        return None


@pytest.mark.parametrize(("method", "delta"), [("nice_increase", 1), ("nice_decrease", -1)])
def test_an_applied_renice_reports_success(monkeypatch, processes, method, delta):
    proc = _Proc(value=5)
    monkeypatch.setattr(psutil, "Process", lambda pid: proc)
    assert getattr(processes, method)(1234) is True
    assert proc.value == 5 + delta


@pytest.mark.parametrize("method", ["nice_increase", "nice_decrease"])
def test_a_refused_renice_reports_failure_instead_of_raising(monkeypatch, processes, method):
    """`AccessDenied` stays swallowed — v4 callers rely on that — but it is no
    longer indistinguishable from success."""
    monkeypatch.setattr(psutil, "Process", lambda pid: _Proc(refuse=True))
    assert getattr(processes, method)(1234) is False


@pytest.mark.parametrize("method", ["nice_increase", "nice_decrease"])
def test_a_vanished_process_still_raises(monkeypatch, processes, method):
    """`psutil.Process(pid)` is built outside the `try` on purpose: a process
    that exited between the paint and the keypress is a different situation
    from one we are not allowed to touch, and the caller reports it
    differently."""

    def _gone(pid):
        raise psutil.NoSuchProcess(pid)

    monkeypatch.setattr(psutil, "Process", _gone)
    with pytest.raises(psutil.NoSuchProcess):
        getattr(processes, method)(1234)

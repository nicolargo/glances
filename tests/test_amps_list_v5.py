#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — unit tests for AmpsListV5 (loader half; cadence in Task 4)."""

from __future__ import annotations

import asyncio
import textwrap
import threading
from pathlib import Path

import pytest

from glances import amps_list_v5 as amps_module
from glances.amps_list_v5 import AmpsListV5
from glances.config_v5 import GlancesConfigV5


@pytest.fixture
def cfg(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Build a GlancesConfigV5 from an inline config body."""

    def _make(body: str) -> GlancesConfigV5:
        xdg_conf = tmp_path / "xdg" / "glances" / "glances.conf"
        xdg_conf.parent.mkdir(parents=True, exist_ok=True)
        xdg_conf.write_text(textwrap.dedent(body).lstrip("\n"))
        monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
        return GlancesConfigV5()

    return _make


def test_no_amp_section_yields_an_empty_registry(cfg):
    amps = AmpsListV5(cfg("[global]\nrefresh = 2\n"))
    assert amps._amps == {}


def test_unknown_amp_falls_back_to_the_default_module(cfg):
    amps = AmpsListV5(
        cfg(
            """
            [amp_foo]
            enable=true
            regex=.*foo.*
            refresh=3
            command=echo hello
            """
        )
    )
    assert "foo" in amps._amps
    assert type(amps._amps["foo"]).__module__ == "glances.amps.default"
    # default AMP capitalises the name (v4 parity)
    assert amps._amps["foo"].NAME == "Foo"


def test_named_module_is_loaded_when_it_exists(cfg):
    amps = AmpsListV5(
        cfg(
            """
            [amp_systemd]
            enable=true
            regex=systemd
            refresh=30
            systemctl_cmd=/bin/systemctl --plain
            """
        )
    )
    assert type(amps._amps["systemd"]).__module__ == "glances.amps.systemd"


def test_amp_module_with_a_missing_dependency_is_skipped(monkeypatch, cfg):
    """`ModuleNotFoundError` means two different things (finding #5): no
    dedicated AMP module (-> fall back to `default`) versus the AMP module
    existing but importing a missing third-party lib (-> skip the AMP, as v4
    does with its "Missing Python Lib" warning). Discriminated on `e.name`."""
    import importlib as _importlib

    real_import = _importlib.import_module

    def _fake_import(name, *args, **kwargs):
        if name == "glances.amps.nginx":
            raise ModuleNotFoundError("No module named 'requests'", name="requests")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("glances.amps_list_v5.importlib.import_module", _fake_import)

    amps = AmpsListV5(cfg("[amp_nginx]\nenable=true\nregex=nginx\nrefresh=60\n"))
    assert amps._amps == {}, "the AMP must be skipped, not silently replaced by the default one"


def test_config_is_loaded_into_the_amp(cfg):
    amps = AmpsListV5(
        cfg(
            """
            [amp_foo]
            enable=true
            regex=.*foo.*
            refresh=3
            countmin=1
            command=echo hello
            """
        )
    )
    amp = amps._amps["foo"]
    assert amp.enable() is True
    assert amp.refresh() == 3.0
    assert amp.count_min() == 1.0
    assert amp.regex() == ".*foo.*"


def test_invalid_amp_name_falls_back_to_the_default_module(cfg):
    amps = AmpsListV5(
        cfg(
            """
            [amp_not-an-identifier]
            enable=true
            refresh=3
            command=echo hello
            """
        )
    )
    assert type(amps._amps["not-an-identifier"]).__module__ == "glances.amps.default"


def test_regex_is_precompiled_once(cfg):
    amps = AmpsListV5(
        cfg(
            """
            [amp_foo]
            enable=true
            regex=.*foo.*
            refresh=3
            """
        )
    )
    assert amps._regex["foo"].pattern == ".*foo.*"


def test_regexless_amp_has_no_compiled_pattern(cfg):
    amps = AmpsListV5(
        cfg(
            """
            [amp_conntrack]
            enable=true
            refresh=30
            command=echo hello
            """
        )
    )
    assert "conntrack" in amps._amps
    assert "conntrack" not in amps._regex


def test_invalid_regex_disables_the_amp(cfg):
    amps = AmpsListV5(
        cfg(
            """
            [amp_foo]
            enable=true
            regex=(unclosed
            refresh=3
            """
        )
    )
    assert amps._amps["foo"].enable() is False


def test_registry_is_per_instance_not_shared(cfg):
    """v4's AmpsList.__amps_dict is a CLASS attribute shared by every
    instance (glances/amps_list.py:31). AmpsListV5 must not repeat that."""
    a = AmpsListV5(cfg("[amp_foo]\nenable=true\nrefresh=3\ncommand=echo a\n"))
    b = AmpsListV5(cfg("[global]\nrefresh = 2\n"))
    assert list(a._amps) == ["foo"]
    assert b._amps == {}


def test_disable_config_exec_reaches_the_amp(cfg):
    amps = AmpsListV5(
        cfg(
            """
            [global]
            disable_config_exec=true

            [amp_foo]
            enable=true
            refresh=3
            command=echo hello
            """
        )
    )
    assert amps._amps["foo"].allow_operators() is False


def test_disable_config_exec_defaults_to_allowing_operators(cfg):
    amps = AmpsListV5(cfg("[amp_foo]\nenable=true\nrefresh=3\ncommand=echo hello\n"))
    assert amps._amps["foo"].allow_operators() is True


def test_a_broken_load_config_skips_only_that_amp(monkeypatch, cfg):
    """A single `[amp_*]` section whose `load_config()` raises must not abort
    construction of the whole registry — only that AMP is skipped, every
    other AMP stays loaded."""
    from glances.amps.amp import GlancesAmp

    real_load_config = GlancesAmp.load_config

    def _fake_load_config(self, config):
        if self.amp_name == "bar":
            raise RuntimeError("boom")
        return real_load_config(self, config)

    monkeypatch.setattr(GlancesAmp, "load_config", _fake_load_config)

    amps = AmpsListV5(
        cfg(
            """
            [amp_foo]
            enable=true
            refresh=3
            command=echo hello

            [amp_bar]
            enable=true
            refresh=3
            command=echo world
            """
        )
    )
    assert "foo" in amps._amps
    assert "bar" not in amps._amps
    assert "bar" not in amps._regex


# ---------------------------------------------------------------------------
# update cycle
# ---------------------------------------------------------------------------

_PROC_PYTHON = {
    "pid": 11,
    "name": "python3",
    "cmdline": ["python3", "app.py"],
    "cpu_percent": 1.0,
    "memory_percent": 2.0,
}
_PROC_NGINX = {"pid": 22, "name": "nginx", "cmdline": ["/usr/sbin/nginx"], "cpu_percent": 3.0, "memory_percent": 4.0}


@pytest.fixture
def procs(monkeypatch):
    """Control the process list the AMPs match against."""

    def _set(processlist):
        monkeypatch.setattr(
            amps_module.glances_processes,
            "get_list",
            lambda: list(processlist),
            raising=False,
        )

    return _set


async def _settle(amps: AmpsListV5) -> None:
    """Await every in-flight AMP run."""
    while amps._inflight:
        await asyncio.gather(*list(amps._inflight.values()), return_exceptions=True)
        await asyncio.sleep(0)


async def test_count_reflects_the_matching_processes(cfg, procs):
    procs([_PROC_PYTHON, _PROC_NGINX])
    amps = AmpsListV5(cfg("[amp_python]\nenable=true\nregex=.*python.*\nrefresh=3\n"))
    await amps.update()
    await _settle(amps)
    assert amps._amps["python"].count() == 1


async def test_cmdline_is_searched_too(cfg, procs):
    procs(
        [{"pid": 1, "name": "sh", "cmdline": ["/usr/bin/foo", "--daemon"], "cpu_percent": 0.0, "memory_percent": 0.0}]
    )
    amps = AmpsListV5(cfg("[amp_foo]\nenable=true\nregex=.*foo.*\nrefresh=3\n"))
    await amps.update()
    await _settle(amps)
    assert amps._amps["foo"].count() == 1


async def test_disabled_amp_is_never_run(cfg, procs):
    procs([_PROC_PYTHON])
    amps = AmpsListV5(cfg("[amp_python]\nenable=false\nregex=.*python.*\nrefresh=3\n"))
    await amps.update()
    await _settle(amps)
    assert amps._amps["python"].result() is None


async def test_regexless_amp_runs_with_an_empty_process_list(cfg, procs):
    """Issue #1690 — no regex means 'run every refresh seconds'."""
    procs([])
    amps = AmpsListV5(cfg("[amp_conntrack]\nenable=true\nrefresh=30\ncommand=echo tracked\n"))
    await amps.update()
    await _settle(amps)
    assert amps._amps["conntrack"].count() == 0
    assert amps._amps["conntrack"].result().strip() == "tracked"


async def test_no_match_sets_the_no_running_process_message(cfg, procs):
    procs([_PROC_NGINX])
    amps = AmpsListV5(cfg("[amp_python]\nenable=true\nregex=.*python.*\nrefresh=3\ncountmin=1\n"))
    await amps.update()
    await _settle(amps)
    assert amps._amps["python"].count() == 0
    assert amps._amps["python"].result() == "No running process"


async def test_no_match_without_countmin_leaves_the_result_alone(cfg, procs):
    procs([_PROC_NGINX])
    amps = AmpsListV5(cfg("[amp_python]\nenable=true\nregex=.*python.*\nrefresh=3\n"))
    await amps.update()
    await _settle(amps)
    assert amps._amps["python"].result() is None


async def test_no_match_does_not_run_the_command(cfg, procs):
    """v4 does not call update() on the no-match branch — nor do we."""
    procs([_PROC_NGINX])
    amps = AmpsListV5(cfg("[amp_python]\nenable=true\nregex=.*python.*\nrefresh=3\ncommand=echo ran\n"))
    await amps.update()
    await _settle(amps)
    assert amps._amps["python"].result() is None


async def test_count_is_refreshed_even_when_the_timer_has_not_fired(cfg, procs):
    """The count must track the process list on EVERY cycle; only the
    (possibly expensive) update() is gated by the AMP's own refresh."""
    procs([_PROC_PYTHON])
    amps = AmpsListV5(cfg("[amp_python]\nenable=true\nregex=.*python.*\nrefresh=3600\ncommand=echo ran\n"))
    await amps.update()
    await _settle(amps)
    assert amps._amps["python"].count() == 1

    calls = []
    amps._amps["python"].update = lambda process_list: calls.append(process_list)
    procs([_PROC_PYTHON, dict(_PROC_PYTHON, pid=12)])
    await amps.update()
    await _settle(amps)

    assert amps._amps["python"].count() == 2, "count must be refreshed every cycle"
    assert calls == [], "update() must not run before the AMP's refresh has elapsed"


async def test_a_run_still_in_flight_is_not_started_twice(cfg, procs):
    procs([_PROC_PYTHON])
    amps = AmpsListV5(cfg("[amp_python]\nenable=true\nregex=.*python.*\nrefresh=0\n"))

    started = threading.Event()
    release = threading.Event()
    calls = []

    def _blocking_update(process_list):
        calls.append(process_list)
        started.set()
        release.wait(timeout=5)

    amps._amps["python"].update = _blocking_update

    await amps.update()
    # Wait for the worker thread to have really entered `update()` before
    # asserting on `calls` — otherwise the assertion races the thread start.
    assert await asyncio.to_thread(started.wait, 5)
    await amps.update()  # second cycle while the first run is still blocked
    assert len(calls) == 1, "the in-flight guard must skip the second launch"

    release.set()
    await _settle(amps)


async def test_the_timer_is_not_consumed_by_a_skipped_cycle(cfg, procs):
    """The in-flight check must run BEFORE should_update(), which re-arms the
    timer as a side effect. Otherwise a skipped cycle silently eats a tick."""
    procs([_PROC_PYTHON])
    amps = AmpsListV5(cfg("[amp_python]\nenable=true\nregex=.*python.*\nrefresh=0\n"))

    release = threading.Event()

    def _blocking_update(process_list):
        release.wait(timeout=5)

    amp = amps._amps["python"]
    amp.update = _blocking_update

    # `_maybe_run` registers the in-flight task synchronously, so the guard is
    # armed as soon as this returns — no need to yield to the event loop.
    await amps.update()
    assert "python" in amps._inflight

    should_update_calls = []
    original = amp.should_update
    amp.should_update = lambda: (should_update_calls.append(1), original())[1]
    await amps.update()
    assert should_update_calls == [], "should_update() must not be called while a run is in flight"

    release.set()
    await _settle(amps)


async def test_a_failing_amp_does_not_break_the_cycle(cfg, procs):
    procs([_PROC_PYTHON])
    amps = AmpsListV5(cfg("[amp_python]\nenable=true\nregex=.*python.*\nrefresh=0\n"))

    def _boom(process_list):
        raise RuntimeError("boom")

    amps._amps["python"].update = _boom
    await amps.update()
    await _settle(amps)
    assert amps._amps["python"].count() == 1  # the cycle completed


async def test_a_malformed_process_entry_yields_no_match(cfg, procs):
    """v4's _build_amps_list assigns `ret` inside a try that catches
    KeyError, then returns it — turning a caught KeyError into an
    UnboundLocalError (glances/amps_list.py:123-140)."""
    procs([{"pid": 1, "name": "python3"}])  # no cpu_percent / memory_percent
    amps = AmpsListV5(cfg("[amp_python]\nenable=true\nregex=.*python.*\nrefresh=3\n"))
    await amps.update()  # must not raise
    await _settle(amps)
    assert amps._amps["python"].count() == 0


async def test_update_returns_every_loaded_amp(cfg, procs):
    procs([])
    amps = AmpsListV5(
        cfg(
            """
            [amp_a]
            enable=true
            refresh=3
            command=echo a

            [amp_b]
            enable=false
            refresh=3
            command=echo b
            """
        )
    )
    returned = await amps.update()
    await _settle(amps)
    assert [type(a).__module__ for a in returned] == ["glances.amps.default", "glances.amps.default"]
    assert len(returned) == 2

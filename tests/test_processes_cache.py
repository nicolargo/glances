"""Tests for the GlancesProcesses internal cache eviction."""

import os
import time

import psutil
import pytest

from glances.processes import GlancesProcesses


@pytest.fixture
def processes():
    return GlancesProcesses()


def test_remove_non_running_procs_keeps_running_pids(processes):
    processes.processlist_cache = {1: {'cmdline': 'a'}, 2: {'cmdline': 'b'}, 3: {'cmdline': 'c'}}
    processes.remove_non_running_procs([{'pid': 1}, {'pid': 3}])
    assert set(processes.processlist_cache) == {1, 3}


def test_remove_non_running_procs_evicts_everything_when_no_proc_runs(processes):
    processes.processlist_cache = {1: {'cmdline': 'a'}, 2: {'cmdline': 'b'}}
    processes.remove_non_running_procs([])
    assert processes.processlist_cache == {}


def test_remove_non_running_procs_is_noop_when_all_running(processes):
    cache = {1: {'cmdline': 'a'}, 2: {'cmdline': 'b'}}
    processes.processlist_cache = dict(cache)
    processes.remove_non_running_procs([{'pid': 1}, {'pid': 2}])
    assert processes.processlist_cache == cache


def test_remove_non_running_procs_ignores_running_pids_absent_from_cache(processes):
    processes.processlist_cache = {1: {'cmdline': 'a'}}
    processes.remove_non_running_procs([{'pid': 1}, {'pid': 42}])
    assert set(processes.processlist_cache) == {1}


def test_remove_non_running_procs_evicts_io_old_of_gone_pids(processes):
    processes.io_old = {1: [10, 20], 2: [30, 40], 3: [50, 60]}
    processes.remove_non_running_procs([{'pid': 1}, {'pid': 3}])
    assert processes.io_old == {1: [10, 20], 3: [50, 60]}


def test_io_old_stays_bounded_across_cycles_of_short_lived_pids(processes):
    # One new pid per cycle, each gone at the next one: io_old must only ever
    # hold the pids of the current cycle, not every pid seen since startup.
    for pid in range(100, 200):
        proc = {'pid': pid, 'io_counters': [0, 0, pid, pid]}
        processes.get_io_counters(proc)
        processes.remove_non_running_procs([proc])
    assert set(processes.io_old) == {199}


def _raise_system_error_for(monkeypatch, pid):
    # psutil 7.2.2 on macOS raises SystemError instead of NoSuchProcess when a
    # process is reaped while its cmdline is read (see psutil issue #3024)
    real_as_dict = psutil.Process.as_dict

    def as_dict(self, *args, **kwargs):
        if self.pid == pid:
            raise SystemError('<built-in function proc_cmdline> returned a result with an exception set')
        return real_as_dict(self, *args, **kwargs)

    monkeypatch.setattr(psutil.Process, 'as_dict', as_dict)


def test_maybe_add_cached_stats_skips_a_process_raising_system_error(processes, monkeypatch):
    pid = os.getpid()
    _raise_system_error_for(monkeypatch, pid)
    proc = processes.maybe_add_cached_stats(True, processes.get_cached_attrs(), {'pid': pid})
    assert proc == {'pid': pid}
    assert pid not in processes.processlist_cache


def test_build_process_list_skips_only_the_process_raising_system_error(processes, monkeypatch):
    failing_pid = os.getppid()
    _raise_system_error_for(monkeypatch, failing_pid)
    attrs = processes.get_sorted_attrs() + ['pid'] + processes.get_cached_attrs()
    pids = {p['pid'] for p in processes.build_process_list(attrs)}
    assert os.getpid() in pids
    assert failing_pid not in pids


def _cpu_time(fn):
    # perf_counter: process_time() only ticks every ~15.6 ms on Windows, which is
    # as coarse as the quantity being measured here
    start = time.perf_counter()
    fn()
    return time.perf_counter() - start


def test_process_iter_uses_no_more_cpu_than_psutil_process_iter(processes):
    attrs = list(dict.fromkeys(processes.get_sorted_attrs() + ['pid'] + processes.get_cached_attrs()))

    def native():
        return list(psutil.process_iter(attrs=attrs, ad_value=None))

    def helper():
        return list(GlancesProcesses.process_iter(attrs))

    # Interleave the samples so both iterators see the same system load, and keep
    # the best sample of each to filter out the scheduler noise
    native_times, helper_times = [], []
    for _ in range(7):
        native_times.append(_cpu_time(native))
        helper_times.append(_cpu_time(helper))
    native_time, helper_time = min(native_times), min(helper_times)
    # The helper runs the same loop as psutil, so the CPU time should be on par.
    # The margin and the 10 ms slack keep the test stable on loaded CI runners
    # while still catching a regression.
    assert helper_time <= native_time * 1.5 + 0.01, (helper_time, native_time)

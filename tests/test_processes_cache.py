"""Tests for the GlancesProcesses internal cache eviction."""

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

"""Tests for reusing the program aggregation between refreshes."""

import pytest

from glances.processes import GlancesProcesses


def make_process(pid, name):
    return {
        'pid': pid,
        'name': name,
        'cmdline': [name],
        'username': 'someone',
        'nice': 0,
        'status': 'S',
        'num_threads': 1,
        'cpu_percent': 1.0,
        'memory_percent': 1.0,
        'cpu_times': {'user': 1.0, 'system': 1.0, 'children_user': 0.0, 'children_system': 0.0, 'iowait': 0.0},
        'memory_info': {'rss': 1024, 'vms': 2048, 'shared': 0, 'text': 0, 'data': 0},
        'io_counters': [0, 0, 0, 0, 0],
        'time_since_update': 1.0,
    }


@pytest.fixture
def processes():
    p = GlancesProcesses()
    p.processlist = [make_process(1, 'worker'), make_process(2, 'worker'), make_process(3, 'other')]
    p.processlist[2]['cpu_percent'] = 99.0  # 'other' sorts ahead of 'worker' by CPU
    return p


def test_aggregation_is_reused_while_the_list_is_unchanged(processes):
    first = processes.get_list(as_programs=True)
    assert processes.get_list(as_programs=True) is first


def test_aggregation_is_rebuilt_when_the_list_is_replaced(processes):
    first = processes.get_list(as_programs=True)
    processes.processlist = [make_process(1, 'worker'), make_process(4, 'newcomer')]
    second = processes.get_list(as_programs=True)
    assert second is not first
    assert {p['name'] for p in second} == {'worker', 'newcomer'}


def test_aggregation_follows_a_re_sort(processes):
    """Sorting replaces the process list, so the programs must be aggregated again in the
    new order rather than served from the previous call."""
    assert [p['name'] for p in processes.get_list(as_programs=True)] == ['worker', 'other']

    processes.set_sort_key('cpu_percent', auto=False)
    resorted = processes.get_list(sorted=True, as_programs=True)

    assert [p['name'] for p in resorted] == ['other', 'worker']


def test_aggregation_content(processes):
    programs = {p['name']: p for p in processes.get_list(as_programs=True)}
    assert programs['worker']['nprocs'] == 2
    assert programs['other']['nprocs'] == 1


def test_aggregation_follows_an_in_place_sort(processes):
    """sort_stats() reorders the list in place when the primary sort raises, leaving the
    object identical; the cache has to notice anyway."""
    # Mixed types in the sort field make the primary sort raise, which is what reaches the
    # in-place branch. nice is compared but never summed, so the aggregation still works.
    processes.processlist[0]['nice'] = 'x'
    assert [p['name'] for p in processes.get_list(as_programs=True)] == ['worker', 'other']

    processes.set_sort_key('nice', auto=False)
    before = processes.processlist
    resorted = processes.get_list(sorted=True, as_programs=True)

    assert processes.processlist is before, 'this test is pointless unless the sort was in place'
    assert [p['name'] for p in resorted] == ['other', 'worker']

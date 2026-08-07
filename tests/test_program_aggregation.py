"""Tests for reusing the program aggregation between refreshes."""

import pytest

from glances.processes import GlancesProcesses, sort_stats


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


def test_aggregation_is_rebuilt_after_a_sort(processes):
    first = processes.get_list(as_programs=True)
    assert processes.get_list(sorted=True, as_programs=True) is not first


def test_aggregation_content(processes):
    programs = {p['name']: p for p in processes.get_list(as_programs=True)}
    assert programs['worker']['nprocs'] == 2
    assert programs['other']['nprocs'] == 1


def test_sort_stats_does_not_mutate_the_input():
    """Every branch must return a new list, or callers cannot tell the result from the input.

    Mixing types in the sort field makes the primary sort raise TypeError, which is what
    reaches the fallback branch; that branch used to sort the caller's list in place.
    """
    stats = [make_process(1, 'b'), make_process(2, 'a')]
    stats[0]['cpu_percent'] = 'not-a-number'

    result = sort_stats(stats, sorted_by='cpu_percent')

    assert result is not stats
    assert [p['pid'] for p in stats] == [1, 2], "the caller's list was reordered"
    assert [p['pid'] for p in result] == [2, 1], 'the fallback sorts by name'

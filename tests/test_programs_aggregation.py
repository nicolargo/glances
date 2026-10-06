"""Tests for aggregating processes into programs."""

import pytest

from glances.programs import processes_to_programs, sum_field_dict

CPU_TIMES_FIELDS = ('user', 'system', 'children_user', 'children_system', 'iowait')


def make_process(pid, name, user, system, iowait):
    return {
        'pid': pid,
        'time_since_update': 1.0,
        'name': name,
        'cmdline': [name],
        'username': 'someone',
        'nice': 0,
        'status': 'S',
        'num_threads': 1,
        'cpu_percent': 1.0,
        'memory_percent': 1.0,
        'cpu_times': {
            'user': user,
            'system': system,
            'children_user': 0.0,
            'children_system': 0.0,
            'iowait': iowait,
        },
        'memory_info': {'rss': 1024, 'vms': 2048, 'shared': 0, 'text': 0, 'data': 0},
        'io_counters': [0, 0, 0, 0, 0],
    }


def test_zero_totals_keep_their_field():
    """A field summing to zero must survive, or programs end up with a different schema."""
    merged = sum_field_dict({'user': 1.0, 'iowait': 0.0}, {'user': 2.0, 'iowait': 0.0})
    assert merged == {'user': 3.0, 'iowait': 0.0}


def test_missing_field_is_added():
    assert sum_field_dict({'user': 1.0}, {'system': 2.0}) == {'user': 1.0, 'system': 2.0}


def test_none_operands_are_tolerated():
    assert sum_field_dict(None, {'user': 1.0}) == {'user': 1.0}
    assert sum_field_dict({'user': 1.0}, None) == {'user': 1.0}


def test_aggregated_program_keeps_every_cpu_times_field():
    processes = [
        make_process(1, 'worker', user=1.5, system=0.5, iowait=0.0),
        make_process(2, 'worker', user=2.5, system=0.5, iowait=0.0),
    ]
    program = processes_to_programs(processes)[0]
    assert set(program['cpu_times']) == set(CPU_TIMES_FIELDS)
    assert program['cpu_times']['iowait'] == 0.0
    assert program['cpu_times']['user'] == 4.0
    assert program['nprocs'] == 2


def test_aggregated_program_keeps_every_memory_info_field():
    processes = [
        make_process(1, 'worker', user=1.0, system=1.0, iowait=1.0),
        make_process(2, 'worker', user=1.0, system=1.0, iowait=1.0),
    ]
    program = processes_to_programs(processes)[0]
    assert set(program['memory_info']) == {'rss', 'vms', 'shared', 'text', 'data'}
    assert program['memory_info']['shared'] == 0
    assert program['memory_info']['rss'] == 2048


@pytest.mark.parametrize(
    'disabled',
    ['cpu_percent', 'memory_percent', 'memory_info', 'cpu_times', 'num_threads', 'nice', 'status', 'io_counters'],
)
def test_disabled_process_stat_is_tolerated(disabled):
    # Stats listed in the [processlist] disable_stats option are absent from the process dicts
    processes = [
        {
            'pid': pid,
            'name': 'worker',
            'time_since_update': 1.0,
            'num_threads': 2,
            'cpu_percent': 10.0,
            'memory_percent': 1.5,
            'cpu_times': {'user': 1.0},
            'memory_info': {'rss': 100},
            'io_counters': [1, 2, 0, 0, 1],
            'username': 'u',
            'nice': 0,
            'status': 'R',
        }
        for pid in (1, 2)
    ]
    for p in processes:
        del p[disabled]

    (program,) = processes_to_programs(processes)

    assert program['nprocs'] == 2
    assert program['childrens'] == [1, 2]

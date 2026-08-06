"""Tests for aggregating processes into programs."""

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

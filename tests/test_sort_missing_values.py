"""Sorting must not be discarded because one row has nothing to sort on.

`sort_stats` wraps the specific sort helpers in a try/except and falls back to
`cpu_percent` for the whole list. So a single row whose `cpu_times` is `{}` or whose
`io_counters` is empty does not fail loudly — it silently reorders every other row while
the header still reads TIME or IOR/IOW.

Those empty values are expected, not corrupt: `glances/programs.py` builds a program with
`p['cpu_times'] or {}` and `list(p['io_counters'] or NO_IO_COUNTERS)`, and its own comment
says "some values can be None, e.g. macOS system processes".
"""

from glances.processes import _sort_cpu_times, _sort_io_counters, sort_stats


def _row(name, cpu_times, io_counters, cpu_percent):
    return {
        'name': name,
        'cpu_times': cpu_times,
        'io_counters': io_counters,
        'cpu_percent': cpu_percent,
        'memory_percent': 1.0,
    }


def test_sort_cpu_times_reads_a_missing_value_as_zero():
    assert _sort_cpu_times({'cpu_times': {}}) == 0
    assert _sort_cpu_times({'cpu_times': None}) == 0
    assert _sort_cpu_times({}) == 0
    assert _sort_cpu_times({'cpu_times': {'user': 5.0, 'system': 1.0}}) == 6.0


def test_sort_io_counters_reads_a_missing_value_as_zero():
    assert _sort_io_counters({'io_counters': []}) == 0
    assert _sort_io_counters({'io_counters': None}) == 0
    assert _sort_io_counters({}) == 0
    # A tuple is what programs.NO_IO_COUNTERS is, and a short list must not raise either.
    assert _sort_io_counters({'io_counters': (900, 90, 100, 10, 1)}) == 880
    assert _sort_io_counters({'io_counters': [900, 90]}) == 990


def test_one_row_without_cpu_times_does_not_reorder_the_others():
    # 'idle' has no cpu_times and the highest cpu_percent, so a fallback to cpu_percent
    # puts it first — which is exactly what used to happen.
    rows = [
        _row('editor', {'user': 5.0, 'system': 1.0}, [0, 0, 0, 0, 0], 1.0),
        _row('idle', {}, [0, 0, 0, 0, 0], 99.0),
        _row('compiler', {'user': 50.0, 'system': 9.0}, [0, 0, 0, 0, 0], 2.0),
    ]

    ordered = sort_stats(rows, sorted_by='cpu_times', sorted_by_secondary='memory_percent')

    assert [row['name'] for row in ordered] == ['compiler', 'editor', 'idle']


def test_one_row_without_io_counters_does_not_reorder_the_others():
    rows = [
        _row('editor', {'user': 0.0, 'system': 0.0}, [900, 90, 100, 10, 1], 1.0),
        _row('idle', {'user': 0.0, 'system': 0.0}, [], 99.0),
        _row('compiler', {'user': 0.0, 'system': 0.0}, [9000, 900, 1000, 100, 1], 2.0),
    ]

    ordered = sort_stats(rows, sorted_by='io_counters', sorted_by_secondary='memory_percent')

    assert [row['name'] for row in ordered] == ['compiler', 'editor', 'idle']

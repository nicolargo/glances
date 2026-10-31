"""`update()` must sort the process list on post-conversion values.

`build_process_list` returns raw `as_dict()` rows: `cpu_times` is a
``pcputimes`` namedtuple and `io_counters` a ``pio`` one — psutil's
``pio(read_count, write_count, read_bytes, write_bytes, ...)`` puts the
*counts* at indexes 0/1, which is why `get_io_counters` reads bytes at
indexes 2/3. The engine used to sort that raw list before the per-process
loop ran `get_io_counters` / `namedtuple_to_dict`, so
`--sort-processes io_counters` subtracted the byte totals as if they were
the previous cycle's values, and `cpu_times` sorting raised inside
`sorted()` and silently fell back to `cpu_percent` order (issue #3830).
The REST API and WebUI serve this engine order directly (`get_list()`);
only the TUI re-sorted later.
"""

from collections import namedtuple

import pytest

from glances.processes import GlancesProcesses

# Raw psutil shapes, as `p.as_dict()` produces them.
pcputimes = namedtuple('pcputimes', ['user', 'system', 'children_user', 'children_system'])
pio = namedtuple('pio', ['read_count', 'write_count', 'read_bytes', 'write_bytes'])


def _raw_proc(pid, name, cpu_percent, cpu_times, io_counters, memory_percent=1.0):
    """A process row in the shape `build_process_list` emits it (pre-conversion)."""
    return {
        'pid': pid,
        'name': name,
        'cmdline': [name],
        'cpu_percent': cpu_percent,
        'memory_percent': memory_percent,
        'memory_info': {'rss': 0, 'vms': 0},
        'status': 'sleeping',
        'num_threads': 1,
        'nice': 0,
        'username': 'root',
        'cpu_times': cpu_times,
        'io_counters': io_counters,
        'gids': {'real': 0},
    }


@pytest.fixture
def engine():
    return GlancesProcesses()


def test_sort_by_cpu_times_orders_on_user_plus_system(engine, monkeypatch):
    # The busiest-by-time process has the LOWEST cpu_percent: a fallback to
    # cpu_percent order (what the pre-fix sort silently did) inverts the list.
    rows = [
        _raw_proc(1, 'highest-cpu', 99.0, pcputimes(1.0, 0.0, 0.0, 0.0), None),
        _raw_proc(2, 'long-runner', 1.0, pcputimes(500.0, 40.0, 0.0, 0.0), None),
        _raw_proc(3, 'mid', 5.0, pcputimes(100.0, 10.0, 0.0, 0.0), None),
    ]
    monkeypatch.setattr(engine, 'build_process_list', lambda attrs: rows)
    engine.set_sort_key('cpu_times', auto=False)

    engine.update()

    assert [p['name'] for p in engine.processlist] == ['long-runner', 'mid', 'highest-cpu']


def test_sort_by_io_counters_orders_on_bytes_since_last_cycle(engine, monkeypatch):
    # The writer performs many small writes: its write *count* dwarfs nothing,
    # but its byte totals are huge — sorting the raw namedtuple subtracts the
    # bytes as if they were last cycle's, sending it to the bottom (the
    # reported symptom).
    rows = [
        _raw_proc(1, 'idle-reader', 0.0, pcputimes(0.0, 0.0, 0.0, 0.0), pio(50, 40, 50, 500)),
        _raw_proc(2, 'heavy-writer', 0.0, pcputimes(0.0, 0.0, 0.0, 0.0), pio(1, 90000, 100, 10_000_000)),
        _raw_proc(3, 'no-io', 0.0, pcputimes(0.0, 0.0, 0.0, 0.0), None),
    ]
    monkeypatch.setattr(engine, 'build_process_list', lambda attrs: rows)
    engine.set_sort_key('io_counters', auto=False)

    engine.update()

    assert [p['name'] for p in engine.processlist] == ['heavy-writer', 'idle-reader', 'no-io']


def test_sort_by_io_counters_uses_the_rate_not_lifetime_bytes(engine, monkeypatch):
    # Second cycle: 'writer' added few new bytes while 'bursty' added many.
    # Only post-conversion rows (with the previous cycle's bytes merged in)
    # can order by rate.
    cycle = iter(
        [
            [
                _raw_proc(1, 'writer', 0.0, pcputimes(0.0, 0.0, 0.0, 0.0), pio(1, 10, 0, 10_000_000)),
                _raw_proc(2, 'bursty', 0.0, pcputimes(0.0, 0.0, 0.0, 0.0), pio(1, 10, 0, 1_000)),
            ],
            [
                _raw_proc(1, 'writer', 0.0, pcputimes(0.0, 0.0, 0.0, 0.0), pio(1, 10, 0, 10_100_000)),
                _raw_proc(2, 'bursty', 0.0, pcputimes(0.0, 0.0, 0.0, 0.0), pio(1, 10, 0, 5_000_000)),
            ],
        ]
    )
    monkeypatch.setattr(engine, 'build_process_list', lambda attrs: next(cycle))
    engine.set_sort_key('io_counters', auto=False)

    engine.update()
    assert [p['name'] for p in engine.processlist] == ['writer', 'bursty']

    engine.update()
    assert [p['name'] for p in engine.processlist] == ['bursty', 'writer']


def test_engine_order_matches_a_post_conversion_resort(engine, monkeypatch):
    """The API serves `get_list()` unsorted: the engine order must already be
    what `get_list(sorted=True)` — the post-conversion re-sort — produces."""
    rows = [
        _raw_proc(1, 'a', 50.0, pcputimes(1.0, 1.0, 0.0, 0.0), pio(5, 5, 10, 10)),
        # Biggest lifetime writer: raw-order (count - bytes) demotes 'b' last.
        _raw_proc(2, 'b', 1.0, pcputimes(300.0, 0.0, 0.0, 0.0), pio(5, 9000, 10, 10_000_000)),
        _raw_proc(3, 'c', 10.0, pcputimes(20.0, 5.0, 0.0, 0.0), pio(5, 50, 10, 40)),
    ]
    monkeypatch.setattr(engine, 'build_process_list', lambda attrs: rows)
    engine.set_sort_key('io_counters', auto=False)

    engine.update()
    api_order = [p['name'] for p in engine.get_list()]
    resorted = [p['name'] for p in engine.get_list(sorted=True)]

    assert api_order == resorted == ['b', 'c', 'a']

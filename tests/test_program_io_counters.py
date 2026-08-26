"""Tests for aggregating a program's disk I/O counters."""

from glances.programs import processes_to_programs

# io_counters is a fixed 5-slot list, not a mapping:
# [read_bytes, write_bytes, read_bytes_old, write_bytes_old, io_tag].
READ, WRITE, READ_OLD, WRITE_OLD, IO_TAG = range(5)


def make_process(pid, name, io_counters):
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
        'cpu_times': {'user': 1.0, 'system': 1.0, 'children_user': 0.0, 'children_system': 0.0, 'iowait': 0.0},
        'memory_info': {'rss': 1024, 'vms': 2048, 'shared': 0, 'text': 0, 'data': 0},
        'io_counters': io_counters,
    }


def one_program(processes):
    programs = processes_to_programs(processes)
    assert len(programs) == 1
    return programs[0]


def test_io_counters_keep_their_five_slots():
    """The list is read by index, so merging must not change its length."""
    program = one_program(
        [
            make_process(1, 'worker', [100, 200, 10, 20, 1]),
            make_process(2, 'worker', [1000, 2000, 100, 200, 1]),
            make_process(3, 'worker', [7, 8, 1, 2, 1]),
        ]
    )
    assert len(program['io_counters']) == 5


def test_io_counters_are_summed_slot_by_slot():
    """A program's I/O is the sum of its processes', like cpu_times and memory_info."""
    program = one_program(
        [
            make_process(1, 'worker', [100, 200, 10, 20, 1]),
            make_process(2, 'worker', [1000, 2000, 100, 200, 1]),
        ]
    )
    assert program['io_counters'][READ] == 1100
    assert program['io_counters'][WRITE] == 2200
    assert program['io_counters'][READ_OLD] == 110
    assert program['io_counters'][WRITE_OLD] == 220


def test_io_tag_is_a_flag_not_a_total():
    """processlist only displays a rate when io_tag == 1 exactly, so summing the flag
    would blank the R/s and W/s columns for every program with two processes."""
    program = one_program(
        [
            make_process(1, 'worker', [100, 200, 10, 20, 1]),
            make_process(2, 'worker', [1000, 2000, 100, 200, 1]),
        ]
    )
    assert program['io_counters'][IO_TAG] == 1


def test_io_tag_is_set_when_any_process_reports_io():
    """One readable process is enough for the program to have a rate worth showing."""
    program = one_program(
        [
            make_process(1, 'worker', [0, 0, 0, 0, 0]),
            make_process(2, 'worker', [1000, 2000, 100, 200, 1]),
        ]
    )
    assert program['io_counters'][IO_TAG] == 1


def test_io_tag_stays_zero_when_no_process_reports_io():
    program = one_program(
        [
            make_process(1, 'worker', [0, 0, 0, 0, 0]),
            make_process(2, 'worker', [0, 0, 0, 0, 0]),
        ]
    )
    assert program['io_counters'][IO_TAG] == 0


def test_a_process_without_io_counters_is_skipped_not_fatal():
    """psutil hands back None for processes it cannot read - macOS system processes,
    and anything the user lacks permission for."""
    program = one_program(
        [
            make_process(1, 'worker', [100, 200, 10, 20, 1]),
            make_process(2, 'worker', None),
        ]
    )
    assert program['io_counters'] == [100, 200, 10, 20, 1]


def test_a_first_process_without_io_counters_still_yields_a_list():
    """The None lands on the entry that seeds the program, so the fallback has to be a
    list of five slots - a dict would raise on the very next merge and index as a key."""
    program = one_program(
        [
            make_process(1, 'worker', None),
            make_process(2, 'worker', [100, 200, 10, 20, 1]),
        ]
    )
    assert program['io_counters'] == [100, 200, 10, 20, 1]


def test_the_program_does_not_borrow_the_process_list():
    """`+=` on a list extends it in place. The program seeded itself with the first
    process's own io_counters, so aggregating wrote back into the process list."""
    processes = [
        make_process(1, 'worker', [100, 200, 10, 20, 1]),
        make_process(2, 'worker', [1000, 2000, 100, 200, 1]),
    ]
    one_program(processes)
    assert processes[0]['io_counters'] == [100, 200, 10, 20, 1]


def test_repeated_aggregation_does_not_grow_the_counters():
    """A re-sort aggregates the same process dicts again; in-place growth made the list
    five slots longer per process on every pass, without bound."""
    processes = [
        make_process(1, 'worker', [100, 200, 10, 20, 1]),
        make_process(2, 'worker', [1000, 2000, 100, 200, 1]),
    ]
    # A copy: on the unfixed code the program aliases the process's list, so comparing
    # against the live object would compare it with itself and pass while it grew.
    first = list(one_program(processes)['io_counters'])
    for _ in range(5):
        assert one_program(processes)['io_counters'] == first

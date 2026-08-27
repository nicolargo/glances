"""Tests for aggregating a program's disk I/O counters."""

from glances.programs import processes_to_programs

# io_counters is a fixed 5-slot list, not a mapping:
# [read_bytes, write_bytes, read_bytes_old, write_bytes_old, io_tag].
READ, WRITE, READ_OLD, WRITE_OLD, IO_TAG = range(5)

# The io_tag values, named so an assertion on them reads as a flag rather than a total.
IO_ABSENT, IO_PRESENT = 0, 1


def make_process(pid, name, io_counters):
    """Build the subset of a process entry that the aggregation reads."""
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
        'cpu_times': {'user': 1.0, 'system': 1.0, 'iowait': 0.0},
        'memory_info': {'rss': 1024, 'vms': 2048},
        'io_counters': io_counters,
    }


def one_program(processes):
    """Aggregate processes that all share a name and return the single program."""
    programs = processes_to_programs(processes)
    assert len(programs) == 1
    return programs[0]


def two_readers():
    """Build two processes of one program, both reporting IO."""
    return [
        make_process(1, 'worker', [100, 200, 10, 20, IO_PRESENT]),
        make_process(2, 'worker', [1000, 2000, 100, 200, IO_PRESENT]),
    ]


def test_io_counters_keep_their_five_slots():
    """The list is read by index, so merging must not change its length."""
    processes = two_readers() + [make_process(3, 'worker', [7, 8, 1, 2, IO_PRESENT])]
    assert len(one_program(processes)['io_counters']) == 5


def test_io_counters_are_summed_slot_by_slot():
    """A program's IO is the sum of its processes', like cpu_times and memory_info."""
    program = one_program(two_readers())
    assert program['io_counters'][READ] == 1100
    assert program['io_counters'][WRITE] == 2200
    assert program['io_counters'][READ_OLD] == 110
    assert program['io_counters'][WRITE_OLD] == 220


def test_io_tag_is_a_flag_not_a_total():
    """The tag stays 1 rather than becoming 2."""
    # processlist displays a rate only when io_tag == 1 exactly, so summing the flag would
    # blank the R/s and W/s columns for every program with two processes.
    assert one_program(two_readers())['io_counters'][IO_TAG] == IO_PRESENT


def test_io_tag_is_set_when_any_process_reports_io():
    """One readable process is enough for the program to have a rate worth showing."""
    processes = [
        make_process(1, 'worker', [0, 0, 0, 0, IO_ABSENT]),
        make_process(2, 'worker', [1000, 2000, 100, 200, IO_PRESENT]),
    ]
    assert one_program(processes)['io_counters'][IO_TAG] == IO_PRESENT


def test_io_tag_stays_unset_when_no_process_reports_io():
    """A program of unreadable processes keeps the tag clear."""
    processes = [
        make_process(1, 'worker', [0, 0, 0, 0, IO_ABSENT]),
        make_process(2, 'worker', [0, 0, 0, 0, IO_ABSENT]),
    ]
    assert one_program(processes)['io_counters'][IO_TAG] == IO_ABSENT


def test_a_process_without_io_counters_is_skipped_not_fatal():
    """A process the aggregation cannot read contributes nothing and raises nothing."""
    # psutil hands back None for processes it cannot read - macOS system processes, and
    # anything the user lacks permission for.
    processes = [
        make_process(1, 'worker', [100, 200, 10, 20, IO_PRESENT]),
        make_process(2, 'worker', None),
    ]
    assert one_program(processes)['io_counters'] == [100, 200, 10, 20, IO_PRESENT]


def test_a_first_process_without_io_counters_still_yields_a_list():
    """A None on the entry that seeds the program still leaves five slots behind."""
    # A dict would raise on the very next merge, and index as a key afterwards.
    processes = [
        make_process(1, 'worker', None),
        make_process(2, 'worker', [100, 200, 10, 20, IO_PRESENT]),
    ]
    assert one_program(processes)['io_counters'] == [100, 200, 10, 20, IO_PRESENT]


def test_the_program_does_not_borrow_the_process_list():
    """Aggregating must leave the process entries it read untouched."""
    # `+=` on a list extends it in place, and the program seeded itself with the first
    # process's own io_counters, so aggregating wrote back into the process list.
    processes = two_readers()
    one_program(processes)
    assert processes[0]['io_counters'] == [100, 200, 10, 20, IO_PRESENT]


def test_repeated_aggregation_does_not_grow_the_counters():
    """Aggregating the same processes again gives the same answer again."""
    # A re-sort aggregates the same process dicts a second time; in-place growth made the
    # list five slots longer per process on every pass, without bound. The expected value
    # is copied because on the unfixed code the program aliases the process's list, so
    # comparing it against the live object would compare it with itself and pass as it grew.
    processes = two_readers()
    first = list(one_program(processes)['io_counters'])
    for _ in range(5):
        assert one_program(processes)['io_counters'] == first

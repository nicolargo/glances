#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

# from glances.logger import logger

# This constant defines the list of available processes sort key
sort_programs_key_list = ['cpu_percent', 'memory_percent', 'cpu_times', 'io_counters', 'name']


def create_program_dict(p):
    """Create a new entry in the dict (new program)"""
    return {
        'time_since_update': p['time_since_update'],
        # some values can be None, e.g. macOS system processes
        'num_threads': p['num_threads'] or 0,
        'cpu_percent': p['cpu_percent'] or 0,
        'memory_percent': p['memory_percent'] or 0,
        'cpu_times': p['cpu_times'] or {},
        'memory_info': p['memory_info'] or {},
        # A copy: the program must not borrow - and then grow - the process's own list.
        'io_counters': list(p['io_counters'] or NO_IO_COUNTERS),
        'childrens': [p['pid']],
        # Others keys are not used
        # but should be set to be compliant with the existing process_list
        'name': p['name'],
        'cmdline': [p['name']],
        'pid': '_',
        'username': p.get('username', '_'),
        'nice': p['nice'],
        'status': p['status'],
    }


# io_counters is a fixed list, not a mapping:
# [read_bytes, write_bytes, read_bytes_old, write_bytes_old, io_tag]
IO_COUNTERS_TAG = 4
NO_IO_COUNTERS = (0, 0, 0, 0, 0)


def sum_io_counters(total, addition):
    """Add addition into total slot by slot.

    `+=` concatenates these lists rather than adding them, so a program reported only its
    first process's disk IO - and, because the program borrowed that process's own list,
    every aggregation extended it in place. The last slot is a flag rather than a total:
    processlist displays a rate only when it is exactly 1, so it is OR-ed, not added.
    """
    total = total or NO_IO_COUNTERS
    addition = addition or NO_IO_COUNTERS
    summed = [a + b for a, b in zip(total[:IO_COUNTERS_TAG], addition[:IO_COUNTERS_TAG])]
    return summed + [max(total[IO_COUNTERS_TAG], addition[IO_COUNTERS_TAG])]


def sum_field_dict(total, addition):
    """Add addition into total field by field.

    Counter() is not usable here: adding two Counters drops every key whose sum is not
    positive, so a program whose iowait or children_user happens to total 0.0 would lose
    that key and end up with a different set of fields than the processes it aggregates.
    """
    merged = dict(total or {})
    for field, value in (addition or {}).items():
        merged[field] = merged.get(field, 0) + value
    return merged


def update_program_dict(program, p):
    """Update an existing entry in the dict (existing program)"""
    # some values can be None, e.g. macOS system processes
    program['num_threads'] += p['num_threads'] or 0
    program['cpu_percent'] += p['cpu_percent'] or 0
    program['memory_percent'] += p['memory_percent'] or 0
    program['cpu_times'] = sum_field_dict(program['cpu_times'], p['cpu_times'])
    program['memory_info'] = sum_field_dict(program['memory_info'], p['memory_info'])

    program['io_counters'] = sum_io_counters(program['io_counters'], p['io_counters'])
    program['childrens'].append(p['pid'])
    # If all the subprocess has the same value, display it
    program['username'] = p.get('username', '_') if p.get('username') == program['username'] else '_'
    program['nice'] = p['nice'] if p['nice'] == program['nice'] else '_'
    program['status'] = p['status'] if p['status'] == program['status'] else '_'


def compute_nprocs(p):
    p['nprocs'] = len(p['childrens'])
    return p


def processes_to_programs(processes):
    """Convert a list of processes to a list of programs."""
    # Start to build a dict of programs (key is program name)
    programs_dict = {}
    key = 'name'
    for p in processes:
        if p[key] not in programs_dict:
            programs_dict[p[key]] = create_program_dict(p)
        else:
            update_program_dict(programs_dict[p[key]], p)

    # Convert the dict to a list of programs
    return [compute_nprocs(p) for p in programs_dict.values()]

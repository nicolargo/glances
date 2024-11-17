#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

from collections import Counter

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
        'io_counters': p['io_counters'] or {},
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


def update_program_dict(program, p):
    """Update an existing entry in the dict (existing program)"""
    # some values can be None, e.g. macOS system processes
    program['num_threads'] += p['num_threads'] or 0
    program['cpu_percent'] += p['cpu_percent'] or 0
    program['memory_percent'] += p['memory_percent'] or 0
    program['cpu_times'] = dict(Counter(program['cpu_times'] or {}) + Counter(p['cpu_times'] or {}))
    program['memory_info'] = dict(Counter(program['memory_info'] or {}) + Counter(p['memory_info'] or {}))

    program['io_counters'] += p['io_counters']
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

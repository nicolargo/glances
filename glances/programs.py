# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

# from glances.logger import logger

# This constant defines the list of available processes sort key
sort_programs_key_list = ['cpu_percent', 'memory_percent', 'cpu_times', 'io_counters', 'name']


def processes_to_programs(processes):
    """Convert a list of processes to a list of programs."""
    # Start to build a dict of programs (key is program name)
    programs_dict = {}
    key = 'name'
    for p in processes:
        if p[key] not in programs_dict:
            # Create a new entry in the dict (new program)
            programs_dict[p[key]] = {
                'time_since_update': p['time_since_update'],
                # some values can be None, e.g. macOS system processes
                'num_threads': p['num_threads'] or 0,
                'cpu_percent': p['cpu_percent'] or 0,
                'memory_percent': p['memory_percent'] or 0,
                'cpu_times': p['cpu_times'] or (),
                'memory_info': p['memory_info'] or (),
                'io_counters': p['io_counters'] or (),
                'childrens': [p['pid']],
                # Others keys are not used
                # but should be set to be compliant with the existing process_list
                'name': p['name'],
                'cmdline': [p['name']],
                'pid': '_',
                'username': p['username'] if 'username' in p else '_',
                'nice': p['nice'],
                'status': p['status'],
            }
        else:
            # Update a existing entry in the dict (existing program)
            # some values can be None, e.g. macOS system processes
            programs_dict[p[key]]['num_threads'] += p['num_threads'] or 0
            programs_dict[p[key]]['cpu_percent'] += p['cpu_percent'] or 0
            programs_dict[p[key]]['memory_percent'] += p['memory_percent'] or 0
            programs_dict[p[key]]['cpu_times'] += p['cpu_times'] or ()
            programs_dict[p[key]]['memory_info'] += p['memory_info'] or ()

            programs_dict[p[key]]['io_counters'] += p['io_counters']
            programs_dict[p[key]]['childrens'].append(p['pid'])
            # If all the subprocess has the same value, display it
            programs_dict[p[key]]['username'] = (
                p['username'] if ('username' in p) and (p['username'] == programs_dict[p[key]]['username']) else '_'
            )
            programs_dict[p[key]]['nice'] = p['nice'] if p['nice'] == programs_dict[p[key]]['nice'] else '_'
            programs_dict[p[key]]['status'] = p['status'] if p['status'] == programs_dict[p[key]]['status'] else '_'

    # Convert the dict to a list of programs
    return [programs_dict[p] for p in programs_dict]

# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2022 Nicolargo <nicolas@nicolargo.com>
#
# Glances is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Glances is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

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
                'num_threads': p['num_threads'],
                'cpu_percent': p['cpu_percent'],
                'memory_percent': p['memory_percent'],
                'cpu_times': p['cpu_times'],
                'memory_info': p['memory_info'],
                'io_counters': p['io_counters'],
                'childrens': [p['pid']],
                # Others keys are not used
                # but should be set to be compliant with the existing process_list
                'name': p['name'],
                'cmdline': [p['name']],
                'pid': '_',
                'username': p['username'],
                'nice': p['nice'],
                'status': p['status'],
            }
        else:
            # Update a existing entry in the dict (existing program)
            programs_dict[p[key]]['num_threads'] += p['num_threads']
            programs_dict[p[key]]['cpu_percent'] += p['cpu_percent']
            programs_dict[p[key]]['memory_percent'] += p['memory_percent']
            programs_dict[p[key]]['cpu_times'] += p['cpu_times']
            programs_dict[p[key]]['memory_info'] += p['memory_info']
            programs_dict[p[key]]['io_counters'] += p['io_counters']
            programs_dict[p[key]]['childrens'].append(p['pid'])
            # If all the subprocess has the same value, display it
            programs_dict[p[key]]['username'] = (
                p['username'] if p['username'] == programs_dict[p[key]]['username'] else '_'
            )
            programs_dict[p[key]]['nice'] = p['nice'] if p['nice'] == programs_dict[p[key]]['nice'] else '_'
            programs_dict[p[key]]['status'] = p['status'] if p['status'] == programs_dict[p[key]]['status'] else '_'

    # Convert the dict to a list of programs
    return [programs_dict[p] for p in programs_dict]

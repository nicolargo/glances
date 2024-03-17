# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Manage Glances events (previously Glances logs in Glances < 3.1)."""

import time
from datetime import datetime

from glances.logger import logger
from glances.processes import glances_processes, sort_stats
from glances.thresholds import glances_thresholds

# Static decision tree for the global alert message
# - msg: Message to be displayed (result of the decision tree)
# - thresholds: a list of stats to take into account
# - thresholds_min: minimal value of the thresholds sum
# -                 0: OK
# -                 1: CAREFUL
# -                 2: WARNING
# -                 3: CRITICAL
tree = [
    {'msg': 'No warning or critical alert detected', 'thresholds': [], 'thresholds_min': 0},
    {'msg': 'High CPU user mode', 'thresholds': ['cpu_user'], 'thresholds_min': 2},
    {'msg': 'High CPU kernel usage', 'thresholds': ['cpu_system'], 'thresholds_min': 2},
    {'msg': 'High CPU I/O waiting', 'thresholds': ['cpu_iowait'], 'thresholds_min': 2},
    {
        'msg': 'Large CPU stolen time. System running the hypervisor is too busy.',
        'thresholds': ['cpu_steal'],
        'thresholds_min': 2,
    },
    {'msg': 'High CPU niced value', 'thresholds': ['cpu_niced'], 'thresholds_min': 2},
    {'msg': 'System overloaded in the last 5 minutes', 'thresholds': ['load'], 'thresholds_min': 2},
    {'msg': 'High swap (paging) usage', 'thresholds': ['memswap'], 'thresholds_min': 2},
    {'msg': 'High memory consumption', 'thresholds': ['mem'], 'thresholds_min': 2},
]

# TODO: change the algo to use the following decision tree
# Source: Inspire by https://scoutapm.com/blog/slow_server_flow_chart
# _yes means threshold >= 2
# _no  means threshold < 2
# With threshold:
# - 0: OK
# - 1: CAREFUL
# - 2: WARNING
# - 3: CRITICAL
tree_new = {
    'cpu_iowait': {
        '_yes': {
            'memswap': {
                '_yes': {
                    'mem': {
                        '_yes': {
                            # Once you've identified the offenders, the resolution will again
                            # depend on whether their memory usage seems business-as-usual or not.
                            # For example, a memory leak can be satisfactorily addressed by a one-time
                            # or periodic restart of the process.
                            # - if memory usage seems anomalous: kill the offending processes.
                            # - if memory usage seems business-as-usual: add RAM to the server,
                            # or split high-memory using services to other servers.
                            '_msg': "Memory issue"
                        },
                        '_no': {
                            # ???
                            '_msg': "Swap issue"
                        },
                    }
                },
                '_no': {
                    # Low swap means you have a "real" IO wait problem. The next step is to see what's hogging your IO.
                    # iotop is an awesome tool for identifying io offenders. Two things to note:
                    # unless you've already installed iotop, it's probably not already on your system.
                    # Recommendation: install it before you need it - - it's no fun trying to install a troubleshooting
                    # tool on an overloaded machine (iotop requires a Linux of 2.62 or above)
                    '_msg': "I/O issue"
                },
            }
        },
        '_no': {
            'cpu_total': {
                '_yes': {
                    'cpu_user': {
                        '_yes': {
                            # We expect the user-time percentage to be high.
                            # There's most likely a program or service you've configured on you server that's
                            # hogging CPU.
                            # Checking the % user time just confirms this. When you see that the % user-time is high,
                            # it's time to see what executable is monopolizing the CPU
                            # Once you've confirmed that the % usertime is high, check the process list(also provided
                            # by top).
                            # Be default, top sorts the process list by % CPU, so you can just look at the top process
                            # or processes.
                            # If there's a single process hogging the CPU in a way that seems abnormal, it's an
                            # anomalous situation
                            # that a service restart can fix. If there are are multiple processes taking up CPU
                            # resources, or it
                            # there's one process that takes lots of resources while otherwise functioning normally,
                            # than your setup
                            # may just be underpowered. You'll need to upgrade your server(add more cores),
                            # or split services out onto
                            # other boxes. In either case, you have a resolution:
                            # - if situation seems anomalous: kill the offending processes.
                            # - if situation seems typical given history: upgrade server or add more servers.
                            '_msg': "CPU issue with user process(es)"
                        },
                        '_no': {
                            'cpu_steal': {
                                '_yes': {
                                    '_msg': "CPU issue with stolen time. System running the hypervisor may be too busy."
                                },
                                '_no': {'_msg': "CPU issue with system process(es)"},
                            }
                        },
                    }
                },
                '_no': {
                    '_yes': {
                        # ???
                        '_msg': "Memory issue"
                    },
                    '_no': {
                        # Your slowness isn't due to CPU or IO problems, so it's likely an application-specific issue.
                        # It's also possible that the slowness is being caused by another server in your cluster, or
                        # by an external service you rely on.
                        # start by checking important applications for uncharacteristic slowness(the DB is a good place
                        # to start), think through which parts of your infrastructure could be slowed down externally.
                        # For example, do you use an externally hosted email service that could slow down critical
                        # parts of your application ?
                        # If you suspect another server in your cluster, strace and lsof can provide information on
                        # what the process is doing or waiting on. Strace will show you which file descriptors are
                        # being read or written to (or being attempted to be read from) and lsof can give you a
                        # mapping of those file descriptors to network connections.
                        '_msg': "External issue"
                    },
                },
            }
        },
    }
}


def build_global_message():
    """Parse the decision tree and return the message.

    Note: message corresponding to the current thresholds values
    """
    # Compute the weight for each item in the tree
    current_thresholds = glances_thresholds.get()
    for i in tree:
        i['weight'] = sum([current_thresholds[t].value() for t in i['thresholds'] if t in current_thresholds])
    themax = max(tree, key=lambda d: d['weight'])
    if themax['weight'] >= themax['thresholds_min']:
        # Check if the weight is > to the minimal threshold value
        return themax['msg']
    else:
        return tree[0]['msg']


class GlancesEvents(object):

    """This class manages events inside the Glances software.

    Events is a list of event (stored in the self.events_list var)
    event_state = "OK|CAREFUL|WARNING|CRITICAL"
    event_type = "CPU*|LOAD|MEM|MON"
    event_value = value

    Item (or event) is defined by:
        {
            "begin": "begin",
            "end": "end",
            "state": "WARNING|CRITICAL",
            "type": "CPU|LOAD|MEM",
            "max": MAX,
            "avg": AVG,
            "min": MIN,
            "sum": SUM,
            "count": COUNT,
            "top": [top 3 process name],
            "desc": "Processes description",
            "sort": "top sort key",
            "global": "global alert message"
        }
    """

    def __init__(self, max_events=10, min_duration=6, min_interval=6):
        """Init the events class.

        max_events: maximum size of the events list
        min_duration: events duration should be > min_duration to be taken into account (in seconds)
        min_interval: minimal interval between same kind of alert (in seconds)
        """
        # Maximum size of the events list
        self.set_max_events(max_events)

        # Minimal event duraton time (in seconds)
        self.set_min_duration(min_duration)

        # Minimal interval between same kind of alert (in seconds)
        self.set_min_interval(min_interval)

        # Init the logs list
        self.events_list = []

    def set_max_events(self, max_events):
        """Set the maximum size of the events list."""
        self.max_events = max_events

    def set_min_duration(self, min_duration):
        """Set the minimal event duration time (in seconds)."""
        self.min_duration = min_duration

    def set_min_interval(self, min_interval):
        """Set the minimum interval between same kind of alert (in seconds)."""
        self.min_interval = min_interval

    def get(self):
        """Return the raw events list."""
        return self.events_list

    def len(self):
        """Return the number of events in the logs list."""
        return self.events_list.__len__()

    def __event_exist(self, event_time, event_type):
        """Return the event position in the events list if:
        type is matching
        and (end is < 0 or event_time - end < min_interval)
        Return -1 if the item is not found.
        """
        for i in range(self.len()):
            if ((self.events_list[i]['end'] < 0) or
                (event_time - self.events_list[i]['end'] < self.min_interval)) and \
               self.events_list[i]['type'] == event_type:
                return i
        return -1

    def get_event_sort_key(self, event_type):
        """Return the process sort key"""
        # Process sort depending on alert type
        if event_type.startswith("MEM"):
            # Sort TOP process by memory_percent
            ret = 'memory_percent'
        elif event_type.startswith("CPU_IOWAIT"):
            # Sort TOP process by io_counters (only for Linux OS)
            ret = 'io_counters'
        else:
            # Default sort is...
            ret = 'cpu_percent'
        return ret

    def set_process_sort(self, event_type):
        """Define the process auto sort key from the alert type."""
        if glances_processes.auto_sort:
            glances_processes.set_sort_key(self.get_event_sort_key(event_type))

    def reset_process_sort(self):
        """Reset the process auto sort key."""
        if glances_processes.auto_sort:
            glances_processes.set_sort_key('auto')

    def add(self, event_state, event_type, event_value, proc_list=None, proc_desc="", min_duration=None):
        """Add a new item to the logs list.

        event_state = "OK|CAREFUL|WARNING|CRITICAL"
        event_type = "CPU|LOAD|MEM|..."
        event_value = value
        proc_list = list of processes
        proc_desc = processes description
        global_message = global alert message

        If 'event' is a 'new one', add it at the beginning of the list.
        If 'event' is not a 'new one', update the list .
        When finished if event duration < peak_time then the alert is not set.
        """
        event_time = time.mktime(datetime.now().timetuple())
        global_message = build_global_message()
        proc_list = proc_list or glances_processes.get_list()

        # Add or update the log
        event_index = self.__event_exist(event_time, event_type)
        if event_index < 0:
            # Event did not exist, add it
            self._create_event(event_time, event_state, event_type, event_value,
                               proc_desc, global_message)
        else:
            # Event exist, update it
            self._update_event(event_time, event_index, event_state, event_type, event_value,
                               proc_list, proc_desc, global_message)

        return self.len()

    def _create_event(self, event_time, event_state, event_type, event_value,
                      proc_desc, global_message):
        """Add a new item in the log list.

        Item is added only if the criticality (event_state) is WARNING or CRITICAL.
        """
        if event_state == "WARNING" or event_state == "CRITICAL":
            # Define the automatic process sort key
            self.set_process_sort(event_type)

            # Create the new log item
            # Time is stored in Epoch format
            # Epoch -> DMYHMS = datetime.fromtimestamp(epoch)
            item = {
                "begin": event_time,
                "end": -1,
                "state": event_state,
                "type": event_type,
                "max": event_value,
                "avg": event_value,
                "min": event_value,
                "sum": event_value,
                "count": 1,
                "top": [],
                "desc": proc_desc,
                "sort": glances_processes.sort_key,
                "global": global_message,
            }

            # Add the item to the list
            self.events_list.insert(0, item)

            # Limit the list to 'max_events' items
            if self.len() > self.max_events:
                self.events_list.pop()
            return True
        else:
            return False

    def _update_event(self, event_time, event_index, event_state, event_type, event_value,
                      proc_list, proc_desc, global_message):
        """Update an event in the list"""
        if event_state in ('OK', 'CAREFUL') and self.events_list[event_index]['end'] < 0:
            # Close the event
            self._close_event(event_time, event_index)
        elif event_state in ('OK', 'CAREFUL') and self.events_list[event_index]['end'] >= 0:
            # Event is already closed, do nothing
            pass
        else:  # event_state == "WARNING" or event_state == "CRITICAL"
            # Set process sort key
            self.set_process_sort(event_type)

            # It's an ongoing event, set the end time to -1
            self.events_list[event_index]['end'] = -1

            # Min/Max/Sum/Count/Avergae value
            self.events_list[event_index]['min'] = min(self.events_list[event_index]['min'], event_value)
            self.events_list[event_index]['max'] = max(self.events_list[event_index]['max'], event_value)
            self.events_list[event_index]['sum'] += event_value
            self.events_list[event_index]['count'] += 1
            self.events_list[event_index]['avg'] = self.events_list[event_index]['sum'] / self.events_list[event_index]['count']

            if event_state == "CRITICAL":
                # Avoid to change from CRITICAL to WARNING
                # If an events have reached the CRITICAL state, it can't go back to WARNING
                self.events_list[event_index]['state'] = event_state

                # TOP PROCESS LIST (only for CRITICAL ALERT)
                events_sort_key = self.get_event_sort_key(event_type)

                # Sort the current process list to retrieve the TOP 3 processes
                self.events_list[event_index]['top'] = [p['name'] for p in sort_stats(proc_list, events_sort_key)[0:3]]
                self.events_list[event_index]['sort'] = events_sort_key

            # MONITORED PROCESSES DESC
            self.events_list[event_index]['desc'] = proc_desc

            # Global message:
            self.events_list[event_index]['global'] = global_message

        return True

    def _close_event(self, event_time, event_index):
        """Close an event in the list"""
        # Reset the automatic process sort key
        self.reset_process_sort()

        # Set the end of the events
        if event_time - self.events_list[event_index]['begin'] >= self.min_duration:
            # If event is >= min_duration seconds
            self.events_list[event_index]['end'] = event_time
        else:
            # If event < min_duration seconds, ignore
            self.events_list.remove(self.events_list[event_index])

    def clean(self, critical=False):
        """Clean the logs list by deleting finished items.

        By default, only delete WARNING message.
        If critical = True, also delete CRITICAL message.
        """
        # Create a new clean list
        clean_events_list = []
        while self.len() > 0:
            item = self.events_list.pop()
            if item['end'] < 0 or (not critical and item['state'].startswith("CRITICAL")):
                clean_events_list.insert(0, item)
        # The list is now the clean one
        self.events_list = clean_events_list
        return self.len()


glances_events = GlancesEvents()

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

from glances.processes import glances_processes, sort_stats


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
            "sort": "top sort key"
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

        If 'event' is a 'new one', add it at the beginning of the list.
        If 'event' is not a 'new one', update the list .
        When finished if event duration < peak_time then the alert is not set.
        """
        event_time = time.mktime(datetime.now().timetuple())
        proc_list = proc_list or glances_processes.get_list()

        # Add or update the log
        event_index = self.__event_exist(event_time, event_type)
        if event_index < 0:
            # Event did not exist, add it
            self._create_event(event_time, event_state, event_type, event_value, proc_desc)
        else:
            # Event exist, update it
            self._update_event(event_time, event_index, event_state, event_type, event_value, proc_list, proc_desc)

        return self.len()

    def _create_event(self, event_time, event_state, event_type, event_value, proc_desc):
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
            }

            # Add the item to the list
            self.events_list.insert(0, item)

            # Limit the list to 'max_events' items
            if self.len() > self.max_events:
                self.events_list.pop()
            return True
        else:
            return False

    def _update_event(self, event_time, event_index, event_state, event_type, event_value, proc_list, proc_desc):
        """Update an event in the list"""
        if event_state == "OK" or event_state == "CAREFUL":
            # Reset the automatic process sort key
            self.reset_process_sort()

            # Set the end of the events
            end_time = event_time
            if end_time - self.events_list[event_index]['begin'] >= self.min_duration:
                # If event is >= min_duration seconds
                self.events_list[event_index]['end'] = end_time
            else:
                # If event < min_duration seconds, ignore
                self.events_list.remove(self.events_list[event_index])
        else:
            # Update the item

            # It's an ogoing event, update the end time
            self.events_list[event_index]['end'] = -1

            # Set process sort key
            self.set_process_sort(event_type)

            # State
            if event_state == "CRITICAL":
                self.events_list[event_index]['state'] = event_state
            # Min value
            self.events_list[event_index]['min'] = min(self.events_list[event_index]['min'], event_value)
            # Max value
            self.events_list[event_index]['max'] = max(self.events_list[event_index]['max'], event_value)
            # Average value
            self.events_list[event_index]['sum'] += event_value
            self.events_list[event_index]['count'] += 1
            self.events_list[event_index]['avg'] = self.events_list[event_index]['sum'] / self.events_list[event_index]['count']

            # TOP PROCESS LIST (only for CRITICAL ALERT)
            if event_state == "CRITICAL":
                events_sort_key = self.get_event_sort_key(event_type)
                # Sort the current process list to retrieve the TOP 3 processes
                self.events_list[event_index]['top'] = [p['name'] for p in sort_stats(proc_list, events_sort_key)[0:3]]
                self.events_list[event_index]['sort'] = events_sort_key

            # MONITORED PROCESSES DESC
            self.events_list[event_index]['desc'] = proc_desc

        return True

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

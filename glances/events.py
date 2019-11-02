# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2019 Nicolargo <nicolas@nicolargo.com>
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

"""Manage Glances events (previously Glances logs in Glances < 3.1)."""

import time
from datetime import datetime

from glances.compat import range
from glances.processes import glances_processes, sort_stats


class GlancesEvents(object):

    """This class manages events inside the Glances software.

    Events is a list of event (stored in the self.events_list var)
    event_state = "OK|CAREFUL|WARNING|CRITICAL"
    event_type = "CPU*|LOAD|MEM|MON"
    event_value = value

    Item (or event) is defined by:
      ["begin",
       "end",
       "WARNING|CRITICAL",
       "CPU|LOAD|MEM",
       MAX, AVG, MIN, SUM, COUNT,
       [top3 process list],
       "Processes description",
       "top sort key"]
    """

    def __init__(self):
        """Init the events class."""
        # Maximum size of the events list
        self.events_max = 10

        # Init the logs list
        self.events_list = []

    def get(self):
        """Return the raw events list."""
        return self.events_list

    def len(self):
        """Return the number of events in the logs list."""
        return self.events_list.__len__()

    def __event_exist(self, event_type):
        """Return the event position, if it exists.

        An event exist if:
        * end is < 0
        * event_type is matching
        Return -1 if the item is not found.
        """
        for i in range(self.len()):
            if self.events_list[i][1] < 0 and self.events_list[i][3] == event_type:
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

    def add(self, event_state, event_type, event_value,
            proc_list=None, proc_desc="", peak_time=6):
        """Add a new item to the logs list.

        If 'event' is a 'new one', add it at the beginning of the list.
        If 'event' is not a 'new one', update the list .
        If event < peak_time then the alert is not set.
        """
        proc_list = proc_list or glances_processes.getlist()

        # Add or update the log
        event_index = self.__event_exist(event_type)
        if event_index < 0:
            # Event did not exist, add it
            self._create_event(event_state, event_type, event_value,
                               proc_list, proc_desc, peak_time)
        else:
            # Event exist, update it
            self._update_event(event_index, event_state, event_type, event_value,
                               proc_list, proc_desc, peak_time)

        return self.len()

    def _create_event(self, event_state, event_type, event_value,
                      proc_list, proc_desc, peak_time):
        """Add a new item in the log list.

        Item is added only if the criticity (event_state) is WARNING or CRITICAL.
        """
        if event_state == "WARNING" or event_state == "CRITICAL":
            # Define the automatic process sort key
            self.set_process_sort(event_type)

            # Create the new log item
            # Time is stored in Epoch format
            # Epoch -> DMYHMS = datetime.fromtimestamp(epoch)
            item = [
                time.mktime(datetime.now().timetuple()),  # START DATE
                -1,  # END DATE
                event_state,  # STATE: WARNING|CRITICAL
                event_type,  # TYPE: CPU, LOAD, MEM...
                event_value,  # MAX
                event_value,  # AVG
                event_value,  # MIN
                event_value,  # SUM
                1,  # COUNT
                [],  # TOP 3 PROCESS LIST
                proc_desc,  # MONITORED PROCESSES DESC
                glances_processes.sort_key]  # TOP PROCESS SORTKEY

            # Add the item to the list
            self.events_list.insert(0, item)

            # Limit the list to 'events_max' items
            if self.len() > self.events_max:
                self.events_list.pop()

            return True
        else:
            return False

    def _update_event(self, event_index, event_state, event_type, event_value,
                      proc_list, proc_desc, peak_time):
        """Update an event in the list"""
        if event_state == "OK" or event_state == "CAREFUL":
            # Reset the automatic process sort key
            self.reset_process_sort()

            # Set the end of the events
            endtime = time.mktime(datetime.now().timetuple())
            if endtime - self.events_list[event_index][0] > peak_time:
                # If event is > peak_time seconds
                self.events_list[event_index][1] = endtime
            else:
                # If event <= peak_time seconds, ignore
                self.events_list.remove(self.events_list[event_index])
        else:
            # Update the item
            self.set_process_sort(event_type)

            # State
            if event_state == "CRITICAL":
                self.events_list[event_index][2] = event_state
            # Min value
            self.events_list[event_index][6] = min(self.events_list[event_index][6],
                                                   event_value)
            # Max value
            self.events_list[event_index][4] = max(self.events_list[event_index][4],
                                                   event_value)
            # Average value
            self.events_list[event_index][7] += event_value
            self.events_list[event_index][8] += 1
            self.events_list[event_index][5] = (self.events_list[event_index][7] /
                                                self.events_list[event_index][8])

            # TOP PROCESS LIST (only for CRITICAL ALERT)
            if event_state == "CRITICAL":
                events_sort_key = self.get_event_sort_key(event_type)
                # Sort the current process list to retreive the TOP 3 processes
                self.events_list[event_index][9] = sort_stats(proc_list,
                                                              events_sort_key)[0:3]
                self.events_list[event_index][11] = events_sort_key

            # MONITORED PROCESSES DESC
            self.events_list[event_index][10] = proc_desc

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
            if item[1] < 0 or (not critical and item[2].startswith("CRITICAL")):
                clean_events_list.insert(0, item)
        # The list is now the clean one
        self.events_list = clean_events_list
        return self.len()


glances_events = GlancesEvents()

# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2015 Nicolargo <nicolas@nicolargo.com>
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

"""Manage logs."""

import time
from datetime import datetime

from glances.compat import range
from glances.processes import glances_processes, sort_stats
# from glances.logger import logger


class GlancesLogs(object):

    """This class manages logs inside the Glances software.

    Logs is a list of list (stored in the self.logs_list var)
    item_state = "OK|CAREFUL|WARNING|CRITICAL"
    item_type = "CPU*|LOAD|MEM|MON"
    item_value = value

    Item is defined by:
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
        """Init the logs class."""
        # Maximum size of the logs list
        self.logs_max = 10

        # Init the logs list
        self.logs_list = []

    def get(self):
        """Return the raw logs list."""
        return self.logs_list

    def len(self):
        """Return the number of item in the logs list."""
        return self.logs_list.__len__()

    def __itemexist__(self, item_type):
        """Return the item position, if it exists.

        An item exist in the list if:
        * end is < 0
        * item_type is matching
        Return -1 if the item is not found.
        """
        for i in range(self.len()):
            if self.logs_list[i][1] < 0 and self.logs_list[i][3] == item_type:
                return i
        return -1

    def get_process_sort_key(self, item_type):
        """Return the process sort key"""
        # Process sort depending on alert type
        if item_type.startswith("MEM"):
            # Sort TOP process by memory_percent
            ret = 'memory_percent'
        elif item_type.startswith("CPU_IOWAIT"):
            # Sort TOP process by io_counters (only for Linux OS)
            ret = 'io_counters'
        else:
            # Default sort is...
            ret = 'cpu_percent'
        return ret

    def set_process_sort(self, item_type):
        """Define the process auto sort key from the alert type."""
        glances_processes.auto_sort = True
        glances_processes.sort_key = self.get_process_sort_key(item_type)

    def reset_process_sort(self):
        """Reset the process auto sort key."""
        # Default sort is...
        glances_processes.auto_sort = True
        glances_processes.sort_key = 'cpu_percent'

    def add(self, item_state, item_type, item_value,
            proc_list=None, proc_desc="", peak_time=6):
        """Add a new item to the logs list.

        If 'item' is a 'new one', add the new item at the beginning of
        the logs list.
        If 'item' is not a 'new one', update the existing item.
        If event < peak_time the the alert is not setoff.
        """
        proc_list = proc_list or glances_processes.getalllist()

        # Add or update the log
        item_index = self.__itemexist__(item_type)
        if item_index < 0:
            # Item did not exist, add if WARNING or CRITICAL
            self._create_item(item_state, item_type, item_value,
                              proc_list, proc_desc, peak_time)
        else:
            # Item exist, update
            self._update_item(item_index, item_state, item_type, item_value,
                              proc_list, proc_desc, peak_time)

        return self.len()

    def _create_item(self, item_state, item_type, item_value,
                     proc_list, proc_desc, peak_time):
        """Create a new item in the log list"""
        if item_state == "WARNING" or item_state == "CRITICAL":
            # Define the automatic process sort key
            self.set_process_sort(item_type)

            # Create the new log item
            # Time is stored in Epoch format
            # Epoch -> DMYHMS = datetime.fromtimestamp(epoch)
            item = [
                time.mktime(datetime.now().timetuple()),  # START DATE
                -1,  # END DATE
                item_state,  # STATE: WARNING|CRITICAL
                item_type,  # TYPE: CPU, LOAD, MEM...
                item_value,  # MAX
                item_value,  # AVG
                item_value,  # MIN
                item_value,  # SUM
                1,  # COUNT
                [],  # TOP 3 PROCESS LIST
                proc_desc,  # MONITORED PROCESSES DESC
                glances_processes.sort_key]  # TOP PROCESS SORTKEY

            # Add the item to the list
            self.logs_list.insert(0, item)
            if self.len() > self.logs_max:
                self.logs_list.pop()

            return True
        else:
            return False

    def _update_item(self, item_index, item_state, item_type, item_value,
                     proc_list, proc_desc, peak_time):
        """Update a item in the log list"""
        if item_state == "OK" or item_state == "CAREFUL":
            # Reset the automatic process sort key
            self.reset_process_sort()

            endtime = time.mktime(datetime.now().timetuple())
            if endtime - self.logs_list[item_index][0] > peak_time:
                # If event is > peak_time seconds
                self.logs_list[item_index][1] = endtime
            else:
                # If event <= peak_time seconds, ignore
                self.logs_list.remove(self.logs_list[item_index])
        else:
            # Update the item

            # State
            if item_state == "CRITICAL":
                self.logs_list[item_index][2] = item_state

            # Value
            if item_value > self.logs_list[item_index][4]:
                # MAX
                self.logs_list[item_index][4] = item_value
            elif item_value < self.logs_list[item_index][6]:
                # MIN
                self.logs_list[item_index][6] = item_value
            # AVG (compute average value)
            self.logs_list[item_index][7] += item_value
            self.logs_list[item_index][8] += 1
            self.logs_list[item_index][5] = (self.logs_list[item_index][7] /
                                             self.logs_list[item_index][8])

            # TOP PROCESS LIST (only for CRITICAL ALERT)
            if item_state == "CRITICAL":
                # Sort the current process list to retreive the TOP 3 processes
                self.logs_list[item_index][9] = sort_stats(proc_list, glances_processes.sort_key)[0:3]
                self.logs_list[item_index][11] = glances_processes.sort_key

            # MONITORED PROCESSES DESC
            self.logs_list[item_index][10] = proc_desc

        return True

    def clean(self, critical=False):
        """Clean the logs list by deleting finished items.

        By default, only delete WARNING message.
        If critical = True, also delete CRITICAL message.
        """
        # Create a new clean list
        clean_logs_list = []
        while self.len() > 0:
            item = self.logs_list.pop()
            if item[1] < 0 or (not critical and item[2].startswith("CRITICAL")):
                clean_logs_list.insert(0, item)
        # The list is now the clean one
        self.logs_list = clean_logs_list
        return self.len()

glances_logs = GlancesLogs()

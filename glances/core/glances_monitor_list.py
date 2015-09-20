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

"""Manage the monitor list."""

# Import system lib
import re
import subprocess

# Import Glances lib
from glances.core.glances_logging import logger
from glances.core.glances_processes import glances_processes


class MonitorList(object):

    """This class describes the optional monitored processes list.

    The monitored list is a list of 'important' processes to monitor.

    The list (Python list) is composed of items (Python dict).
    An item is defined (dict keys):
    * description: Description of the processes (max 16 chars)
    * regex: regular expression of the processes to monitor
    * command: (optional) shell command for extended stat
    * countmin: (optional) minimal number of processes
    * countmax: (optional) maximum number of processes
    """

    # Maximum number of items in the list
    __monitor_list_max_size = 10
    # The list
    __monitor_list = []

    def __init__(self, config):
        """Init the monitoring list from the configuration file, if it exists."""
        self.config = config

        if self.config is not None and self.config.has_section('monitor'):
            # Process monitoring list
            logger.debug("Monitor list configuration detected")
            self.__set_monitor_list('monitor', 'list')
        else:
            self.__monitor_list = []

    def __set_monitor_list(self, section, key):
        """Init the monitored processes list.

        The list is defined in the Glances configuration file.
        """
        for l in range(1, self.__monitor_list_max_size + 1):
            value = {}
            key = "list_" + str(l) + "_"
            try:
                description = self.config.get_value(section, key + 'description')
                regex = self.config.get_value(section, key + 'regex')
                command = self.config.get_value(section, key + 'command')
                countmin = self.config.get_value(section, key + 'countmin')
                countmax = self.config.get_value(section, key + 'countmax')
            except Exception as e:
                logger.error("Cannot read monitored list: {0}".format(e))
            else:
                if description is not None and regex is not None:
                    # Build the new item
                    value["description"] = description
                    try:
                        re.compile(regex)
                    except Exception:
                        continue
                    else:
                        value["regex"] = regex
                    value["command"] = command
                    value["countmin"] = countmin
                    value["countmax"] = countmax
                    value["count"] = None
                    value["result"] = None
                    # Add the item to the list
                    self.__monitor_list.append(value)

    def __str__(self):
        return str(self.__monitor_list)

    def __repr__(self):
        return self.__monitor_list

    def __getitem__(self, item):
        return self.__monitor_list[item]

    def __len__(self):
        return len(self.__monitor_list)

    def __get__(self, item, key):
        """Meta function to return key value of item.

        Return None if not defined or item > len(list)
        """
        if item < len(self.__monitor_list):
            try:
                return self.__monitor_list[item][key]
            except Exception:
                return None
        else:
            return None

    def update(self):
        """Update the command result attributed."""
        # Only continue if monitor list is not empty
        if len(self.__monitor_list) == 0:
            return self.__monitor_list

        # Iter upon the monitored list
        for i in range(0, len(self.get())):
            # Search monitored processes by a regular expression
            processlist = glances_processes.getalllist()
            monitoredlist = [p for p in processlist if re.search(self.regex(i), p['cmdline']) is not None]
            self.__monitor_list[i]['count'] = len(monitoredlist)

            if self.command(i) is not None:
                # Execute the user command line
                try:
                    self.__monitor_list[i]['result'] = subprocess.check_output(self.command(i),
                                                                               shell=True)
                except subprocess.CalledProcessError:
                    self.__monitor_list[i]['result'] = 'Error: ' + self.command(i)
                except Exception:
                    self.__monitor_list[i]['result'] = 'Cannot execute command'
                # Only save the first line
                self.__monitor_list[i]['result'] = self.__monitor_list[i]['result'].decode('utf-8').split('\n')[0]

            if self.command(i) is None or self.__monitor_list[i]['result'] == '':
                # If there is no command specified in the conf file
                # then display CPU and MEM %
                self.__monitor_list[i]['result'] = 'CPU: {0:.1f}% | MEM: {1:.1f}%'.format(
                    sum([p['cpu_percent'] for p in monitoredlist]),
                    sum([p['memory_percent'] for p in monitoredlist]))

        return self.__monitor_list

    def get(self):
        """Return the monitored list (list of dict)."""
        return self.__monitor_list

    def set(self, newlist):
        """Set the monitored list (list of dict)."""
        self.__monitor_list = newlist

    def getAll(self):
        # Deprecated: use get()
        return self.get()

    def setAll(self, newlist):
        # Deprecated: use set()
        self.set(newlist)

    def description(self, item):
        """Return the description of the item number (item)."""
        return self.__get__(item, "description")

    def regex(self, item):
        """Return the regular expression of the item number (item)."""
        return self.__get__(item, "regex")

    def command(self, item):
        """Return the stat command of the item number (item)."""
        return self.__get__(item, "command")

    def result(self, item):
        """Return the reult command of the item number (item)."""
        return self.__get__(item, "result")

    def countmin(self, item):
        """Return the minimum number of processes of the item number (item)."""
        return self.__get__(item, "countmin")

    def countmax(self, item):
        """Return the maximum number of processes of the item number (item)."""
        return self.__get__(item, "countmax")

#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Glances - An eye on your system
#
# Copyright (C) 2014 Nicolargo <nicolas@nicolargo.com>
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

class monitorList:
    """
    This class describes the optionnal monitored processes list
    A list of 'important' processes to monitor.

    The list (Python list) is composed of items (Python dict)
    An item is defined (Dict keys'):
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
        """
        Init the monitoring list from the configuration file
        """

        self.config = config 

        if self.config.has_section('monitor'):
            # Process monitoring list
            self.__setMonitorList('monitor', 'list')

    def __setMonitorList(self, section, key):
        """
        Init the monitored processes list
        The list is defined in the Glances configuration file
        """
        for l in range(1, self.__monitor_list_max_size + 1):
            value = {}
            key = "list_" + str(l) + "_"
            try:
                description = self.config.get_raw_option(section, key + "description")
                regex = self.config.get_raw_option(section, key + "regex")
                command = self.config.get_raw_option(section, key + "command")
                countmin = self.config.get_raw_option(section, key + "countmin")
                countmax = self.config.get_raw_option(section, key + "countmax")
            except Exception,e:
                print(_("Error reading monitored list: %s" % e))
                pass
            else:
                if description is not None and regex is not None:
                    # Build the new item
                    value["description"] = description
                    value["regex"] = regex
                    value["command"] = command
                    value["countmin"] = countmin
                    value["countmax"] = countmax
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
        """
        Meta function to return key value of item
        None if not defined or item > len(list)
        """
        if item < len(self.__monitor_list):
            try:
                return self.__monitor_list[item][key]
            except Exception:
                return None
        else:
            return None

    def getAll(self):
        return self.__monitor_list

    def setAll(self, newlist):
        self.__monitor_list = newlist

    def description(self, item):
        """
        Return the description of the item number (item)
        """
        return self.__get__(item, "description")

    def regex(self, item):
        """
        Return the regular expression of the item number (item)
        """
        return self.__get__(item, "regex")

    def command(self, item):
        """
        Return the stats command of the item number (item)
        """
        return self.__get__(item, "command")

    def countmin(self, item):
        """
        Return the minimum number of processes of the item number (item)
        """
        return self.__get__(item, "countmin")

    def countmax(self, item):
        """
        Return the maximum number of processes of the item number (item)
        """
        return self.__get__(item, "countmax")


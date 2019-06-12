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

"""Manage the folder list."""
from __future__ import unicode_literals

import os

from glances.timer import Timer
from glances.compat import range, nativestr
from glances.logger import logger

# Use the built-in version of scandir/walk if possible, otherwise
# use the scandir module version
scandir_tag = True
try:
    # For Python 3.5 or higher
    from os import scandir
except ImportError:
    # For others...
    try:
        from scandir import scandir
    except ImportError:
        scandir_tag = False


class FolderList(object):

    """This class describes the optional monitored folder list.

    The folder list is a list of 'important' folder to monitor.

    The list (Python list) is composed of items (Python dict).
    An item is defined (dict keys):
    * path: Path to the folder
    * careful: optional careful threshold (in MB)
    * warning: optional warning threshold (in MB)
    * critical: optional critical threshold (in MB)
    """

    # Maximum number of items in the list
    __folder_list_max_size = 10
    # The folder list
    __folder_list = []
    # Default refresh time is 30 seconds for this plugins
    __default_refresh = 30

    def __init__(self, config):
        """Init the folder list from the configuration file, if it exists."""
        self.config = config

        # A list of Timer
        # One timer per folder
        # default timer is __default_refresh, can be overwrite by folder_1_refresh=600
        self.timer_folders = []
        self.first_grab = True

        if self.config is not None and self.config.has_section('folders'):
            if scandir_tag:
                # Process monitoring list
                logger.debug("Folder list configuration detected")
                self.__set_folder_list('folders')
            else:
                logger.error('Scandir not found. Please use Python 3.5+ or install the scandir lib')
        else:
            self.__folder_list = []

    def __set_folder_list(self, section):
        """Init the monitored folder list.

        The list is defined in the Glances configuration file.
        """
        for l in range(1, self.__folder_list_max_size + 1):
            value = {}
            key = 'folder_' + str(l) + '_'

            # Path is mandatory
            value['indice'] = str(l)
            value['path'] = self.config.get_value(section, key + 'path')
            if value['path'] is None:
                continue
            else:
                value['path'] = nativestr(value['path'])

            # Optional conf keys
            # Refresh time
            value['refresh'] = int(self.config.get_value(section,
                                                         key + 'refresh',
                                                         default=self.__default_refresh))
            self.timer_folders.append(Timer(value['refresh']))
            # Thesholds
            for i in ['careful', 'warning', 'critical']:
                # Read threshold
                value[i] = self.config.get_value(section, key + i)
                if value[i] is not None:
                    logger.debug("{} threshold for folder {} is {}".format(i, value["path"], value[i]))
                # Read action
                action = self.config.get_value(section, key + i + '_action')
                if action is not None:
                    value[i + '_action'] = action
                    logger.debug("{} action for folder {} is {}".format(i, value["path"], value[i + '_action']))

            # Add the item to the list
            self.__folder_list.append(value)

    def __str__(self):
        return str(self.__folder_list)

    def __repr__(self):
        return self.__folder_list

    def __getitem__(self, item):
        return self.__folder_list[item]

    def __len__(self):
        return len(self.__folder_list)

    def __get__(self, item, key):
        """Meta function to return key value of item.

        Return None if not defined or item > len(list)
        """
        if item < len(self.__folder_list):
            try:
                return self.__folder_list[item][key]
            except Exception:
                return None
        else:
            return None

    def __folder_size(self, path):
        """Return the size of the directory given by path

        path: <string>"""

        ret = 0
        for f in scandir(path):
            if f.is_dir() and (f.name != '.' or f.name != '..'):
                ret += self.__folder_size(os.path.join(path, f.name))
            else:
                try:
                    ret += f.stat().st_size
                except OSError:
                    pass

        return ret

    def update(self):
        """Update the command result attributed."""
        # Only continue if monitor list is not empty
        if len(self.__folder_list) == 0:
            return self.__folder_list

        # Iter upon the folder list
        for i in range(len(self.get())):
            # Update folder size
            if not self.first_grab and not self.timer_folders[i].finished():
                continue
            # Get folder size
            try:
                self.__folder_list[i]['size'] = self.__folder_size(self.path(i))
            except OSError as e:
                logger.debug('Cannot get folder size ({}). Error: {}'.format(self.path(i), e))
                if e.errno == 13:
                    # Permission denied
                    self.__folder_list[i]['size'] = '!'
                else:
                    self.__folder_list[i]['size'] = '?'
            # Reset the timer
            self.timer_folders[i].reset()

        # It is no more the first time...
        self.first_grab = False

        return self.__folder_list

    def get(self):
        """Return the monitored list (list of dict)."""
        return self.__folder_list

    def set(self, newlist):
        """Set the monitored list (list of dict)."""
        self.__folder_list = newlist

    def getAll(self):
        # Deprecated: use get()
        return self.get()

    def setAll(self, newlist):
        # Deprecated: use set()
        self.set(newlist)

    def path(self, item):
        """Return the path of the item number (item)."""
        return self.__get__(item, "path")

    def careful(self, item):
        """Return the careful threshold of the item number (item)."""
        return self.__get__(item, "careful")

    def warning(self, item):
        """Return the warning threshold of the item number (item)."""
        return self.__get__(item, "warning")

    def critical(self, item):
        """Return the critical threshold of the item number (item)."""
        return self.__get__(item, "critical")

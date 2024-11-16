#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Manage the folder list."""

from glances.globals import folder_size, nativestr
from glances.logger import logger
from glances.timer import Timer


class FolderList:
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
            # Process monitoring list
            logger.debug("Folder list configuration detected")
            self.__set_folder_list('folders')
        else:
            self.__folder_list = []

    def __set_folder_list(self, section):
        """Init the monitored folder list.

        The list is defined in the Glances configuration file.
        """
        for line in range(1, self.__folder_list_max_size + 1):
            value = {}
            key = 'folder_' + str(line) + '_'

            # Path is mandatory
            value['indice'] = str(line)
            value['path'] = self.config.get_value(section, key + 'path')
            if value['path'] is None:
                continue
            value['path'] = nativestr(value['path'])

            # Optional conf keys
            # Refresh time
            value['refresh'] = int(self.config.get_value(section, key + 'refresh', default=self.__default_refresh))
            self.timer_folders.append(Timer(value['refresh']))
            # Thresholds
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

    def update(self, key='path'):
        """Update the command result attributed."""
        # Only continue if monitor list is not empty
        if not self.__folder_list:
            return self.__folder_list

        # Iter upon the folder list
        for i in range(len(self.get())):
            # Update folder size
            if not self.first_grab and not self.timer_folders[i].finished():
                continue
            # Set the key (see issue #2327)
            self.__folder_list[i]['key'] = key
            # Get folder size
            self.__folder_list[i]['size'], self.__folder_list[i]['errno'] = folder_size(self.path(i))
            if self.__folder_list[i]['errno'] != 0:
                logger.debug(
                    'Folder size ({} ~ {}) may not be correct. Error: {}'.format(
                        self.path(i), self.__folder_list[i]['size'], self.__folder_list[i]['errno']
                    )
                )
            # Reset the timer
            self.timer_folders[i].reset()

        # It is no more the first time...
        self.first_grab = False

        return self.__folder_list

    def get(self):
        """Return the monitored list (list of dict)."""
        return self.__folder_list

    def set(self, new_list):
        """Set the monitored list (list of dict)."""
        self.__folder_list = new_list

    def getAll(self):
        # Deprecated: use get()
        return self.get()

    def setAll(self, new_list):
        # Deprecated: use set()
        self.set(new_list)

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

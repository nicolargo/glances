# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2016 Nicolargo <nicolas@nicolargo.com>
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

"""Manage the AMPs list."""

import os
import re
import subprocess

from glances.compat import listkeys, iteritems
from glances.logger import logger
from glances.globals import amps_path
from glances.processes import glances_processes


class AmpsList(object):

    """This class describes the optional application process monitoring list.

    The AMP list is a list of processes with a specific monitoring action.

    The list (Python list) is composed of items (Python dict).
    An item is defined (dict keys):
    *...
    """

    # The dict
    __amps_dict = {}

    def __init__(self, args, config):
        """Init the AMPs list."""
        self.args = args
        self.config = config

        # Create the AMPS list
        self.load_amps()
        self.load_configs()

    def load_amps(self):
        """Load all amps in the 'amps' folder."""
        header = "glances_"
        for item in os.listdir(amps_path):
            if (item.startswith(header) and
                    item.endswith(".py") and
                    item != (header + "amp.py")):
                # Import the amp
                amp = __import__(os.path.basename(item)[:-3])
                # Add the AMP to the dictionary
                # The key is the AMP name
                # for example, the file glances_xxx.py
                # generate self._amps_list["xxx"] = ...
                amp_name = os.path.basename(item)[len(header):-3].lower()
                self.__amps_dict[amp_name] = amp.Amp(self.args)
        # Log AMPs list
        logger.debug("Available AMPs list: {0}".format(self.getList()))

    def load_configs(self):
        """Load the AMP configuration files."""
        # For each AMPs, call the load_config method
        for a in self.get():
            self.get()[a].load_config(self.config)

    def __str__(self):
        return str(self.__amps_dict)

    def __repr__(self):
        return self.__amps_dict

    def __getitem__(self, item):
        return self.__amps_dict[item]

    def __len__(self):
        return len(self.__amps_dict)

    def update(self):
        """Update the command result attributed."""
        # Search application monitored processes by a regular expression
        processlist = [p for p in glances_processes.getalllist()]

        # Iter upon the AMPs dict
        for k, v in iteritems(self.get()):
            amps_list = [p for p in processlist for c in p['cmdline'] if re.search(v.regex(), c) is not None]
            if len(amps_list) > 0:
                # At least one process is matching the regex
                logger.debug("AMPS: {} process detected (PID={})".format(k, amps_list[0]['pid']))
                # Call the AMP update method
                v.update()

        return self.__amps_dict

    def getList(self):
        """Return the AMPs list."""
        return listkeys(self.__amps_dict)

    def get(self):
        """Return the AMPs dict."""
        return self.__amps_dict

    def set(self, new_dict):
        """Set the AMPs dict."""
        self.__amps_dict = new_dict

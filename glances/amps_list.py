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

"""Manage the AMPs list."""

import os
import re
import threading

from glances.compat import listkeys, iteritems
from glances.logger import logger
from glances.globals import amps_path
from glances.processes import glances_processes


class AmpsList(object):

    """This class describes the optional application monitoring process list.

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

        # Load the AMP configurations / scripts
        self.load_configs()

    def load_configs(self):
        """Load the AMP configuration files."""
        if self.config is None:
            return False

        # Display a warning (deprecated) message if the monitor section exist
        if "monitor" in self.config.sections():
            logger.warning("A deprecated [monitor] section exists in the Glances configuration file. You should use the new Applications Monitoring Process module instead (http://glances.readthedocs.io/en/develop/aoa/amps.html).")

        header = "glances_"
        # For each AMP scrip, call the load_config method
        for s in self.config.sections():
            if s.startswith("amp_"):
                # An AMP section exists in the configuration file
                # If an AMP script exist in the glances/amps folder, use it
                amp_conf_name = s[4:]
                amp_script = os.path.join(amps_path, header + s[4:] + ".py")
                if not os.path.exists(amp_script):
                    # If not, use the default script
                    amp_script = os.path.join(amps_path, "glances_default.py")
                try:
                    amp = __import__(os.path.basename(amp_script)[:-3])
                except ImportError as e:
                    logger.warning("Missing Python Lib ({}), cannot load {} AMP".format(e, amp_conf_name))
                except Exception as e:
                    logger.warning("Cannot load {} AMP ({})".format(amp_conf_name, e))
                else:
                    # Add the AMP to the dictionary
                    # The key is the AMP name
                    # for example, the file glances_xxx.py
                    # generate self._amps_list["xxx"] = ...
                    self.__amps_dict[amp_conf_name] = amp.Amp(name=amp_conf_name, args=self.args)
                    # Load the AMP configuration
                    self.__amps_dict[amp_conf_name].load_config(self.config)
        # Log AMPs list
        logger.debug("AMPs list: {}".format(self.getList()))

        return True

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
        # Get the current processes list (once)
        processlist = glances_processes.getlist()

        # Iter upon the AMPs dict
        for k, v in iteritems(self.get()):
            if not v.enable():
                # Do not update if the enable tag is set
                continue

            amps_list = self._build_amps_list(v, processlist)

            if len(amps_list) > 0:
                # At least one process is matching the regex
                logger.debug("AMPS: {} processes {} detected ({})".format(len(amps_list),
                                                                          k,
                                                                          amps_list))
                # Call the AMP update method
                thread = threading.Thread(target=v.update_wrapper, args=[amps_list])
                thread.start()
            else:
                # Set the process number to 0
                v.set_count(0)
                if v.count_min() is not None and v.count_min() > 0:
                    # Only display the "No running process message" if countmin is defined
                    v.set_result("No running process")

        return self.__amps_dict

    def _build_amps_list(self, amp_value, processlist):
        """Return the AMPS process list according to the amp_value

        Search application monitored processes by a regular expression
        """
        ret = []
        try:
            # Search in both cmdline and name (for kernel thread, see #1261)
            for p in processlist:
                add_it = False
                if (re.search(amp_value.regex(), p['name']) is not None):
                    add_it = True
                else:
                    for c in p['cmdline']:
                        if (re.search(amp_value.regex(), c) is not None):
                            add_it = True
                            break
                if add_it:
                    ret.append({'pid': p['pid'],
                                'cpu_percent': p['cpu_percent'],
                                'memory_percent': p['memory_percent']})

        except (TypeError, KeyError) as e:
            logger.debug("Can not build AMPS list ({})".format(e))

        return ret

    def getList(self):
        """Return the AMPs list."""
        return listkeys(self.__amps_dict)

    def get(self):
        """Return the AMPs dict."""
        return self.__amps_dict

    def set(self, new_dict):
        """Set the AMPs dict."""
        self.__amps_dict = new_dict

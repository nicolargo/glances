#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Manage the AMPs list."""

import os
import re
import threading

from glances.globals import amps_path, iteritems, listkeys
from glances.logger import logger
from glances.processes import glances_processes


class AmpsList:
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

        # For each AMP script, call the load_config method
        for s in self.config.sections():
            if s.startswith("amp_"):
                # An AMP section exists in the configuration file
                # If an AMP module exist in amps_path (glances/amps) folder then use it
                amp_name = s[4:]
                amp_module = os.path.join(amps_path, amp_name)
                if not os.path.exists(amp_module):
                    # If not, use the default script
                    amp_module = os.path.join(amps_path, "default")
                try:
                    amp = __import__(os.path.basename(amp_module))
                except ImportError as e:
                    logger.warning(f"Missing Python Lib ({e}), cannot load AMP {amp_name}")
                except Exception as e:
                    logger.warning(f"Cannot load AMP {amp_name} ({e})")
                else:
                    # Add the AMP to the dictionary
                    # The key is the AMP name
                    # for example, the file glances_xxx.py
                    # generate self._amps_list["xxx"] = ...
                    self.__amps_dict[amp_name] = amp.Amp(name=amp_name, args=self.args)
                    # Load the AMP configuration
                    self.__amps_dict[amp_name].load_config(self.config)
        # Log AMPs list
        logger.debug(f"AMPs list: {self.getList()}")

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
        processlist = glances_processes.get_list()

        # Iter upon the AMPs dict
        for k, v in iteritems(self.get()):
            if not v.enable():
                # Do not update if the enable tag is set
                continue

            if v.regex() is None:
                # If there is no regex, execute anyway (see issue #1690)
                v.set_count(0)
                # Call the AMP update method
                thread = threading.Thread(target=v.update_wrapper, args=[[]])
                thread.start()
                continue

            amps_list = self._build_amps_list(v, processlist)

            if amps_list:
                # At least one process is matching the regex
                logger.debug(f"AMPS: {len(amps_list)} processes {k} detected ({amps_list})")
                # Call the AMP update method
                thread = threading.Thread(target=v.update_wrapper, args=[amps_list])
                thread.start()
            else:
                # Set the process number to 0
                v.set_count(0)
                if v.count_min() is not None and v.count_min() > 0:
                    # Only display the "No running process message" if count_min is defined
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
                if (re.search(amp_value.regex(), p['name']) is not None) or (
                    p['cmdline'] is not None
                    and p['cmdline'] != []
                    and re.search(amp_value.regex(), ' '.join(p['cmdline'])) is not None
                ):
                    ret.append(
                        {'pid': p['pid'], 'cpu_percent': p['cpu_percent'], 'memory_percent': p['memory_percent']}
                    )

        except (TypeError, KeyError) as e:
            logger.debug(f"Can not build AMPS list ({e})")

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

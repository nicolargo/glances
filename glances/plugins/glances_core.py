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

"""CPU core plugin."""

from glances.plugins.glances_plugin import GlancesPlugin

import psutil


class Plugin(GlancesPlugin):

    """Glances CPU core plugin.

    Get stats about CPU core number.

    stats is integer (number of core)
    """

    def __init__(self, args=None):
        """Init the plugin."""
        GlancesPlugin.__init__(self, args=args)

        # We dot not want to display the stat in the curse interface
        # The core number is displayed by the load plugin
        self.display_curse = False

        # Init the stat
        self.reset()

    def reset(self):
        """Reset/init the stat using the input method."""
        self.stats = {}

    def update(self):
        """Update core stats.

        Stats is a dict (with both physical and log cpu number) instead of a integer.
        """
        # Reset the stats
        self.reset()

        if self.input_method == 'local':
            # Update stats using the standard system lib

            # The PSUtil 2.0 include psutil.cpu_count() and psutil.cpu_count(logical=False)
            # Return a dict with:
            # - phys: physical cores only (hyper thread CPUs are excluded)
            # - log: logical CPUs in the system
            # Return None if undefine
            try:
                self.stats["phys"] = psutil.cpu_count(logical=False)
                self.stats["log"] = psutil.cpu_count()
            except NameError:
                self.reset()

        elif self.input_method == 'snmp':
            # Update stats using SNMP
            # http://stackoverflow.com/questions/5662467/how-to-find-out-the-number-of-cpus-using-snmp
            pass

        return self.stats

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

# Import system libs
# Check for PSUtil already done in the glances_core script
from psutil import cpu_count

# Import Glances libs
from glances.plugins.glances_plugin import GlancesPlugin


class Plugin(GlancesPlugin):
    """
    Glances' Core Plugin
    Get stats about CPU core number

    stats is integer (number of core)
    """

    def __init__(self):
        GlancesPlugin.__init__(self)

        # We dot not want to display the stat in the curse interface
        # The core number is displayed by the load plugin
        self.display_curse = False

        # Return a dict (with both physical and log cpu number) instead of a integer
        self.stats = None

    def update(self):
        """
        Update core stats
        """

        # The PSUtil 2.0 include psutil.cpu_count() and psutil.cpu_count(logical=False)
        # Return a dict with:
        # - phys: physical cores only (hyper thread CPUs are excluded)
        # - log: logical CPUs in the system
        # Return None if undefine
        core_stats = {}
        try:
            core_stats["phys"] = cpu_count(logical=False)
            core_stats["log"] = cpu_count()
        except NameError:
            core_stats = None

        self.stats = core_stats

        return self.stats

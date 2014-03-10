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
from psutil import NUM_CPUS

# from ..plugins.glances_plugin import GlancesPlugin
from glances_plugin import GlancesPlugin


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

    def update(self):
        """
        Update core stats
        """

        # !!! Note: The PSUtil 2.0 include psutil.cpu_count() and psutil.cpu_count(logical=False)
        # !!! TODO: We had to return a dict (with both hys and log cpu number) instead of a integer
        try:
            self.stats = NUM_CPUS
        except Exception, e:
            self.stats = None

        return self.stats

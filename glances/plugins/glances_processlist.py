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

# !!! Not optimized because both processcount and processlist
# !!! grab all processes.
# !!! Action: create a new file globalprocesses.py with a global
# !!! variable instance of GlancesGrabProcesses classes and share
# !!! it between the two plugins

from psutil import process_iter, AccessDenied, NoSuchProcess

from glances.core.glances_globals import is_BSD, is_Mac, is_Windows
from glances.core.glances_timer import Timer
from glances_plugin import GlancesPlugin, getTimeSinceLastUpdate
from glances_processcount import GlancesGrabProcesses


class Plugin(GlancesPlugin):
    """
    Glances's processes Plugin

    stats is a list
    """

    def __init__(self):
        GlancesPlugin.__init__(self)

        # Init the process class
        self.glancesgrabprocesses = GlancesGrabProcesses()


    def update(self):
        """
        Update processes stats
        """

        self.glancesgrabprocesses.update()
        self.stats = self.glancesgrabprocesses.getlist()

        # processcount = self.glancesgrabprocesses.getcount()
        # process = self.glancesgrabprocesses.getlist()
        # if not hasattr(self, 'process'):
        #     self.processcount = {}
        #     self.process = []
        # else:
        #     self.processcount = processcount
        #     self.process = process


    def get_stats(self):
        # Return the stats object for the RPC API
        # Convert it to string
        return str(self.stats)

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

from psutil import disk_io_counters

from glances.core.glances_globals import is_Mac
from glances_plugin import GlancesPlugin, getTimeSinceLastUpdate

class Plugin(GlancesPlugin):
    """
    Glances's disks IO Plugin

    stats is a list
    """

    def __init__(self):
        GlancesPlugin.__init__(self)


    def update(self):
        """
        Update disk IO stats
        """

        self.diskio = []

        # Disk IO stat not available on Mac OS
        if is_Mac:
            self.stats = self.diskio
            return self.stats

        # By storing time data we enable Rx/s and Tx/s calculations in the
        # XML/RPC API, which would otherwise be overly difficult work
        # for users of the API
        time_since_update = getTimeSinceLastUpdate('disk')

        if not hasattr(self, 'diskio_old'):
            try:
                self.diskio_old = disk_io_counters(perdisk=True)
            except IOError:
                self.diskio_error_tag = True
        else:
            self.diskio_new = disk_io_counters(perdisk=True)
            for disk in self.diskio_new:
                try:
                    # Try necessary to manage dynamic disk creation/del
                    diskstat = {}
                    diskstat['time_since_update'] = time_since_update
                    diskstat['disk_name'] = disk
                    diskstat['read_bytes'] = (
                        self.diskio_new[disk].read_bytes -
                        self.diskio_old[disk].read_bytes)
                    diskstat['write_bytes'] = (
                        self.diskio_new[disk].write_bytes -
                        self.diskio_old[disk].write_bytes)
                except Exception:
                    continue
                else:
                    self.diskio.append(diskstat)
            self.diskio_old = self.diskio_new

        self.stats = self.diskio


    def get_stats(self):
        # Return the stats object for the RPC API
        # Sort it by disk name
        # Convert it to string
        return str(sorted(self.stats, key=lambda network: network['disk_name']))

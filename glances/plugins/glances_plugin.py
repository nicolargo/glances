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

from time import time

last_update_times = {}

def getTimeSinceLastUpdate(IOType):
    global last_update_times
    # assert(IOType in ['net', 'disk', 'process_disk'])
    current_time = time()
    last_time = last_update_times.get(IOType)
    if not last_time:
        time_since_update = 1
    else:
        time_since_update = current_time - last_time
    last_update_times[IOType] = current_time
    return time_since_update


class GlancesPlugin(object):
    """
    Main class for Glances' plugin
    """

    def __init__(self):
        # Init the stat list
        self.stats = None
    
    def __str__(self):
        # Return the human-readable stats
        return str(self.stats)

    def get_stats(self):
        # Return the stats object for the RPC API
        # Had to convert it to string
        return str(self.stats)

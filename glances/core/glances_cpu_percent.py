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

"""CPU percent stats shared between CPU and Quicklook plugins."""

from glances.core.glances_timer import Timer

import psutil


class CpuPercent(object):

    """Get and store the CPU percent."""

    def __init__(self, cached_time=1):
        self.cpu_percent = 0

        # cached_time is the minimum time interval between stats updates
        # since last update is passed (will retrieve old cached info instead)
        self.timer = Timer(0)
        self.cached_time = cached_time

    def get(self):
        """Update and/or return the CPU using the psutil library."""
        # Never update more than 1 time per cached_time
        if self.timer.finished():
            self.cpu_percent = psutil.cpu_percent(interval=0.0)
            self.timer = Timer(self.cached_time)
        return self.cpu_percent


# CpuPercent instance shared between plugins
cpu_percent = CpuPercent()

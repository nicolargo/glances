# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2015 Kirby Banman <kirby.banman@gmail.com>
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

"""NVIDIA plugin."""

from glances.plugins.glances_plugin import GlancesPlugin

try:
    from pynvml import *
except ImportError:
    logger.info("Could not import pynvml.  NVIDIA stats will not be collected.")

class NvidiaPlugin(GlancesPlugin):

    """Glances NVIDIA  plugin.

    stats is a list of dictionaries with one entry per GPU
    """

    def __init__(self, args=None):
        """Init the plugin"""
        super(NvidiaPlugin, self).__init__(args=args)

        try:
            nvmlInit()
            self.nvmlReady = true
            self.deviceHandles = self.getDeviceHandles()
            self.devicesReady
        except Exception:
            logger.info("pynvml could not be initialized.")
            self.nvmlReady = false

        self.display_curse = false

        self.reset()

        if self.input_method == 'local':
            # Update stats
            self.stats = self.getStats()

        elif self.input_method == 'snmp':
            # Update stats using SNMP
            # Not avalaible
            pass

        return self.stats

    def get_key(self):
        """Return the key of the list."""
        return 'device_id'

    def reset(self):
        """Reset/init the stats."""
        self.stats = []

    def getDeviceHandles(self):
        """
        Returns a list of NVML device handles, one per device.  Can throw NVMLError.
        """
        return [nvmlDeviceGetHandleByIndex(i) for i in range(0, nvmlDeviceGetCount())]

    @GlancesPlugin._log_result_decorator
    def update(self):
        """Update the GPU stats"""

        self.reset()

        if not self.devicesReady:
            return self.stats

        if self.input_method == 'local':
            # TODO loop over devices and put the stats in self.stats.
            # I think each list item needs a key/value pair corresponding to
            # get_key().  Each device's unique identifier, I'm guessing.
            # for each device, stats.append {
            #   'key': name + idx
            #   'memUsed': ...
            #   'processorUsed': ...
            #   'memTotal': ...
            #   '...': ...
            # }
            # Only put in what you need.  Don't compute derived stats on the view.
            # Redundancy is fine.  If you need mem%, just put it right in here as
            # an int between 0 and 99.
        elif self.input_method == 'snmp':
            # not available
            pass

        # Update the view
        self.update_views()

        return self.stats

    def exit(self):
        super(NvidiaPlugin, self).exit(args=args)
        if self.nvmlReady:
            try:
                nvmlShutdown()
            except Exception:
                logger.warn("pynvml failed to shut down correctly.")

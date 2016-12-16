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

from glances.logger import logger
from glances.plugins.glances_plugin import GlancesPlugin

try:
    from pynvml import *
except ImportError:
    logger.info("Could not import pynvml.  NVIDIA stats will not be collected.")


class Plugin(GlancesPlugin):

    """Glances NVIDIA  plugin.

    stats is a list of dictionaries with one entry per GPU
    """

    def __init__(self, args=None):
        """Init the plugin"""
        super(Plugin, self).__init__(args=args)

        try:
            nvmlInit()
            self.nvml_ready = True
            self.device_handles = self.get_device_handles()
            self.devices_ready
        except Exception:
            logger.info("pynvml could not be initialized.")
            self.nvml_ready = False

        self.display_curse = False

        self.reset()

        if self.input_method == 'local':
            # Update stats
            self.stats = self.get_stats()
        elif self.input_method == 'snmp':
            # Update stats using SNMP
            # Not avalaible
            pass

    def reset(self):
        """Reset/init the stats."""
        self.stats = []

    @GlancesPlugin._log_result_decorator
    def update(self):
        """Update the GPU stats"""

        self.reset()

        if not self.devices_ready:
            return self.stats

        if self.input_method == 'local':
            self.stats = self.get_stats()
        elif self.input_method == 'snmp':
            # not available
            pass

        # Update the view
        self.update_views()

        return self.stats

    def get_key(self):
        """Return the key of the list."""
        return 'gpu_id'

    def get_device_handles(self):
        """
        Returns a list of NVML device handles, one per device.  Can throw NVMLError.
        """
        return [nvmlDeviceGetHandleByIndex(i) for i in range(0, nvmlDeviceGetCount())]

    def get_stats(self):
        stats = []
        for index, device_handle in enumerate(self.device_handles):
            device_stats = {}
            device_stats['key'] = index
            device_stats['name'] = self.get_device_name(device_handle)
            device_stats['memory_percent'] = self.get_memory_percent(device_handle)
            device_stats['processor_percent'] = self.get_processor_percent(device_handle)

            stats.append(device_stats)

        return stats

    def get_device_name(self, device_handle):
        try:
            return nvmlDeviceGetName(device_handle)
        except NVMlError:
            return "NVIDIA GPU"

    def get_memory_percent(self, device_handle):
        try:
            return nvmlDeviceGetUtilizationRates(device_handle).memory
        except NVMLError:
            try:
                memory_info = nvmlDeviceGetMemoryInfo(device_handle)
                return memory_info.used * 100 / memory_info.total
            except NVMLError:
                return -1

    def get_processor_percent(self, device_handle):
        try:
            return nvmlDeviceGetUtilizationRates(device_handle).gpu
        except NVMLError:
            return -1

    def exit(self):
        super(NvidiaPlugin, self).exit(args=args)
        if self.nvml_ready:
            try:
                nvmlShutdown()
            except Exception:
                logger.warn("pynvml failed to shut down correctly.")

# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2016 Kirby Banman <kirby.banman@gmail.com>
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

"""GPU plugin (limited to NVIDIA chipsets)"""

from glances.logger import logger
from glances.plugins.glances_plugin import GlancesPlugin

try:
    import pynvml
except ImportError:
    logger.debug("Could not import pynvml.  NVIDIA stats will not be collected.")
    gpu_nvidia_tag = False
else:
    gpu_nvidia_tag = True


class Plugin(GlancesPlugin):

    """Glances GPU plugin (limited to NVIDIA chipsets).

    stats is a list of dictionaries with one entry per GPU
    """

    def __init__(self, args=None):
        """Init the plugin"""
        super(Plugin, self).__init__(args=args)

        # Init the NVidia API
        self.init_nvidia()

        # We want to display the stat in the curse interface
        # !!! TODO: Not implemented yeat
        self.display_curse = False

        # Init the stats
        self.reset()

    def reset(self):
        """Reset/init the stats."""
        self.stats = []

    def init_nvidia(self):
        """Init the NVIDIA API"""
        if not gpu_nvidia_tag:
            self.nvml_ready = False

        try:
            pynvml.nvmlInit()
            self.device_handles = self.get_device_handles()
            self.nvml_ready = True
        except Exception:
            logger.debug("pynvml could not be initialized.")
            self.nvml_ready = False

        return self.nvml_ready

    @GlancesPlugin._check_decorator
    @GlancesPlugin._log_result_decorator
    def update(self):
        """Update the GPU stats"""

        self.reset()

        if not self.nvml_ready:
            return self.stats

        if self.input_method == 'local':
            self.stats = self.get_device_stats()
        elif self.input_method == 'snmp':
            # not available
            pass

        # Update the view
        # self.update_views()

        return self.stats

    def get_key(self):
        """Return the key of the list."""
        return 'gpu_id'

    def get_device_handles(self):
        """
        Returns a list of NVML device handles, one per device.  Can throw NVMLError.
        """
        return [pynvml.nvmlDeviceGetHandleByIndex(i) for i in range(0, pynvml.nvmlDeviceGetCount())]

    def get_device_stats(self):
        """Get GPU stats"""
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
        """Get GPU device name"""
        try:
            return pynvml.nvmlDeviceGetName(device_handle)
        except pynvml.NVMlError:
            return "NVIDIA GPU"

    def get_memory_percent(self, device_handle):
        """Get GPU device memory consumption in percent"""
        try:
            return pynvml.nvmlDeviceGetUtilizationRates(device_handle).memory
        except pynvml.NVMLError:
            try:
                memory_info = pynvml.nvmlDeviceGetMemoryInfo(device_handle)
                return memory_info.used * 100 / memory_info.total
            except pynvml.NVMLError:
                return None

    def get_processor_percent(self, device_handle):
        """Get GPU device CPU consumption in percent"""
        try:
            return pynvml.nvmlDeviceGetUtilizationRates(device_handle).gpu
        except pynvml.NVMLError:
            return None

    def exit(self):
        """Overwrite the exit method to close the GPU API"""
        if self.nvml_ready:
            try:
                pynvml.nvmlShutdown()
            except Exception as e:
                logger.debug("pynvml failed to shutdown correctly ({})".format(e))

        # Call the father exit method
        super(Plugin, self).exit()

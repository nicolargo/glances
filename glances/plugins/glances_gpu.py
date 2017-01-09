# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2017 Kirby Banman <kirby.banman@gmail.com>
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
        self.display_curse = True

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

    def get_key(self):
        """Return the key of the list."""
        return 'gpu_id'

    @GlancesPlugin._check_decorator
    @GlancesPlugin._log_result_decorator
    def update(self):
        """Update the GPU stats"""

        self.reset()

        # !!! JUST FOR TEST
        # self.stats = [{"key": "gpu_id", "mem": None, "proc": 60, "gpu_id": 0, "name": "GeForce GTX 560 Ti"}]
        # self.stats = [{"key": "gpu_id", "mem": 10, "proc": 60, "gpu_id": 0, "name": "GeForce GTX 560 Ti"}]
        # self.stats = [{"key": "gpu_id", "mem": 48.64645, "proc": 60.73, "gpu_id": 0, "name": "GeForce GTX 560 Ti"},
        #               {"key": "gpu_id", "mem": 70.743, "proc": 80.28, "gpu_id": 1, "name": "GeForce GTX 560 Ti"},
        #               {"key": "gpu_id", "mem": 0, "proc": 0, "gpu_id": 2, "name": "GeForce GTX 560 Ti"}]
        # self.stats = [{"key": "gpu_id", "mem": 48.64645, "proc": 60.73, "gpu_id": 0, "name": "GeForce GTX 560 Ti"},
        #               {"key": "gpu_id", "mem": None, "proc": 80.28, "gpu_id": 1, "name": "GeForce GTX 560 Ti"},
        #               {"key": "gpu_id", "mem": 0, "proc": 0, "gpu_id": 2, "name": "ANOTHER GPU"}]
        # !!! TO BE COMMENTED

        if not self.nvml_ready:
            return self.stats

        if self.input_method == 'local':
            self.stats = self.get_device_stats()
        elif self.input_method == 'snmp':
            # not available
            pass

        return self.stats

    def update_views(self):
        """Update stats views."""
        # Call the father's method
        super(Plugin, self).update_views()

        # Add specifics informations
        # Alert
        for i in self.stats:
            # Init the views for the current GPU
            self.views[i[self.get_key()]] = {'proc': {}, 'mem': {}}
            # Processor alert
            if 'proc' in i:
                alert = self.get_alert(i['proc'], header='proc')
                self.views[i[self.get_key()]]['proc']['decoration'] = alert
            # Memory alert
            if 'mem' in i:
                alert = self.get_alert(i['mem'], header='mem')
                self.views[i[self.get_key()]]['mem']['decoration'] = alert

        return True

    def msg_curse(self, args=None):
        """Return the dict to display in the curse interface."""
        # Init the return message
        ret = []

        # Only process if stats exist, not empty (issue #871) and plugin not disabled
        if not self.stats or (self.stats == []) or self.is_disable():
            return ret

        # Check if all GPU have the same name
        same_name = all(s['name'] == self.stats[0]['name'] for s in self.stats)

        # gpu_stats contain the first GPU in the list
        gpu_stats = self.stats[0]

        # Header
        header = ''
        if len(self.stats) > 1:
            header += '{} '.format(len(self.stats))
        if same_name:
            header += '{} {}'.format('GPU', gpu_stats['name'])
        else:
            header += '{}'.format('GPU')
        msg = header[:17]
        ret.append(self.curse_add_line(msg, "TITLE"))

        # Build the string message
        if len(self.stats) == 1 or args.meangpu:
            # GPU stat summary or mono GPU
            # New line
            ret.append(self.curse_new_line())
            # GPU PROC
            try:
                mean_proc = sum(s['proc'] for s in self.stats if s is not None) / len(self.stats)
            except TypeError:
                mean_proc_msg = '{:>4}'.format('N/A')
            else:
                mean_proc_msg = '{:>3.0f}%'.format(mean_proc)
            if len(self.stats) > 1:
                msg = '{:13}'.format('proc mean:')
            else:
                msg = '{:13}'.format('proc:')
            ret.append(self.curse_add_line(msg))
            ret.append(self.curse_add_line(
                mean_proc_msg, self.get_views(item=gpu_stats[self.get_key()],
                                              key='proc',
                                              option='decoration')))
            # New line
            ret.append(self.curse_new_line())
            # GPU MEM
            try:
                mean_mem = sum(s['mem'] for s in self.stats if s is not None) / len(self.stats)
            except TypeError:
                mean_mem_msg = '{:>4}'.format('N/A')
            else:
                mean_mem_msg = '{:>3.0f}%'.format(mean_mem)
            if len(self.stats) > 1:
                msg = '{:13}'.format('mem mean:')
            else:
                msg = '{:13}'.format('mem:')
            ret.append(self.curse_add_line(msg))
            ret.append(self.curse_add_line(
                mean_mem_msg, self.get_views(item=gpu_stats[self.get_key()],
                                             key='mem',
                                             option='decoration')))
        else:
            # Multi GPU
            for gpu_stats in self.stats:
                # New line
                ret.append(self.curse_new_line())
                # GPU ID + PROC + MEM
                id_msg = '{}'.format(gpu_stats['gpu_id'])
                try:
                    proc_msg = '{:>3.0f}%'.format(gpu_stats['proc'])
                except ValueError:
                    proc_msg = '{:>4}'.format('N/A')
                try:
                    mem_msg = '{:>3.0f}%'.format(gpu_stats['mem'])
                except ValueError:
                    mem_msg = '{:>4}'.format('N/A')
                msg = '{}: {} mem: {}'.format(id_msg, proc_msg, mem_msg)
                ret.append(self.curse_add_line(msg))

        return ret

    def get_device_handles(self):
        """
        Returns a list of NVML device handles, one per device.  Can throw NVMLError.
        """
        return [pynvml.nvmlDeviceGetHandleByIndex(i) for i in range(pynvml.nvmlDeviceGetCount())]

    def get_device_stats(self):
        """Get GPU stats"""
        stats = []

        for index, device_handle in enumerate(self.device_handles):
            device_stats = {}
            # Dictionnary key is the GPU_ID
            device_stats['key'] = self.get_key()
            # GPU id (for multiple GPU, start at 0)
            device_stats['gpu_id'] = index
            # GPU name
            device_stats['name'] = self.get_device_name(device_handle)
            # Memory consumption in % (not available on all GPU)
            device_stats['mem'] = self.get_mem(device_handle)
            # Processor consumption in %
            device_stats['proc'] = self.get_proc(device_handle)
            stats.append(device_stats)

        return stats

    def get_device_name(self, device_handle):
        """Get GPU device name"""
        try:
            return pynvml.nvmlDeviceGetName(device_handle)
        except pynvml.NVMlError:
            return "NVIDIA"

    def get_mem(self, device_handle):
        """Get GPU device memory consumption in percent"""
        try:
            memory_info = pynvml.nvmlDeviceGetMemoryInfo(device_handle)
            return memory_info.used * 100.0 / memory_info.total
        except pynvml.NVMLError:
            return None

    def get_proc(self, device_handle):
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

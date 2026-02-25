#
# This file is part of Glances.
#
# Copyright (C) 2020 Kirby Banman <kirby.banman@gmail.com>
# Copyright (C) 2024 Nicolas Hennion <nicolashennion@gmail.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""GPU plugin for Glances.

Currently supported:
- NVIDIA GPU (need pynvml lib)
- AMD GPU (no lib needed)
- Intel GPU (no lib needed)

Quick test:
- Start Glances
- In a terminal: vblank_mode=0 glxgears
"""

from glances.globals import to_fahrenheit
from glances.logger import logger
from glances.plugins.gpu.cards.amd import AmdGPU
from glances.plugins.gpu.cards.intel import IntelGPU
from glances.plugins.gpu.cards.nvidia import NvidiaGPU
from glances.plugins.plugin.model import GlancesPluginModel

# Fields description
# description: human readable description
# short_name: shortname to use un UI
# unit: unit type
# rate: is it a rate ? If yes, // by time_since_update when displayed,
# min_symbol: Auto unit should be used if value > than 1 'X' (K, M, G)...
fields_description = {
    'gpu_id': {
        'description': 'GPU identification',
    },
    'name': {
        'description': 'GPU name',
    },
    'mem': {
        'description': 'Memory consumption',
        'unit': 'percent',
    },
    'proc': {
        'description': 'GPU processor consumption',
        'unit': 'percent',
    },
    'temperature': {
        'description': 'GPU temperature',
        'unit': 'celsius',
    },
    'fan_speed': {
        'description': 'GPU fan speed',
        'unit': 'roundperminute',
    },
}

# Define the history items list
# All items in this list will be historised if the --enable-history tag is set
items_history_list = [
    {'name': 'proc', 'description': 'GPU processor', 'y_unit': '%'},
    {'name': 'mem', 'description': 'Memory consumption', 'y_unit': '%'},
]


class GpuPlugin(GlancesPluginModel):
    """Glances GPU plugin.

    stats is a list of dictionaries with one entry per GPU
    """

    def __init__(self, args=None, config=None):
        """Init the plugin."""
        super().__init__(
            args=args,
            config=config,
            items_history_list=items_history_list,
            stats_init_value=[],
            fields_description=fields_description,
        )
        # Init the Nvidia GPU API
        try:
            self.nvidia = NvidiaGPU()
        except Exception as e:
            logger.debug(f'Nvidia GPU initialization error: {e}')
            self.nvidia = None

        # Init the AMD GPU API
        try:
            self.amd = AmdGPU()
        except Exception as e:
            logger.debug(f'AMD GPU initialization error: {e}')
            self.amd = None
        # Just for test purpose (uncomment to test on computer without AMD GPU)
        # self.amd = AmdGPU(drm_root_folder='./tests-data/plugins/gpu/amd/sys/class/drm')

        # Init the Intel GPU API
        try:
            self.intel = IntelGPU()
        except Exception as e:
            logger.debug(f'Intel GPU initialization error: {e}')
            self.intel = None
        # Just for test purpose (uncomment to test on computer without Intel GPU)
        # self.intel = IntelGPU(drm_root_folder='./tests-data/plugins/gpu/intel/sys/class/drm')

        # We want to display the stat in the curse interface
        self.display_curse = True

    def exit(self):
        """Overwrite the exit method to close the GPU API."""
        self.nvidia.exit()
        self.amd.exit()
        self.intel.exit()
        # Call the father exit method
        super().exit()

    def get_key(self):
        """Return the key of the list."""
        return 'gpu_id'

    @GlancesPluginModel._check_decorator
    @GlancesPluginModel._log_result_decorator
    def update(self):
        """Update the GPU stats."""
        # Init new stats
        stats = self.get_init_value()

        # Get the stats
        if self.nvidia:
            stats.extend(self.nvidia.get_device_stats())
        if self.amd:
            stats.extend(self.amd.get_device_stats())
        if self.intel:
            stats.extend(self.intel.get_device_stats())

        # !!!
        # Uncomment to test on computer without Nvidia GPU
        # One GPU sample:
        # stats = [
        #     {
        #         "key": "gpu_id",
        #         "gpu_id": "nvidia0",
        #         "name": "Fake GeForce GTX",
        #         "mem": 5.792331695556641,
        #         "proc": 4,
        #         "temperature": 26,
        #         "fan_speed": 30,
        #     }
        # ]
        # Two GPU sample:
        # stats = [
        #     {
        #         "key": "gpu_id",
        #         "gpu_id": "nvidia0",
        #         "name": "Fake GeForce GTX1",
        #         "mem": 5.792331695556641,
        #         "proc": 4,
        #         "temperature": 26,
        #         "fan_speed": 30,
        #     },
        #     {
        #         "key": "gpu_id",
        #         "gpu_id": "nvidia1",
        #         "name": "Fake GeForce GTX1",
        #         "mem": 15,
        #         "proc": 8,
        #         "temperature": 65,
        #         "fan_speed": 75,
        #     },
        # ]

        # Update the stats
        self.stats = stats

        return self.stats

    def update_views(self):
        """Update stats views."""
        # Call the father's method
        super().update_views()

        # Add specifics information
        # Alert
        for i in self.stats:
            # Init the views for the current GPU
            self.views[i[self.get_key()]] = {'proc': {}, 'mem': {}, 'temperature': {}}
            # Processor alert
            if 'proc' in i:
                alert = self.get_alert(i['proc'], header='proc')
                self.views[i[self.get_key()]]['proc']['decoration'] = alert
            # Memory alert
            if 'mem' in i:
                alert = self.get_alert(i['mem'], header='mem')
                self.views[i[self.get_key()]]['mem']['decoration'] = alert
            # Temperature alert
            if 'temperature' in i:
                alert = self.get_alert(i['temperature'], header='temperature')
                self.views[i[self.get_key()]]['temperature']['decoration'] = alert

        return True

    def _get_mean(self, key):
        """Calculate mean value for a given key across all GPU stats.

        Returns None if calculation fails (e.g., missing data).
        """
        try:
            return sum(s[key] for s in self.stats if s is not None) / len(self.stats)
        except (TypeError, ZeroDivisionError):
            return None

    def _format_value(self, value, unit='%'):
        """Format a value with unit, or return N/A if value is None."""
        if value is None:
            return '{:>4}'.format('N/A')
        return f'{value:>3.0f}{unit}'

    def _build_header(self):
        """Build the header string based on GPU count and names."""
        same_name = all(s['name'] == self.stats[0]['name'] for s in self.stats)
        gpu_name = self.stats[0]['name']
        gpu_count = len(self.stats)

        if gpu_count > 1:
            if same_name:
                header = f'{gpu_count} {gpu_name}'
            else:
                header = f'{gpu_count} GPUs'
        elif same_name:
            header = gpu_name
        else:
            header = 'GPU'
        return header[:17]

    def _add_metric_line(self, ret, key, label, label_mean, unit='%'):
        """Add a metric line (label + value) to the curse output.

        Args:
            ret: The return list to append to
            key: The metric key (e.g., 'proc', 'mem', 'temperature')
            label: Label for single GPU mode
            label_mean: Label for multi-GPU mean mode
            unit: Unit suffix for the value (default: '%')
        """
        gpu_stats = self.stats[0]
        is_multi = len(self.stats) > 1

        ret.append(self.curse_new_line())
        ret.append(self.curse_add_line(f'{label_mean if is_multi else label:13}'))
        mean_value = self._get_mean(key)
        ret.append(
            self.curse_add_line(
                self._format_value(mean_value, unit),
                self.get_views(item=gpu_stats[self.get_key()], key=key, option='decoration'),
            )
        )

    def _msg_curse_summary(self, ret, args):
        """Build curse output for summary view (single GPU or mean mode)."""
        self._add_metric_line(ret, 'proc', 'proc:', 'proc mean:')
        self._add_metric_line(ret, 'mem', 'mem:', 'mem mean:')

        # Temperature needs special handling for Fahrenheit conversion
        gpu_stats = self.stats[0]
        is_multi = len(self.stats) > 1
        ret.append(self.curse_new_line())
        ret.append(self.curse_add_line('{:13}'.format('temp mean:' if is_multi else 'temperature:')))
        mean_temp = self._get_mean('temperature')
        if mean_temp is not None and args and args.fahrenheit:
            mean_temp = to_fahrenheit(mean_temp)
        unit = 'F' if args and args.fahrenheit else 'C'
        ret.append(
            self.curse_add_line(
                self._format_value(mean_temp, unit),
                self.get_views(item=gpu_stats[self.get_key()], key='temperature', option='decoration'),
            )
        )

    def _msg_curse_multi(self, ret):
        """Build curse output for multi-GPU detailed view."""
        for gpu_stats in self.stats:
            ret.append(self.curse_new_line())
            # id_msg = '{:7}'.format(gpu_stats['gpu_id'])
            id_msg = '{:7}'.format(gpu_stats['name'][0:9])
            msg = f'{id_msg}'
            ret.append(self.curse_add_line(msg))
            if gpu_stats.get('proc') is not None:
                proc_msg = self._format_value(gpu_stats.get('proc'))
                msg = f' {proc_msg}'
                ret.append(
                    self.curse_add_line(
                        msg,
                        self.get_views(item=gpu_stats[self.get_key()], key='proc', option='decoration'),
                    )
                )
            if gpu_stats.get('mem') is not None:
                mem_msg = self._format_value(gpu_stats.get('mem'))
                msg += f' mem {mem_msg}'
                ret.append(
                    self.curse_add_line(
                        msg,
                        self.get_views(item=gpu_stats[self.get_key()], key='mem', option='decoration'),
                    )
                )

    def msg_curse(self, args=None, max_width=None):
        """Return the dict to display in the curse interface."""
        ret = []

        # Only process if stats exist, not empty (issue #871) and plugin not disabled
        if not self.stats or self.is_disabled():
            return ret

        # Header
        ret.append(self.curse_add_line(self._build_header(), "TITLE"))

        # Build the string message
        if len(self.stats) == 1 or args.meangpu:
            self._msg_curse_summary(ret, args)
        else:
            self._msg_curse_multi(ret)

        return ret

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
"""

from glances.globals import to_fahrenheit
from glances.plugins.gpu.cards.amd import AmdGPU
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


class PluginModel(GlancesPluginModel):
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
        # Init the GPU API
        self.nvidia = NvidiaGPU()
        self.amd = AmdGPU()
        # Just for test purpose (uncomment to test on computer without AMD GPU)
        # self.amd = AmdGPU(drm_root_folder='./test-data/plugins/gpu/amd/sys/class/drm')

        # We want to display the stat in the curse interface
        self.display_curse = True

    def exit(self):
        """Overwrite the exit method to close the GPU API."""
        self.nvidia.exit()
        self.amd.exit()

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
        stats.extend(self.nvidia.get_device_stats())
        stats.extend(self.amd.get_device_stats())

        # !!!
        # Uncomment to test on computer without GPU
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

    def msg_curse(self, args=None, max_width=None):
        """Return the dict to display in the curse interface."""
        # Init the return message
        ret = []

        # Only process if stats exist, not empty (issue #871) and plugin not disabled
        if not self.stats or (self.stats == []) or self.is_disabled():
            return ret

        # Check if all GPU have the same name
        same_name = all(s['name'] == self.stats[0]['name'] for s in self.stats)

        # gpu_stats contain the first GPU in the list
        gpu_stats = self.stats[0]

        # Header
        header = ''
        if len(self.stats) > 1:
            header += f'{len(self.stats)}'
            if same_name:
                header += ' {}'.format(gpu_stats['name'])
            else:
                header += ' GPUs'
        elif same_name:
            header += '{}'.format(gpu_stats['name'])
        else:
            header += 'GPU'
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
                mean_proc_msg = f'{mean_proc:>3.0f}%'
            if len(self.stats) > 1:
                msg = '{:13}'.format('proc mean:')
            else:
                msg = '{:13}'.format('proc:')
            ret.append(self.curse_add_line(msg))
            ret.append(
                self.curse_add_line(
                    mean_proc_msg, self.get_views(item=gpu_stats[self.get_key()], key='proc', option='decoration')
                )
            )
            # New line
            ret.append(self.curse_new_line())
            # GPU MEM
            try:
                mean_mem = sum(s['mem'] for s in self.stats if s is not None) / len(self.stats)
            except TypeError:
                mean_mem_msg = '{:>4}'.format('N/A')
            else:
                mean_mem_msg = f'{mean_mem:>3.0f}%'
            if len(self.stats) > 1:
                msg = '{:13}'.format('mem mean:')
            else:
                msg = '{:13}'.format('mem:')
            ret.append(self.curse_add_line(msg))
            ret.append(
                self.curse_add_line(
                    mean_mem_msg, self.get_views(item=gpu_stats[self.get_key()], key='mem', option='decoration')
                )
            )
            # New line
            ret.append(self.curse_new_line())
            # GPU TEMPERATURE
            try:
                mean_temperature = sum(s['temperature'] for s in self.stats if s is not None) / len(self.stats)
            except TypeError:
                mean_temperature_msg = '{:>4}'.format('N/A')
            else:
                unit = 'C'
                if args.fahrenheit:
                    mean_temperature = to_fahrenheit(mean_temperature)
                    unit = 'F'
                mean_temperature_msg = f'{mean_temperature:>3.0f}{unit}'
            if len(self.stats) > 1:
                msg = '{:13}'.format('temp mean:')
            else:
                msg = '{:13}'.format('temperature:')
            ret.append(self.curse_add_line(msg))
            ret.append(
                self.curse_add_line(
                    mean_temperature_msg,
                    self.get_views(item=gpu_stats[self.get_key()], key='temperature', option='decoration'),
                )
            )
        else:
            # Multi GPU
            # Temperature is not displayed in this mode...
            for gpu_stats in self.stats:
                # New line
                ret.append(self.curse_new_line())
                # GPU ID + PROC + MEM + TEMPERATURE
                id_msg = '{:>7}'.format(gpu_stats['gpu_id'])
                try:
                    proc_msg = '{:>3.0f}%'.format(gpu_stats['proc'])
                except (ValueError, TypeError):
                    proc_msg = '{:>4}'.format('N/A')
                try:
                    mem_msg = '{:>3.0f}%'.format(gpu_stats['mem'])
                except (ValueError, TypeError):
                    mem_msg = '{:>4}'.format('N/A')
                msg = f'{id_msg} {proc_msg} mem {mem_msg}'
                ret.append(self.curse_add_line(msg))

        return ret

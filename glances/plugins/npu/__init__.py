#
# This file is part of Glances.
#
# Copyright (C) 2026 Nicolas Hennion <nicolashennion@gmail.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""NPU plugin for Glances.

Currently supported:
- AMD NPU (Ryzen AI - Phoenix, Hawk Point, Strix Point)
- Intel NPU (Meteor Lake, Lunar Lake, Arrow Lake)
- Rockchip NPU (RK3588, RK3576)
"""

from glances.logger import logger
from glances.plugins.npu.cards.amd import AmdNPU
from glances.plugins.npu.cards.intel import IntelNPU
from glances.plugins.npu.cards.rockchip import RockchipNPU
from glances.plugins.plugin.model import GlancesPluginModel

# Fields description
# description: human readable description
# short_name: shortname to use un UI
# unit: unit type
# rate: is it a rate ? If yes, // by time_since_update when displayed,
# min_symbol: Auto unit should be used if value > than 1 'X' (K, M, G)...
fields_description = {
    'npu_id': {
        'description': 'NPU identification',
    },
    'name': {
        'description': 'NPU name',
    },
    'load': {
        'description': 'NPU load',
        'unit': 'percent',
    },
    'freq': {
        'description': 'NPU frequency',
        'unit': 'percent',
    },
    'freq_current': {
        'description': 'NPU current frequency',
        'unit': 'hertz',
    },
    'freq_max': {
        'description': 'NPU maximum frequency',
        'unit': 'hertz',
    },
    'mem': {
        'description': 'Memory consumption',
        'unit': 'percent',
    },
    'memory_used': {
        'description': 'Memory used',
        'unit': 'byte',
    },
    'memory_total': {
        'description': 'Memory total',
        'unit': 'byte',
    },
    'temperature': {
        'description': 'NPU temperature',
        'unit': 'celsius',
    },
    'power': {
        'description': 'NPU power consumption',
        'unit': 'watt',
    },
}

# Define the history items list
# All items in this list will be historised if the --enable-history tag is set
items_history_list = [
    {'name': 'freq', 'description': 'NPU processor frequency', 'y_unit': '%'},
    {'name': 'load', 'description': 'NPU processor load', 'y_unit': '%'},
    {'name': 'mem', 'description': 'Memory consumption', 'y_unit': '%'},
]


class NpuPlugin(GlancesPluginModel):
    """Glances NPU plugin.

    stats is a list of dictionaries with one entry per NPU
    """

    def __init__(
        self,
        args=None,
        config=None,
        amd_npu_root_folder: str = '/',
        intel_npu_root_folder: str = '/',
        rockchip_npu_root_folder: str = '/',
    ):
        """Init the plugin."""
        super().__init__(
            args=args,
            config=config,
            items_history_list=items_history_list,
            stats_init_value=[],
            fields_description=fields_description,
        )

        # Init the AMD NPU
        # Just for test purpose (uncomment to test on computer without AMD NPU)
        # amd_npu_root_folder = './tests-data/plugins/npu/amd'
        self.amd = AmdNPU(npu_root_folder=amd_npu_root_folder)

        # Init the Intel NPU
        # Just for test purpose (uncomment to test on computer without Intel NPU)
        # intel_npu_root_folder = './tests-data/plugins/npu/intel'
        self.intel = IntelNPU(npu_root_folder=intel_npu_root_folder)

        # Init the Rockchip NPU
        # Just for test purpose (uncomment to test on computer without Rockchip NPU)
        # rockchip_npu_root_folder = './tests-data/plugins/npu/rockchip'
        self.rockchip = RockchipNPU(npu_root_folder=rockchip_npu_root_folder)

        # We want to display the stat in the curse interface
        self.display_curse = True

    def exit(self):
        """Overwrite the exit method to close the NPU API."""
        self.amd.exit()
        self.intel.exit()
        self.rockchip.exit()

        # Call the father exit method
        super().exit()

    def get_key(self):
        """Return the key of the list."""
        return 'npu_id'

    @GlancesPluginModel._check_decorator
    @GlancesPluginModel._log_result_decorator
    def update(self):
        """Update the NPU stats."""
        # Init new stats
        stats = self.get_init_value()

        # Get the stats
        if self.amd.is_available():
            try:
                stats.append(self.amd.get_device_stats())
            except Exception as e:
                logger.debug(f"Error getting AMD NPU stats, disable AMD NPU: {e}")
                self.amd.disable()
        if self.intel.is_available():
            try:
                stats.append(self.intel.get_device_stats())
            except Exception as e:
                logger.debug(f"Error getting Intel NPU stats, disable Intel NPU: {e}")
                self.intel.disable()
        if self.rockchip.is_available():
            try:
                stats.append(self.rockchip.get_device_stats())
            except Exception as e:
                logger.debug(f"Error getting Rockchip NPU stats, disable Rockchip NPU: {e}")
                self.rockchip.disable()

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
            self.views[i[self.get_key()]] = {'load': {}, 'freq': {}, 'mem': {}}
            # Load alert
            if 'load' in i:
                alert = self.get_alert(i['load'], header='load')
                self.views[i[self.get_key()]]['load']['decoration'] = alert
            # Frequency alert
            if 'freq' in i:
                alert = self.get_alert(i['freq'], header='freq')
                self.views[i[self.get_key()]]['freq']['decoration'] = alert
            # Memory alert
            if 'mem' in i:
                alert = self.get_alert(i['mem'], header='mem')
                self.views[i[self.get_key()]]['mem']['decoration'] = alert

        return True

    def _format_value(self, value, unit='%'):
        """Format a value with unit, or return N/A if value is None."""
        if value is None:
            return '{:>5}'.format('N/A')
        return f'{value:>4.0f}{unit}'

    def msg_curse(self, args=None, max_width=None):
        """Return the dict to display in the curse interface."""
        ret = []

        # Only process if stats exist, not empty and plugin not disabled
        if not self.stats or self.is_disabled():
            return ret

        # First name is NPU name (limited to 15 characters)
        ret.append(self.curse_add_line(self.stats[0]['name'][:17], 'TITLE'))

        # Second line is load (or frequency) percent and frequency limit
        ret.append(self.curse_new_line())
        if self.stats[0]['load'] is not None:
            msg = '{:<3.0%}'.format(self.stats[0]['load'] / 100)
            ret.append(
                self.curse_add_line(
                    msg, self.get_views(key='load', item=self.stats[0][self.get_key()], option='decoration')
                )
            )
        else:
            msg = '{:<3.0%}'.format(self.stats[0]['freq'] / 100)
            ret.append(
                self.curse_add_line(
                    msg, self.get_views(key='freq', item=self.stats[0][self.get_key()], option='decoration')
                )
            )
        freq = '{}/{}Hz'.format(
            self.auto_unit(self.stats[0]['freq_current']), self.auto_unit(self.stats[0]['freq_max'])
        )
        msg = f'{freq:>14}'
        ret.append(self.curse_add_line(msg, 'DEFAULT'))

        # Third line is memory
        # Note: for the moment not available
        ret.append(self.curse_new_line())
        ret.append(self.curse_add_line('{:<12}'.format('mem:')))
        msg = self._format_value(self.stats[0]['mem'], unit='%')
        ret.append(
            self.curse_add_line(msg, self.get_views(key='mem', item=self.stats[0][self.get_key()], option='mem'))
        )

        # Fourth line is temperature
        # Note: for the moment only available for INTEL NPU
        ret.append(self.curse_new_line())
        ret.append(self.curse_add_line('{:<12}'.format('temperature:')))
        msg = self._format_value(self.stats[0]['temperature'], unit='C')
        ret.append(
            self.curse_add_line(
                msg, self.get_views(key='temperature', item=self.stats[0][self.get_key()], option='decoration')
            )
        )

        return ret

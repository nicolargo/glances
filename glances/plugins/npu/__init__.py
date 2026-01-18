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
    'freq': {
        'description': 'NPU frequency',
        'unit': 'percent',
    },
    'load': {
        'description': 'NPU load',
        'unit': 'percent',
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
    {'name': 'proc', 'description': 'NPU processor', 'y_unit': '%'},
    {'name': 'mem', 'description': 'Memory consumption', 'y_unit': '%'},
]


class NpuPlugin(GlancesPluginModel):
    """Glances NPU plugin.

    stats is a list of dictionaries with one entry per NPU
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

        # Init the AMD NPU
        # Just for test purpose (uncomment to test on computer without AMD NPU)
        # self.amd = AmdNPU(npu_root_folder='./tests-data/plugins/npu/amd')
        self.amd = AmdNPU()

        # Init the Intel NPU
        # Just for test purpose (uncomment to test on computer without Intel NPU)
        # self.intel = IntelNPU(npu_root_folder='./tests-data/plugins/npu/intel')
        self.intel = IntelNPU()

        # Init the Rockchip NPU
        # Just for test purpose (uncomment to test on computer without Rockchip NPU)
        # self.rockchip = RockchipNPU(npu_root_folder='./tests-data/plugins/npu/rockchip')
        self.rockchip = RockchipNPU()

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
            stats.append(self.amd.get_device_stats())
        if self.intel.is_available():
            stats.append(self.intel.get_device_stats())
        if self.rockchip.is_available():
            stats.append(self.rockchip.get_device_stats())
        # Update the stats
        self.stats = stats

        return self.stats

    def update_views(self):
        """Update stats views."""
        # Call the father's method
        super().update_views()

        return True

    def msg_curse(self, args=None, max_width=None):
        """Return the dict to display in the curse interface."""
        ret = []

        # Only process if stats exist, not empty (issue #871) and plugin not disabled
        if not self.stats or self.is_disabled():
            return ret

        # Header
        # Build the string message

        return ret

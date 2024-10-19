#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Quicklook plugin."""

import psutil

from glances.cpu_percent import cpu_percent
from glances.logger import logger
from glances.outputs.glances_bars import Bar
from glances.outputs.glances_sparklines import Sparkline
from glances.plugins.load import get_load_average, get_nb_log_core, get_nb_phys_core
from glances.plugins.plugin.model import GlancesPluginModel

# Fields description
# description: human readable description
# short_name: shortname to use un UI
# unit: unit type
# rate: is it a rate ? If yes, // by time_since_update when displayed,
# min_symbol: Auto unit should be used if value > than 1 'X' (K, M, G)...
fields_description = {
    'cpu': {
        'description': 'CPU percent usage',
        'unit': 'percent',
    },
    'mem': {
        'description': 'MEM percent usage',
        'unit': 'percent',
    },
    'swap': {
        'description': 'SWAP percent usage',
        'unit': 'percent',
    },
    'load': {
        'description': 'LOAD percent usage',
        'unit': 'percent',
    },
    'cpu_log_core': {
        'description': 'Number of logical CPU core',
        'unit': 'number',
    },
    'cpu_phys_core': {
        'description': 'Number of physical CPU core',
        'unit': 'number',
    },
    'cpu_name': {
        'description': 'CPU name',
    },
    'cpu_hz_current': {
        'description': 'CPU current frequency',
        'unit': 'hertz',
    },
    'cpu_hz': {
        'description': 'CPU max frequency',
        'unit': 'hertz',
    },
}

# Define the history items list
# All items in this list will be historised if the --enable-history tag is set
items_history_list = [
    {'name': 'cpu', 'description': 'CPU percent usage', 'y_unit': '%'},
    {'name': 'percpu', 'description': 'PERCPU percent usage', 'y_unit': '%'},
    {'name': 'mem', 'description': 'MEM percent usage', 'y_unit': '%'},
    {'name': 'swap', 'description': 'SWAP percent usage', 'y_unit': '%'},
    {'name': 'load', 'description': 'LOAD percent usage', 'y_unit': '%'},
]


class PluginModel(GlancesPluginModel):
    """Glances quicklook plugin.

    'stats' is a dictionary.
    """

    AVAILABLE_STATS_LIST = ['cpu', 'mem', 'swap', 'load']
    DEFAULT_STATS_LIST = ['cpu', 'mem', 'load']

    def __init__(self, args=None, config=None):
        """Init the quicklook plugin."""
        super().__init__(
            args=args, config=config, items_history_list=items_history_list, fields_description=fields_description
        )

        # We want to display the stat in the curse interface
        self.display_curse = True

        # Manage the maximum number of CPU to display (related to enhancement request #2734)
        self.max_cpu_display = config.get_int_value('percpu', 'max_cpu_display', 4) if config else 4

        # Define the stats list
        self.stats_list = self.get_conf_value('list', default=self.DEFAULT_STATS_LIST)
        if not set(self.stats_list).issubset(self.AVAILABLE_STATS_LIST):
            logger.warning(f'Quicklook plugin: Invalid stats list: {self.stats_list}')
            self.stats_list = self.AVAILABLE_STATS_LIST

    @GlancesPluginModel._check_decorator
    @GlancesPluginModel._log_result_decorator
    def update(self):
        """Update quicklook stats using the input method."""
        # Init new stats
        stats = self.get_init_value()

        # Grab quicklook stats: CPU, MEM and SWAP
        if self.input_method == 'local':
            # Get system information
            cpu_info = cpu_percent.get_info()
            stats['cpu_name'] = cpu_info['cpu_name']
            stats['cpu_hz_current'] = (
                self._mhz_to_hz(cpu_info['cpu_hz_current']) if cpu_info['cpu_hz_current'] is not None else None
            )
            stats['cpu_hz'] = self._mhz_to_hz(cpu_info['cpu_hz']) if cpu_info['cpu_hz'] is not None else None

            # Get the CPU percent value (global and per core)
            # Stats is shared across all plugins
            stats['cpu'] = cpu_percent.get_cpu()
            stats['percpu'] = cpu_percent.get_percpu()

            # Get the virtual and swap memory
            stats['mem'] = psutil.virtual_memory().percent
            try:
                stats['swap'] = psutil.swap_memory().percent
            except RuntimeError:
                # Correct issue in Illumos OS (see #1767)
                stats['swap'] = None

            # Get load
            stats['cpu_log_core'] = get_nb_log_core()
            stats['cpu_phys_core'] = get_nb_phys_core()
            try:
                # Load average is a tuple (1 min, 5 min, 15 min)
                # Process only the 15 min value (index 2)
                stats['load'] = get_load_average(percent=True)[2]
            except (TypeError, IndexError):
                stats['load'] = None

        elif self.input_method == 'snmp':
            # Not available
            pass

        # Update the stats
        self.stats = stats

        return self.stats

    def update_views(self):
        """Update stats views."""
        # Call the father's method
        super().update_views()

        # Alert for CPU, MEM and SWAP
        for key in self.stats_list:
            if key in self.stats:
                self.views[key]['decoration'] = self.get_alert(self.stats[key], header=key)

        # Alert for LOAD
        if 'load' in self.stats:
            self.views['load']['decoration'] = self.get_alert(self.stats['load'], header='load')

        # Define the list of stats to display
        self.views['list'] = self.stats_list

    def msg_curse(self, args=None, max_width=10):
        """Return the list to display in the UI."""
        # Init the return message
        ret = []

        # Only process if stats exist...
        if not self.stats or self.is_disabled():
            return ret

        if not max_width:
            # No max_width defined, return an empty message
            logger.debug(f"No max_width defined for the {self.plugin_name} plugin, it will not be displayed.")
            return ret

        # Define the data: Bar (default behavior) or Sparkline
        data = {}
        for key in self.stats_list:
            if self.args.sparkline and self.history_enable() and not self.args.client:
                data[key] = Sparkline(max_width)
            else:
                # Fallback to bar if Sparkline module is not installed
                data[key] = Bar(max_width, bar_char=self.get_conf_value('bar_char', default=['|'])[0])

        # Build the string message
        ##########################

        # System information
        if (
            'cpu_hz_current' in self.stats
            and self.stats['cpu_hz_current'] is not None
            and 'cpu_hz' in self.stats
            and self.stats['cpu_hz'] is not None
        ):
            msg_freq = ' {:.2f}/{:.2f}GHz'.format(
                self._hz_to_ghz(self.stats['cpu_hz_current']), self._hz_to_ghz(self.stats['cpu_hz'])
            )
        else:
            msg_freq = ''

        if 'cpu_name' in self.stats and (max_width - len(msg_freq) + 7) > 0:
            msg_name = '{:{width}}'.format(self.stats['cpu_name'], width=max_width - len(msg_freq) + 7)
        else:
            msg_name = '' if msg_freq == '' else 'Frequency'

        ret.append(self.curse_add_line(msg_name))
        ret.append(self.curse_add_line(msg_freq))
        ret.append(self.curse_new_line())

        # Loop over CPU, MEM and LOAD
        for key in self.stats_list:
            if key == 'cpu' and args.percpu:
                ret.extend(self._msg_per_cpu(data, key, max_width))
            else:
                if type(data[key]).__name__ == 'Sparkline':
                    # Sparkline display an history
                    data[key].percents = [i[1] for i in self.get_raw_history(item=key, nb=data[key].size)]
                    # A simple padding in order to align metrics to the right
                    data[key].percents += [None] * (data[key].size - len(data[key].percents))
                else:
                    # Bar only the last value
                    data[key].percent = self.stats[key]
                msg = f'{key.upper():4} '
                ret.extend(self._msg_create_line(msg, data[key], key))
                ret.append(self.curse_new_line())

        # Remove the last new line
        ret.pop()

        # Return the message with decoration
        return ret

    def _msg_per_cpu(self, data, key, max_width):
        """Create per-cpu view"""
        ret = []

        # Get history (only used with the sparkline option)
        if type(data[key]).__name__ == 'Sparkline':
            raw_cpu = self.get_raw_history(item='percpu', nb=data[key].size)

        # Manage the maximum number of CPU to display (related to enhancement request #2734)
        if len(self.stats['percpu']) > self.max_cpu_display:
            # If the number of CPU is > max_cpu_display then sort and display top 'n'
            percpu_list = sorted(self.stats['percpu'], key=lambda x: x['total'], reverse=True)
        else:
            percpu_list = self.stats['percpu']

        # Display the first max_cpu_display CPU
        for cpu in percpu_list[0 : self.max_cpu_display]:
            cpu_id = cpu[cpu['key']]
            if type(data[key]).__name__ == 'Sparkline':
                # Sparkline display an history
                data[key].percents = [i[1][cpu_id]['total'] for i in raw_cpu]
                # A simple padding in order to align metrics to the right
                data[key].percents += [None] * (data[key].size - len(data[key].percents))
            else:
                # Bar will only display the last value
                data[key].percent = cpu['total']
            if cpu_id < 10:
                msg = f'{key.upper():3}{cpu_id} '
            else:
                msg = f'{cpu_id:4} '
            ret.extend(self._msg_create_line(msg, data[key], key))
            ret.append(self.curse_new_line())

        # Add a new line with sum of all others CPU
        if len(self.stats['percpu']) > self.max_cpu_display:
            if type(data[key]).__name__ == 'Sparkline':
                sum_other = Sparkline(max_width)
                # Sparkline display an history
                sum_other.percents = [
                    sum([i['total'] for i in r[1] if i[i['key']] >= self.max_cpu_display])
                    / len([i['total'] for i in r[1] if i[i['key']] >= self.max_cpu_display])
                    for r in raw_cpu
                ]
                # A simple padding in order to align metrics to the right
                sum_other.percents += [None] * (sum_other.size - len(sum_other.percents))
            else:
                # Bar will only display the last value
                sum_other = Bar(max_width, bar_char=self.get_conf_value('bar_char', default=['|'])[0])
                sum_other.percent = sum([i['total'] for i in percpu_list[self.max_cpu_display :]]) / len(
                    percpu_list[self.max_cpu_display :]
                )
            msg = msg = f'{key.upper():3}* '
            ret.extend(self._msg_create_line(msg, sum_other, key))
            ret.append(self.curse_new_line())

        return ret

    def _msg_create_line(self, msg, data, key):
        """Create a new line to the Quick view."""
        return [
            self.curse_add_line(msg),
            self.curse_add_line(data.pre_char, decoration='BOLD'),
            self.curse_add_line(data.get(), self.get_views(key=key, option='decoration')),
            self.curse_add_line(data.post_char, decoration='BOLD'),
            self.curse_add_line('  '),
        ]

    def _hz_to_ghz(self, hz):
        """Convert Hz to Ghz."""
        return hz / 1000000000.0

    def _mhz_to_hz(self, hz):
        """Convert Mhz to Hz."""
        return hz * 1000000.0

# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Quicklook plugin."""

from glances.cpu_percent import cpu_percent
from glances.outputs.glances_bars import Bar
from glances.outputs.glances_sparklines import Sparkline
from glances.plugins.plugin.model import GlancesPluginModel

import psutil


# Define the history items list
# All items in this list will be historised if the --enable-history tag is set
items_history_list = [
    {'name': 'cpu', 'description': 'CPU percent usage', 'y_unit': '%'},
    {'name': 'percpu', 'description': 'PERCPU percent usage', 'y_unit': '%'},
    {'name': 'mem', 'description': 'MEM percent usage', 'y_unit': '%'},
    {'name': 'swap', 'description': 'SWAP percent usage', 'y_unit': '%'},
]


class PluginModel(GlancesPluginModel):
    """Glances quicklook plugin.

    'stats' is a dictionary.
    """

    def __init__(self, args=None, config=None):
        """Init the quicklook plugin."""
        super(PluginModel, self).__init__(args=args, config=config, items_history_list=items_history_list)
        # We want to display the stat in the curse interface
        self.display_curse = True

    @GlancesPluginModel._check_decorator
    @GlancesPluginModel._log_result_decorator
    def update(self):
        """Update quicklook stats using the input method."""
        # Init new stats
        stats = self.get_init_value()

        # Grab quicklook stats: CPU, MEM and SWAP
        if self.input_method == 'local':
            # Get the latest CPU percent value
            stats['cpu'] = cpu_percent.get()
            stats['percpu'] = cpu_percent.get(percpu=True)

            # Use the psutil lib for the memory (virtual and swap)
            stats['mem'] = psutil.virtual_memory().percent
            try:
                stats['swap'] = psutil.swap_memory().percent
            except RuntimeError:
                # Correct issue in Illumos OS (see #1767)
                stats['swap'] = None

            # Get additional information
            cpu_info = cpu_percent.get_info()
            stats['cpu_name'] = cpu_info['cpu_name']
            stats['cpu_hz_current'] = (
                self._mhz_to_hz(cpu_info['cpu_hz_current']) if cpu_info['cpu_hz_current'] is not None else None
            )
            stats['cpu_hz'] = self._mhz_to_hz(cpu_info['cpu_hz']) if cpu_info['cpu_hz'] is not None else None

        elif self.input_method == 'snmp':
            # Not available
            pass

        # Update the stats
        self.stats = stats

        return self.stats

    def update_views(self):
        """Update stats views."""
        # Call the father's method
        super(PluginModel, self).update_views()

        # Add specifics information
        # Alert only
        for key in ['cpu', 'mem', 'swap']:
            if key in self.stats:
                self.views[key]['decoration'] = self.get_alert(self.stats[key], header=key)

    def msg_curse(self, args=None, max_width=10):
        """Return the list to display in the UI."""
        # Init the return message
        ret = []

        # Only process if stats exist...
        if not self.stats or self.is_disabled():
            return ret

        # Define the data: Bar (default behavior) or Sparkline
        sparkline_tag = False
        if self.args.sparkline and self.history_enable() and not self.args.client:
            data = Sparkline(max_width)
            sparkline_tag = data.available
        if not sparkline_tag:
            # Fallback to bar if Sparkline module is not installed
            data = Bar(max_width, percentage_char=self.get_conf_value('percentage_char', default=['|'])[0])

        # Build the string message
        if 'cpu_name' in self.stats and 'cpu_hz_current' in self.stats and 'cpu_hz' in self.stats:
            msg_name = self.stats['cpu_name']
            if self.stats['cpu_hz_current'] and self.stats['cpu_hz']:
                msg_freq = ' - {:.2f}/{:.2f}GHz'.format(
                    self._hz_to_ghz(self.stats['cpu_hz_current']), self._hz_to_ghz(self.stats['cpu_hz'])
                )
            else:
                msg_freq = ''
            if len(msg_name + msg_freq) - 6 <= max_width:
                ret.append(self.curse_add_line(msg_name))
            ret.append(self.curse_add_line(msg_freq))
            ret.append(self.curse_new_line())
        for key in ['cpu', 'mem', 'swap']:
            if key == 'cpu' and args.percpu:
                if sparkline_tag:
                    raw_cpu = self.get_raw_history(item='percpu', nb=data.size)
                for cpu_index, cpu in enumerate(self.stats['percpu']):
                    if sparkline_tag:
                        # Sparkline display an history
                        data.percents = [i[1][cpu_index]['total'] for i in raw_cpu]
                        # A simple padding in order to align metrics to the right
                        data.percents += [None] * (data.size - len(data.percents))
                    else:
                        # Bar only the last value
                        data.percent = cpu['total']
                    if cpu[cpu['key']] < 10:
                        msg = '{:3}{} '.format(key.upper(), cpu['cpu_number'])
                    else:
                        msg = '{:4} '.format(cpu['cpu_number'])
                    ret.extend(self._msg_create_line(msg, data, key))
                    ret.append(self.curse_new_line())
            else:
                if sparkline_tag:
                    # Sparkline display an history
                    data.percents = [i[1] for i in self.get_raw_history(item=key, nb=data.size)]
                    # A simple padding in order to align metrics to the right
                    data.percents += [None] * (data.size - len(data.percents))
                else:
                    # Bar only the last value
                    data.percent = self.stats[key]
                msg = '{:4} '.format(key.upper())
                ret.extend(self._msg_create_line(msg, data, key))
                ret.append(self.curse_new_line())

        # Remove the last new line
        ret.pop()

        # Return the message with decoration
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

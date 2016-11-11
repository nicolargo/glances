# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2015 Nicolargo <nicolas@nicolargo.com>
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

"""Quicklook plugin."""

from glances.cpu_percent import cpu_percent
from glances.outputs.glances_bars import Bar
from glances.plugins.glances_plugin import GlancesPlugin

import psutil

cpuinfo_tag = False
try:
    from cpuinfo import cpuinfo
except:
    # Correct issue #754
    # Waiting for a correction on the upstream Cpuinfo lib
    pass
else:
    cpuinfo_tag = True


class Plugin(GlancesPlugin):

    """Glances quicklook plugin.

    'stats' is a dictionary.
    """

    def __init__(self, args=None):
        """Init the quicklook plugin."""
        super(Plugin, self).__init__(args=args)

        # We want to display the stat in the curse interface
        self.display_curse = True

        # Init stats
        self.reset()

    def reset(self):
        """Reset/init the stats."""
        self.stats = {}

    @GlancesPlugin._check_decorator
    @GlancesPlugin._log_result_decorator
    def update(self):
        """Update quicklook stats using the input method."""
        # Reset stats
        self.reset()

        # Grab quicklook stats: CPU, MEM and SWAP
        if self.input_method == 'local':
            # Get the latest CPU percent value
            self.stats['cpu'] = cpu_percent.get()
            self.stats['percpu'] = cpu_percent.get(percpu=True)
            # Use the PsUtil lib for the memory (virtual and swap)
            self.stats['mem'] = psutil.virtual_memory().percent
            self.stats['swap'] = psutil.swap_memory().percent
        elif self.input_method == 'snmp':
            # Not available
            pass

        # Optionnaly, get the CPU name/frequency
        # thanks to the cpuinfo lib: https://github.com/workhorsy/py-cpuinfo
        if cpuinfo_tag:
            cpu_info = cpuinfo.get_cpu_info()
            #  Check cpu_info (issue #881)
            if cpu_info is not None:
                self.stats['cpu_name'] = cpu_info['brand']
                self.stats['cpu_hz_current'] = cpu_info['hz_actual_raw'][0]
                self.stats['cpu_hz'] = cpu_info['hz_advertised_raw'][0]

        return self.stats

    def update_views(self):
        """Update stats views."""
        # Call the father's method
        super(Plugin, self).update_views()

        # Add specifics informations
        # Alert only
        for key in ['cpu', 'mem', 'swap']:
            if key in self.stats:
                self.views[key]['decoration'] = self.get_alert(self.stats[key], header=key)

    def msg_curse(self, args=None, max_width=10):
        """Return the list to display in the UI."""
        # Init the return message
        ret = []

        # Only process if stats exist...
        if not self.stats or self.is_disable():
            return ret

        # Define the bar
        bar = Bar(max_width)

        # Build the string message
        if 'cpu_name' in self.stats and 'cpu_hz_current' in self.stats and 'cpu_hz' in self.stats:
            msg_name = '{} - '.format(self.stats['cpu_name'])
            msg_freq = '{:.2f}/{:.2f}GHz'.format(self._hz_to_ghz(self.stats['cpu_hz_current']),
                                                 self._hz_to_ghz(self.stats['cpu_hz']))
            if len(msg_name + msg_freq) - 6 <= max_width:
                ret.append(self.curse_add_line(msg_name))
            ret.append(self.curse_add_line(msg_freq))
            ret.append(self.curse_new_line())
        for key in ['cpu', 'mem', 'swap']:
            if key == 'cpu' and args.percpu:
                for cpu in self.stats['percpu']:
                    bar.percent = cpu['total']
                    if cpu[cpu['key']] < 10:
                        msg = '{:3}{} '.format(key.upper(), cpu['cpu_number'])
                    else:
                        msg = '{:4} '.format(cpu['cpu_number'])
                    ret.extend(self._msg_create_line(msg, bar, key))
            else:
                bar.percent = self.stats[key]
                msg = '{:4} '.format(key.upper())
                ret.extend(self._msg_create_line(msg, bar, key))

        # Return the message with decoration
        return ret

    def _msg_create_line(self, msg, bar, key):
        """Create a new line to the Quickview"""
        ret = []

        ret.append(self.curse_add_line(msg))
        ret.append(self.curse_add_line(bar.pre_char, decoration='BOLD'))
        ret.append(self.curse_add_line(str(bar), self.get_views(key=key, option='decoration')))
        ret.append(self.curse_add_line(bar.post_char, decoration='BOLD'))
        ret.append(self.curse_add_line('  '))
        ret.append(self.curse_new_line())

        return ret

    def _hz_to_ghz(self, hz):
        """Convert Hz to Ghz"""
        return hz / 1000000000.0

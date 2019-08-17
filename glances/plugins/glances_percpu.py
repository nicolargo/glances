# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2019 Nicolargo <nicolas@nicolargo.com>
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

"""Per-CPU plugin."""

from glances.logger import logger
from glances.cpu_percent import cpu_percent
from glances.plugins.glances_plugin import GlancesPlugin

# Define the history items list
items_history_list = [{'name': 'user',
                       'description': 'User CPU usage',
                       'y_unit': '%'},
                      {'name': 'system',
                       'description': 'System CPU usage',
                       'y_unit': '%'}]


class Plugin(GlancesPlugin):
    """Glances per-CPU plugin.

    'stats' is a list of dictionaries that contain the utilization percentages
    for each CPU.
    """

    def __init__(self, args=None, config=None):
        """Init the plugin."""
        super(Plugin, self).__init__(args=args,
                                     config=config,
                                     items_history_list=items_history_list,
                                     stats_init_value=[])

        # We want to display the stat in the curse interface
        self.display_curse = True

    def get_key(self):
        """Return the key of the list."""
        return 'cpu_number'

    @GlancesPlugin._check_decorator
    @GlancesPlugin._log_result_decorator
    def update(self):
        """Update per-CPU stats using the input method."""
        # Init new stats
        stats = self.get_init_value()

        # Grab per-CPU stats using psutil's cpu_percent(percpu=True) and
        # cpu_times_percent(percpu=True) methods
        if self.input_method == 'local':
            stats = cpu_percent.get(percpu=True)
        else:
            # Update stats using SNMP
            pass

        # Update the stats
        self.stats = stats

        return self.stats

    def msg_curse(self, args=None, max_width=None):
        """Return the dict to display in the curse interface."""
        # Init the return message
        ret = []

        # Only process if stats exist...
        if not self.stats or not self.args.percpu or self.is_disable():
            return ret

        # Build the string message
        if self.is_disable('quicklook'):
            msg = '{:7}'.format('PER CPU')
            ret.append(self.curse_add_line(msg, "TITLE"))

        # Per CPU stats displayed per line
        for stat in ['user', 'system', 'idle', 'iowait', 'steal']:
            if stat not in self.stats[0]:
                continue
            msg = '{:>7}'.format(stat)
            ret.append(self.curse_add_line(msg))

        # Per CPU stats displayed per column
        for cpu in self.stats:
            ret.append(self.curse_new_line())
            if self.is_disable('quicklook'):
                try:
                    msg = '{:6.1f}%'.format(cpu['total'])
                except TypeError:
                    # TypeError: string indices must be integers (issue #1027)
                    msg = '{:>6}%'.format('?')
                ret.append(self.curse_add_line(msg))
            for stat in ['user', 'system', 'idle', 'iowait', 'steal']:
                if stat not in self.stats[0]:
                    continue
                try:
                    msg = '{:6.1f}%'.format(cpu[stat])
                except TypeError:
                    msg = '{:>6}%'.format('?')
                ret.append(self.curse_add_line(msg,
                                               self.get_alert(cpu[stat],
                                                              header=stat)))

        return ret

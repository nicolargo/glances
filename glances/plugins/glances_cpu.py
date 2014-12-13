# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2014 Nicolargo <nicolas@nicolargo.com>
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

"""CPU plugin."""

import psutil

from glances.plugins.glances_plugin import GlancesPlugin

# SNMP OID
# percentage of user CPU time: .1.3.6.1.4.1.2021.11.9.0
# percentages of system CPU time: .1.3.6.1.4.1.2021.11.10.0
# percentages of idle CPU time: .1.3.6.1.4.1.2021.11.11.0
snmp_oid = {'default': {'user': '1.3.6.1.4.1.2021.11.9.0',
                        'system': '1.3.6.1.4.1.2021.11.10.0',
                        'idle': '1.3.6.1.4.1.2021.11.11.0'},
            'windows': {'percent': '1.3.6.1.2.1.25.3.3.1.2'},
            'esxi': {'percent': '1.3.6.1.2.1.25.3.3.1.2'}}

# Define the history items list
# - 'name' define the stat identifier
# - 'color' define the graph color in #RGB format
# - 'y_unit' define the Y label
# All items in this list will be historised if the --enable-history tag is set
items_history_list = [{'name': 'user', 'color': '#00FF00', 'y_unit': '%'},
                      {'name': 'system', 'color': '#FF0000', 'y_unit': '%'}]


class Plugin(GlancesPlugin):

    """Glances CPU plugin.

    'stats' is a dictionary that contains the system-wide CPU utilization as a
    percentage.
    """

    def __init__(self, args=None):
        """Init the CPU plugin."""
        GlancesPlugin.__init__(self, args=args, items_history_list=items_history_list)

        # We want to display the stat in the curse interface
        self.display_curse = True

        # Init stats
        self.reset()

    def reset(self):
        """Reset/init the stats."""
        self.stats = {}

    @GlancesPlugin._log_result_decorator
    def update(self):
        """Update CPU stats using the input method."""
        # Reset stats
        self.reset()

        # Grab CPU stats using psutil's cpu_percent and cpu_times_percent methods
        if self.get_input() == 'local':
            # Get all possible values for CPU stats: user, system, idle,
            # nice (UNIX), iowait (Linux), irq (Linux, FreeBSD), steal (Linux 2.6.11+)
            # The following stats are returned by the API but not displayed in the UI:
            # softirq (Linux), guest (Linux 2.6.24+), guest_nice (Linux 3.2.0+)
            self.stats['total'] = psutil.cpu_percent(interval=0.0)
            cpu_times_percent = psutil.cpu_times_percent(interval=0.0)
            for stat in ['user', 'system', 'idle', 'nice', 'iowait',
                         'irq', 'softirq', 'steal', 'guest', 'guest_nice']:
                if hasattr(cpu_times_percent, stat):
                    self.stats[stat] = getattr(cpu_times_percent, stat)
        elif self.get_input() == 'snmp':
            # Update stats using SNMP
            if self.get_short_system_name() in ('windows', 'esxi'):
                # Windows or VMWare ESXi
                # You can find the CPU utilization of windows system by querying the oid
                # Give also the number of core (number of element in the table)
                try:
                    cpu_stats = self.set_stats_snmp(snmp_oid=snmp_oid[self.get_short_system_name()],
                                                    bulk=True)
                except KeyError:
                    self.reset()

                # Iter through CPU and compute the idle CPU stats
                self.stats['nb_log_core'] = 0
                self.stats['idle'] = 0
                for c in cpu_stats:
                    if c.startswith('percent'):
                        self.stats['idle'] += float(cpu_stats['percent.3'])
                        self.stats['nb_log_core'] += 1
                if self.stats['nb_log_core'] > 0:
                    self.stats['idle'] = self.stats['idle'] / self.stats['nb_log_core']
                self.stats['idle'] = 100 - self.stats['idle']

            else:
                # Default behavor
                try:
                    self.stats = self.set_stats_snmp(snmp_oid=snmp_oid[self.get_short_system_name()])
                except KeyError:
                    self.stats = self.set_stats_snmp(snmp_oid=snmp_oid['default'])

                if self.stats['idle'] == '':
                    self.reset()
                    return self.stats

                # Convert SNMP stats to float
                for key in list(self.stats.keys()):
                    self.stats[key] = float(self.stats[key])

        # Update the history list
        self.update_stats_history()

        return self.stats

    def msg_curse(self, args=None):
        """Return the list to display in the curse interface."""
        # Init the return message
        ret = []

        # Only process if stats exist...
        if self.stats == {}:
            return ret

        # Build the string message
        # If user stat is not here, display only idle / total CPU usage (for exemple on Windows OS)
        idle_tag = 'user' not in self.stats
        # Header
        msg = '{0:8}'.format(_("CPU"))
        ret.append(self.curse_add_line(msg, "TITLE"))
        # Total CPU usage
        msg = '{0:>5}%'.format(self.stats['total'])
        if idle_tag:
            ret.append(self.curse_add_line(msg, self.get_alert_log(self.stats['total']), header="system"))
        else:
            ret.append(self.curse_add_line(msg))
        # Nice CPU
        if 'nice' in self.stats:
            msg = '  {0:8}'.format(_("nice:"))
            ret.append(self.curse_add_line(msg, optional=True))
            msg = '{0:>5}%'.format(self.stats['nice'])
            ret.append(self.curse_add_line(msg, optional=True))
        # New line
        ret.append(self.curse_new_line())
        # User CPU
        if 'user' in self.stats:
            msg = '{0:8}'.format(_("user:"))
            ret.append(self.curse_add_line(msg))
            msg = '{0:>5}%'.format(self.stats['user'])
            ret.append(self.curse_add_line(msg, self.get_alert_log(self.stats['user'], header="user")))
        elif 'idle' in self.stats:
            msg = '{0:8}'.format(_("idle:"))
            ret.append(self.curse_add_line(msg))
            msg = '{0:>5}%'.format(self.stats['idle'])
            ret.append(self.curse_add_line(msg))
        # IRQ CPU
        if 'irq' in self.stats:
            msg = '  {0:8}'.format(_("irq:"))
            ret.append(self.curse_add_line(msg, optional=True))
            msg = '{0:>5}%'.format(self.stats['irq'])
            ret.append(self.curse_add_line(msg, optional=True))
        # New line
        ret.append(self.curse_new_line())
        # System CPU
        if 'system' in self.stats and not idle_tag:
            msg = '{0:8}'.format(_("system:"))
            ret.append(self.curse_add_line(msg))
            msg = '{0:>5}%'.format(self.stats['system'])
            ret.append(self.curse_add_line(msg, self.get_alert_log(self.stats['system'], header="system")))
        else:
            msg = '{0:8}'.format(_("core:"))
            ret.append(self.curse_add_line(msg))
            msg = '{0:>6}'.format(self.stats['nb_log_core'])
            ret.append(self.curse_add_line(msg))
        # IOWait CPU
        if 'iowait' in self.stats:
            msg = '  {0:8}'.format(_("iowait:"))
            ret.append(self.curse_add_line(msg, optional=True))
            msg = '{0:>5}%'.format(self.stats['iowait'])
            ret.append(self.curse_add_line(msg, self.get_alert_log(self.stats['iowait'], header="iowait"), optional=True))
        # New line
        ret.append(self.curse_new_line())
        # Idle CPU
        if 'idle' in self.stats and not idle_tag:
            msg = '{0:8}'.format(_("idle:"))
            ret.append(self.curse_add_line(msg))
            msg = '{0:>5}%'.format(self.stats['idle'])
            ret.append(self.curse_add_line(msg))
        # Steal CPU usage
        if 'steal' in self.stats:
            msg = '  {0:8}'.format(_("steal:"))
            ret.append(self.curse_add_line(msg, optional=True))
            msg = '{0:>5}%'.format(self.stats['steal'])
            ret.append(self.curse_add_line(msg, self.get_alert(self.stats['steal'], header="steal"), optional=True))

        # Return the message with decoration
        return ret

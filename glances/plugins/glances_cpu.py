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

from glances.plugins.glances_plugin import GlancesPlugin

import psutil

# SNMP OID
# percentage of user CPU time: .1.3.6.1.4.1.2021.11.9.0
# percentages of system CPU time: .1.3.6.1.4.1.2021.11.10.0
# percentages of idle CPU time: .1.3.6.1.4.1.2021.11.11.0
snmp_oid = {'user': '1.3.6.1.4.1.2021.11.9.0',
            'system': '1.3.6.1.4.1.2021.11.10.0',
            'idle': '1.3.6.1.4.1.2021.11.11.0'}


class Plugin(GlancesPlugin):

    """
    Glances' CPU plugin.

    stats is a dict
    """

    def __init__(self, args=None):
        """Init the CPU plugin."""
        GlancesPlugin.__init__(self, args=args)

        # We want to display the stat in the curse interface
        self.display_curse = True
        # Set the message position
        # It is NOT the curse position but the Glances column/line
        # Enter -1 to right align
        self.column_curse = 0
        # Enter -1 to diplay bottom
        self.line_curse = 1

        # Init stats
        self.first_call = True
        self.reset()

    def reset(self):
        """Reset/init the stats."""
        self.stats = {}

    def update(self):
        """Update CPU stats using the input method."""
        # Reset stats
        self.reset()

        if self.get_input() == 'local':
            # Update stats using the standard system lib

            # Grab CPU using the PSUtil cpu_times_percent method
            cputimespercent = psutil.cpu_times_percent(interval=0.0, percpu=False)

            # Get all possible value for CPU stats
            # user
            # system
            # idle
            # nice (UNIX)
            # iowait (Linux)
            # irq (Linux, FreeBSD)
            # softirq (Linux)
            # steal (Linux >= 2.6.11)
            # The following stats are returned by the API but not displayed in the UI:
            # guest (Linux >= 2.6.24)
            # guest_nice (Linux >= 3.2.0)
            for cpu in ['user', 'system', 'idle', 'nice',
                        'iowait', 'irq', 'softirq', 'steal',
                        'guest', 'guest_nice']:
                if hasattr(cputimespercent, cpu):
                    self.stats[cpu] = getattr(cputimespercent, cpu)
        elif self.get_input() == 'snmp':
            # Update stats using SNMP
            self.stats = self.set_stats_snmp(snmp_oid=snmp_oid)

            if self.stats['user'] == '':
                self.reset()
                return self.stats

            for key in self.stats.iterkeys():
                self.stats[key] = float(self.stats[key])

        return self.stats

    def msg_curse(self, args=None):
        """Return the list to display in the curse interface."""
        # Init the return message
        ret = []

        # Only process if stats exist...
        if self.stats == {}:
            return ret

        # Build the string message
        # Header
        msg = '{0:8}'.format(_("CPU"))
        ret.append(self.curse_add_line(msg, "TITLE"))
        # Total CPU usage
        msg = '{0:>6.1%}'.format((100 - self.stats['idle']) / 100)
        ret.append(self.curse_add_line(msg))
        # Nice CPU
        if 'nice' in self.stats:
            msg = '  {0:8}'.format(_("nice:"))
            ret.append(self.curse_add_line(msg, optional=True))
            msg = '{0:>6.1%}'.format(self.stats['nice'] / 100)
            ret.append(self.curse_add_line(msg, optional=True))
        # New line
        ret.append(self.curse_new_line())
        # User CPU
        if 'user' in self.stats:
            msg = '{0:8}'.format(_("user:"))
            ret.append(self.curse_add_line(msg))
            msg = '{0:>6.1%}'.format(self.stats['user'] / 100)
            ret.append(self.curse_add_line(msg, self.get_alert_log(self.stats['user'], header="user")))
        # IRQ CPU
        if 'irq' in self.stats:
            msg = '  {0:8}'.format(_("irq:"))
            ret.append(self.curse_add_line(msg, optional=True))
            msg = '{0:>6.1%}'.format(self.stats['irq'] / 100)
            ret.append(self.curse_add_line(msg, optional=True))
        # New line
        ret.append(self.curse_new_line())
        # System CPU
        if 'system' in self.stats:
            msg = '{0:8}'.format(_("system:"))
            ret.append(self.curse_add_line(msg))
            msg = '{0:>6.1%}'.format(self.stats['system'] / 100)
            ret.append(self.curse_add_line(msg, self.get_alert_log(self.stats['system'], header="system")))
        # IOWait CPU
        if 'iowait' in self.stats:
            msg = '  {0:8}'.format(_("iowait:"))
            ret.append(self.curse_add_line(msg, optional=True))
            msg = '{0:>6.1%}'.format(self.stats['iowait'] / 100)
            ret.append(self.curse_add_line(msg, self.get_alert_log(self.stats['iowait'], header="iowait"), optional=True))
        # New line
        ret.append(self.curse_new_line())
        # Idle CPU
        if 'idle' in self.stats:
            msg = '{0:8}'.format(_("idle:"))
            ret.append(self.curse_add_line(msg))
            msg = '{0:>6.1%}'.format(self.stats['idle'] / 100)
            ret.append(self.curse_add_line(msg))
        # Steal CPU usage
        if 'steal' in self.stats:
            msg = '  {0:8}'.format(_("steal:"))
            ret.append(self.curse_add_line(msg, optional=True))
            msg = '{0:>6.1%}'.format(self.stats['steal'] / 100)
            ret.append(self.curse_add_line(msg, self.get_alert(self.stats['steal'], header="steal"), optional=True))

        # Return the message with decoration
        return ret

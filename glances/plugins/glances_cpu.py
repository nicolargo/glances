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
"""
Glances CPU plugin
"""

# Import system libs
# Check for PSUtil already done in the glances_core script
from psutil import cpu_times_percent

# Import Glances libs
from glances.plugins.glances_plugin import GlancesPlugin


class Plugin(GlancesPlugin):
    """
    Glances' Cpu Plugin

    stats is a dict
    """

    def __init__(self):
        GlancesPlugin.__init__(self)

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
        self.stats = {}

    def update(self):
        """
        Update CPU stats
        """

        # Grab CPU using the PSUtil cpu_times_percent method
        cputimespercent = cpu_times_percent(interval=0.0, percpu=False)

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
        cpu_stats = {}
        for cpu in ['user', 'system', 'idle', 'nice',
                    'iowait', 'irq', 'softirq', 'steal',
                    'guest', 'guest_nice']:
            if (hasattr(cputimespercent, cpu)):
                cpu_stats[cpu] = getattr(cputimespercent, cpu)

        # Set the global variable to the new stats
        self.stats = cpu_stats

        return self.stats

    def msg_curse(self, args=None):
        """
        Return the list to display in the curse interface
        """

        # Init the return message
        ret = []

        # Only process if stats exist...
        if (self.stats == {}):
            return ret

        # Build the string message
        # Header
        msg = "{0:8}".format(_("CPU"))
        ret.append(self.curse_add_line(msg, "TITLE"))
        # Total CPU usage
        msg = "{0}".format(format((100 - self.stats['idle']) / 100, '>6.1%'))
        ret.append(self.curse_add_line(msg))
        # Steal CPU usage
        # ret.append(self.curse_add_line("  ", optional=True))
        if ('steal' in self.stats):
            msg = "  {0:8}".format(_("steal:"))
            ret.append(self.curse_add_line(msg, optional=True))
            msg = "{0}".format(format(self.stats['steal'] / 100, '>6.1%'))
            ret.append(self.curse_add_line(msg, self.get_alert(self.stats['steal'], header="steal"), optional=True))
        # New line
        ret.append(self.curse_new_line())
        # User CPU
        if ('user' in self.stats):
            msg = "{0:8}".format(_("user:"))
            ret.append(self.curse_add_line(msg))
            msg = "{0}".format(format(self.stats['user'] / 100, '>6.1%'))
            ret.append(self.curse_add_line(msg, self.get_alert_log(self.stats['user'], header="user")))
        # IOWait CPU
        # ret.append(self.curse_add_line("  ", optional=True))
        if ('iowait' in self.stats):
            msg = "  {0:8}".format(_("iowait:"))
            ret.append(self.curse_add_line(msg, optional=True))
            msg = "{0}".format(format(self.stats['iowait'] / 100, '>6.1%'))
            ret.append(self.curse_add_line(msg, self.get_alert_log(self.stats['iowait'], header="iowait"), optional=True))
        # New line
        ret.append(self.curse_new_line())
        # System CPU
        if ('system' in self.stats):
            msg = "{0:8}".format(_("system:"))
            ret.append(self.curse_add_line(msg))
            msg = "{0}".format(format(self.stats['system'] / 100, '>6.1%'))
            ret.append(self.curse_add_line(msg, self.get_alert_log(self.stats['system'], header="system")))
        # IRQ CPU
        # ret.append(self.curse_add_line("  ", optional=True))
        if ('irq' in self.stats):
            msg = "  {0:8}".format(_("irq:"))
            ret.append(self.curse_add_line(msg, optional=True))
            msg = "{0}".format(format(self.stats['irq'] / 100, '>6.1%'))
            ret.append(self.curse_add_line(msg, optional=True))
        # New line
        ret.append(self.curse_new_line())
        # Nice CPU
        if ('nice' in self.stats):
            msg = "{0:8}".format(_("nice:"))
            ret.append(self.curse_add_line(msg))
            msg = "{0}".format(format(self.stats['nice'] / 100, '>6.1%'))
            ret.append(self.curse_add_line(msg))
        # Idles CPU
        # ret.append(self.curse_add_line("  ", optional=True))
        if ('idle' in self.stats):
            msg = "  {0:8}".format(_("idle:"))
            ret.append(self.curse_add_line(msg, optional=True))
            msg = "{0}".format(format(self.stats['idle'] / 100, '>6.1%'))
            ret.append(self.curse_add_line(msg, optional=True))

        # Return the message with decoration
        return ret

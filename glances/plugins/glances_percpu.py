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

"""Per-CPU plugin."""

import psutil

from glances.plugins.glances_plugin import GlancesPlugin


class Plugin(GlancesPlugin):

    """Glances per-CPU plugin.

    'stats' is a list of dictionaries that contain the utilization percentages
    for each CPU.
    """

    def __init__(self, args=None):
        """Init the plugin."""
        GlancesPlugin.__init__(self, args=args)

        # We want to display the stat in the curse interface
        self.display_curse = True

        # Init stats
        self.reset()

    def reset(self):
        """Reset/init the stats."""
        self.stats = []

    def update(self):
        """Update per-CPU stats using the input method."""
        # Reset stats
        self.reset()

        # Grab per-CPU stats using psutil's cpu_percent(percpu=True) and
        # cpu_times_percent(percpu=True) methods
        if self.get_input() == 'local':
            percpu_percent = psutil.cpu_percent(interval=0.0, percpu=True)
            percpu_times_percent = psutil.cpu_times_percent(interval=0.0, percpu=True)
            for cputimes in percpu_times_percent:
                for cpupercent in percpu_percent:
                    cpu = {'total': cpupercent,
                           'user': cputimes.user,
                           'system': cputimes.system,
                           'idle': cputimes.idle}
                    # The following stats are for API purposes only
                    if hasattr(cputimes, 'nice'):
                        cpu['nice'] = cputimes.nice
                    if hasattr(cputimes, 'iowait'):
                        cpu['iowait'] = cputimes.iowait
                    if hasattr(cputimes, 'irq'):
                        cpu['irq'] = cputimes.irq
                    if hasattr(cputimes, 'softirq'):
                        cpu['softirq'] = cputimes.softirq
                    if hasattr(cputimes, 'steal'):
                        cpu['steal'] = cputimes.steal
                    if hasattr(cputimes, 'guest'):
                        cpu['guest'] = cputimes.guest
                    if hasattr(cputimes, 'guest_nice'):
                        cpu['guest_nice'] = cputimes.guest_nice
                self.stats.append(cpu)
        else:
            # Update stats using SNMP
            pass

        return self.stats

    def msg_curse(self, args=None):
        """Return the dict to display in the curse interface."""
        # Init the return message
        ret = []

        # No per CPU stat ? Exit...
        if not self.stats:
            msg = _("PER CPU not available")
            ret.append(self.curse_add_line(msg, "TITLE"))
            return ret

        # Build the string message
        # Header
        msg = '{0:8}'.format(_("PER CPU"))
        ret.append(self.curse_add_line(msg, "TITLE"))

        # Total per-CPU usage
        for cpu in self.stats:
            msg = '{0:>6}%'.format(cpu['total'])
            ret.append(self.curse_add_line(msg))

        # User per-CPU
        ret.append(self.curse_new_line())
        msg = '{0:8}'.format(_("user:"))
        ret.append(self.curse_add_line(msg))
        for cpu in self.stats:
            msg = '{0:>6}%'.format(cpu['user'])
            ret.append(self.curse_add_line(msg, self.get_alert(cpu['user'], header="user")))

        # System per-CPU
        ret.append(self.curse_new_line())
        msg = '{0:8}'.format(_("system:"))
        ret.append(self.curse_add_line(msg))
        for cpu in self.stats:
            msg = '{0:>6}%'.format(cpu['system'])
            ret.append(self.curse_add_line(msg, self.get_alert(cpu['system'], header="system")))

        # Idle per-CPU
        ret.append(self.curse_new_line())
        msg = '{0:8}'.format(_("idle:"))
        ret.append(self.curse_add_line(msg))
        for cpu in self.stats:
            msg = '{0:>6}%'.format(cpu['idle'])
            ret.append(self.curse_add_line(msg))

        # Return the message with decoration
        return ret

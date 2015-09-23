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

"""Per-CPU plugin."""

from glances.core.glances_cpu_percent import cpu_percent
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

    def get_key(self):
        """Return the key of the list."""
        return 'cpu_number'

    def reset(self):
        """Reset/init the stats."""
        self.stats = []

    def update(self):
        """Update per-CPU stats using the input method."""
        # Reset stats
        self.reset()

        # Grab per-CPU stats using psutil's cpu_percent(percpu=True) and
        # cpu_times_percent(percpu=True) methods
        if self.input_method == 'local':
            self.stats = cpu_percent.get(percpu=True)
        else:
            # Update stats using SNMP
            pass

        return self.stats

    def msg_curse(self, args=None):
        """Return the dict to display in the curse interface."""
        # Init the return message
        ret = []

        # Only process if plugin not disable
        if args.disable_cpu:
            return ret

        # No per CPU stat ? Exit...
        if not self.stats:
            msg = 'PER CPU not available'
            ret.append(self.curse_add_line(msg, "TITLE"))
            return ret

        # Build the string message
        # Header
        msg = '{0:8}'.format('PER CPU')
        ret.append(self.curse_add_line(msg, "TITLE"))

        # Total per-CPU usage
        for cpu in self.stats:
            msg = '{0:>6}%'.format(cpu['total'])
            ret.append(self.curse_add_line(msg))

        # Stats per-CPU
        for stat in ['user', 'system', 'idle', 'iowait', 'steal']:
            if stat not in self.stats[0]:
                continue

            ret.append(self.curse_new_line())
            msg = '{0:8}'.format(stat + ':')
            ret.append(self.curse_add_line(msg))
            for cpu in self.stats:
                msg = '{0:>6}%'.format(cpu[stat])
                ret.append(self.curse_add_line(msg,
                                               self.get_alert(cpu[stat], header=stat)))

        # Return the message with decoration
        return ret

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

"""Load plugin."""

# Import system libs
import os

# Import Glances libs
from glances.plugins.glances_core import Plugin as CorePlugin
from glances.plugins.glances_plugin import GlancesPlugin

# SNMP OID
# 1 minute Load: .1.3.6.1.4.1.2021.10.1.3.1
# 5 minute Load: .1.3.6.1.4.1.2021.10.1.3.2
# 15 minute Load: .1.3.6.1.4.1.2021.10.1.3.3
snmp_oid = {'min1': '1.3.6.1.4.1.2021.10.1.3.1',
            'min5': '1.3.6.1.4.1.2021.10.1.3.2',
            'min15': '1.3.6.1.4.1.2021.10.1.3.3'}


class Plugin(GlancesPlugin):

    """Glances' load plugin.

    stats is a dict
    """

    def __init__(self, args=None):
        """Init the plugin."""
        GlancesPlugin.__init__(self, args=args)

        # We want to display the stat in the curse interface
        self.display_curse = True
        # Set the message position
        # It is NOT the curse position but the Glances column/line
        # Enter -1 to right align
        self.column_curse = 1
        # Enter -1 to diplay bottom
        self.line_curse = 1

        # Init stats
        self.reset()

    def reset(self):
        """Reset/init the stats."""
        self.stats = {}

    def update(self):
        """Update load stats."""
        # Reset stats
        self.reset()

        # Call CorePlugin in order to display the core number
        try:
            nb_log_core = CorePlugin().update()["log"]
        except Exception:
            nb_log_core = 0

        if self.get_input() == 'local':
            # Update stats using the standard system lib

            # Get the load using the os standard lib
            try:
                load = os.getloadavg()
            except (OSError, AttributeError):
                self.stats = {}
            else:
                self.stats = {'min1': load[0],
                              'min5': load[1],
                              'min15': load[2],
                              'cpucore': nb_log_core}
        elif self.get_input() == 'snmp':
            # Update stats using SNMP
            self.stats = self.set_stats_snmp(snmp_oid=snmp_oid)

            self.stats['cpucore'] = nb_log_core

            if self.stats['min1'] == '':
                self.reset()
                return self.stats

            for key in self.stats.iterkeys():
                self.stats[key] = float(self.stats[key])

        return self.stats

    def msg_curse(self, args=None):
        """Return the dict to display in the curse interface."""
        # Init the return message
        ret = []

        # Only process if stats exist...
        if self.stats == {}:
            return ret

        # Build the string message
        # Header
        msg = '{0:8}'.format(_("LOAD"))
        ret.append(self.curse_add_line(msg, "TITLE"))
        # Core number
        if self.stats['cpucore'] > 0:
            msg = _("{0}-core").format(self.stats['cpucore'], '>1')
            ret.append(self.curse_add_line(msg))
        # New line
        ret.append(self.curse_new_line())
        # 1min load
        msg = '{0:8}'.format(_("1 min:"))
        ret.append(self.curse_add_line(msg))
        msg = '{0:>6.2f}'.format(self.stats['min1'])
        ret.append(self.curse_add_line(msg))
        # New line
        ret.append(self.curse_new_line())
        # 5min load
        msg = '{0:8}'.format(_("5 min:"))
        ret.append(self.curse_add_line(msg))
        msg = '{0:>6.2f}'.format(self.stats['min5'])
        ret.append(self.curse_add_line(
            msg, self.get_alert(self.stats['min5'], max=100 * self.stats['cpucore'])))
        # New line
        ret.append(self.curse_new_line())
        # 15min load
        msg = '{0:8}'.format(_("15 min:"))
        ret.append(self.curse_add_line(msg))
        msg = '{0:>6.2f}'.format(self.stats['min15'])
        ret.append(self.curse_add_line(
            msg, self.get_alert_log(self.stats['min15'], max=100 * self.stats['cpucore'])))

        return ret

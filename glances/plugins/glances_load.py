#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Glances - An eye on your system
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
Glances load plugin
"""

# Import system libs
from os import getloadavg

# Import Glances libs
from glances.plugins.glances_plugin import GlancesPlugin
from glances.plugins.glances_core import Plugin as CorePlugin


class Plugin(GlancesPlugin):
    """
    Glances's Load Plugin

    stats is a dict
    """

    def __init__(self):
        GlancesPlugin.__init__(self)

        # Instance for the CorePlugin in order to display the core number
        self.core_plugin = CorePlugin()

        # We want to display the stat in the curse interface
        self.display_curse = True
        # Set the message position
        # It is NOT the curse position but the Glances column/line
        # Enter -1 to right align
        self.column_curse = 1
        # Enter -1 to diplay bottom
        self.line_curse = 1

        # Init stats
        self.stats = {}

    def update(self):
        """
        Update load stats
        """

        # Get the load using the os standard lib
        try:
            load = getloadavg()
        except OSError:
            self.stats = {}
        else:
            self.stats = {'min1': load[0],
                          'min5': load[1],
                          'min15': load[2]}

        return self.stats

    def msg_curse(self, args=None):
        """
        Return the dict to display in the curse interface
        """

        # Init the return message
        ret = []

        # Only process if stats exist...
        if (self.stats == {}):
            return ret

        # Build the string message
        # Header
        msg = "{0:4} ".format(_("LOAD"))
        ret.append(self.curse_add_line(msg, "TITLE"))
        # Core number
        msg = "{0:3}-core".format(self.core_plugin.update()["log"])
        ret.append(self.curse_add_line(msg))
        # New line
        ret.append(self.curse_new_line())
        # 1min load
        msg = "{0:8}".format(_("1 min:"))
        ret.append(self.curse_add_line(msg))
        msg = "{0}".format(format(self.stats['min1'], '>5.2f'))
        ret.append(self.curse_add_line(msg))
        # New line
        ret.append(self.curse_new_line())
        # 5min load
        msg = "{0:8}".format(_("5 min:"))
        ret.append(self.curse_add_line(msg))
        msg = "{0}".format(format(self.stats['min5'], '>5.2f'))
        ret.append(self.curse_add_line(
            msg, self.get_alert(self.stats['min5'], max=100 * self.core_plugin.update()["log"])))
        # New line
        ret.append(self.curse_new_line())
        # 15min load
        msg = "{0:8}".format(_("15 min:"))
        ret.append(self.curse_add_line(msg))
        msg = "{0}".format(format(self.stats['min15'], '>5.2f'))
        ret.append(self.curse_add_line(
            msg, self.get_alert_log(self.stats['min15'], max=100 * self.core_plugin.update()["log"])))

        return ret

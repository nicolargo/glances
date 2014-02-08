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

# Import system libs
# Check for PSUtil already done in the glances_core script
from os import getloadavg

# from ..plugins.glances_plugin import GlancesPlugin
from glances_plugin import GlancesPlugin
from glances_core import Plugin as CorePlugin

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


    def update(self):
        """
        Update load stats
        """
        try:
            load = getloadavg()

            self.stats = {'min1': load[0],
                          'min5': load[1],
                          'min15': load[2]}
        except Exception, err:
            self.stats = {}

        return self.stats


    def msg_curse(self):
        """
        Return the dict to display in the curse interface
        """
        # Init the return message
        ret = []

        # Build the string message
        # Header
        msg = "{0:4} ".format(_("LOAD"))
        ret.append(self.curse_add_line(msg, "BOLD"))
        # Core number
        msg = "{0:3}-core".format(self.core_plugin.update())
        ret.append(self.curse_add_line(msg, "NORMAL"))
        # New line
        ret.append(self.curse_new_line())
        # 1min load
        # msg = "{0:7} {1}".format(
        #             _("1 min:"),
        #             format(self.stats['min1'], '>5.2f'))
        msg = "{0:7} {1} {2}".format(
                    _("1 min:"),
                    format(self.stats['min1'], '>5.2f'),
                    str(self.get_alert(self.stats['min1'], max=100*self.core_plugin.update())))
        ret.append(self.curse_add_line(msg, "NORMAL"))
        # New line
        ret.append(self.curse_new_line())
        # 5min load
        msg = "{0:7} {1}".format(
                    _("5 min:"),
                    format(self.stats['min5'], '>5.2f'))
        ret.append(self.curse_add_line(msg, "NORMAL"))
        # New line
        ret.append(self.curse_new_line())
        # 15min load
        msg = "{0:7} {1}".format(
                    _("15 min:"),
                    format(self.stats['min15'], '>5.2f'))
        ret.append(self.curse_add_line(msg, "NORMAL"))
        
        # !!! Limits (debug only)
        ret.append(self.curse_new_line())
        msg = str(self.get_limits())
        ret.append(self.curse_add_line(msg, "NORMAL"))

        return ret
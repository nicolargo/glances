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

# Import Glances lib
from glances_plugin import GlancesPlugin
from glances.core.glances_globals import glances_monitors


class Plugin(GlancesPlugin):
    """
    Glances's monitor Plugin

    Only for display
    """

    def __init__(self):
        GlancesPlugin.__init__(self)

        # We want to display the stat in the curse interface
        self.display_curse = True
        # Set the message position
        # It is NOT the curse position but the Glances column/line
        # Enter -1 to right align 
        self.column_curse = 1
        # Enter -1 to diplay bottom
        self.line_curse = 3


    def load_limits(self, config):
        """
        No limit...
        """
    
        pass


    def update(self):
        """
        Nothing to do here
        Just return the global glances_log
        """

        # !!! It is not just a get 
        # !!! An update should be done on the server side before
        # !!! New in v2: the monitor list is executed on the server side !
        self.stats = glances_monitors.get()


    def msg_curse(self, args=None):
        """
        Return the dict to display in the curse interface
        """
        # Init the return message
        ret = []

        # Build the string message
        if (self.stats != []):
            msg = "{0}".format(_("Monitored list"))
            ret.append(self.curse_add_line(msg, "TITLE"))
            for m in self.stats:
                ret.append(self.curse_new_line())
                msg = "{0}".format(str(m))
                ret.append(self.curse_add_line(msg))

        return ret

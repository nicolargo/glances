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
from glances.core.glances_globals import glances_logs


class Plugin(GlancesPlugin):
    """
    Glances's alert Plugin

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
        self.line_curse = 4


    def update(self):
        """
        Nothing to do here
        Just return the global glances_log
        """

        self.stats = glances_logs.get()


    def msg_curse(self, args=None):
        """
        Return the dict to display in the curse interface
        """
        # Init the return message
        ret = []

        # Build the string message
        # Header
        if (self.stats == []):
            msg = "{0:8}".format(_("No alert detected"))
            ret.append(self.curse_add_line(msg, "TITLE"))
        else:
            msg = "{0:8}".format(_("ALERT"))
            ret.append(self.curse_add_line(msg, "TITLE"))

        return ret

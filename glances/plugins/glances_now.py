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
from datetime import datetime

# from ..plugins.glances_plugin import GlancesPlugin
from glances_plugin import GlancesPlugin

class Plugin(GlancesPlugin):
    """
    Glances' Core Plugin
    Get current date/time

    stats is (string)
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
        self.line_curse = -1


    def update(self):
        """
        Update current date/time
        """

        # Now
        # Had to convert it to string because datetime is not JSON serializable
        self.stats = datetime.now().strftime(_("%Y-%m-%d %H:%M:%S"))

        return self.stats

    def msg_curse(self, args=None):
        """
        Return the string to display in the curse interface
        """

        # Init the return message
        ret = []

        # Build the string message
        # 23 is the padding for the process list
        msg = _("{0:23}").format(self.stats)
        ret.append(self.curse_add_line(msg))

        return ret
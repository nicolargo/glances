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

# Import system libs
# Check for PSUtil already done in the glances_core script
try:
    from psutil import get_boot_time
except:
    from psutil import BOOT_TIME

from datetime import datetime

# Import Glances libs
from glances.plugins.glances_plugin import GlancesPlugin


class Plugin(GlancesPlugin):
    """
    Glances' Uptime Plugin
    Get stats about uptime

    stats is date (string)
    """

    def __init__(self):
        GlancesPlugin.__init__(self)

        # We want to display the stat in the curse interface
        self.display_curse = True
        # Set the message position
        # It is NOT the curse position but the Glances column/line
        # Enter -1 to right align
        self.column_curse = -1
        # Enter -1 to diplay bottom
        self.line_curse = 0

    def update(self):
        """
        Update uptime stat
        """
        try:
            # For PsUtil >= 0.7.0
            uptime = datetime.now() - datetime.fromtimestamp(get_boot_time())
        except NameError:
            uptime = datetime.now() - datetime.fromtimestamp(BOOT_TIME)
        else:
            uptime = '.UNKNOW'

        # Convert uptime to string (because datetime is not JSONifi)
        self.stats = str(uptime).split('.')[0]

    def msg_curse(self, args=None):
        """
        Return the string to display in the curse interface
        """

        # Init the return message
        ret = []

        # Add the line with decoration
        ret.append(self.curse_add_line(_("Uptime: {}").format(self.stats)))

        # Return the message with decoration
        return ret

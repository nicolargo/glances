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

"""Uptime plugin."""

# Import system libs
from datetime import datetime, timedelta

# Import Glances libs
from glances.plugins.glances_plugin import GlancesPlugin

# Import psutil
import psutil

# SNMP OID
snmp_oid = {'_uptime': '1.3.6.1.2.1.1.3.0'}


class Plugin(GlancesPlugin):

    """Glances uptime plugin.

    stats is date (string)
    """

    def __init__(self, args=None):
        """Init the plugin."""
        GlancesPlugin.__init__(self, args=args)

        # We want to display the stat in the curse interface
        self.display_curse = True

        # Set the message position
        self.align = 'right'

        # Init the stats
        self.reset()

    def reset(self):
        """Reset/init the stats."""
        self.stats = {}

    def update(self):
        """Update uptime stat using the input method."""
        # Reset stats
        self.reset()

        if self.input_method == 'local':
            # Update stats using the standard system lib
            uptime = datetime.now() - datetime.fromtimestamp(psutil.boot_time())

            # Convert uptime to string (because datetime is not JSONifi)
            self.stats = str(uptime).split('.')[0]
        elif self.input_method == 'snmp':
            # Update stats using SNMP
            uptime = self.get_stats_snmp(snmp_oid=snmp_oid)['_uptime']
            try:
                # In hundredths of seconds
                self.stats = str(timedelta(seconds=int(uptime) / 100))
            except Exception:
                pass

        # Return the result
        return self.stats

    def msg_curse(self, args=None):
        """Return the string to display in the curse interface."""
        return [self.curse_add_line('Uptime: {0}'.format(self.stats))]

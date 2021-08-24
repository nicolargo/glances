# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2019 Nicolargo <nicolas@nicolargo.com>
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

from datetime import datetime, timedelta

from glances.plugins.glances_plugin import GlancesPlugin

import psutil

# SNMP OID
snmp_oid = {'_uptime': '1.3.6.1.2.1.1.3.0'}


class Plugin(GlancesPlugin):
    """Glances uptime plugin.

    stats is date (string)
    """

    def __init__(self, args=None, config=None):
        """Init the plugin."""
        super(Plugin, self).__init__(args=args, config=config)

        # We want to display the stat in the curse interface
        self.display_curse = True

        # Set the message position
        self.align = 'right'

        # Init the stats
        self.uptime = datetime.now() - datetime.fromtimestamp(psutil.boot_time())

    def get_export(self):
        """Overwrite the default export method.

        Export uptime in seconds.
        """
        # Convert the delta time to seconds (with cast)
        # Correct issue #1092 (thanks to @IanTAtWork)
        return {'seconds': int(self.uptime.total_seconds())}

    @GlancesPlugin._check_decorator
    @GlancesPlugin._log_result_decorator
    def update(self):
        """Update uptime stat using the input method."""
        # Init new stats
        stats = self.get_init_value()

        if self.input_method == 'local':
            # Update stats using the standard system lib
            self.uptime = datetime.now() - datetime.fromtimestamp(psutil.boot_time())

            # Convert uptime to string (because datetime is not JSONifi)
            stats = str(self.uptime).split('.')[0]
        elif self.input_method == 'snmp':
            # Update stats using SNMP
            uptime = self.get_stats_snmp(snmp_oid=snmp_oid)['_uptime']
            try:
                # In hundredths of seconds
                stats = str(timedelta(seconds=int(uptime) / 100))
            except Exception:
                pass

        # Update the stats
        self.stats = stats

        return self.stats

    def msg_curse(self, args=None, max_width=None):
        """Return the string to display in the curse interface."""
        return [self.curse_add_line('Uptime: {}'.format(self.stats))]

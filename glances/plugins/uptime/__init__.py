#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Uptime plugin."""

from datetime import datetime, timedelta

import psutil

from glances.plugins.plugin.model import GlancesPluginModel

# SNMP OID
snmp_oid = {'_uptime': '1.3.6.1.2.1.1.3.0'}


class PluginModel(GlancesPluginModel):
    """Glances uptime plugin.

    stats is date (string)
    """

    def __init__(self, args=None, config=None):
        """Init the plugin."""
        super().__init__(args=args, config=config)

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

    @GlancesPluginModel._check_decorator
    @GlancesPluginModel._log_result_decorator
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
        # Init the return message
        ret = []

        # Only process if stats exist and plugin not disabled
        if not self.stats or self.is_disabled():
            return ret

        return [self.curse_add_line(f'Uptime: {self.stats}')]

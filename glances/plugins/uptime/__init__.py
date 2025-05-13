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

# Fields description
# https://github.com/nicolargo/glances/wiki/How-to-create-a-new-plugin-%3F#create-the-plugin-script
fields_description = {
    'human': {'description': 'Uptime in human readable format.', 'unit': 'string', 'short_name': 'Uptime'},
    'seconds': {'description': 'Number of seconds since boot.', 'unit': 'seconds', 'display': False},
}

# SNMP OID
snmp_oid = {'_uptime': '1.3.6.1.2.1.1.3.0'}


class UptimePlugin(GlancesPluginModel):
    """Glances uptime plugin.

    stats is date (string)
    """

    def __init__(self, args=None, config=None):
        """Init the plugin."""
        super().__init__(args=args, config=config, fields_description=fields_description)

        # We want to display the stat in the curse interface
        self.display_curse = True

        # Set the message position
        self.align = 'right'

    # def get_export(self):
    #     """Overwrite the default export method.

    #     Export uptime in seconds.
    #     """
    #     # Convert the delta time to seconds (with cast)
    #     # Correct issue #1092 (thanks to @IanTAtWork)
    #     return {'seconds': int(self.uptime.total_seconds())}

    @GlancesPluginModel._check_decorator
    @GlancesPluginModel._log_result_decorator
    def update(self):
        """Update uptime stat using the input method."""
        # Init new stats
        stats = self.get_init_value()

        if self.input_method == 'local':
            # Update stats using the standard system lib
            # Convert uptime to string (because datetime is not JSONifi)
            uptime = datetime.now() - datetime.fromtimestamp(psutil.boot_time())
            stats['human'] = str(uptime).split('.')[0]
            stats['seconds'] = int(uptime.total_seconds())
        elif self.input_method == 'snmp':
            # Update stats using SNMP
            uptime = self.get_stats_snmp(snmp_oid=snmp_oid)['_uptime']
            try:
                # In hundredths of seconds
                stats['human'] = str(timedelta(seconds=int(uptime) / 100))
                stats['seconds'] = str(timedelta(seconds=int(uptime) / 100))
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

        return [self.curse_add_line(f'Uptime: {self.stats["human"]}')]

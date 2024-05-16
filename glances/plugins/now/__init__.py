#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Now (current date) plugin."""

import datetime
from time import strftime, tzname

from glances.plugins.plugin.model import GlancesPluginModel

# Fields description
# description: human readable description
# short_name: shortname to use un UI
# unit: unit type
# rate: if True then compute and add *_gauge and *_rate_per_is fields
# min_symbol: Auto unit should be used if value > than 1 'X' (K, M, G)...
fields_description = {
    'custom': {'description': 'Current date in custom format.'},
    'iso': {'description': 'Current date in ISO 8601 format.'},
}


class PluginModel(GlancesPluginModel):
    """Plugin to get the current date/time.

    stats is a dict:
    {
        "custom": "2024-04-27 16:43:52 CEST",
        "iso": "2024-04-27T16:28:23.382748"
    }
    """

    def __init__(self, args=None, config=None):
        """Init the plugin."""
        super().__init__(args=args, config=config, fields_description=fields_description, stats_init_value={})

        # We want to display the stat in the curse interface
        self.display_curse = True

        # Set the message position
        self.align = 'bottom'

        if args and args.strftime_format:
            self.strftime = args.strftime_format
        elif config:
            if 'global' in config.as_dict():
                self.strftime = config.as_dict()['global']['strftime_format']

    def update(self):
        """Update current date/time."""
        stats = self.get_init_value()

        # Start with the ISO format
        stats['iso'] = datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()

        # Then the custom
        if self.strftime:
            stats['custom'] = strftime(self.strftime)
        else:
            if len(tzname[1]) > 6:
                stats['custom'] = strftime('%Y-%m-%d %H:%M:%S %z')
            else:
                stats['custom'] = strftime('%Y-%m-%d %H:%M:%S %Z')

        self.stats = stats
        return self.stats

    def msg_curse(self, args=None, max_width=None):
        """Return the string to display in the curse interface."""
        # Init the return message
        ret = []

        if not self.stats or self.is_disabled():
            return ret

        # Build the string message
        # 23 is the padding for the process list
        msg = '{:23}'.format(self.stats['custom'])
        ret.append(self.curse_add_line(msg))

        return ret

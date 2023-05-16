# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Now (current date) plugin."""

from time import tzname, strftime
from glances.plugins.plugin.model import GlancesPluginModel


class PluginModel(GlancesPluginModel):
    """Plugin to get the current date/time.

    stats is (string)
    """

    def __init__(self, args=None, config=None):
        """Init the plugin."""
        super(PluginModel, self).__init__(args=args, config=config)

        # We want to display the stat in the curse interface
        self.display_curse = True

        # Set the message position
        self.align = 'bottom'

        if args.strftime_format:
            self.strftime = args.strftime_format
        elif config is not None:
            if 'global' in config.as_dict():
                self.strftime = config.as_dict()['global']['strftime_format']

    def reset(self):
        """Reset/init the stats."""
        self.stats = ''

    def update(self):
        """Update current date/time."""
        # Had to convert it to string because datetime is not JSON serializable
        # Add the time zone (issue #1249 / #1337 / #1598)

        if self.strftime:
            self.stats = strftime(self.strftime)
        else:
            if len(tzname[1]) > 6:
                self.stats = strftime('%Y-%m-%d %H:%M:%S %z')
            else:
                self.stats = strftime('%Y-%m-%d %H:%M:%S %Z')

        return self.stats

    def msg_curse(self, args=None, max_width=None):
        """Return the string to display in the curse interface."""
        # Init the return message
        ret = []

        if not self.stats or self.is_disabled():
            return ret

        # Build the string message
        # 23 is the padding for the process list
        msg = '{:23}'.format(self.stats)
        ret.append(self.curse_add_line(msg))

        return ret

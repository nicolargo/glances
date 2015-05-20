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

"""Alert plugin."""

# Import system lib
from datetime import datetime

# Import Glances libs
from glances.core.glances_logs import glances_logs
from glances.plugins.glances_plugin import GlancesPlugin


class Plugin(GlancesPlugin):

    """Glances alert plugin.

    Only for display.
    """

    def __init__(self, args=None):
        """Init the plugin."""
        GlancesPlugin.__init__(self, args=args)

        # We want to display the stat in the curse interface
        self.display_curse = True

        # Set the message position
        self.align = 'bottom'

        # Init the stats
        self.reset()

    def reset(self):
        """Reset/init the stats."""
        self.stats = []

    def update(self):
        """Nothing to do here. Just return the global glances_log."""
        # Set the stats to the glances_logs
        self.stats = glances_logs.get()

    def msg_curse(self, args=None):
        """Return the dict to display in the curse interface."""
        # Init the return message
        ret = []

        # Only process if display plugin enable...
        if args.disable_log:
            return ret

        # Build the string message
        # Header
        if not self.stats:
            msg = 'No warning or critical alert detected'
            ret.append(self.curse_add_line(msg, "TITLE"))
        else:
            # Header
            msg = 'Warning or critical alerts'
            ret.append(self.curse_add_line(msg, "TITLE"))
            logs_len = glances_logs.len()
            if logs_len > 1:
                msg = ' (lasts {0} entries)'.format(logs_len)
            else:
                msg = ' (one entry)'
            ret.append(self.curse_add_line(msg, "TITLE"))
            # Loop over alerts
            for alert in self.stats:
                # New line
                ret.append(self.curse_new_line())
                # Start
                msg = str(datetime.fromtimestamp(alert[0]))
                ret.append(self.curse_add_line(msg))
                # Duration
                if alert[1] > 0:
                    # If finished display duration
                    msg = ' ({0})'.format(datetime.fromtimestamp(alert[1]) -
                                          datetime.fromtimestamp(alert[0]))
                else:
                    msg = ' (ongoing)'
                ret.append(self.curse_add_line(msg))
                ret.append(self.curse_add_line(" - "))
                # Infos
                if alert[1] > 0:
                    # If finished do not display status
                    msg = '{0} on {1}'.format(alert[2], alert[3])
                    ret.append(self.curse_add_line(msg))
                else:
                    msg = str(alert[3])
                    ret.append(self.curse_add_line(msg, decoration=alert[2]))
                # Min / Mean / Max
                if self.approx_equal(alert[6], alert[4], tolerance=0.1):
                    msg = ' ({0:.1f})'.format(alert[5])
                else:
                    msg = ' (Min:{0:.1f} Mean:{1:.1f} Max:{2:.1f})'.format(
                        alert[6], alert[5], alert[4])
                ret.append(self.curse_add_line(msg))

                # else:
                #     msg = ' Running...'
                #     ret.append(self.curse_add_line(msg))

                # !!! Debug only
                # msg = ' | {0}'.format(alert)
                # ret.append(self.curse_add_line(msg))

        return ret

    def approx_equal(self, a, b, tolerance=0.0):
        """Compare a with b using the tolerance (if numerical)."""
        if str(int(a)).isdigit() and str(int(b)).isdigit():
            return abs(a - b) <= max(abs(a), abs(b)) * tolerance
        else:
            return a == b

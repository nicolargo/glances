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

# Import system lib
from datetime import datetime, timedelta

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
        self.line_curse = 5


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
            msg = "{0}".format(_("No warning or critical alert detected"))
            ret.append(self.curse_add_line(msg, "TITLE"))
        else:
            # Header
            msg = "{0}".format(_("Warning or critical alerts"))
            ret.append(self.curse_add_line(msg, "TITLE"))
            logs_len = glances_logs.len()
            if (logs_len > 1):
                msg = " {0}".format(_("(lasts %s entries)") % logs_len)
            else:
                msg = " {0}".format(_("(one entry)"))
            ret.append(self.curse_add_line(msg, "TITLE"))
            # Loop over alerts
            for alert in glances_logs.get():
                # New line
                ret.append(self.curse_new_line())
                # Start
                msg = "{0}".format(datetime.fromtimestamp(alert[0]))
                ret.append(self.curse_add_line(msg))
                # Duration
                if (alert[1] > 0):
                    # If finished display duration
                    msg = " ({0})".format(datetime.fromtimestamp(alert[1]) - datetime.fromtimestamp(alert[0]))
                else:
                    msg = _(" (ongoing)")
                ret.append(self.curse_add_line(msg))                    
                ret.append(self.curse_add_line(" - "))
                # Infos
                if (alert[1] > 0):
                    # If finished do not display status
                    msg = "{0} {1} {2}".format(alert[2], _("on"), alert[3])
                    ret.append(self.curse_add_line(msg))
                else:
                    msg = "{0}".format(alert[3])
                    ret.append(self.curse_add_line(msg, decoration=alert[2]))
                # Min / Mean / Max
                msg = " ({0:.1f}/{1:.1f}/{2:.1f})".format(alert[6], alert[5], alert[4])
                ret.append(self.curse_add_line(msg))

                # else:
                #     msg = " {0}".format(_("Running..."))
                #     ret.append(self.curse_add_line(msg))

                # !!! Debug only
                # msg = " | {0}".format(alert)
                # ret.append(self.curse_add_line(msg))

        return ret

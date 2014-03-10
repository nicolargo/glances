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

# Import Glances lib
from glances_plugin import GlancesPlugin
from glances.core.glances_globals import glances_monitors


class Plugin(GlancesPlugin):
    """
    Glances's monitor Plugin

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
        self.line_curse = 3

    def load_limits(self, config):
        """
        No limit...
        """
        pass

    def update(self):
        """
        Nothing to do here
        Just return the global glances_log
        """
        # Update the monitored list (result of command)
        glances_monitors.update()
        # Put it on the stats var
        self.stats = glances_monitors.get()

        return self.stats

    def get_alert(self, nbprocess=0, countmin=None, countmax=None):
        # Return the alert status relative to the process number
        if (countmin is None):
            countmin = nbprocess
        if (countmax is None):
            countmax = nbprocess
        if (nbprocess > 0):
            if (int(countmin) <= int(nbprocess) <= int(countmax)):
                return 'OK'
            else:
                return 'WARNING'
        else:
            if (int(countmin) == 0):
                return 'OK'
            else:
                return 'CRITICAL'

    def msg_curse(self, args=None):
        """
        Return the dict to display in the curse interface
        """
        # Init the return message
        ret = []

        # Build the string message
        for m in self.stats:
            msg = "{0:<16} ".format(str(m['description']))
            ret.append(self.curse_add_line(
                msg, self.get_alert(m['count'], m['countmin'], m['countmax'])))
            msg = "{0:<3} ".format(m['count'] if (m['count'] > 1) else "")
            ret.append(self.curse_add_line(msg))
            msg = "{0:13} ".format(_("RUNNING") if (m['count'] >= 1) else _("NOT RUNNING"))
            ret.append(self.curse_add_line(msg))
            msg = "{0}".format(m['result'] if (m['count'] >= 1) else "")
            ret.append(self.curse_add_line(msg))
            ret.append(self.curse_new_line())

        # Delete the last empty line
        try:
            ret.pop()
        except IndexError:
            pass

        return ret

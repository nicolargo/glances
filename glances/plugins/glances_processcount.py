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

from glances_plugin import GlancesPlugin
from glances.core.glances_globals import glances_processes, process_auto_by


class Plugin(GlancesPlugin):
    """
    Glances's processes Plugin

    stats is a list
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
        self.line_curse = 2

        # Note: 'glances_processes' is already init in the glances_processes.py script

    def update(self):
        """
        Update processes stats
        """

        # Here, update is call for processcount AND processlist
        glances_processes.update()

        # Return the processes count
        self.stats = glances_processes.getcount()

        return self.stats

    def msg_curse(self, args=None):
        """
        Return the dict to display in the curse interface
        """

        # Init the return message
        ret = []

        # Build the string message
        # Header
        msg = "{0} ".format(_("TASKS"))
        ret.append(self.curse_add_line(msg, "TITLE"))
        # Compute processes
        other = self.stats['total']
        msg = "{0}".format(str(self.stats['total']))
        ret.append(self.curse_add_line(msg))

        if ('thread' in self.stats):
            msg = " ({0} {1}),".format(str(self.stats['thread']), _("thr"))
            ret.append(self.curse_add_line(msg))

        if ('running' in self.stats):
            other -= self.stats['running']
            msg = " {0} {1},".format(str(self.stats['running']), _("run"))
            ret.append(self.curse_add_line(msg))

        if ('sleeping' in self.stats):
            other -= self.stats['sleeping']
            msg = " {0} {1},".format(str(self.stats['sleeping']), _("slp"))
            ret.append(self.curse_add_line(msg))

        msg = " {0} {1} ".format(str(other), _("oth"))
        ret.append(self.curse_add_line(msg))

        # Display sort information
        if (args.process_sorted_by == 'auto'):
            msg = "{0}".format(_("sorted automatically"))
            ret.append(self.curse_add_line(msg))
            msg = " {0} {1}".format(_("by"), process_auto_by)
            ret.append(self.curse_add_line(msg))
        else:
            msg = "{0} {1}".format(_("sorted by"), args.process_sorted_by)
            ret.append(self.curse_add_line(msg))

        # Return the message with decoration
        return ret

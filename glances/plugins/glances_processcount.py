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
from _processes import processes


class Plugin(GlancesPlugin):
    """
    Glances's processes Plugin

    stats is a list
    """

    def __init__(self):
        GlancesPlugin.__init__(self)

        # Nothing else to do...
        # 'processes' is already init in the _processes.py script

        # We want to display the stat in the curse interface
        self.display_curse = True
        # Set the message position
        # It is NOT the curse position but the Glances column/line
        # Enter -1 to right align 
        self.column_curse = 1
        # Enter -1 to diplay bottom
        self.line_curse = 2
        

    def update(self):
        """
        Update processes stats
        """

        # Here, update is call for processcount AND processlist
        processes.update()

        self.stats = processes.getcount()


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
        else:
            msg = "{0}".format(_("sorted by ") + args.process_sorted_by)
        ret.append(self.curse_add_line(msg, 'UNDERLINE'))

        # Return the message with decoration 
        return ret

# -*- coding: utf-8 -*-
#
# This file is part of Glances.
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

"""Process count plugin."""

# Import Glances libs
from glances.core.glances_globals import glances_processes
from glances.plugins.glances_plugin import GlancesPlugin


class Plugin(GlancesPlugin):

    """Glances' processes plugin.

    stats is a list
    """

    def __init__(self, args=None):
        """Init the plugin."""
        GlancesPlugin.__init__(self, args=args)

        # We want to display the stat in the curse interface
        self.display_curse = True
        # Set the message position
        # It is NOT the curse position but the Glances column/line
        # Enter -1 to right align
        self.column_curse = 1
        # Enter -1 to diplay bottom
        self.line_curse = 2

        # Note: 'glances_processes' is already init in the glances_processes.py script

    def reset(self):
        """Reset/init the stats."""
        self.stats = {}

    def update(self):
        """Update processes stats using the input method."""
        # Reset stats
        self.reset()

        if self.get_input() == 'local':
            # Update stats using the standard system lib
            # Here, update is call for processcount AND processlist
            glances_processes.update()

            # Return the processes count
            self.stats = glances_processes.getcount()
        elif self.get_input() == 'snmp':
            # Update stats using SNMP
            # !!! TODO
            pass

        return self.stats

    def msg_curse(self, args=None):
        """Return the dict to display in the curse interface."""
        # Init the return message
        ret = []

        # Only process if stats exist and display plugin enable...
        # if self.stats == {} or args.disable_process:
        #     return ret

        if args.disable_process:
            msg = _("PROCESSES DISABLED (press 'z' to display)")
            ret.append(self.curse_add_line(msg))
            return ret

        if self.stats == {}:
            return ret

        # Build the string message
        # Header
        msg = _("TASKS ")
        ret.append(self.curse_add_line(msg, "TITLE"))
        # Compute processes
        other = self.stats['total']
        msg = str(self.stats['total'])
        ret.append(self.curse_add_line(msg))

        if 'thread' in self.stats:
            msg = _(" ({0} thr),").format(self.stats['thread'])
            ret.append(self.curse_add_line(msg))

        if 'running' in self.stats:
            other -= self.stats['running']
            msg = _(" {0} run,").format(self.stats['running'])
            ret.append(self.curse_add_line(msg))

        if 'sleeping' in self.stats:
            other -= self.stats['sleeping']
            msg = _(" {0} slp,").format(self.stats['sleeping'])
            ret.append(self.curse_add_line(msg))

        msg = _(" {0} oth ").format(other)
        ret.append(self.curse_add_line(msg))

        # Display sort information
        try:
            args.process_sorted_by
        except AttributeError:
            args.process_sorted_by = glances_processes.getsortkey()
        if args.process_sorted_by == 'auto':
            msg = _("sorted automatically")
            ret.append(self.curse_add_line(msg))
            msg = _(" by {0}").format(glances_processes.getsortkey())
            ret.append(self.curse_add_line(msg))
        else:
            msg = _("sorted by {0}").format(args.process_sorted_by)
            ret.append(self.curse_add_line(msg))

        # Return the message with decoration
        return ret

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

"""
Help plugin.

Just a stupid plugin to display the help screen.
"""

# Import Glances libs
from glances.core.glances_globals import appname, psutil_version, version
from glances.plugins.glances_plugin import GlancesPlugin


class Plugin(GlancesPlugin):

    """Glances' help plugin."""

    def __init__(self, args=None, config=None):
        """Init the plugin."""
        GlancesPlugin.__init__(self, args=args)

        # Set the config instance
        self.config = config

        # We want to display the stat in the curse interface
        self.display_curse = True

    def update(self):
        """No stats. It is just a plugin to display the help."""
        pass

    def msg_curse(self, args=None):
        """Return the list to display in the curse interface."""
        # Init the return message
        ret = []

        # Build the string message
        # Header
        msg = '{0} {1}'.format(appname.title(), version)
        ret.append(self.curse_add_line(msg, "TITLE"))
        msg = ' with PSutil {0}'.format(psutil_version)
        ret.append(self.curse_add_line(msg))
        ret.append(self.curse_new_line())

        # Configuration file path
        try:
            msg = 'Configuration file: {0}'.format(self.config.loaded_config_file)
        except AttributeError:
            pass
        else:
            ret.append(self.curse_new_line())
            ret.append(self.curse_add_line(msg))
            ret.append(self.curse_new_line())

        # Keys
        msg_col = ' {0:1}  {1:35}'
        msg_col2 = '   {0:1}  {1:35}'

        ret.append(self.curse_new_line())
        msg = msg_col.format('a', 'Sort processes automatically')
        ret.append(self.curse_add_line(msg))
        msg = msg_col2.format('b', 'Bytes or bits for network I/O')
        ret.append(self.curse_add_line(msg))
        ret.append(self.curse_new_line())
        msg = msg_col.format('c', 'Sort processes by CPU%')
        ret.append(self.curse_add_line(msg))
        msg = msg_col2.format('l', 'Show/hide alert logs')
        ret.append(self.curse_add_line(msg))
        ret.append(self.curse_new_line())
        msg = msg_col.format('m', 'Sort processes by MEM%')
        ret.append(self.curse_add_line(msg))
        msg = msg_col2.format('w', 'Delete warning alerts')
        ret.append(self.curse_add_line(msg))
        ret.append(self.curse_new_line())
        msg = msg_col.format('u', 'Sort processes by USER')
        ret.append(self.curse_add_line(msg))
        msg = msg_col2.format('x', 'Delete warning and critical alerts')
        ret.append(self.curse_add_line(msg))
        ret.append(self.curse_new_line())
        msg = msg_col.format('p', 'Sort processes by name')
        ret.append(self.curse_add_line(msg))
        msg = msg_col2.format('1', 'Global CPU or per-CPU stats')
        ret.append(self.curse_add_line(msg))
        ret.append(self.curse_new_line())
        msg = msg_col.format('i', 'Sort processes by I/O rate')
        ret.append(self.curse_add_line(msg))
        msg = msg_col2.format('D', 'Enable/disable Docker stats')
        ret.append(self.curse_add_line(msg))
        ret.append(self.curse_new_line())
        msg = msg_col.format('t', 'Sort processes by TIME')
        ret.append(self.curse_add_line(msg))
        msg = msg_col2.format('T', 'View network I/O as combination')
        ret.append(self.curse_add_line(msg))
        ret.append(self.curse_new_line())
        msg = msg_col.format('d', 'Show/hide disk I/O stats')
        ret.append(self.curse_add_line(msg))
        msg = msg_col2.format('U', 'View cumulative network I/O')
        ret.append(self.curse_add_line(msg))
        ret.append(self.curse_new_line())
        msg = msg_col.format('f', 'Show/hide filesystem stats')
        ret.append(self.curse_add_line(msg))
        msg = msg_col2.format('F', 'Show filesystem free space')
        ret.append(self.curse_add_line(msg))
        ret.append(self.curse_new_line())
        msg = msg_col.format('n', 'Show/hide network stats')
        ret.append(self.curse_add_line(msg))
        msg = msg_col2.format('g', 'Generate graphs for current history')
        ret.append(self.curse_add_line(msg))
        ret.append(self.curse_new_line())
        msg = msg_col.format('s', 'Show/hide sensors stats')
        ret.append(self.curse_add_line(msg))
        msg = msg_col2.format('r', 'Reset history')
        ret.append(self.curse_add_line(msg))
        ret.append(self.curse_new_line())
        msg = msg_col.format('2', 'Show/hide left sidebar')
        ret.append(self.curse_add_line(msg))
        msg = msg_col2.format('h', 'Show/hide this help screen')
        ret.append(self.curse_add_line(msg))
        ret.append(self.curse_new_line())
        msg = msg_col.format('z', 'Enable/disable processes stats')
        ret.append(self.curse_add_line(msg))
        msg = msg_col2.format('q', 'Quit (Esc or Ctrl-c also work)')
        ret.append(self.curse_add_line(msg))
        ret.append(self.curse_new_line())
        msg = msg_col.format('3', 'Enable/disable quick look plugin')
        ret.append(self.curse_add_line(msg))
        ret.append(self.curse_new_line())
        msg = msg_col.format('e', 'Enable/disable top extended stats')
        ret.append(self.curse_add_line(msg))
        ret.append(self.curse_new_line())
        msg = msg_col.format('/', 'Enable/disable short processes name')
        ret.append(self.curse_add_line(msg))

        ret.append(self.curse_new_line())
        ret.append(self.curse_new_line())
        msg = '{0}: {1}'.format('ENTER', 'Edit the process filter pattern')
        ret.append(self.curse_add_line(msg))

        # Return the message with decoration
        return ret

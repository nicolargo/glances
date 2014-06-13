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

"""
Help plugin.

Just a stupid plugin to display the help screen.
"""

# Import Glances libs
from glances.core.glances_globals import appname, psutil_version, version
from glances.plugins.glances_plugin import GlancesPlugin


class Plugin(GlancesPlugin):

    """Glances' help plugin."""

    def __init__(self, args=None):
        """Init the plugin."""
        GlancesPlugin.__init__(self, args=args)

        # We want to display the stat in the curse interface
        self.display_curse = True
        # Set the message position
        # It is NOT the curse position but the Glances column/line
        # Enter -1 to right align
        self.column_curse = 0
        # Enter -1 to diplay bottom
        self.line_curse = 0

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
        msg = _(" with psutil {0}").format(psutil_version)
        ret.append(self.curse_add_line(msg))
        ret.append(self.curse_new_line())

        # Keys
        msg_col = ' {0:1}  {1:35}'
        msg_col2 = '   {0:1}  {1:35}'

        ret.append(self.curse_new_line())
        msg = msg_col.format(_("a"), _("Sort processes automatically"))
        ret.append(self.curse_add_line(msg))
        msg = msg_col2.format(_("b"), _("Bytes or bits for network I/O"))
        ret.append(self.curse_add_line(msg))
        ret.append(self.curse_new_line())
        msg = msg_col.format(_("c"), _("Sort processes by CPU%"))
        ret.append(self.curse_add_line(msg))
        msg = msg_col2.format(_("l"), _("Show/hide logs (alerts)"))
        ret.append(self.curse_add_line(msg))
        ret.append(self.curse_new_line())
        msg = msg_col.format(_("m"), _("Sort processes by MEM%"))
        ret.append(self.curse_add_line(msg))
        msg = msg_col2.format(_("w"), _("Delete warning alerts"))
        ret.append(self.curse_add_line(msg))
        ret.append(self.curse_new_line())
        msg = msg_col.format(_("p"), _("Sort processes by name"))
        ret.append(self.curse_add_line(msg))
        msg = msg_col2.format(_("x"), _("Delete warning and critical alerts"))
        ret.append(self.curse_add_line(msg))
        ret.append(self.curse_new_line())
        msg = msg_col.format(_("i"), _("Sort processes by I/O rate"))
        ret.append(self.curse_add_line(msg))
        msg = msg_col2.format(_("1"), _("Global CPU or per-CPU stats"))
        ret.append(self.curse_add_line(msg))
        ret.append(self.curse_new_line())
        msg = msg_col.format(_("d"), _("Show/hide disk I/O stats"))
        ret.append(self.curse_add_line(msg))
        msg = msg_col2.format(_("h"), _("Show/hide this help screen"))
        ret.append(self.curse_add_line(msg))
        ret.append(self.curse_new_line())
        msg = msg_col.format(_("f"), _("Show/hide file system stats"))
        ret.append(self.curse_add_line(msg))
        msg = msg_col2.format(_("t"), _("View network I/O as combination"))
        ret.append(self.curse_add_line(msg))
        ret.append(self.curse_new_line())
        msg = msg_col.format(_("n"), _("Show/hide network stats"))
        ret.append(self.curse_add_line(msg))
        msg = msg_col2.format(_("u"), _("View cumulative network I/O"))
        ret.append(self.curse_add_line(msg))
        ret.append(self.curse_new_line())
        msg = msg_col.format(_("s"), _("Show/hide sensors stats"))
        ret.append(self.curse_add_line(msg))
        msg = msg_col2.format(_("z"), _("Enable/disable processes stats"))
        ret.append(self.curse_add_line(msg))
        ret.append(self.curse_new_line())
        msg = msg_col.format(_("q"), _("Quit (Esc and Ctrl-C also work)"))
        ret.append(self.curse_add_line(msg))

        # Return the message with decoration
        return ret

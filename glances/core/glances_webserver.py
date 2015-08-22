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

"""Glances Web Interface (Bottle based)."""

# Import Glances libs
from glances.core.glances_globals import is_windows
from glances.core.glances_processes import glances_processes
from glances.core.glances_stats import GlancesStats
from glances.outputs.glances_bottle import GlancesBottle


class GlancesWebServer(object):

    """This class creates and manages the Glances Web server session."""

    def __init__(self, config=None, args=None):
        # Init stats
        self.stats = GlancesStats(config)

        if not is_windows and args.no_kernel_threads:
            # Ignore kernel threads in process list
            glances_processes.disable_kernel_threads()

        # Initial system informations update
        self.stats.update()

        # Init the Bottle Web server
        self.web = GlancesBottle(args=args)

    def serve_forever(self):
        """Main loop for the Web server."""
        self.web.start(self.stats)

    def end(self):
        """End of the Web server."""
        self.web.end()
        self.stats.end()

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
"""
Glances Web Interface (Bottle based)
"""

# Import Glances libs
from glances.core.glances_stats import GlancesStats
from glances.outputs.glances_bottle import glancesBottle


class GlancesWebServer():
    """
    This class creates and manages the Glances Web Server session
    """

    def __init__(self, config=None, args=None):

        # Init stats
        self.stats = GlancesStats(config)

        # Initial system informations update
        self.stats.update()

        # Init the Bottle Web server
        self.web = glancesBottle(args=args)

    def serve_forever(self):
        """
        Main loop for the Web Server
        """
        self.web.start(self.stats)

    def end(self):
        """
        End of the Web Server
        """
        self.web.end()

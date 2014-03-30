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
import sys
try:
    from bottle import Bottle, template
except ImportError:
    print('Bottle module not found. Glances cannot start in web server mode.')
    sys.exit(1)

# Import Glances lib
from glances.core.glances_timer import Timer
from glances.core.glances_globals import glances_logs, glances_processes


class glancesBottle:
    """
    This class manage the Bottle Web Server
    """

    def __init__(self, args=None):

        # Init args
        self.args = args

        # Init stats
        # Will be updated within Bottle route
        self.stats = None

        # Init Bottle
        self._host = 'localhost'
        self._port = 8080
        self._app = Bottle()
        self._route()

    def _route(self):
        """
        Define route
        """
        self._app.route('/', method="GET", callback=self._index)

    def start(self, stats):
        # Init stats
        self.stats = stats

        # Start the Bottle
        self._app.run(host=self._host, port=self._port)

    def end(self):
        # End the Bottle
        pass

    def _index(self):
        print "DEBUG: %s " % self.stats.get_plugin('system')
        return "Hello Glances"

    def display(self, stats, cs_status="None"):
        """
        Display stats on the screen

        stats: Stats database to display
        cs_status:
            "None": standalone or server mode
            "Connected": Client is connected to the server
            "Disconnected": Client is disconnected from the server

        Return:
            True if the stats have been displayed
            False if the help have been displayed
        """
        pass


    def display_plugin(self, plugin_stats, display_optional=True, max_y=65535):
        """
        Display the plugin_stats on the screen
        If display_optional=True display the optional stats
        max_y do not display line > max_y
        """
        # Exit if:
        # - the plugin_stats message is empty
        # - the display tag = False
        if ((plugin_stats['msgdict'] == []) 
            or (not plugin_stats['display'])):
            # Display the next plugin at the current plugin position
            try:
                self.column_to_x[plugin_stats['column'] + 1] = self.column_to_x[plugin_stats['column']]
                self.line_to_y[plugin_stats['line'] + 1] = self.line_to_y[plugin_stats['line']]
            except Exception, e:
                pass
            # Exit
            return 0

        pass

    def update(self, stats, cs_status="None"):
        """
        Update the Web interface
        stats: Stats database to display
        cs_status:
            "None": standalone or server mode
            "Connected": Client is connected to the server
            "Disconnected": Client is disconnected from the server
        """
        pass

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
import os
import sys
try:
    from bottle import Bottle, template, static_file, TEMPLATE_PATH
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

        # Update the template path (glances/outputs/bottle)
        TEMPLATE_PATH.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'bottle'))

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
        # Update the stat
        self.stats.update()
        # Display
        return self.display(self.stats)

    def display(self, stats):
        """
        Display stats on the screen

        stats: Stats database to display
        """
        html = template('header')
        html += template('newline')
        html += template(self.stats.get_plugin('system').get_bottle(self.args), 
                         **self.stats.get_plugin('system').get_raw())
        html += template(self.stats.get_plugin('uptime').get_bottle(self.args))
        html += template('endline')
        html += template('footer')

        return html

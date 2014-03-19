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
Manage the Glances' client 
"""

# Import system libs
import sys
import socket
import json

# Import Glances libs
from glances.core.glances_globals import __version__
from glances.outputs.glances_curses import glancesCurses
from glances.core.glances_stats import GlancesStatsClient

try:
    # Python 2
    from xmlrpclib import ServerProxy, ProtocolError
except ImportError:
    # Python 3
    from xmlrpc.client import ServerProxy, ProtocolError


class GlancesClient():
    """
    This class creates and manages the TCP client
    """

    def __init__(self,
                 args=None,
                 server_address="localhost", server_port=61209,
                 username="glances", password=""):
        # Build the URI
        if (password != ""):
            uri = 'http://%s:%s@%s:%d' % (username, password, server_address, server_port)
        else:
            uri = 'http://%s:%d' % (server_address, server_port)

        # Try to connect to the URI
        try:
            self.client = ServerProxy(uri)
        except Exception:
            print(_("Error: creating client socket") + " %s" % uri)
            pass

        # Init stats
        self.stats = GlancesStatsClient()

        # Init screen
        self.screen = glancesCurses(args=args)

    def login(self):
        """
        Logon to the server
        """
        try:
            client_version = self.client.init()
        except socket.error as err:
            print("{} ({})".format(_("Error: Connection to server failed"), err))
            sys.exit(2)
        except ProtocolError as err:
            if (str(err).find(" 401 ") > 0):
                print("{} ({})".format(_("Error: Connection to server failed"), _("Bad password")))
            else:
                print("{} ({})".format(_("Error: Connection to server failed"), err))
            sys.exit(2)
        # Debug
        # print "Server version: {}\nClient version: {}\n".format(__version__, client_version)
        return __version__[:3] == client_version[:3]

    def update(self):
        """
        Get stats from server
        """
        try:
            server_stats = json.loads(self.client.getAll())
        except Exception:
            server_stats = {}

        # Put it in the internal dict
        self.stats.update(server_stats)

    def serve_forever(self):
        """
        Main loop
        """
        while True:
            # Update the stats
            self.update()

            # Update the screen
            self.screen.update(self.stats, cs_status="Connected")

    def close(self):
        """
        End of the client session
        """
        pass

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

# Import system libs
import sys
import socket
import json

# Import Glances libs
from ..core.glances_globals import __version__
from ..core.glances_limits import glancesLimits
from ..core.glances_monitor_list import monitorList
from ..core.glances_stats import GlancesStatsServer
from ..core.glances_timer import Timer

# Other imports
try:
    # Python 2
    from SimpleXMLRPCServer import SimpleXMLRPCRequestHandler
    from SimpleXMLRPCServer import SimpleXMLRPCServer
except ImportError:
    # Python 3
    from xmlrpc.server import SimpleXMLRPCRequestHandler
    from xmlrpc.server import SimpleXMLRPCServer

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

    def __init__(self, server_address, server_port=61209,
                 username="glances", password=""):
        # Build the URI
        if password != "":
            uri = 'http://%s:%s@%s:%d' % (username, password, server_address, server_port)
        else:
            uri = 'http://%s:%d' % (server_address, server_port)

        # Try to connect to the URI
        try:
            self.client = ServerProxy(uri)
        except Exception:
            print(_("Error: creating client socket") + " %s" % uri)
            pass
        return

    def client_init(self):
        try:
            client_version = self.client.init()
        except ProtocolError as err:
            if str(err).find(" 401 ") > 0:
                print(_("Error: Connection to server failed. Bad password."))
                sys.exit(-1)
            else:
                print(_("Error: Connection to server failed. Unknown error."))
                sys.exit(-1)
        return __version__[:3] == client_version[:3]

    def client_get_limits(self):
        try:
            serverlimits = json.loads(self.client.getAllLimits())
        except Exception:
            return {}
        else:
            return serverlimits

    def client_get_monitored(self):
        try:
            servermonitored = json.loads(self.client.getAllMonitored())
        except Exception:
            return []
        else:
            return servermonitored

    def client_get(self):
        try:
            stats = json.loads(self.client.getAll())
        except Exception:
            return {}
        else:
            return stats

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

"""Manage the Glances client browser (list of Glances server)."""

# Import system libs
import json
import socket
try:
    from xmlrpc.client import Transport, ServerProxy, ProtocolError, Fault
except ImportError:
    # Python 2
    from xmlrpclib import Transport, ServerProxy, ProtocolError, Fault

# Import Glances libs
from glances.core.glances_globals import logger
from glances.outputs.glances_curses import GlancesCurses
from glances.core.glances_autodiscover import GlancesAutoDiscoverServer
from glances.core.glances_client import GlancesClientTransport


class GlancesClientBrowser(object):

    """This class creates and manages the TCP client browser (servers' list)."""

    def __init__(self, config=None, args=None):
        # Store the arg/config
        self.args = args
        self.config = config

        # Start the autodiscover mode (Zeroconf listener)
        if self.args.autodiscover:
            self.autodiscover_server = GlancesAutoDiscoverServer()

        # Init screen
        self.screen = GlancesCurses(args=self.args)

    def get_servers_list(self):
        """Return the current server list (dict of dict)"""
        if self.args.autodiscover:
            return self.autodiscover_server.get_servers_list()
        else:
            return {}

    def serve_forever(self):
        """Main client loop."""
        while True:
            # No need to update the server list
            # It's done by the GlancesAutoDiscoverListener class (glances_autodiscover.py)
            # For each server in the list, grab elementary stats (CPU, LOAD, MEM)
            # logger.debug(self.get_servers_list())
            try:
                iteritems = self.get_servers_list().iteritems()
            except AttributeError:
                iteritems = self.get_servers_list().items()
            # Dictionnary can change size during iteration...
            try:
                for k, v in iteritems:
                    # !!! Perhaps, it will be better to store the ServerProxy instance in the get_servers_list
                    uri = 'http://%s:%s' % (self.get_servers_list()
                                            [k]['ip'], self.get_servers_list()[k]['port'])
                    # Configure the server timeout to 3 seconds
                    t = GlancesClientTransport()
                    t.set_timeout(3)
                    # !!! How to manage password protection ??? Disable autodiscover if password is set ?
                    try:
                        s = ServerProxy(uri, t)
                    except Exception as e:
                        logger.warning(
                            _("Couldn't create socket {0}: {1}").format(uri, e))
                    else:
                        try:
                            # LOAD
                            self.get_servers_list()[k]['load_min5'] = json.loads(
                                s.getLoad())['min5']
                            # CPU%
                            self.get_servers_list()[k][
                                'cpu_percent'] = 100 - json.loads(s.getCpu())['idle']
                            # MEM%
                            self.get_servers_list()[k]['mem_percent'] = json.loads(
                                s.getMem())['percent']
                            # OS (human readable name)
                            self.get_servers_list()[k]['hr_name'] = json.loads(
                                s.getSystem())['hr_name']
                        except (socket.error, Fault, KeyError) as e:
                            logger.warning(
                                _("Can not grab stats form {0}: {1}").format(uri, e))
            except RuntimeError:
                logger.debug(
                    _("Server list dictionnary change inside the loop (wait next update)"))

            # Update the screen
            self.screen.update_browser(self.get_servers_list())

    def end(self):
        """End of the client session."""
        pass

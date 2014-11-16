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
    from xmlrpc.client import ServerProxy, Fault, ProtocolError
except ImportError:
    # Python 2
    from xmlrpclib import ServerProxy, Fault, ProtocolError

# Import Glances libs
from glances.core.glances_globals import logger
from glances.outputs.glances_curses import GlancesCursesBrowser
from glances.core.glances_autodiscover import GlancesAutoDiscoverServer
from glances.core.glances_client import GlancesClientTransport, GlancesClient


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
        self.screen = GlancesCursesBrowser(args=self.args)

    def get_servers_list(self):
        """Return the current server list (list of dict)"""
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
                for v in self.get_servers_list():
                    # !!! Perhaps, it will be better to store the ServerProxy instance in the get_servers_list
                    uri = 'http://%s:%s' % (v['ip'], v['port'])
                    t = GlancesClientTransport()
                    t.set_timeout(3)
                    # Get common stats
                    try:
                        s = ServerProxy(uri, t)
                    except Exception as e:
                        logger.warning(
                            "Client browser couldn't create socket {0}: {1}".format(uri, e))
                    else:
                        try:
                            # LOAD
                            v['load_min5'] = json.loads(s.getLoad())['min5']
                            # CPU%
                            v['cpu_percent'] = 100 - \
                                json.loads(s.getCpu())['idle']
                            # MEM%
                            v['mem_percent'] = json.loads(
                                s.getMem())['percent']
                            # OS (Human Readable name)
                            v['hr_name'] = json.loads(s.getSystem())['hr_name']
                        except (socket.error, Fault, KeyError) as e:
                            logger.warning(
                                "Can not grab stats form {0}: {1}".format(uri, e))
                        except ProtocolError as e:
                            logger.debug(
                                "Password protected server. Can not grab stats from {0}: {1}".format(uri, e))
            # List can change size during iteration...
            except RuntimeError:
                logger.debug(
                    "Server list dictionnary change inside the loop (wait next update)")

            # Update the screen (list or Glances client)
            if self.screen.get_active() is None:
                #  Display the Glances browser
                self.screen.update(self.get_servers_list())
            else:
                # Display the Glance client on the selected server
                logger.info("Connect Glances client to the %s server" %
                            self.get_servers_list()[self.screen.get_active()]['key'])

                # Init the client
                args_server = self.args

                # Overwrite connection setting
                args_server.client = self.get_servers_list(
                )[self.screen.get_active()]['ip']
                args_server.port = self.get_servers_list()[self.screen.get_active()][
                    'port']
                client = GlancesClient(config=self.config,
                                       args=args_server)

                # Test if client and server are in the same major version
                if not client.login():
                    logger.error(
                        "The server version is not compatible with the client")

                # Start the client loop
                client.serve_forever(return_to_browser=True)

                logger.debug("Disconnect Glances client from the %s server" %
                             self.get_servers_list()[self.screen.get_active()]['key'])
                self.screen.set_active(None)

    def end(self):
        """End of the client browser session."""
        self.screen.end()

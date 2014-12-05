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
from glances.core.glances_client import GlancesClient, GlancesClientTransport
from glances.core.glances_staticlist import GlancesStaticServer


class GlancesClientBrowser(object):

    """This class creates and manages the TCP client browser (servers' list)."""

    def __init__(self, config=None, args=None):
        # Store the arg/config
        self.args = args
        self.config = config

        # Init the static server list (if defined)
        self.static_server = GlancesStaticServer(config=self.config)

        # Start the autodiscover mode (Zeroconf listener)
        if not self.args.disable_autodiscover:
            self.autodiscover_server = GlancesAutoDiscoverServer()
        else:
            self.autodiscover_server = None

        # Init screen
        self.screen = GlancesCursesBrowser(args=self.args)

    def get_servers_list(self):
        """
        Return the current server list (list of dict)
        Merge of static + autodiscover servers list
        """
        ret = []

        if self.args.browser:
            ret = self.static_server.get_servers_list()
            if self.autodiscover_server is not None:
                ret = self.static_server.get_servers_list() + self.autodiscover_server.get_servers_list()

        return ret

    def serve_forever(self):
        """Main client loop."""
        while True:
            # No need to update the server list
            # It's done by the GlancesAutoDiscoverListener class (glances_autodiscover.py)
            # Or define staticaly in the configuration file (module glances_staticlist.py)
            # For each server in the list, grab elementary stats (CPU, LOAD, MEM, OS...)
            # logger.debug(self.get_servers_list())
            try:
                for v in self.get_servers_list():
                    # Do not retreive stats for statics server
                    # Why ? Because for each offline servers, the timeout will be reached
                    # So ? The curse interface freezes
                    if (v['type'] == 'STATIC' and v['status'] in ['UNKNOWN', 'SNMP', 'OFFLINE']):
                        continue

                    # Select the connection mode (with or without password)
                    if v['password'] != "":
                        uri = 'http://{0}:{1}@{2}:{3}'.format(v['username'], v['password'],
                                                              v['ip'], v['port'])
                    else:
                        uri = 'http://{0}:{1}'.format(v['ip'], v['port'])

                    # Try to connect to the server
                    t = GlancesClientTransport()
                    t.set_timeout(3)

                    # Get common stats
                    try:
                        s = ServerProxy(uri, transport=t)
                    except Exception as e:
                        logger.warning(
                            "Client browser couldn't create socket {0}: {1}".format(uri, e))
                    else:
                        # Mandatory stats
                        try:
                            # CPU%
                            cpu_percent = 100 - json.loads(s.getCpu())['idle']
                            v['cpu_percent'] = '{0:.1f}'.format(cpu_percent)
                            # MEM%
                            v['mem_percent'] = json.loads(s.getMem())['percent']
                            # OS (Human Readable name)
                            v['hr_name'] = json.loads(s.getSystem())['hr_name']
                        except (socket.error, Fault, KeyError) as e:
                            logger.debug(
                                "Error while grabbing stats form {0}: {1}".format(uri, e))
                            v['status'] = 'OFFLINE'
                        except ProtocolError as e:
                            if str(e).find(" 401 ") > 0:
                                # Error 401 (Authentication failed)
                                # Password is not the good one...
                                v['password'] = None
                                v['status'] = 'PROTECTED'
                            else:
                                v['status'] = 'OFFLINE'
                            logger.debug(
                                "Cannot grab stats from {0}: {1}".format(uri, e))
                        else:
                            # Status
                            v['status'] = 'ONLINE'

                            # Optional stats (load is not available on Windows OS)
                            try:
                                # LOAD
                                load_min5 = json.loads(s.getLoad())['min5']
                                v['load_min5'] = '{0:.2f}'.format(load_min5)
                            except Exception as e:
                                logger.warning(
                                    "Error while grabbing stats form {0}: {1}".format(uri, e))
            # List can change size during iteration...
            except RuntimeError:
                logger.debug(
                    "Server list dictionnary change inside the loop (wait next update)")

            # Update the screen (list or Glances client)
            if self.screen.get_active() is None:
                #  Display the Glances browser
                self.screen.update(self.get_servers_list())
            else:
                # Display the Glances client for the selected server
                logger.debug("Selected server: %s" % self.get_servers_list()[self.screen.get_active()])

                # Connection can take time
                # Display a popup
                self.screen.display_popup(_("Connect to %s:%s" % (v['name'], v['port'])), duration=1)

                # A password is needed to access to the server's stats
                if self.get_servers_list()[self.screen.get_active()]['password'] is None:
                    from hashlib import sha256
                    # Display a popup to enter password
                    clear_password = self.screen.display_popup(_("Password needed for %s: " % v['name']), is_input=True)
                    # Hash with SHA256
                    encoded_password = sha256(clear_password).hexdigest()
                    # Store the password for the selected server
                    self.set_in_selected('password', encoded_password)

                # Display the Glance client on the selected server
                logger.info("Connect Glances client to the %s server" %
                            self.get_servers_list()[self.screen.get_active()]['key'])

                # Init the client
                args_server = self.args

                # Overwrite connection setting
                args_server.client = self.get_servers_list()[self.screen.get_active()]['ip']
                args_server.port = self.get_servers_list()[self.screen.get_active()]['port']
                args_server.username = self.get_servers_list()[self.screen.get_active()]['username']
                args_server.password = self.get_servers_list()[self.screen.get_active()]['password']
                client = GlancesClient(config=self.config,
                                       args=args_server)

                # Test if client and server are in the same major version
                if not client.login(return_to_browser=True):
                    self.screen.display_popup(_("Sorry, cannot connect to %s (see log file for additional information)" % v['name']))

                    # Set the ONLINE status for the selected server
                    self.set_in_selected('status', 'OFFLINE')
                else:
                    # Start the client loop
                    # Return connection type: 'glances' or 'snmp'
                    connection_type = client.serve_forever(return_to_browser=True)

                    try:
                        logger.debug("Disconnect Glances client from the %s server" %
                                     self.get_servers_list()[self.screen.get_active()]['key'])
                    except IndexError:
                        # Server did not exist anymore
                        pass
                    else:
                        # Set the ONLINE status for the selected server
                        if connection_type == 'snmp':
                            self.set_in_selected('status', 'SNMP')
                        else:
                            self.set_in_selected('status', 'ONLINE')

                # Return to the browser (no server selected)
                self.screen.set_active(None)

    def set_in_selected(self, key, value):
        """Set the (key, value) for the selected server in the list"""
        # Static list then dynamic one
        if self.screen.get_active() >= len(self.static_server.get_servers_list()):
            self.autodiscover_server.set_server(self.screen.get_active() - len(self.static_server.get_servers_list()),
                                                key,
                                                value)
        else:
            self.static_server.set_server(self.screen.get_active(),
                                          key,
                                          value)

    def end(self):
        """End of the client browser session."""
        self.screen.end()

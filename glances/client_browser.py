# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2017 Nicolargo <nicolas@nicolargo.com>
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

import json
import socket
import threading

from glances.compat import Fault, ProtocolError, ServerProxy
from glances.autodiscover import GlancesAutoDiscoverServer
from glances.client import GlancesClient, GlancesClientTransport
from glances.logger import logger, LOG_FILENAME
from glances.password_list import GlancesPasswordList as GlancesPassword
from glances.static_list import GlancesStaticServer
from glances.outputs.glances_curses_browser import GlancesCursesBrowser


class GlancesClientBrowser(object):

    """This class creates and manages the TCP client browser (servers list)."""

    def __init__(self, config=None, args=None):
        # Store the arg/config
        self.args = args
        self.config = config
        self.static_server = None
        self.password = None

        # Load the configuration file
        self.load()

        # Start the autodiscover mode (Zeroconf listener)
        if not self.args.disable_autodiscover:
            self.autodiscover_server = GlancesAutoDiscoverServer()
        else:
            self.autodiscover_server = None

        # Init screen
        self.screen = GlancesCursesBrowser(args=self.args)

    def load(self):
        """Load server and password list from the confiuration file."""
        # Init the static server list (if defined)
        self.static_server = GlancesStaticServer(config=self.config)

        # Init the password list (if defined)
        self.password = GlancesPassword(config=self.config)

    def get_servers_list(self):
        """Return the current server list (list of dict).

        Merge of static + autodiscover servers list.
        """
        ret = []

        if self.args.browser:
            ret = self.static_server.get_servers_list()
            if self.autodiscover_server is not None:
                ret = self.static_server.get_servers_list() + self.autodiscover_server.get_servers_list()

        return ret

    def __get_uri(self, server):
        """Return the URI for the given server dict."""
        # Select the connection mode (with or without password)
        if server['password'] != "":
            if server['status'] == 'PROTECTED':
                # Try with the preconfigure password (only if status is PROTECTED)
                clear_password = self.password.get_password(server['name'])
                if clear_password is not None:
                    server['password'] = self.password.sha256_hash(clear_password)
            return 'http://{}:{}@{}:{}'.format(server['username'], server['password'],
                                               server['ip'], server['port'])
        else:
            return 'http://{}:{}'.format(server['ip'], server['port'])

    def __update_stats(self, server):
        """
        Update stats for the given server (picked from the server list)
        """
        # Get the server URI
        uri = self.__get_uri(server)

        # Try to connect to the server
        t = GlancesClientTransport()
        t.set_timeout(3)

        # Get common stats
        try:
            s = ServerProxy(uri, transport=t)
        except Exception as e:
            logger.warning(
                "Client browser couldn't create socket {}: {}".format(uri, e))
        else:
            # Mandatory stats
            try:
                # CPU%
                cpu_percent = 100 - json.loads(s.getCpu())['idle']
                server['cpu_percent'] = '{:.1f}'.format(cpu_percent)
                # MEM%
                server['mem_percent'] = json.loads(s.getMem())['percent']
                # OS (Human Readable name)
                server['hr_name'] = json.loads(s.getSystem())['hr_name']
            except (socket.error, Fault, KeyError) as e:
                logger.debug(
                    "Error while grabbing stats form {}: {}".format(uri, e))
                server['status'] = 'OFFLINE'
            except ProtocolError as e:
                if e.errcode == 401:
                    # Error 401 (Authentication failed)
                    # Password is not the good one...
                    server['password'] = None
                    server['status'] = 'PROTECTED'
                else:
                    server['status'] = 'OFFLINE'
                logger.debug("Cannot grab stats from {} ({} {})".format(uri, e.errcode, e.errmsg))
            else:
                # Status
                server['status'] = 'ONLINE'

                # Optional stats (load is not available on Windows OS)
                try:
                    # LOAD
                    load_min5 = json.loads(s.getLoad())['min5']
                    server['load_min5'] = '{:.2f}'.format(load_min5)
                except Exception as e:
                    logger.warning(
                        "Error while grabbing stats form {}: {}".format(uri, e))

        return server

    def __display_server(self, server):
        """
        Connect and display the given server
        """
        # Display the Glances client for the selected server
        logger.debug("Selected server: {}".format(server))

        # Connection can take time
        # Display a popup
        self.screen.display_popup(
            'Connect to {}:{}'.format(server['name'], server['port']), duration=1)

        # A password is needed to access to the server's stats
        if server['password'] is None:
            # First of all, check if a password is available in the [passwords] section
            clear_password = self.password.get_password(server['name'])
            if (clear_password is None or self.get_servers_list()
                    [self.screen.active_server]['status'] == 'PROTECTED'):
                # Else, the password should be enter by the user
                # Display a popup to enter password
                clear_password = self.screen.display_popup(
                    'Password needed for {}: '.format(server['name']), is_input=True)
            # Store the password for the selected server
            if clear_password is not None:
                self.set_in_selected('password', self.password.sha256_hash(clear_password))

        # Display the Glance client on the selected server
        logger.info("Connect Glances client to the {} server".format(server['key']))

        # Init the client
        args_server = self.args

        # Overwrite connection setting
        args_server.client = server['ip']
        args_server.port = server['port']
        args_server.username = server['username']
        args_server.password = server['password']
        client = GlancesClient(config=self.config, args=args_server, return_to_browser=True)

        # Test if client and server are in the same major version
        if not client.login():
            self.screen.display_popup(
                "Sorry, cannot connect to '{}'\n"
                "See '{}' for more details".format(server['name'], LOG_FILENAME))

            # Set the ONLINE status for the selected server
            self.set_in_selected('status', 'OFFLINE')
        else:
            # Start the client loop
            # Return connection type: 'glances' or 'snmp'
            connection_type = client.serve_forever()

            try:
                logger.debug("Disconnect Glances client from the {} server".format(server['key']))
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
        self.screen.active_server = None

    def __serve_forever(self):
        """Main client loop."""
        # No need to update the server list
        # It's done by the GlancesAutoDiscoverListener class (autodiscover.py)
        # Or define staticaly in the configuration file (module static_list.py)
        # For each server in the list, grab elementary stats (CPU, LOAD, MEM, OS...)

        logger.debug("Iter through the following server list: {}".format(self.get_servers_list()))
        for v in self.get_servers_list():
            thread = threading.Thread(target=self.__update_stats, args=[v])
            thread.start()

        # Update the screen (list or Glances client)
        if self.screen.active_server is None:
            #  Display the Glances browser
            self.screen.update(self.get_servers_list())
        else:
            # Display the active server
            self.__display_server(self.get_servers_list()[self.screen.active_server])

        # Loop
        self.__serve_forever()

    def serve_forever(self):
        """Wrapper to the serve_forever function.

        This function will restore the terminal to a sane state
        before re-raising the exception and generating a traceback.
        """
        try:
            return self.__serve_forever()
        finally:
            self.end()

    def set_in_selected(self, key, value):
        """Set the (key, value) for the selected server in the list."""
        # Static list then dynamic one
        if self.screen.active_server >= len(self.static_server.get_servers_list()):
            self.autodiscover_server.set_server(
                self.screen.active_server - len(self.static_server.get_servers_list()),
                key, value)
        else:
            self.static_server.set_server(self.screen.active_server, key, value)

    def end(self):
        """End of the client browser session."""
        self.screen.end()

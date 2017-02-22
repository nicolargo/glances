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

"""Manage the Glances client."""

import json
import socket
import sys

from glances import __version__
from glances.compat import Fault, ProtocolError, ServerProxy, Transport
from glances.logger import logger
from glances.stats_client import GlancesStatsClient
from glances.outputs.glances_curses import GlancesCursesClient


class GlancesClientTransport(Transport):

    """This class overwrite the default XML-RPC transport and manage timeout."""

    def set_timeout(self, timeout):
        self.timeout = timeout


class GlancesClient(object):

    """This class creates and manages the TCP client."""

    def __init__(self, config=None, args=None, timeout=7, return_to_browser=False):
        # Store the arg/config
        self.args = args
        self.config = config

        # Default client mode
        self._client_mode = 'glances'

        # Return to browser or exit
        self.return_to_browser = return_to_browser

        # Build the URI
        if args.password != "":
            self.uri = 'http://{}:{}@{}:{}'.format(args.username, args.password,
                                                   args.client, args.port)
        else:
            self.uri = 'http://{}:{}'.format(args.client, args.port)
        logger.debug("Try to connect to {}".format(self.uri))

        # Try to connect to the URI
        transport = GlancesClientTransport()
        # Configure the server timeout
        transport.set_timeout(timeout)
        try:
            self.client = ServerProxy(self.uri, transport=transport)
        except Exception as e:
            self.log_and_exit("Client couldn't create socket {}: {}".format(self.uri, e))

    def log_and_exit(self, msg=''):
        """Log and exit."""
        if not self.return_to_browser:
            logger.critical(msg)
            sys.exit(2)
        else:
            logger.error(msg)

    @property
    def client_mode(self):
        """Get the client mode."""
        return self._client_mode

    @client_mode.setter
    def client_mode(self, mode):
        """Set the client mode.

        - 'glances' = Glances server (default)
        - 'snmp' = SNMP (fallback)
        """
        self._client_mode = mode

    def _login_glances(self):
        """Login to a Glances server"""
        client_version = None
        try:
            client_version = self.client.init()
        except socket.error as err:
            # Fallback to SNMP
            self.client_mode = 'snmp'
            logger.error("Connection to Glances server failed ({} {})".format(err.errno, err.strerror))
            fallbackmsg = 'No Glances server found on {}. Trying fallback to SNMP...'.format(self.uri)
            if not self.return_to_browser:
                print(fallbackmsg)
            else:
                logger.info(fallbackmsg)
        except ProtocolError as err:
            # Other errors
            msg = "Connection to server {} failed".format(self.uri)
            if err.errcode == 401:
                msg += " (Bad username/password)"
            else:
                msg += " ({} {})".format(err.errcode, err.errmsg)
            self.log_and_exit(msg)
            return False

        if self.client_mode == 'glances':
            # Check that both client and server are in the same major version
            if __version__.split('.')[0] == client_version.split('.')[0]:
                # Init stats
                self.stats = GlancesStatsClient(config=self.config, args=self.args)
                self.stats.set_plugins(json.loads(self.client.getAllPlugins()))
                logger.debug("Client version: {} / Server version: {}".format(__version__, client_version))
            else:
                self.log_and_exit(('Client and server not compatible: '
                                   'Client version: {} / Server version: {}'.format(__version__, client_version)))
                return False

        return True

    def _login_snmp(self):
        """Login to a SNMP server"""
        logger.info("Trying to grab stats by SNMP...")

        from glances.stats_client_snmp import GlancesStatsClientSNMP

        # Init stats
        self.stats = GlancesStatsClientSNMP(config=self.config, args=self.args)

        if not self.stats.check_snmp():
            self.log_and_exit("Connection to SNMP server failed")
            return False

        return True

    def login(self):
        """Logon to the server."""

        if self.args.snmp_force:
            # Force SNMP instead of Glances server
            self.client_mode = 'snmp'
        else:
            # First of all, trying to connect to a Glances server
            if not self._login_glances():
                return False

        # Try SNMP mode
        if self.client_mode == 'snmp':
            if not self._login_snmp():
                return False

        # Load limits from the configuration file
        # Each client can choose its owns limits
        logger.debug("Load limits from the client configuration file")
        self.stats.load_limits(self.config)

        # Init screen
        self.screen = GlancesCursesClient(config=self.config, args=self.args)

        # Return True: OK
        return True

    def update(self):
        """Update stats from Glances/SNMP server."""
        if self.client_mode == 'glances':
            return self.update_glances()
        elif self.client_mode == 'snmp':
            return self.update_snmp()
        else:
            self.end()
            logger.critical("Unknown server mode: {}".format(self.client_mode))
            sys.exit(2)

    def update_glances(self):
        """Get stats from Glances server.

        Return the client/server connection status:
        - Connected: Connection OK
        - Disconnected: Connection NOK
        """
        # Update the stats
        try:
            server_stats = json.loads(self.client.getAll())
        except socket.error:
            # Client cannot get server stats
            return "Disconnected"
        except Fault:
            # Client cannot get server stats (issue #375)
            return "Disconnected"
        else:
            # Put it in the internal dict
            self.stats.update(server_stats)
            return "Connected"

    def update_snmp(self):
        """Get stats from SNMP server.

        Return the client/server connection status:
        - SNMP: Connection with SNMP server OK
        - Disconnected: Connection NOK
        """
        # Update the stats
        try:
            self.stats.update()
        except Exception:
            # Client cannot get SNMP server stats
            return "Disconnected"
        else:
            # Grab success
            return "SNMP"

    def serve_forever(self):
        """Main client loop."""
        exitkey = False
        try:
            while True and not exitkey:
                # Update the stats
                cs_status = self.update()

                # Update the screen
                exitkey = self.screen.update(self.stats,
                                             cs_status=cs_status,
                                             return_to_browser=self.return_to_browser)

                # Export stats using export modules
                self.stats.export(self.stats)
        except Exception as e:
            logger.critical(e)
            self.end()

        return self.client_mode

    def end(self):
        """End of the client session."""
        self.screen.end()

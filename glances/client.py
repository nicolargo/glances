# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Manage the Glances client."""

import ujson
import socket
import sys
import time

from glances import __version__
from glances.compat import Fault, ProtocolError, ServerProxy, Transport
from glances.logger import logger
from glances.stats_client import GlancesStatsClient
from glances.outputs.glances_curses import GlancesCursesClient
from glances.timer import Counter


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

        self._quiet = args.quiet
        self.refresh_time = args.time

        # Default client mode
        self._client_mode = 'glances'

        # Return to browser or exit
        self.return_to_browser = return_to_browser

        # Build the URI
        if args.password != "":
            self.uri = 'http://{}:{}@{}:{}'.format(args.username, args.password, args.client, args.port)
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

    @property
    def quiet(self):
        return self._quiet

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
            fall_back_msg = 'No Glances server found on {}. Trying fallback to SNMP...'.format(self.uri)
            if not self.return_to_browser:
                print(fall_back_msg)
            else:
                logger.info(fall_back_msg)
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
                self.stats.set_plugins(ujson.loads(self.client.getAllPlugins()))
                logger.debug("Client version: {} / Server version: {}".format(__version__, client_version))
            else:
                self.log_and_exit(
                    (
                        'Client and server not compatible: '
                        'Client version: {} / Server version: {}'.format(__version__, client_version)
                    )
                )
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
        if self.quiet:
            # In quiet mode, nothing is displayed
            logger.info("Quiet mode is ON: Nothing will be displayed")
        else:
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
            server_stats = ujson.loads(self.client.getAll())
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

        # Test if client and server are in the same major version
        if not self.login():
            logger.critical("The server version is not compatible with the client")
            self.end()
            return self.client_mode

        exit_key = False
        try:
            while True and not exit_key:
                # Update the stats
                counter = Counter()
                cs_status = self.update()
                logger.debug('Stats updated duration: {} seconds'.format(counter.get()))

                # Export stats using export modules
                counter_export = Counter()
                self.stats.export(self.stats)
                logger.debug('Stats exported duration: {} seconds'.format(counter_export.get()))

                # Patch for issue1326 to avoid < 0 refresh
                adapted_refresh = self.refresh_time - counter.get()
                adapted_refresh = adapted_refresh if adapted_refresh > 0 else 0

                # Update the screen
                if not self.quiet:
                    exit_key = self.screen.update(
                        self.stats,
                        duration=adapted_refresh,
                        cs_status=cs_status,
                        return_to_browser=self.return_to_browser,
                    )
                else:
                    # In quiet mode, we only wait adapated_refresh seconds
                    time.sleep(adapted_refresh)
        except Exception as e:
            logger.critical(e)
            self.end()

        return self.client_mode

    def end(self):
        """End of the client session."""
        if not self.quiet:
            self.screen.end()

# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2015 Nicolargo <nicolas@nicolargo.com>
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

# Import system libs
import json
import socket
import sys
try:
    from xmlrpc.client import Transport, ServerProxy, ProtocolError, Fault
except ImportError:
    # Python 2
    from xmlrpclib import Transport, ServerProxy, ProtocolError, Fault

# Import Glances libs
from glances.core.glances_globals import version
from glances.core.glances_logging import logger
from glances.core.glances_stats import GlancesStatsClient
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
            uri = 'http://{0}:{1}@{2}:{3}'.format(args.username, args.password,
                                                  args.client, args.port)
        else:
            uri = 'http://{0}:{1}'.format(args.client, args.port)
        logger.debug("Try to connect to {0}".format(uri))

        # Try to connect to the URI
        transport = GlancesClientTransport()
        # Configure the server timeout
        transport.set_timeout(timeout)
        try:
            self.client = ServerProxy(uri, transport=transport)
        except Exception as e:
            self.log_and_exit("Client couldn't create socket {0}: {1}".format(uri, e))

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

    def login(self):
        """Logon to the server."""
        ret = True

        if not self.args.snmp_force:
            # First of all, trying to connect to a Glances server
            client_version = None
            try:
                client_version = self.client.init()
            except socket.error as err:
                # Fallback to SNMP
                self.client_mode = 'snmp'
                logger.error("Connection to Glances server failed: {0}".format(err))
                fallbackmsg = 'No Glances server found. Trying fallback to SNMP...'
                if not self.return_to_browser:
                    print(fallbackmsg)
                else:
                    logger.info(fallbackmsg)
            except ProtocolError as err:
                # Others errors
                if str(err).find(" 401 ") > 0:
                    msg = "Connection to server failed (bad password)"
                else:
                    msg = "Connection to server failed ({0})".format(err)
                self.log_and_exit(msg)
                return False

            if self.client_mode == 'glances':
                # Check that both client and server are in the same major version
                if version.split('.')[0] == client_version.split('.')[0]:
                    # Init stats
                    self.stats = GlancesStatsClient(config=self.config, args=self.args)
                    self.stats.set_plugins(json.loads(self.client.getAllPlugins()))
                    logger.debug("Client version: {0} / Server version: {1}".format(version, client_version))
                else:
                    self.log_and_exit("Client and server not compatible: \
                                      Client version: {0} / Server version: {1}".format(version, client_version))
                    return False

        else:
            self.client_mode = 'snmp'

        # SNMP mode
        if self.client_mode == 'snmp':
            logger.info("Trying to grab stats by SNMP...")

            from glances.core.glances_stats import GlancesStatsClientSNMP

            # Init stats
            self.stats = GlancesStatsClientSNMP(config=self.config, args=self.args)

            if not self.stats.check_snmp():
                self.log_and_exit("Connection to SNMP server failed")
                return False

        if ret:
            # Load limits from the configuration file
            # Each client can choose its owns limits
            self.stats.load_limits(self.config)

            # Init screen
            self.screen = GlancesCursesClient(args=self.args)

        # Return result
        return ret

    def update(self):
        """Update stats from Glances/SNMP server."""
        if self.client_mode == 'glances':
            return self.update_glances()
        elif self.client_mode == 'snmp':
            return self.update_snmp()
        else:
            self.end()
            logger.critical("Unknown server mode: {0}".format(self.client_mode))
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
            server_stats['monitor'] = json.loads(self.client.getAllMonitored())
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

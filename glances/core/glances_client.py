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
try:
    import http.client as httplib
except:  
    # Python 2
    import httplib

# Import Glances libs
from glances.core.glances_globals import version, logger
from glances.core.glances_stats import GlancesStatsClient
from glances.outputs.glances_curses import GlancesCurses


class GlancesClientTransport(Transport):
    """This class overwrite the default XML-RPC transport and manage timeout"""
    
    def set_timeout(self, timeout):
        self.timeout = timeout

    def make_connection(self, host):
        return httplib.HTTPConnection(host, timeout=self.timeout)


class GlancesClient(object):
    """This class creates and manages the TCP client."""

    def __init__(self, config=None, args=None):
        # Store the arg/config
        self.args = args
        self.config = config

        # Client mode:
        self.set_mode()

        # Build the URI
        if args.password != "":
            uri = 'http://{0}:{1}@{2}:{3}'.format(args.username, args.password,
                                                  args.client, args.port)
        else:
            uri = 'http://{0}:{1}'.format(args.client, args.port)

        # Try to connect to the URI
        transport = GlancesClientTransport()
        # Configure the server timeout to 7 seconds
        transport.set_timeout(7)
        try:
            self.client = ServerProxy(uri, transport = transport)
        except Exception as e:
            logger.error(_("Couldn't create socket {0}: {1}").format(uri, e))
            sys.exit(2)

    def set_mode(self, mode='glances'):
        """Set the client mode.

        - 'glances' = Glances server (default)
        - 'snmp' = SNMP (fallback)
        """
        self.mode = mode
        return self.mode

    def get_mode(self):
        """Get the client mode.

        - 'glances' = Glances server (default)
        - 'snmp' = SNMP (fallback)
        """
        return self.mode

    def login(self):
        """Logon to the server."""
        ret = True

        if not self.args.snmp_force:
            # First of all, trying to connect to a Glances server
            self.set_mode('glances')
            client_version = None
            try:
                client_version = self.client.init()
            except socket.error as err:
                # Fallback to SNMP
                logger.error(_("Connection to Glances server failed"))
                self.set_mode('snmp')
                fallbackmsg = _("Trying fallback to SNMP...")
                print(fallbackmsg)
            except ProtocolError as err:
                # Others errors
                if str(err).find(" 401 ") > 0:
                    logger.error(_("Connection to server failed (Bad password)"))
                else:
                    logger.error(_("Connection to server failed ({0})").format(err))
                sys.exit(2)

            if self.get_mode() == 'glances' and version[:3] == client_version[:3]:
                # Init stats
                self.stats = GlancesStatsClient()
                self.stats.set_plugins(json.loads(self.client.getAllPlugins()))
            else:
                logger.error("Client version: %s / Server version: %s" % (version, client_version))

        else:
            self.set_mode('snmp')

        if self.get_mode() == 'snmp':            
            logger.info(_("Trying to grab stats by SNMP..."))
            # Fallback to SNMP if needed
            from glances.core.glances_stats import GlancesStatsClientSNMP

            # Init stats
            self.stats = GlancesStatsClientSNMP(args=self.args)

            if not self.stats.check_snmp():
                logger.error(_("Connection to SNMP server failed"))
                sys.exit(2)

        if ret:
            # Load limits from the configuration file
            # Each client can choose its owns limits
            self.stats.load_limits(self.config)

            # Init screen
            self.screen = GlancesCurses(args=self.args)

        # Return result
        return ret

    def update(self):
        """Update stats from Glances/SNMP server."""
        if self.get_mode() == 'glances':
            return self.update_glances()
        elif self.get_mode() == 'snmp':
            return self.update_snmp()
        else:
            self.end()
            logger.critical(_("Unknown server mode: {0}").format(self.get_mode()))
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
        except:
            # Client can not get SNMP server stats
            return "Disconnected"
        else:
            # Grab success
            return "SNMP"

    def serve_forever(self):
        """Main client loop."""
        while True:
            # Update the stats
            cs_status = self.update()

            # Update the screen
            self.screen.update(self.stats, cs_status=cs_status)

    def end(self):
        """End of the client session."""
        self.screen.end()

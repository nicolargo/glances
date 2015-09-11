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

"""Manage autodiscover Glances server (thk to the ZeroConf protocol)."""

# Import system libs
import socket
import sys

try:
    from zeroconf import (
        __version__ as __zeroconf_version,
        ServiceBrowser,
        ServiceInfo,
        Zeroconf
    )
    zeroconf_tag = True
except ImportError:
    zeroconf_tag = False

# Import Glances libs
from glances.core.glances_globals import appname, is_freebsd
from glances.core.glances_logging import logger

# Zeroconf 0.17 or higher is needed
if zeroconf_tag:
    zeroconf_min_version = (0, 17, 0)
    zeroconf_version = tuple([int(num) for num in __zeroconf_version.split('.')])
    logger.debug("Zeroconf version {0} detected.".format(__zeroconf_version))
    if zeroconf_version < zeroconf_min_version:
        logger.critical("Please install zeroconf 0.17 or higher.")
        sys.exit(1)

# Global var
zeroconf_type = "_%s._tcp." % appname


class AutoDiscovered(object):

    """Class to manage the auto discovered servers dict."""

    def __init__(self):
        # server_dict is a list of dict (JSON compliant)
        # [ {'key': 'zeroconf name', ip': '172.1.2.3', 'port': 61209, 'cpu': 3, 'mem': 34 ...} ... ]
        self._server_list = []

    def get_servers_list(self):
        """Return the current server list (list of dict)."""
        return self._server_list

    def set_server(self, server_pos, key, value):
        """Set the key to the value for the server_pos (position in the list)."""
        self._server_list[server_pos][key] = value

    def add_server(self, name, ip, port):
        """Add a new server to the list."""
        new_server = {
            'key': name,  # Zeroconf name with both hostname and port
            'name': name.split(':')[0],  # Short name
            'ip': ip,  # IP address seen by the client
            'port': port,  # TCP port
            'username': 'glances',  # Default username
            'password': '',  # Default password
            'status': 'UNKNOWN',  # Server status: 'UNKNOWN', 'OFFLINE', 'ONLINE', 'PROTECTED'
            'type': 'DYNAMIC'}  # Server type: 'STATIC' or 'DYNAMIC'
        self._server_list.append(new_server)
        logger.debug("Updated servers list (%s servers): %s" %
                     (len(self._server_list), self._server_list))

    def remove_server(self, name):
        """Remove a server from the dict."""
        for i in self._server_list:
            if i['key'] == name:
                try:
                    self._server_list.remove(i)
                    logger.debug("Remove server %s from the list" % name)
                    logger.debug("Updated servers list (%s servers): %s" % (
                        len(self._server_list), self._server_list))
                except ValueError:
                    logger.error(
                        "Cannot remove server %s from the list" % name)


class GlancesAutoDiscoverListener(object):

    """Zeroconf listener for Glances server."""

    def __init__(self):
        # Create an instance of the servers list
        self.servers = AutoDiscovered()

    def get_servers_list(self):
        """Return the current server list (list of dict)."""
        return self.servers.get_servers_list()

    def set_server(self, server_pos, key, value):
        """Set the key to the value for the server_pos (position in the list)."""
        self.servers.set_server(server_pos, key, value)

    def add_service(self, zeroconf, srv_type, srv_name):
        """Method called when a new Zeroconf client is detected.

        Return True if the zeroconf client is a Glances server
        Note: the return code will never be used
        """
        if srv_type != zeroconf_type:
            return False
        logger.debug("Check new Zeroconf server: %s / %s" %
                     (srv_type, srv_name))
        info = zeroconf.get_service_info(srv_type, srv_name)
        if info:
            new_server_ip = socket.inet_ntoa(info.address)
            new_server_port = info.port

            # Add server to the global dict
            self.servers.add_server(srv_name, new_server_ip, new_server_port)
            logger.info("New Glances server detected (%s from %s:%s)" %
                        (srv_name, new_server_ip, new_server_port))
        else:
            logger.warning(
                "New Glances server detected, but Zeroconf info failed to be grabbed")
        return True

    def remove_service(self, zeroconf, srv_type, srv_name):
        """Remove the server from the list."""
        self.servers.remove_server(srv_name)
        logger.info(
            "Glances server %s removed from the autodetect list" % srv_name)


class GlancesAutoDiscoverServer(object):

    """Implementation of the Zeroconf protocol (server side for the Glances client)."""

    def __init__(self, args=None):
        if zeroconf_tag:
            logger.info("Init autodiscover mode (Zeroconf protocol)")
            try:
                self.zeroconf = Zeroconf()
            except socket.error as e:
                logger.error("Cannot start Zeroconf (%s)" % e)
                self.zeroconf_enable_tag = False
            else:
                self.listener = GlancesAutoDiscoverListener()
                self.browser = ServiceBrowser(
                    self.zeroconf, zeroconf_type, self.listener)
                self.zeroconf_enable_tag = True
        else:
            logger.error("Cannot start autodiscover mode (Zeroconf lib is not installed)")
            self.zeroconf_enable_tag = False

    def get_servers_list(self):
        """Return the current server list (dict of dict)."""
        if zeroconf_tag and self.zeroconf_enable_tag:
            return self.listener.get_servers_list()
        else:
            return []

    def set_server(self, server_pos, key, value):
        """Set the key to the value for the server_pos (position in the list)."""
        if zeroconf_tag and self.zeroconf_enable_tag:
            self.listener.set_server(server_pos, key, value)

    def close(self):
        if zeroconf_tag and self.zeroconf_enable_tag:
            self.zeroconf.close()


class GlancesAutoDiscoverClient(object):

    """Implementation of the zeroconf protocol (client side for the Glances server)."""

    def __init__(self, hostname, args=None):
        if zeroconf_tag:
            zeroconf_bind_address = args.bind_address
            try:
                self.zeroconf = Zeroconf()
            except socket.error as e:
                logger.error("Cannot start zeroconf: {0}".format(e))

            # XXX FreeBSD: Segmentation fault (core dumped)
            # -- https://bitbucket.org/al45tair/netifaces/issues/15
            if not is_freebsd:
                try:
                    # -B @ overwrite the dynamic IPv4 choice
                    if zeroconf_bind_address == '0.0.0.0':
                        zeroconf_bind_address = self.find_active_ip_address()
                except KeyError:
                    # Issue #528 (no network interface available)
                    pass

            print("Announce the Glances server on the LAN (using {0} IP address)".format(zeroconf_bind_address))
            self.info = ServiceInfo(
                zeroconf_type, '{0}:{1}.{2}'.format(hostname, args.port, zeroconf_type),
                address=socket.inet_aton(zeroconf_bind_address), port=args.port,
                weight=0, priority=0, properties={}, server=hostname)
            self.zeroconf.register_service(self.info)
        else:
            logger.error("Cannot announce Glances server on the network: zeroconf library not found.")

    @staticmethod
    def find_active_ip_address():
        """Try to find the active IP addresses."""
        import netifaces
        # Interface of the default gateway
        gateway_itf = netifaces.gateways()['default'][netifaces.AF_INET][1]
        # IP address for the interface
        return netifaces.ifaddresses(gateway_itf)[netifaces.AF_INET][0]['addr']

    def close(self):
        if zeroconf_tag:
            self.zeroconf.unregister_service(self.info)
            self.zeroconf.close()

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

"""Manage autodiscover Glances server (thk to the ZeroConf protocol)."""

# Import system libs
import sys
import socket
try:
    import netifaces
    netifaces_tag = True
except ImportError:
    netifaces_tag = True
try:
    from zeroconf import ServiceBrowser, ServiceInfo, Zeroconf
    zeroconf_tag = True
except ImportError:
    zeroconf_tag = False

# Import Glances libs
from glances.core.glances_globals import appname, logger

# Global var
zeroconf_type = "_%s._tcp." % appname


class AutoDiscovered(object):

    """Class to manage the auto discovered servers dict"""

    def __init__(self):
        # server_dict is a list of dict (JSON compliant)
        # [ {'key': 'zeroconf name', ip': '172.1.2.3', 'port': 61209, 'cpu': 3, 'mem': 34 ...} ... ]
        self._server_list = []

    def get_servers_list(self):
        """Return the current server list (list of dict)"""
        return self._server_list

    def set_server(self, server_pos, key, value):
        """Set the key to the value for the server_pos (position in the list)"""
        self._server_list[server_pos][key] = value

    def add_server(self, name, ip, port):
        """Add a new server to the list"""
        new_server = {'key': name,  # Zeroconf name with both hostname and port
                      'name': name.split(':')[0],  # Short name
                      'ip': ip,  # IP address seen by the client
                      'port': port,  # TCP port
                      'username': 'glances', # Default username
                      'password': '', # Default password
                      'status': 'UNKNOWN', # Server status: 'UNKNOWN', 'OFFLINE', 'ONLINE', 'PROTECTED'
                      'type': 'DYNAMIC', # Server type: 'STATIC' or 'DYNAMIC'
                      }
        self._server_list.append(new_server)
        logger.debug("Updated servers list (%s servers): %s" %
                     (len(self._server_list), self._server_list))

    def remove_server(self, name):
        """Remove a server from the dict"""
        for i in self._server_list:
            if i['key'] == name:
                try:
                    self._server_list.remove(i)
                    logger.debug("Remove server %s from the list" % name)
                    logger.debug("Updated servers list (%s servers): %s" % (
                        len(self._server_list), self._server_list))
                except ValueError:
                    logger.error(
                        "Can not remove server %s from the list" % name)


class GlancesAutoDiscoverListener(object):

    """Zeroconf listener for Glances server"""

    def __init__(self):
        # Create an instance of the servers list
        self.servers = AutoDiscovered()

    def get_servers_list(self):
        """Return the current server list (list of dict)"""
        return self.servers.get_servers_list()

    def set_server(self, server_pos, key, value):
        """Set the key to the value for the server_pos (position in the list)"""
        self.servers.set_server(server_pos, key, value)

    def addService(self, zeroconf, srv_type, srv_name):
        """Method called when a new Zeroconf client is detected
        Return True if the zeroconf client is a Glances server
        Note: the return code will never be used
        """
        if srv_type != zeroconf_type:
            return False
        logger.debug("Check new Zeroconf server: %s / %s" %
                     (srv_type, srv_name))
        info = zeroconf.getServiceInfo(srv_type, srv_name)
        if info:
            new_server_ip = socket.inet_ntoa(info.getAddress())
            new_server_port = info.getPort()

            # Add server to the global dict
            self.servers.add_server(srv_name, new_server_ip, new_server_port)
            logger.info("New Glances server detected (%s from %s:%s)" %
                        (srv_name, new_server_ip, new_server_port))
        else:
            logger.warning(
                "New Glances server detected, but Zeroconf info failed to be grabbed")
        return True

    def removeService(self, zeroconf, srv_type, srv_name):
        # Remove the server from the list
        self.servers.remove_server(srv_name)
        logger.info(
            "Glances server %s removed from the autodetect list" % srv_name)


class GlancesAutoDiscoverServer(object):

    """Implementation of the Zeroconf protocol (server side for the Glances client)"""

    def __init__(self, args=None):
        if zeroconf_tag:
            logger.info("Init autodiscover mode (Zeroconf protocol)")
            try:
                self.zeroconf = Zeroconf()
            except socket.error as e:
                logger.error("Can not start Zeroconf (%s)" % e)
                self.zeroconf_enable_tag = False
            else:
                self.listener = GlancesAutoDiscoverListener()
                self.browser = ServiceBrowser(
                    self.zeroconf, zeroconf_type, self.listener)
                self.zeroconf_enable_tag = True
        else:
            logger.error(
                "Can not start autodiscover mode (Zeroconf lib is not installed)")
            self.zeroconf_enable_tag = False

    def get_servers_list(self):
        """Return the current server list (dict of dict)"""
        if zeroconf_tag and self.zeroconf_enable_tag:
            return self.listener.get_servers_list()
        else:
            return []

    def set_server(self, server_pos, key, value):
        """Set the key to the value for the server_pos (position in the list)"""
        if zeroconf_tag and self.zeroconf_enable_tag:
            self.listener.set_server(server_pos, key, value)

    def close(self):
        if zeroconf_tag and self.zeroconf_enable_tag:
            self.zeroconf.close()


class GlancesAutoDiscoverClient(object):

    """Implementation of the Zeroconf protocol (client side for the Glances server)"""

    def __init__(self, hostname, args=None):
        if netifaces_tag:
            try:
                zeroconf_bind_address = netifaces.ifaddresses(
                    netifaces.interfaces()[1])[netifaces.AF_INET][0]['addr']
            except:
                zeroconf_bind_address = args.bind_address
            print("Announce the Glances server on the local area network (using %s IP address)" %
                  zeroconf_bind_address)

            if zeroconf_tag:
                logger.info(
                    "Announce the Glances server on the local area network (using %s IP address)" % zeroconf_bind_address)
                try:
                    self.zeroconf = Zeroconf()
                except socket.error as e:
                    logger.error("Can not start Zeroconf (%s)" % e)
                else:
                    self.info = ServiceInfo(zeroconf_type,
                                            hostname + ':' +
                                            str(args.port) + '.' + zeroconf_type,
                                            address=socket.inet_aton(
                                                zeroconf_bind_address),
                                            port=args.port,
                                            weight=0,
                                            priority=0,
                                            properties={},
                                            server=hostname)
                    self.zeroconf.registerService(self.info)
            else:
                logger.error(
                    "Can not announce Glances server on the network (Zeroconf lib is not installed)")
        else:
            logger.error(
                "Can not announce Glances server on the network (Netifaces lib is not installed)")

    def close(self):
        if zeroconf_tag:
            self.zeroconf.unregisterService(self.info)
            self.zeroconf.close()

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
        # server_dict is a dict of dict
        # key: ip:port
        # value: {'cpu': 3, 'mem': 34 ...}
        self._server_dict = {}

    def get_servers_list(self):
        """Return the current server list (dict of dict)"""
        return self._server_dict

    def add_server(self, name, ip, port):
        """Add a new server to the dict"""
        try:
            self._server_dict[name] = {'name': name.split(':')[0], 'ip': ip, 'port': port}
            logger.debug("Servers list: %s" % self._server_dict)
        except KeyError:
            pass

    def remove_server(self, name):
        """Remove a server from the dict"""
        try:
            del(self._server_dict[name])
            logger.debug("Servers list: %s" % self._server_dict)
        except KeyError:
            pass


class GlancesAutoDiscoverListener(object):

    """Zeroconf listener for Glances server"""

    def __init__(self):
        # Create an instance of the servers list
        self.servers = AutoDiscovered()

    def get_servers_list(self):
        """Return the current server list (dict of dict)"""
        return self.servers.get_servers_list()

    def addService(self, zeroconf, srv_type, srv_name):
        """Method called when a new Zeroconf client is detected
        Return True if the zeroconf client is a Glances server
        Note: the return code will never be used
        """
        if srv_type != zeroconf_type:
            return False
        info = zeroconf.getServiceInfo(srv_type, srv_name)
        if info:
            new_server_ip = socket.inet_ntoa(info.getAddress())
            new_server_port = info.getPort()

            # !!! Only for dev
            # new_server_name = info.getServer()
            prop = info.getProperties()
            if prop:
                logger.debug("Zeroconf properties are %s" % prop)

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
            self.zeroconf = Zeroconf()
            self.listener = GlancesAutoDiscoverListener()
            self.browser = ServiceBrowser(
                self.zeroconf, zeroconf_type, self.listener)
        else:
            logger.error(
                "Can not start autodiscover mode (Zeroconf lib is not installed)")

    def get_servers_list(self):
        """Return the current server list (dict of dict)"""
        if zeroconf_tag:
            return self.listener.get_servers_list()
        else:
            return {}

    def close(self):
        if zeroconf_tag:
            self.zeroconf.close()


class GlancesAutoDiscoverClient(object):

    """Implementation of the Zeroconf protocol (client side for the Glances server)"""

    def __init__(self, hostname, args=None):
        if netifaces_tag:
            # !!! TO BE REFACTOR
            # OK with server: LANGUAGE=en_US.utf8 python -m glances -s -d -B 192.168.176.128
            # KO with server: LANGUAGE=en_US.utf8 python -m glances -s -d
            try:
                zeroconf_bind_address = netifaces.ifaddresses(netifaces.interfaces()[1])[netifaces.AF_INET][0]['addr']
            except:
                zeroconf_bind_address = args.bind_address
            print("Announce the Glances server on the local area network (using %s IP address)" % zeroconf_bind_address)
            # /!!!            

            if zeroconf_tag:
                logger.info(
                    "Announce the Glances server on the local area network (using %s IP address)" % zeroconf_bind_address)
                self.zeroconf = Zeroconf()
                self.info = ServiceInfo(zeroconf_type,
                                        hostname+':'+str(args.port)+'.'+zeroconf_type,
                                        address=socket.inet_aton(zeroconf_bind_address),
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

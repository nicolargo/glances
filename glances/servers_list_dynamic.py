#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Manage autodiscover Glances server (thk to the ZeroConf protocol)."""

import socket
import sys

from glances.globals import BSD
from glances.logger import logger

try:
    from zeroconf import ServiceBrowser, ServiceInfo, Zeroconf
    from zeroconf import __version__ as __zeroconf_version

    zeroconf_tag = True
except ImportError:
    zeroconf_tag = False

# Zeroconf 0.17 or higher is needed
if zeroconf_tag:
    zeroconf_min_version = (0, 17, 0)
    zeroconf_version = tuple([int(num) for num in __zeroconf_version.split('.')])
    logger.debug(f"Zeroconf version {__zeroconf_version} detected.")
    if zeroconf_version < zeroconf_min_version:
        logger.critical("Please install zeroconf 0.17 or higher.")
        sys.exit(1)

# Global var
# Recent versions of the zeroconf python package doesn't like a zeroconf type that ends with '._tcp.'.
# Correct issue: zeroconf problem with zeroconf_type = "_%s._tcp." % 'glances' #888
zeroconf_type = "_{}._tcp.local.".format('glances')


class AutoDiscovered:
    """Class to manage the auto discovered servers dict."""

    def __init__(self):
        # server_dict is a list of dict (JSON compliant)
        # [ {'key': 'zeroconf name', ip': '172.1.2.3', 'port': 61209, 'protocol': 'rpc', 'cpu': 3, 'mem': 34 ...} ... ]
        self._server_list = []

    def get_servers_list(self):
        """Return the current server list (list of dict)."""
        return self._server_list

    def set_server(self, server_pos, key, value):
        """Set the key to the value for the server_pos (position in the list)."""
        self._server_list[server_pos][key] = value

    def add_server(self, name, ip, port, protocol='rpc'):
        """Add a new server to the list."""
        new_server = {
            'key': name,  # Zeroconf name with both hostname and port
            'name': name.split(':')[0],  # Short name
            'ip': ip,  # IP address seen by the client
            'port': port,  # TCP port
            'protocol': str(protocol),  # RPC or RESTFUL protocol
            'username': 'glances',  # Default username
            'password': '',  # Default password
            'status': 'UNKNOWN',  # Server status: 'UNKNOWN', 'OFFLINE', 'ONLINE', 'PROTECTED'
            'type': 'DYNAMIC',
        }  # Server type: 'STATIC' or 'DYNAMIC'
        self._server_list.append(new_server)
        logger.debug(f"Updated servers list ({len(self._server_list)} servers): {self._server_list}")

    def remove_server(self, name):
        """Remove a server from the dict."""
        for i in self._server_list:
            if i['key'] == name:
                try:
                    self._server_list.remove(i)
                    logger.debug(f"Remove server {name} from the list")
                    logger.debug(f"Updated servers list ({len(self._server_list)} servers): {self._server_list}")
                except ValueError:
                    logger.error(f"Cannot remove server {name} from the list")


class GlancesAutoDiscoverListener:
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

        Note: the return code will never be used

        :return: True if the zeroconf client is a Glances server
        """
        if srv_type != zeroconf_type:
            return False
        logger.debug(f"Check new Zeroconf server: {srv_type} / {srv_name}")
        info = zeroconf.get_service_info(srv_type, srv_name)
        if info and (info.addresses or info.parsed_addresses):
            address = info.addresses[0] if info.addresses else info.parsed_addresses[0]
            new_server_ip = socket.inet_ntoa(address)
            new_server_port = info.port
            new_server_protocol = info.properties[b'protocol'].decode() if b'protocol' in info.properties else 'rpc'

            # Add server to the global dict
            self.servers.add_server(
                srv_name,
                new_server_ip,
                new_server_port,
                protocol=new_server_protocol,
            )
            logger.info(
                f"New {new_server_protocol} Glances server detected ({srv_name} from {new_server_ip}:{new_server_port})"
            )
        else:
            logger.warning("New Glances server detected, but failed to be get Zeroconf ServiceInfo ")
        return True

    def remove_service(self, zeroconf, srv_type, srv_name):
        """Remove the server from the list."""
        self.servers.remove_server(srv_name)
        logger.info(f"Glances server {srv_name} removed from the autodetect list")

    def update_service(self, zeroconf, srv_type, srv_name):
        """Update the server from the list.
        Done by a dirty hack (remove + add).
        """
        self.remove_service(zeroconf, srv_type, srv_name)
        self.add_service(zeroconf, srv_type, srv_name)
        logger.info(f"Glances server {srv_name} updated from the autodetect list")


class GlancesAutoDiscoverServer:
    """Implementation of the Zeroconf protocol (server side for the Glances client)."""

    def __init__(self, args=None):
        if zeroconf_tag:
            logger.info("Init autodiscover mode (Zeroconf protocol)")
            try:
                self.zeroconf = Zeroconf()
            except OSError as e:
                logger.error(f"Cannot start Zeroconf ({e})")
                self.zeroconf_enable_tag = False
            else:
                self.listener = GlancesAutoDiscoverListener()
                self.browser = ServiceBrowser(self.zeroconf, zeroconf_type, self.listener)
                self.zeroconf_enable_tag = True
        else:
            logger.error("Cannot start autodiscover mode (Zeroconf lib is not installed)")
            self.zeroconf_enable_tag = False

    def get_servers_list(self):
        """Return the current server list (dict of dict)."""
        if zeroconf_tag and self.zeroconf_enable_tag:
            return self.listener.get_servers_list()
        return []

    def set_server(self, server_pos, key, value):
        """Set the key to the value for the server_pos (position in the list)."""
        if zeroconf_tag and self.zeroconf_enable_tag:
            self.listener.set_server(server_pos, key, value)

    def close(self):
        if zeroconf_tag and self.zeroconf_enable_tag:
            self.zeroconf.close()


class GlancesAutoDiscoverClient:
    """Implementation of the zeroconf protocol (client side for the Glances server)."""

    def __init__(self, hostname, args=None):
        if zeroconf_tag:
            zeroconf_bind_address = args.bind_address
            try:
                self.zeroconf = Zeroconf()
            except OSError as e:
                logger.error(f"Cannot start zeroconf: {e}")

            # XXX *BSDs: Segmentation fault (core dumped)
            # -- https://bitbucket.org/al45tair/netifaces/issues/15
            if not BSD:
                try:
                    # -B @ overwrite the dynamic IPv4 choice
                    if zeroconf_bind_address == '0.0.0.0':
                        zeroconf_bind_address = self.find_active_ip_address()
                except KeyError:
                    # Issue #528 (no network interface available)
                    pass

            # Ensure zeroconf_bind_address is an IP address not an host
            zeroconf_bind_address = socket.gethostbyname(zeroconf_bind_address)

            # Check IP v4/v6
            address_family = socket.getaddrinfo(zeroconf_bind_address, args.port)[0][0]

            # Start the zeroconf service
            try:
                self.info = ServiceInfo(
                    zeroconf_type,
                    f'{hostname}:{args.port}.{zeroconf_type}',
                    address=socket.inet_pton(address_family, zeroconf_bind_address),
                    port=args.port,
                    weight=0,
                    priority=0,
                    properties={'protocol': 'rest' if args.webserver else 'rpc'},
                    server=hostname,
                )
            except TypeError:
                # Manage issue 1663 with breaking change on ServiceInfo method
                # address (only one address) is replaced by addresses (list of addresses)
                self.info = ServiceInfo(
                    zeroconf_type,
                    name=f'{hostname}:{args.port}.{zeroconf_type}',
                    addresses=[socket.inet_pton(address_family, zeroconf_bind_address)],
                    port=args.port,
                    weight=0,
                    priority=0,
                    properties={'protocol': 'rest' if args.webserver else 'rpc'},
                    server=hostname,
                )
            try:
                self.zeroconf.register_service(self.info)
            except Exception as e:
                logger.error(f"Error while announcing Glances server: {e}")
            else:
                print(f"Announce the Glances server on the LAN (using {zeroconf_bind_address} IP address)")
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

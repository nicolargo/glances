#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Manage the Glances server."""

import json
import socket
import sys
from base64 import b64decode

from defusedxml import xmlrpc

from glances import __version__
from glances.logger import logger
from glances.processes import glances_processes
from glances.servers_list_dynamic import GlancesAutoDiscoverClient
from glances.stats_server import GlancesStatsServer
from glances.timer import Timer

# Correct issue #1025 by monkey path the xmlrpc lib
xmlrpc.monkey_patch()


class GlancesXMLRPCHandler(xmlrpc.xmlrpc_server.SimpleXMLRPCRequestHandler):
    """Main XML-RPC handler."""

    rpc_paths = ('/RPC2',)

    def end_headers(self):
        # Hack to add a specific header
        # Thk to: https://gist.github.com/rca/4063325
        self.send_my_headers()
        super().end_headers()

    def send_my_headers(self):
        # Specific header is here (solved the issue #227)
        self.send_header("Access-Control-Allow-Origin", "*")

    def authenticate(self, headers):
        # auth = headers.get('Authorization')
        try:
            (basic, _, encoded) = headers.get('Authorization').partition(' ')
        except Exception:
            # Client did not ask for authentication
            # If server need it then exit
            return not self.server.isAuth
        else:
            # Client authentication
            (basic, _, encoded) = headers.get('Authorization').partition(' ')
            assert basic == 'Basic', 'Only basic authentication supported'
            # Encoded portion of the header is a string
            # Need to convert to byte-string
            encoded_byte_string = encoded.encode()
            # Decode base64 byte string to a decoded byte string
            decoded_bytes = b64decode(encoded_byte_string)
            # Convert from byte string to a regular string
            decoded_string = decoded_bytes.decode()
            # Get the username and password from the string
            (username, _, password) = decoded_string.partition(':')
            # Check that username and password match internal global dictionary
            return self.check_user(username, password)

    def check_user(self, username, password):
        # Check username and password in the dictionary
        if username in self.server.user_dict:
            from glances.password import GlancesPassword

            # TODO: config is not taken into account: it may be a problem ?
            pwd = GlancesPassword(username=username, config=None)
            return pwd.check_password(self.server.user_dict[username], password)
        return False

    def parse_request(self):
        if xmlrpc.xmlrpc_server.SimpleXMLRPCRequestHandler.parse_request(self):
            # Next we authenticate
            if self.authenticate(self.headers):
                return True
            # if authentication fails, tell the client
            self.send_error(401, 'Authentication failed')
        return False

    def log_message(self, log_format, *args):
        # No message displayed on the server side
        pass


class GlancesXMLRPCServer(xmlrpc.xmlrpc_server.SimpleXMLRPCServer):
    """Init a SimpleXMLRPCServer instance (IPv6-ready)."""

    finished = False

    def __init__(self, bind_address, bind_port=61209, requestHandler=GlancesXMLRPCHandler, config=None):
        self.bind_address = bind_address
        self.bind_port = bind_port
        self.config = config
        try:
            self.address_family = socket.getaddrinfo(bind_address, bind_port)[0][0]
        except OSError as e:
            logger.error(f"Couldn't open socket: {e}")
            sys.exit(1)

        super().__init__((bind_address, bind_port), requestHandler)

    def end(self):
        """Stop the server"""
        self.server_close()
        self.finished = True

    def serve_forever(self):
        """Main loop"""
        while not self.finished:
            self.handle_request()


class GlancesInstance:
    """All the methods of this class are published as XML-RPC methods."""

    def __init__(self, config=None, args=None):
        # Init stats
        self.stats = GlancesStatsServer(config=config, args=args)

        # Initial update
        self.stats.update()

        # cached_time is the minimum time interval between stats updates
        # i.e. XML/RPC calls will not retrieve updated info until the time
        # since last update is passed (will retrieve old cached info instead)
        self.timer = Timer(0)
        self.cached_time = args.cached_time

    def __update__(self):
        # Never update more than 1 time per cached_time
        if self.timer.finished():
            self.stats.update()
            self.timer = Timer(self.cached_time)

    def init(self):
        # Return the Glances version
        return __version__

    def getAll(self):
        # Update and return all the stats
        self.__update__()
        return json.dumps(self.stats.getAll())

    def getAllPlugins(self):
        # Return the plugins list
        return json.dumps(self.stats.getPluginsList())

    def getAllLimits(self):
        # Return all the plugins limits
        return json.dumps(self.stats.getAllLimitsAsDict())

    def getAllViews(self):
        # Return all the plugins views
        return json.dumps(self.stats.getAllViewsAsDict())

    def getPlugin(self, plugin):
        # Update and return the plugin stat
        self.__update__()
        return json.dumps(self.stats.get_plugin(plugin).get_raw())

    def getPluginView(self, plugin):
        # Update and return the plugin view
        return json.dumps(self.stats.get_plugin(plugin).get_views())


class GlancesServer:
    """This class creates and manages the TCP server."""

    def __init__(self, requestHandler=GlancesXMLRPCHandler, config=None, args=None):
        # Args
        self.args = args

        # Set the args for the glances_processes instance
        glances_processes.set_args(args)

        # Init the XML RPC server
        try:
            self.server = GlancesXMLRPCServer(args.bind_address, args.port, requestHandler, config=config)
        except Exception as e:
            logger.critical(f"Cannot start Glances server: {e}")
            sys.exit(2)
        else:
            print(f'Glances XML-RPC server is running on {args.bind_address}:{args.port}')

        # The users dict
        # username / password couple
        # By default, no auth is needed
        self.server.user_dict = {}
        self.server.isAuth = False

        # Register functions
        self.server.register_introspection_functions()
        self.server.register_instance(GlancesInstance(config, args))

        if not self.args.disable_autodiscover:
            # Note: The Zeroconf service name will be based on the hostname
            # Correct issue: Zeroconf problem with zeroconf service name #889
            logger.info('Autodiscover is enabled with service name {}'.format(socket.gethostname().split('.', 1)[0]))
            self.autodiscover_client = GlancesAutoDiscoverClient(socket.gethostname().split('.', 1)[0], args)
        else:
            logger.info("Glances autodiscover announce is disabled")

    def add_user(self, username, password):
        """Add an user to the dictionary."""
        self.server.user_dict[username] = password
        self.server.isAuth = True

    def serve_forever(self):
        """Call the main loop."""
        # Set the server login/password (if -P/--password tag)
        if self.args.password != "":
            self.add_user(self.args.username, self.args.password)
        # Serve forever
        self.server.serve_forever()

    def end(self):
        """End of the Glances server session."""
        if not self.args.disable_autodiscover:
            self.autodiscover_client.close()
        self.server.end()

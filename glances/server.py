# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2019 Nicolargo <nicolas@nicolargo.com>
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

"""Manage the Glances server."""

import json
import socket
import sys
from base64 import b64decode

from glances import __version__
from glances.compat import SimpleXMLRPCRequestHandler, SimpleXMLRPCServer, Server
from glances.autodiscover import GlancesAutoDiscoverClient
from glances.logger import logger
from glances.stats_server import GlancesStatsServer
from glances.timer import Timer


class GlancesXMLRPCHandler(SimpleXMLRPCRequestHandler, object):

    """Main XML-RPC handler."""

    rpc_paths = ('/RPC2', )

    def end_headers(self):
        # Hack to add a specific header
        # Thk to: https://gist.github.com/rca/4063325
        self.send_my_headers()
        super(GlancesXMLRPCHandler, self).end_headers()

    def send_my_headers(self):
        # Specific header is here (solved the issue #227)
        self.send_header("Access-Control-Allow-Origin", "*")

    def authenticate(self, headers):
        # auth = headers.get('Authorization')
        try:
            (basic, _, encoded) = headers.get('Authorization').partition(' ')
        except Exception:
            # Client did not ask for authentidaction
            # If server need it then exit
            return not self.server.isAuth
        else:
            # Client authentication
            (basic, _, encoded) = headers.get('Authorization').partition(' ')
            assert basic == 'Basic', 'Only basic authentication supported'
            # Encoded portion of the header is a string
            # Need to convert to bytestring
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
            pwd = GlancesPassword()
            return pwd.check_password(self.server.user_dict[username], password)
        else:
            return False

    def parse_request(self):
        if SimpleXMLRPCRequestHandler.parse_request(self):
            # Next we authenticate
            if self.authenticate(self.headers):
                return True
            else:
                # if authentication fails, tell the client
                self.send_error(401, 'Authentication failed')
        return False

    def log_message(self, log_format, *args):
        # No message displayed on the server side
        pass


class GlancesXMLRPCServer(SimpleXMLRPCServer, object):

    """Init a SimpleXMLRPCServer instance (IPv6-ready)."""

    finished = False

    def __init__(self, bind_address, bind_port=61209,
                 requestHandler=GlancesXMLRPCHandler):

        self.bind_address = bind_address
        self.bind_port = bind_port
        try:
            self.address_family = socket.getaddrinfo(bind_address, bind_port)[0][0]
        except socket.error as e:
            logger.error("Couldn't open socket: {}".format(e))
            sys.exit(1)

        super(GlancesXMLRPCServer, self).__init__((bind_address, bind_port), requestHandler)

    def end(self):
        """Stop the server"""
        self.server_close()
        self.finished = True

    def serve_forever(self):
        """Main loop"""
        while not self.finished:
            self.handle_request()


class GlancesInstance(object):

    """All the methods of this class are published as XML-RPC methods."""

    def __init__(self,
                 config=None,
                 args=None):
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

    def __getattr__(self, item):
        """Overwrite the getattr method in case of attribute is not found.

        The goal is to dynamically generate the API get'Stats'() methods.
        """
        header = 'get'
        # Check if the attribute starts with 'get'
        if item.startswith(header):
            try:
                # Update the stat
                self.__update__()
                # Return the attribute
                return getattr(self.stats, item)
            except Exception:
                # The method is not found for the plugin
                raise AttributeError(item)
        else:
            # Default behavior
            raise AttributeError(item)


class GlancesServer(object):

    """This class creates and manages the TCP server."""

    def __init__(self,
                 requestHandler=GlancesXMLRPCHandler,
                 config=None,
                 args=None):
        # Args
        self.args = args

        # Init the XML RPC server
        try:
            self.server = GlancesXMLRPCServer(args.bind_address, args.port, requestHandler)
        except Exception as e:
            logger.critical("Cannot start Glances server: {}".format(e))
            sys.exit(2)
        else:
            print('Glances XML-RPC server is running on {}:{}'.format(args.bind_address, args.port))

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

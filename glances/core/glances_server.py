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

"""Manage the Glances server."""

# Import system libs
import json
import socket
import sys
from base64 import b64decode
try:
    from xmlrpc.server import SimpleXMLRPCRequestHandler
    from xmlrpc.server import SimpleXMLRPCServer
except ImportError:  # Python 2
    from SimpleXMLRPCServer import SimpleXMLRPCRequestHandler
    from SimpleXMLRPCServer import SimpleXMLRPCServer

# Import Glances libs
from glances.core.glances_autodiscover import GlancesAutoDiscoverClient
from glances.core.glances_globals import version
from glances.core.glances_logging import logger
from glances.core.glances_stats import GlancesStatsServer
from glances.core.glances_timer import Timer


class GlancesXMLRPCHandler(SimpleXMLRPCRequestHandler):

    """Main XML-RPC handler."""

    rpc_paths = ('/RPC2', )

    def end_headers(self):
        # Hack to add a specific header
        # Thk to: https://gist.github.com/rca/4063325
        self.send_my_headers()
        SimpleXMLRPCRequestHandler.end_headers(self)

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
            from glances.core.glances_password import GlancesPassword

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


class GlancesXMLRPCServer(SimpleXMLRPCServer):

    """Init a SimpleXMLRPCServer instance (IPv6-ready)."""

    def __init__(self, bind_address, bind_port=61209,
                 requestHandler=GlancesXMLRPCHandler):

        try:
            self.address_family = socket.getaddrinfo(bind_address, bind_port)[0][0]
        except socket.error as e:
            logger.error("Couldn't open socket: {0}".format(e))
            sys.exit(1)

        SimpleXMLRPCServer.__init__(self, (bind_address, bind_port),
                                    requestHandler)


class GlancesInstance(object):

    """All the methods of this class are published as XML-RPC methods."""

    def __init__(self, cached_time=1, config=None):
        # Init stats
        self.stats = GlancesStatsServer(config)

        # Initial update
        self.stats.update()

        # cached_time is the minimum time interval between stats updates
        # i.e. XML/RPC calls will not retrieve updated info until the time
        # since last update is passed (will retrieve old cached info instead)
        self.timer = Timer(0)
        self.cached_time = cached_time

    def __update__(self):
        # Never update more than 1 time per cached_time
        if self.timer.finished():
            self.stats.update()
            self.timer = Timer(self.cached_time)

    def init(self):
        # Return the Glances version
        return version

    def getAll(self):
        # Update and return all the stats
        self.__update__()
        return json.dumps(self.stats.getAll())

    def getAllPlugins(self):
        # Return the plugins list
        return json.dumps(self.stats.getAllPlugins())

    def getAllLimits(self):
        # Return all the plugins limits
        return json.dumps(self.stats.getAllLimitsAsDict())

    def getAllViews(self):
        # Return all the plugins views
        return json.dumps(self.stats.getAllViewsAsDict())

    def getAllMonitored(self):
        # Return the processes monitored list
        # return json.dumps(self.monitors.getAll())
        return json.dumps(self.stats.getAll()['monitor'])

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

    def __init__(self, requestHandler=GlancesXMLRPCHandler,
                 cached_time=1,
                 config=None,
                 args=None):
        # Args
        self.args = args

        # Init the XML RPC server
        try:
            self.server = GlancesXMLRPCServer(args.bind_address, args.port, requestHandler)
        except Exception as e:
            logger.critical("Cannot start Glances server: {0}".format(e))
            sys.exit(2)

        # The users dict
        # username / password couple
        # By default, no auth is needed
        self.server.user_dict = {}
        self.server.isAuth = False

        # Register functions
        self.server.register_introspection_functions()
        self.server.register_instance(GlancesInstance(cached_time, config))

        if not self.args.disable_autodiscover:
            # Note: The Zeroconf service name will be based on the hostname
            self.autodiscover_client = GlancesAutoDiscoverClient(socket.gethostname(), args)
        else:
            logger.info("Glances autodiscover announce is disabled")

    def add_user(self, username, password):
        """Add an user to the dictionary."""
        self.server.user_dict[username] = password
        self.server.isAuth = True

    def serve_forever(self):
        """Call the main loop."""
        self.server.serve_forever()

    def server_close(self):
        """Close the Glances server session."""
        self.server.server_close()

    def end(self):
        """End of the Glances server session."""
        if not self.args.disable_autodiscover:
            self.autodiscover_client.close()
        self.server_close()

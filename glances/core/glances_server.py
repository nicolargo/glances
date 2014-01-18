#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Glances - An eye on your system
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

# Import system libs
import sys
import socket

from ..core.glances_timer import Timer

try:
    # Python 2
    from SimpleXMLRPCServer import SimpleXMLRPCRequestHandler
    from SimpleXMLRPCServer import SimpleXMLRPCServer
except ImportError:
    # Python 3
    from xmlrpc.server import SimpleXMLRPCRequestHandler
    from xmlrpc.server import SimpleXMLRPCServer

try:
    # Python 2
    from xmlrpclib import ServerProxy, ProtocolError
except ImportError:
    # Python 3
    from xmlrpc.client import ServerProxy, ProtocolError


class GlancesXMLRPCHandler(SimpleXMLRPCRequestHandler):
    """
    Main XMLRPC handler
    """
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
            #    Encoded portion of the header is a string
            #    Need to convert to bytestring
            encodedByteString = encoded.encode()
            #    Decode Base64 byte String to a decoded Byte String
            decodedBytes = b64decode(encodedByteString)
            #    Convert from byte string to a regular String
            decodedString = decodedBytes.decode()
            #    Get the username and password from the string
            (username, _, password) = decodedString.partition(':')
            #    Check that username and password match internal global dictionary
            return self.check_user(username, password)

    def check_user(self, username, password):
        # Check username and password in the dictionnary
        if username in self.server.user_dict:
            if self.server.user_dict[username] == md5(password).hexdigest():
                return True
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

    def log_message(self, format, *args):
        # No message displayed on the server side
        pass


class GlancesXMLRPCServer(SimpleXMLRPCServer):
    """
    Init a SimpleXMLRPCServer instance (IPv6-ready)
    """

    def __init__(self, bind_address, bind_port=61209,
                 requestHandler=GlancesXMLRPCHandler):

        try:
            self.address_family = socket.getaddrinfo(bind_address, bind_port)[0][0]
        except socket.error as e:
            print(_("Couldn't open socket: %s") % e)
            sys.exit(1)

        SimpleXMLRPCServer.__init__(self, (bind_address, bind_port),
                                    requestHandler)


class GlancesInstance():
    """
    All the methods of this class are published as XML RPC methods
    """

    def __init__(self, cached_time=1):
        # cached_time is the minimum time interval between stats updates
        # i.e. XML/RPC calls will not retrieve updated info until the time
        # since last update is passed (will retrieve old cached info instead)
        self.timer = Timer(0)
        self.cached_time = cached_time

    def __update__(self):
        # Never update more than 1 time per cached_time
        if self.timer.finished():
            stats.update()
            self.timer = Timer(self.cached_time)

    def init(self):
        # Return the Glances version
        return __version__

    def getAll(self):
        # Update and return all the stats
        self.__update__()
        return json.dumps(stats.getAll())

    def getAllLimits(self):
        # Return all the limits
        return json.dumps(limits.getAll())

    def getAllMonitored(self):
        # Return the processes monitored list
        return json.dumps(monitors.getAll())

    def getSystem(self):
        # Return operating system info
        # No need to update...
        #~ self.__update__()
        return json.dumps(stats.getSystem())

    def getCore(self):
        # Update and return number of Core
        self.__update__()
        return json.dumps(stats.getCore())

    def getCpu(self):
        # Update and return CPU stats
        self.__update__()
        return json.dumps(stats.getCpu())

    def getLoad(self):
        # Update and return LOAD stats
        self.__update__()
        return json.dumps(stats.getLoad())

    def getMem(self):
        # Update and return MEM stats
        self.__update__()
        return json.dumps(stats.getMem())

    def getMemSwap(self):
        # Update and return MEMSWAP stats
        self.__update__()
        return json.dumps(stats.getMemSwap())

    def getSensors(self):
        # Update and return SENSORS stats
        self.__update__()
        return json.dumps(stats.getSensors())

    def getHDDTemp(self):
        # Update and return HDDTEMP stats
        self.__update__()
        return json.dumps(stats.getHDDTemp())

    def getNetwork(self):
        # Update and return NET stats
        self.__update__()
        return json.dumps(stats.getNetwork())

    def getDiskIO(self):
        # Update and return DISK IO stats
        self.__update__()
        return json.dumps(stats.getDiskIO())

    def getFs(self):
        # Update and return FS stats
        self.__update__()
        return json.dumps(stats.getFs())

    def getProcessCount(self):
        # Update and return ProcessCount stats
        self.__update__()
        return json.dumps(stats.getProcessCount())

    def getProcessList(self):
        # Update and return ProcessList stats
        self.__update__()
        return json.dumps(stats.getProcessList())

    def getBatPercent(self):
        # Update and return total batteries percent stats
        self.__update__()
        return json.dumps(stats.getBatPercent())

    def getNow(self):
        # Update and return current date/hour
        self.__update__()
        return json.dumps(stats.getNow().strftime(_("%Y-%m-%d %H:%M:%S")))

    def getUptime(self):
        # Update and return system uptime
        self.__update__()
        return json.dumps(stats.getUptime().strftime(_("%Y-%m-%d %H:%M:%S")))

    def __getTimeSinceLastUpdate(self, IOType):
        assert(IOType in ['net', 'disk', 'process_disk'])
        return getTimeSinceLastUpdate(IOType)

    def getNetTimeSinceLastUpdate(self):
        return getTimeSinceLastUpdate('net')

    def getDiskTimeSinceLastUpdate(self):
        return getTimeSinceLastUpdate('net')

    def getProcessDiskTimeSinceLastUpdate(self):
        return getTimeSinceLastUpdate('process_disk')


class GlancesServer():
    """
    This class creates and manages the TCP client
    """

    def __init__(self, bind_address="0.0.0.0", bind_port=61209,
                 requestHandler=GlancesXMLRPCHandler, cached_time=1):
        # Init the XML RPC server
        try:
            self.server = GlancesXMLRPCServer(bind_address, bind_port, requestHandler)
        except Exception, err:
            print(_("Error: Can not start Glances server (%s)") % err)
            sys.exit(2)

        # The users dict
        # username / MD5 password couple
        # By default, no auth is needed
        self.server.user_dict = {}
        self.server.isAuth = False
        # Register functions
        self.server.register_introspection_functions()
        self.server.register_instance(GlancesInstance(cached_time))

    def add_user(self, username, password):
        """
        Add an user to the dictionnary
        """
        self.server.user_dict[username] = md5(password).hexdigest()
        self.server.isAuth = True

    def serve_forever(self):
        self.server.serve_forever()

    def server_close(self):
        self.server.server_close()

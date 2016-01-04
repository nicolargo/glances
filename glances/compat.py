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

# flake8: noqa
# pylint: skip-file
"""Python 2/3 compatibility shims."""

import operator
import sys

PY3 = sys.version_info[0] == 3

if PY3:
    import queue
    from configparser import ConfigParser, NoOptionError, NoSectionError
    from xmlrpc.client import Fault, ProtocolError, ServerProxy, Transport
    from xmlrpc.server import SimpleXMLRPCRequestHandler, SimpleXMLRPCServer

    input = input
    range = range
    map = map

    text_type = str
    binary_type = bytes

    viewkeys = operator.methodcaller('keys')
    viewvalues = operator.methodcaller('values')
    viewitems = operator.methodcaller('items')

    def listitems(d):
        return list(d.items())

    def listkeys(d):
        return list(d.keys())

    def listvalues(d):
        return list(d.values())

    def iteritems(d):
        return iter(d.items())

    def iterkeys(d):
        return iter(d.keys())

    def itervalues(d):
        return iter(d.values())

    def u(s):
        return s

    def b(s):
        if isinstance(s, binary_type):
            return s
        return s.encode('latin-1')

    def nativestr(s):
        if isinstance(s, text_type):
            return s
        return s.decode('utf-8', 'replace')
else:
    import Queue as queue
    from itertools import imap as map
    from ConfigParser import SafeConfigParser as ConfigParser, NoOptionError, NoSectionError
    from SimpleXMLRPCServer import SimpleXMLRPCRequestHandler, SimpleXMLRPCServer
    from xmlrpclib import Fault, ProtocolError, ServerProxy, Transport

    input = raw_input
    range = xrange
    ConfigParser.read_file = ConfigParser.readfp

    text_type = unicode
    binary_type = str

    viewkeys = operator.methodcaller('viewkeys')
    viewvalues = operator.methodcaller('viewvalues')
    viewitems = operator.methodcaller('viewitems')

    def listitems(d):
        return d.items()

    def listkeys(d):
        return d.keys()

    def listvalues(d):
        return d.values()

    def iteritems(d):
        return d.iteritems()

    def iterkeys(d):
        return d.iterkeys()

    def itervalues(d):
        return d.itervalues()

    def u(s):
        return s.decode('utf-8')

    def b(s):
        return s

    def nativestr(s):
        if isinstance(s, binary_type):
            return s
        return s.encode('utf-8', 'replace')

try:
    # Python 2.6
    from logutils.dictconfig import dictConfig
except ImportError:
    from logging.config import dictConfig

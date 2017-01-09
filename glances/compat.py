# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2017 Nicolargo <nicolas@nicolargo.com>
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
import unicodedata
import types

PY3 = sys.version_info[0] == 3

if PY3:
    import queue
    from configparser import ConfigParser, NoOptionError, NoSectionError
    from xmlrpc.client import Fault, ProtocolError, ServerProxy, Transport
    from xmlrpc.server import SimpleXMLRPCRequestHandler, SimpleXMLRPCServer
    from urllib.request import urlopen
    from urllib.error import URLError

    input = input
    range = range
    map = map

    text_type = str
    binary_type = bytes
    bool_type = bool

    viewkeys = operator.methodcaller('keys')
    viewvalues = operator.methodcaller('values')
    viewitems = operator.methodcaller('items')

    def to_ascii(s):
        """Convert the bytes string to a ASCII string
        Usefull to remove accent (diacritics)"""
        return str(s, 'utf-8')

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
    from urllib2 import urlopen, URLError

    input = raw_input
    range = xrange
    ConfigParser.read_file = ConfigParser.readfp

    text_type = unicode
    binary_type = str
    bool_type = types.BooleanType

    viewkeys = operator.methodcaller('viewkeys')
    viewvalues = operator.methodcaller('viewvalues')
    viewitems = operator.methodcaller('viewitems')

    def to_ascii(s):
        """Convert the unicode 's' to a ASCII string
        Usefull to remove accent (diacritics)"""
        if isinstance(s, binary_type):
            return s
        return unicodedata.normalize('NFKD', s).encode('ASCII', 'ignore')

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

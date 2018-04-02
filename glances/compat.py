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
import subprocess

from glances.logger import logger

PY3 = sys.version_info[0] == 3

if PY3:
    import queue
    from configparser import ConfigParser, NoOptionError, NoSectionError
    from statistics import mean
    from xmlrpc.client import Fault, ProtocolError, ServerProxy, Transport, Server
    from xmlrpc.server import SimpleXMLRPCRequestHandler, SimpleXMLRPCServer
    from urllib.request import urlopen
    from urllib.error import HTTPError, URLError
    from urllib.parse import urlparse

    input = input
    range = range
    map = map

    text_type = str
    binary_type = bytes
    bool_type = bool
    long = int

    viewkeys = operator.methodcaller('keys')
    viewvalues = operator.methodcaller('values')
    viewitems = operator.methodcaller('items')

    def to_ascii(s):
        """Convert the bytes string to a ASCII string
        Usefull to remove accent (diacritics)"""
        if isinstance(s, binary_type):
            return s.decode()
        return s.encode('ascii', 'ignore').decode()

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
        if isinstance(s, text_type):
            return s
        return s.decode('utf-8', 'replace')

    def b(s):
        if isinstance(s, binary_type):
            return s
        return s.encode('utf-8')

    def nativestr(s):
        if isinstance(s, text_type):
            return s
        return s.decode('utf-8', 'replace')

    def system_exec(command):
        """Execute a system command and return the resul as a str"""
        try:
            res = subprocess.run(command.split(' '),
                                 stdout=subprocess.PIPE).stdout.decode('utf-8')
        except Exception as e:
            logger.debug('Can not evaluate command {} ({})'.format(command, e))
            res = ''
        return res.rstrip()

else:
    import Queue as queue
    from itertools import imap as map
    from ConfigParser import SafeConfigParser as ConfigParser, NoOptionError, NoSectionError
    from SimpleXMLRPCServer import SimpleXMLRPCRequestHandler, SimpleXMLRPCServer
    from xmlrpclib import Fault, ProtocolError, ServerProxy, Transport, Server
    from urllib2 import urlopen, HTTPError, URLError
    from urlparse import urlparse

    input = raw_input
    range = xrange
    ConfigParser.read_file = ConfigParser.readfp

    text_type = unicode
    binary_type = str
    bool_type = types.BooleanType
    long = long

    viewkeys = operator.methodcaller('viewkeys')
    viewvalues = operator.methodcaller('viewvalues')
    viewitems = operator.methodcaller('viewitems')

    def mean(numbers):
        return float(sum(numbers)) / max(len(numbers), 1)

    def to_ascii(s):
        """Convert the unicode 's' to a ASCII string
        Usefull to remove accent (diacritics)"""
        if isinstance(s, binary_type):
            return s
        return unicodedata.normalize('NFKD', s).encode('ascii', 'ignore')

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
        if isinstance(s, text_type):
            return s
        return s.decode('utf-8')

    def b(s):
        if isinstance(s, binary_type):
            return s
        return s.encode('utf-8', 'replace')

    def nativestr(s):
        if isinstance(s, binary_type):
            return s
        return s.encode('utf-8', 'replace')

    def system_exec(command):
        """Execute a system command and return the resul as a str"""
        try:
            res = subprocess.check_output(command.split(' '))
        except Exception as e:
            logger.debug('Can not execute command {} ({})'.format(command, e))
            res = ''
        return res.rstrip()


# Globals functions for both Python 2 and 3


def subsample(data, sampling):
    """Compute a simple mean subsampling.

    Data should be a list of numerical itervalues

    Return a subsampled list of sampling lenght
    """
    if len(data) <= sampling:
        return data
    sampling_length = int(round(len(data) / float(sampling)))
    return [mean(data[s * sampling_length:(s + 1) * sampling_length]) for s in xrange(0, sampling)]


def time_serie_subsample(data, sampling):
    """Compute a simple mean subsampling.

    Data should be a list of set (time, value)

    Return a subsampled list of sampling lenght
    """
    if len(data) <= sampling:
        return data
    t = [t[0] for t in data]
    v = [t[1] for t in data]
    sampling_length = int(round(len(data) / float(sampling)))
    t_subsampled = [t[s * sampling_length:(s + 1) * sampling_length][0] for s in xrange(0, sampling)]
    v_subsampled = [mean(v[s * sampling_length:(s + 1) * sampling_length]) for s in xrange(0, sampling)]
    return list(zip(t_subsampled, v_subsampled))

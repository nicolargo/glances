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

"""Glances unitary tests suite for the XML/RPC API."""

import gettext
import locale
import sys
import time
import unittest
import shlex
import subprocess
import xmlrpclib
import json
import types

from glances.core.glances_globals import (
    appname,
    is_linux,
    version
)

SERVER_PORT = 61234
URL = "http://localhost:%s" % SERVER_PORT
pid = None

# Global variables
# =================

# Unitary test is only available from a GNU/Linus machine
if not is_linux:
    print('ERROR: XML/RPC API unitaries tests should be ran on GNU/Linux operating system')
    sys.exit(2)
else:
    print('Unitary tests for {0} {1}'.format(appname, version))

# Import local settings
from glances.core.glances_globals import gettext_domain, locale_dir
locale.setlocale(locale.LC_ALL, '')
gettext.install(gettext_domain, locale_dir)

# Init Glances core
from glances.core.glances_main import GlancesMain
core = GlancesMain()
if not core.is_standalone():
    print('ERROR: Glances core should be ran in standalone mode')
    sys.exit(1)

# Init Glances stats
from glances.core.glances_stats import GlancesStats
stats = GlancesStats()

# Init the XML/RCP client
client = xmlrpclib.ServerProxy(URL)

# Unitest class
# ==============

class TestGlances(unittest.TestCase):

    """Test Glances class."""

    def setUp(self):
        """The function is called *every time* before test_*."""
        print('\n' + '=' * 78)

    def test_000_start_server(self):
        """Start the Glances Web Server"""
        print('INFO: [TEST_000] Start the Glances Web Server')
    
        global pid
    
        cmdline = "/usr/bin/python -m glances -s -p %s" % SERVER_PORT
        print("Run the Glances Server on port %s" % SERVER_PORT)
        args = shlex.split(cmdline)
        pid = subprocess.Popen(args)
        print("Please wait...")
        time.sleep(1)
    
        self.assertTrue(pid is not None)

    def test_001_all(self):
        """All"""
        method = "getAll()"
        print('INFO: [TEST_001] Connection test')

        print("XML/RPC request: %s" % method)
        req = json.loads(client.getAll())

        self.assertIsInstance(req, types.DictType)

    def test_002_pluginslist(self):
        """Plugins list"""
        method = "getAllPlugins()"
        print('INFO: [TEST_002] Get plugins list')

        print("XML/RPC request: %s" % method)
        req = json.loads(client.getAllPlugins())

        self.assertIsInstance(req, types.ListType)

    def test_003_system(self):
        """System"""
        method = "getSystem()"
        print('INFO: [TEST_003] Method: %s' % method)

        req = json.loads(client.getSystem())

        self.assertIsInstance(req, types.DictType)

    def test_004_cpu(self):
        """CPU"""
        method = "getCpu(), getPerCpu(), getLoad() and getCore()"
        print('INFO: [TEST_004] Method: %s' % method)

        req = json.loads(client.getCpu())
        self.assertIsInstance(req, types.DictType)

        req = json.loads(client.getPerCpu())
        self.assertIsInstance(req, types.ListType)

        req = json.loads(client.getLoad())
        self.assertIsInstance(req, types.DictType)

        req = json.loads(client.getCore())
        self.assertIsInstance(req, types.DictType)

    def test_005_mem(self):
        """MEM"""
        method = "getMem() and getMemSwap()"
        print('INFO: [TEST_005] Method: %s' % method)

        req = json.loads(client.getMem())
        self.assertIsInstance(req, types.DictType)

        req = json.loads(client.getMemSwap())
        self.assertIsInstance(req, types.DictType)

    def test_006_net(self):
        """NETWORK"""
        method = "getNetwork()"
        print('INFO: [TEST_006] Method: %s' % method)

        req = json.loads(client.getNetwork())
        self.assertIsInstance(req, types.ListType)

    def test_007_disk(self):
        """DISK"""
        method = "getFs() and getDiskIO()"
        print('INFO: [TEST_007] Method: %s' % method)

        req = json.loads(client.getFs())
        self.assertIsInstance(req, types.ListType)

        req = json.loads(client.getDiskIO())
        self.assertIsInstance(req, types.ListType)

    def test_008_sensors(self):
        """SENSORS"""
        method = "getSensors()"
        print('INFO: [TEST_008] Method: %s' % method)

        req = json.loads(client.getSensors())
        self.assertIsInstance(req, types.ListType)

    def test_009_process(self):
        """PROCESS"""
        method = "getProcessCount() and getProcessList()"
        print('INFO: [TEST_009] Method: %s' % method)

        req = json.loads(client.getProcessCount())
        self.assertIsInstance(req, types.DictType)

        req = json.loads(client.getProcessList())
        self.assertIsInstance(req, types.ListType)

    def test_999_stop_server(self):
        """Stop the Glances Web Server"""
        print('INFO: [TEST_999] Stop the Glances Server')

        print("Stop the Glances Server")
        pid.terminate()
        print("Please wait...")
        time.sleep(1)

        self.assertTrue(True)

if __name__ == '__main__':
    unittest.main()

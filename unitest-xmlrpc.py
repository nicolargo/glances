#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Glances - An eye on your system
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

"""Glances unitary tests suite for the XML-RPC API."""

import json
import shlex
import subprocess
import time
import unittest

from glances import __version__
from glances.compat import ServerProxy

SERVER_PORT = 61234
URL = "http://localhost:%s" % SERVER_PORT
pid = None

# Init the XML-RPC client
client = ServerProxy(URL)

# Unitest class
# ==============
print('XML-RPC API unitary tests for Glances %s' % __version__)


class TestGlances(unittest.TestCase):
    """Test Glances class."""

    def setUp(self):
        """The function is called *every time* before test_*."""
        print('\n' + '=' * 78)

    def test_000_start_server(self):
        """Start the Glances Web Server."""
        global pid

        print('INFO: [TEST_000] Start the Glances Web Server')
        cmdline = "python -m glances -s -p %s" % SERVER_PORT
        print("Run the Glances Server on port %s" % SERVER_PORT)
        args = shlex.split(cmdline)
        pid = subprocess.Popen(args)
        print("Please wait...")
        time.sleep(1)

        self.assertTrue(pid is not None)

    def test_001_all(self):
        """All."""
        method = "getAll()"
        print('INFO: [TEST_001] Connection test')
        print("XML-RPC request: %s" % method)
        req = json.loads(client.getAll())

        self.assertIsInstance(req, dict)

    def test_002_pluginslist(self):
        """Plugins list."""
        method = "getAllPlugins()"
        print('INFO: [TEST_002] Get plugins list')
        print("XML-RPC request: %s" % method)
        req = json.loads(client.getAllPlugins())

        self.assertIsInstance(req, list)

    def test_003_system(self):
        """System."""
        method = "getSystem()"
        print('INFO: [TEST_003] Method: %s' % method)
        req = json.loads(client.getSystem())

        self.assertIsInstance(req, dict)

    def test_004_cpu(self):
        """CPU."""
        method = "getCpu(), getPerCpu(), getLoad() and getCore()"
        print('INFO: [TEST_004] Method: %s' % method)

        req = json.loads(client.getCpu())
        self.assertIsInstance(req, dict)

        req = json.loads(client.getPerCpu())
        self.assertIsInstance(req, list)

        req = json.loads(client.getLoad())
        self.assertIsInstance(req, dict)

        req = json.loads(client.getCore())
        self.assertIsInstance(req, dict)

    def test_005_mem(self):
        """MEM."""
        method = "getMem() and getMemSwap()"
        print('INFO: [TEST_005] Method: %s' % method)

        req = json.loads(client.getMem())
        self.assertIsInstance(req, dict)

        req = json.loads(client.getMemSwap())
        self.assertIsInstance(req, dict)

    def test_006_net(self):
        """NETWORK."""
        method = "getNetwork()"
        print('INFO: [TEST_006] Method: %s' % method)

        req = json.loads(client.getNetwork())
        self.assertIsInstance(req, list)

    def test_007_disk(self):
        """DISK."""
        method = "getFs(), getFolders() and getDiskIO()"
        print('INFO: [TEST_007] Method: %s' % method)

        req = json.loads(client.getFs())
        self.assertIsInstance(req, list)

        req = json.loads(client.getFolders())
        self.assertIsInstance(req, list)

        req = json.loads(client.getDiskIO())
        self.assertIsInstance(req, list)

    def test_008_sensors(self):
        """SENSORS."""
        method = "getSensors()"
        print('INFO: [TEST_008] Method: %s' % method)

        req = json.loads(client.getSensors())
        self.assertIsInstance(req, list)

    def test_009_process(self):
        """PROCESS."""
        method = "getProcessCount() and getProcessList()"
        print('INFO: [TEST_009] Method: %s' % method)

        req = json.loads(client.getProcessCount())
        self.assertIsInstance(req, dict)

        req = json.loads(client.getProcessList())
        self.assertIsInstance(req, list)

    def test_010_all_limits(self):
        """All limits."""
        method = "getAllLimits()"
        print('INFO: [TEST_010] Method: %s' % method)

        req = json.loads(client.getAllLimits())
        self.assertIsInstance(req, dict)
        self.assertIsInstance(req['cpu'], dict)

    def test_011_all_views(self):
        """All views."""
        method = "getAllViews()"
        print('INFO: [TEST_011] Method: %s' % method)

        req = json.loads(client.getAllViews())
        self.assertIsInstance(req, dict)
        self.assertIsInstance(req['cpu'], dict)

    def test_012_irq(self):
        """IRQS"""
        method = "getIrqs()"
        print('INFO: [TEST_012] Method: %s' % method)
        req = json.loads(client.getIrq())
        self.assertIsInstance(req, list)

    def test_013_plugin_views(self):
        """Plugin views."""
        method = "getViewsCpu()"
        print('INFO: [TEST_013] Method: %s' % method)

        req = json.loads(client.getViewsCpu())
        self.assertIsInstance(req, dict)

    def test_999_stop_server(self):
        """Stop the Glances Web Server."""
        print('INFO: [TEST_999] Stop the Glances Server')

        print("Stop the Glances Server")
        pid.terminate()
        time.sleep(1)

        self.assertTrue(True)


if __name__ == '__main__':
    unittest.main()

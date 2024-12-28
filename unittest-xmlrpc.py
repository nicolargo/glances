#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances unitary tests suite for the XML-RPC API."""

import json
import os
import shlex
import subprocess
import time
import unittest

from glances import __version__
from glances.client import GlancesClient

SERVER_HOST = 'localhost'
SERVER_PORT = 61235
pid = None


# Init the XML-RPC client
class args:
    client = SERVER_HOST
    port = SERVER_PORT
    username = ""
    password = ""
    time = 3
    quiet = False


client = GlancesClient(args=args).client

# Unitest class
# ==============
print(f'XML-RPC API unitary tests for Glances {__version__}')


class TestGlances(unittest.TestCase):
    """Test Glances class."""

    def setUp(self):
        """The function is called *every time* before test_*."""
        print('\n' + '=' * 78)

    def test_000_start_server(self):
        """Start the Glances Web Server."""
        global pid

        print('INFO: [TEST_000] Start the Glances Web Server')
        if os.path.isfile('./venv/bin/python'):
            cmdline = "./venv/bin/python"
        else:
            cmdline = "python"
        cmdline += f" -m glances -B localhost -s -p {SERVER_PORT}"
        print(f"Run the Glances Server on port {SERVER_PORT}")
        args = shlex.split(cmdline)
        pid = subprocess.Popen(args)
        print("Please wait...")
        time.sleep(1)

        self.assertTrue(pid is not None)

    def test_001_all(self):
        """All."""
        method = "getAll()"
        print('INFO: [TEST_001] Connection test')
        print(f"XML-RPC request: {method}")
        req = json.loads(client.getAll())

        self.assertIsInstance(req, dict)

    def test_002_pluginslist(self):
        """Plugins list."""
        method = "getAllPlugins()"
        print('INFO: [TEST_002] Get plugins list')
        print(f"XML-RPC request: {method}")
        req = json.loads(client.getAllPlugins())
        print(req)

        self.assertIsInstance(req, list)
        self.assertIn('cpu', req)

    def test_003_system(self):
        """System."""
        method = "getSystem()"
        print(f'INFO: [TEST_003] Method: {method}')
        req = json.loads(client.getPlugin('system'))

        self.assertIsInstance(req, dict)

    def test_004_cpu(self):
        """CPU."""
        method = "getCpu(), getPerCpu(), getLoad() and getCore()"
        print(f'INFO: [TEST_004] Method: {method}')

        req = json.loads(client.getPlugin('cpu'))
        self.assertIsInstance(req, dict)

        req = json.loads(client.getPlugin('percpu'))
        self.assertIsInstance(req, list)

        req = json.loads(client.getPlugin('load'))
        self.assertIsInstance(req, dict)

        req = json.loads(client.getPlugin('core'))
        self.assertIsInstance(req, dict)

    def test_005_mem(self):
        """MEM."""
        method = "getMem() and getMemSwap()"
        print(f'INFO: [TEST_005] Method: {method}')

        req = json.loads(client.getPlugin('mem'))
        self.assertIsInstance(req, dict)

        req = json.loads(client.getPlugin('memswap'))
        self.assertIsInstance(req, dict)

    def test_006_net(self):
        """NETWORK."""
        method = "getNetwork()"
        print(f'INFO: [TEST_006] Method: {method}')

        req = json.loads(client.getPlugin('network'))
        self.assertIsInstance(req, list)

    def test_007_disk(self):
        """DISK."""
        method = "getFs(), getFolders() and getDiskIO()"
        print(f'INFO: [TEST_007] Method: {method}')

        req = json.loads(client.getPlugin('fs'))
        self.assertIsInstance(req, list)

        req = json.loads(client.getPlugin('folders'))
        self.assertIsInstance(req, list)

        req = json.loads(client.getPlugin('diskio'))
        self.assertIsInstance(req, list)

    def test_008_sensors(self):
        """SENSORS."""
        method = "getSensors()"
        print(f'INFO: [TEST_008] Method: {method}')

        req = json.loads(client.getPlugin('sensors'))
        self.assertIsInstance(req, list)

    def test_009_process(self):
        """PROCESS."""
        method = "getProcessCount() and getProcessList()"
        print(f'INFO: [TEST_009] Method: {method}')

        req = json.loads(client.getPlugin('processcount'))
        self.assertIsInstance(req, dict)

        req = json.loads(client.getPlugin('processlist'))
        self.assertIsInstance(req, list)

    def test_010_all_limits(self):
        """All limits."""
        method = "getAllLimits()"
        print(f'INFO: [TEST_010] Method: {method}')

        req = json.loads(client.getAllLimits())
        self.assertIsInstance(req, dict)
        self.assertIsInstance(req['cpu'], dict)

    def test_011_all_views(self):
        """All views."""
        method = "getAllViews()"
        print(f'INFO: [TEST_011] Method: {method}')

        req = json.loads(client.getAllViews())
        self.assertIsInstance(req, dict)
        self.assertIsInstance(req['cpu'], dict)

    def test_012_irq(self):
        """IRQS"""
        method = "getIrqs()"
        print(f'INFO: [TEST_012] Method: {method}')
        req = json.loads(client.getPlugin('irq'))
        self.assertIsInstance(req, list)

    def test_013_plugin_views(self):
        """Plugin views."""
        method = "getViewsCpu()"
        print(f'INFO: [TEST_013] Method: {method}')

        req = json.loads(client.getPluginView('cpu'))
        self.assertIsInstance(req, dict)

    def test_999_stop_server(self):
        """Stop the Glances Web Server."""
        print('INFO: [TEST_999] Stop the Glances Server')
        print(client.system.listMethods())

        print("Stop the Glances Server")
        pid.terminate()
        time.sleep(1)

        self.assertTrue(True)


if __name__ == '__main__':
    unittest.main()

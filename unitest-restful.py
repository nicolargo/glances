#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Glances - An eye on your system
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

"""Glances unitary tests suite for the RESTful API."""

import shlex
import subprocess
import time
import unittest

from glances import __version__
from glances.compat import text_type

import requests

SERVER_PORT = 61234
URL = "http://localhost:%s/api/2" % SERVER_PORT
pid = None

# Unitest class
# ==============
print('RESTful API unitary tests for Glances %s' % __version__)


class TestGlances(unittest.TestCase):
    """Test Glances class."""

    def setUp(self):
        """The function is called *every time* before test_*."""
        print('\n' + '=' * 78)

    def test_000_start_server(self):
        """Start the Glances Web Server."""
        global pid

        print('INFO: [TEST_000] Start the Glances Web Server')
        cmdline = "python -m glances -w -p %s" % SERVER_PORT
        print("Run the Glances Web Server on port %s" % SERVER_PORT)
        args = shlex.split(cmdline)
        pid = subprocess.Popen(args)
        print("Please wait...")
        time.sleep(3)

        self.assertTrue(pid is not None)

    def test_001_all(self):
        """All."""
        method = "all"
        print('INFO: [TEST_001] Get all stats')
        print("HTTP RESTful request: %s/%s" % (URL, method))
        req = requests.get("%s/%s" % (URL, method))

        self.assertTrue(req.ok)

    def test_002_pluginslist(self):
        """Plugins list."""
        method = "pluginslist"
        print('INFO: [TEST_002] Plugins list')
        print("HTTP RESTful request: %s/%s" % (URL, method))
        req = requests.get("%s/%s" % (URL, method))

        self.assertTrue(req.ok)
        self.assertIsInstance(req.json(), list)
        self.assertIn('cpu', req.json())

    def test_003_plugins(self):
        """Plugins."""
        method = "pluginslist"
        print('INFO: [TEST_003] Plugins')
        plist = requests.get("%s/%s" % (URL, method))

        for p in plist.json():
            print("HTTP RESTful request: %s/%s" % (URL, p))
            req = requests.get("%s/%s" % (URL, p))
            self.assertTrue(req.ok)
            if p in ('uptime', 'now'):
                self.assertIsInstance(req.json(), text_type)
            elif p in ('fs', 'monitor', 'percpu', 'sensors', 'alert', 'processlist',
                       'diskio', 'hddtemp', 'batpercent', 'network', 'folders'):
                self.assertIsInstance(req.json(), list)
            elif p in ('psutilversion', 'help'):
                pass
            else:
                self.assertIsInstance(req.json(), dict)

    def test_004_items(self):
        """Items."""
        method = "cpu"
        print('INFO: [TEST_004] Items for the CPU method')
        ilist = requests.get("%s/%s" % (URL, method))

        for i in ilist.json():
            print("HTTP RESTful request: %s/%s/%s" % (URL, method, i))
            req = requests.get("%s/%s/%s" % (URL, method, i))
            self.assertTrue(req.ok)
            self.assertIsInstance(req.json(), dict)
            self.assertIsInstance(req.json()[i], float)

    def test_005_values(self):
        """Values."""
        method = "processlist"
        print('INFO: [TEST_005] Item=Value for the PROCESSLIST method')
        print("%s/%s/pid/0" % (URL, method))
        req = requests.get("%s/%s/pid/0" % (URL, method))

        self.assertTrue(req.ok)
        self.assertIsInstance(req.json(), dict)

    def test_006_all_limits(self):
        """All limits."""
        method = "all/limits"
        print('INFO: [TEST_006] Get all limits')
        print("HTTP RESTful request: %s/%s" % (URL, method))
        req = requests.get("%s/%s" % (URL, method))

        self.assertTrue(req.ok)
        self.assertIsInstance(req.json(), dict)

    def test_007_all_views(self):
        """All views."""
        method = "all/views"
        print('INFO: [TEST_007] Get all views')
        print("HTTP RESTful request: %s/%s" % (URL, method))
        req = requests.get("%s/%s" % (URL, method))

        self.assertTrue(req.ok)
        self.assertIsInstance(req.json(), dict)

    def test_008_plugins_limits(self):
        """Plugins limits."""
        method = "pluginslist"
        print('INFO: [TEST_008] Plugins limits')
        plist = requests.get("%s/%s" % (URL, method))

        for p in plist.json():
            print("HTTP RESTful request: %s/%s/limits" % (URL, p))
            req = requests.get("%s/%s/limits" % (URL, p))
            self.assertTrue(req.ok)
            self.assertIsInstance(req.json(), dict)

    def test_009_plugins_views(self):
        """Plugins views."""
        method = "pluginslist"
        print('INFO: [TEST_009] Plugins views')
        plist = requests.get("%s/%s" % (URL, method))

        for p in plist.json():
            print("HTTP RESTful request: %s/%s/views" % (URL, p))
            req = requests.get("%s/%s/views" % (URL, p))
            self.assertTrue(req.ok)
            self.assertIsInstance(req.json(), dict)

    def test_999_stop_server(self):
        """Stop the Glances Web Server."""
        print('INFO: [TEST_999] Stop the Glances Web Server')

        print("Stop the Glances Web Server")
        pid.terminate()
        time.sleep(1)

        self.assertTrue(True)

if __name__ == '__main__':
    unittest.main()

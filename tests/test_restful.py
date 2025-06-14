#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances unitary tests suite for the RESTful API."""

import numbers
import os
import shlex
import subprocess
import time
import types
import unittest

import requests

from glances import __version__
from glances.globals import text_type
from glances.outputs.glances_restful_api import GlancesRestfulApi
from glances.timer import Counter

SERVER_PORT = 61234
API_VERSION = GlancesRestfulApi.API_VERSION
URL = f"http://localhost:{SERVER_PORT}/api/{API_VERSION}"
pid = None

# Unitest class
# ==============
print(f'RESTful API unitary tests for Glances {__version__}')


class TestGlances(unittest.TestCase):
    """Test Glances class."""

    def setUp(self):
        """The function is called *every time* before test_*."""
        print('\n' + '=' * 78)

    def http_get(self, url, gzip=False):
        """Make the request"""
        if gzip:
            ret = requests.get(url, stream=True, headers={'Accept-encoding': 'gzip'})
        else:
            ret = requests.get(url, headers={'Accept-encoding': 'identity'})
        return ret

    def test_000_start_server(self):
        """Start the Glances Web Server."""
        global pid

        print('INFO: [TEST_000] Start the Glances Web Server API')
        if os.path.isfile('./venv/bin/python'):
            cmdline = "./venv/bin/python"
        else:
            cmdline = "python"
        cmdline += f" -m glances -B 0.0.0.0 -w --browser -p {SERVER_PORT} --disable-webui -C ./conf/glances.conf"
        print(f"Run the Glances Web Server on port {SERVER_PORT}")
        args = shlex.split(cmdline)
        pid = subprocess.Popen(args)
        print("Please wait 5 seconds...")
        time.sleep(5)

        self.assertTrue(pid is not None)

    def test_001_all(self):
        """All."""
        method = "all"
        print('INFO: [TEST_001] Get all stats')
        print(f"HTTP RESTful request: {URL}/{method}")
        # First call is not cached
        counter_first_call = Counter()
        first_req = self.http_get(f"{URL}/{method}")
        self.assertTrue(first_req.ok)
        self.assertTrue(first_req.json(), dict)
        counter_first_call_result = counter_first_call.get()
        # Second call (if it is in the same second) is cached
        counter_second_call = Counter()
        second_req = self.http_get(f"{URL}/{method}")
        self.assertTrue(second_req.ok)
        self.assertTrue(second_req.json(), dict)
        counter_second_call_result = counter_second_call.get()
        # Check if result of first call is equal to second call
        self.assertEqual(first_req.json(), second_req.json(), "The result of the first and second call should be equal")
        # Check cache result
        print(
            f"First API call took {counter_first_call_result:.2f} seconds"
            f" and second API call (cached) took {counter_second_call_result:.2f} seconds"
        )
        self.assertTrue(
            counter_second_call_result < counter_first_call_result,
            "The second call should be cached (faster than the first one)",
        )

    def test_002_pluginslist(self):
        """Plugins list."""
        method = "pluginslist"
        print('INFO: [TEST_002] Plugins list')
        print(f"HTTP RESTful request: {URL}/{method}")
        req = self.http_get(f"{URL}/{method}")

        self.assertTrue(req.ok)
        self.assertIsInstance(req.json(), list)
        self.assertIn('cpu', req.json())

    def test_003_plugins(self):
        """Plugins."""
        method = "pluginslist"
        print('INFO: [TEST_003] Plugins')
        plist = self.http_get(f"{URL}/{method}")

        for p in plist.json():
            print(f"HTTP RESTful request: {URL}/{p}")
            req = self.http_get(f"{URL}/{p}")
            self.assertTrue(req.ok)
            if p in ('uptime', 'version', 'psutilversion'):
                self.assertIsInstance(req.json(), text_type)
            elif p in (
                'fs',
                'percpu',
                'sensors',
                'alert',
                'processlist',
                'programlist',
                'diskio',
                'hddtemp',
                'batpercent',
                'network',
                'folders',
                'amps',
                'ports',
                'irq',
                'wifi',
                'gpu',
                'containers',
                'vms',
            ):
                self.assertIsInstance(req.json(), list)
                if len(req.json()) > 0:
                    self.assertIsInstance(req.json()[0], dict)
            else:
                self.assertIsInstance(req.json(), dict)

    def test_004_items(self):
        """Items."""
        method = "cpu"
        print('INFO: [TEST_004] Items for the CPU method')
        ilist = self.http_get(f"{URL}/{method}")

        for i in ilist.json():
            print(f"HTTP RESTful request: {URL}/{method}/{i}")
            req = self.http_get(f"{URL}/{method}/{i}")
            self.assertTrue(req.ok)
            self.assertIsInstance(req.json(), dict)
            print(req.json()[i])
            # Value can be a number or None (for _rate in first loop)
            self.assertIsInstance(req.json()[i], (numbers.Number, types.NoneType))

    def test_005_values(self):
        """Values."""
        method = "processlist"
        print('INFO: [TEST_005] Item=Value for the PROCESSLIST method')
        req = self.http_get(f"{URL}/{method}/pid/value/0")

        self.assertTrue(req.ok)
        self.assertIsInstance(req.json(), dict)

    def test_006_all_limits(self):
        """All limits."""
        method = "all/limits"
        print('INFO: [TEST_006] Get all limits')
        print(f"HTTP RESTful request: {URL}/{method}")
        req = self.http_get(f"{URL}/{method}")

        self.assertTrue(req.ok)
        self.assertIsInstance(req.json(), dict)

    def test_007_all_views(self):
        """All views."""
        method = "all/views"
        print('INFO: [TEST_007] Get all views')
        print(f"HTTP RESTful request: {URL}/{method}")
        req = self.http_get(f"{URL}/{method}")

        self.assertTrue(req.ok)
        self.assertIsInstance(req.json(), dict)

    def test_008_plugins_limits(self):
        """Plugins limits."""
        method = "pluginslist"
        print('INFO: [TEST_008] Plugins limits')
        plist = self.http_get(f"{URL}/{method}")

        for p in plist.json():
            print(f"HTTP RESTful request: {URL}/{p}/limits")
            req = self.http_get(f"{URL}/{p}/limits")
            self.assertTrue(req.ok)
            self.assertIsInstance(req.json(), dict)

    def test_009_plugins_views(self):
        """Plugins views."""
        method = "pluginslist"
        print('INFO: [TEST_009] Plugins views')
        plist = self.http_get(f"{URL}/{method}")

        for p in plist.json():
            print(f"HTTP RESTful request: {URL}/{p}/views")
            req = self.http_get(f"{URL}/{p}/views")
            self.assertTrue(req.ok)
            self.assertIsInstance(req.json(), dict)

    def test_010_history(self):
        """History."""
        method = "history"
        print('INFO: [TEST_010] History')
        print(f"HTTP RESTful request: {URL}/cpu/{method}")
        req = self.http_get(f"{URL}/cpu/{method}")
        self.assertIsInstance(req.json(), dict)
        self.assertIsInstance(req.json()['user'], list)
        self.assertTrue(len(req.json()['user']) > 0)
        print(f"HTTP RESTful request: {URL}/cpu/{method}/3")
        req = self.http_get(f"{URL}/cpu/{method}/3")
        self.assertIsInstance(req.json(), dict)
        self.assertIsInstance(req.json()['user'], list)
        self.assertTrue(len(req.json()['user']) > 1)
        print(f"HTTP RESTful request: {URL}/cpu/system/{method}")
        req = self.http_get(f"{URL}/cpu/system/{method}")
        self.assertIsInstance(req.json(), list)
        self.assertIsInstance(req.json()[0], list)
        print(f"HTTP RESTful request: {URL}/cpu/system/{method}/3")
        req = self.http_get(f"{URL}/cpu/system/{method}/3")
        self.assertIsInstance(req.json(), list)
        self.assertIsInstance(req.json()[0], list)

    def test_011_issue1401(self):
        """Check issue #1401."""
        method = "network/interface_name"
        print('INFO: [TEST_011] Issue #1401')
        req = self.http_get(f"{URL}/{method}")
        self.assertTrue(req.ok)
        self.assertIsInstance(req.json(), dict)
        self.assertIsInstance(req.json()['interface_name'], list)

    def test_012_status(self):
        """Check status endpoint."""
        method = "status"
        print('INFO: [TEST_012] Status')
        print(f"HTTP RESTful request: {URL}/{method}")
        req = self.http_get(f"{URL}/{method}")

        self.assertTrue(req.ok)
        self.assertEqual(req.json()['version'], __version__)

    def test_013_top(self):
        """Values."""
        method = "processlist"
        request = f"{URL}/{method}/top/2"
        print('INFO: [TEST_013] Top nb item of PROCESSLIST')
        print(request)
        req = self.http_get(request)

        self.assertTrue(req.ok)
        self.assertIsInstance(req.json(), list)
        self.assertEqual(len(req.json()), 2)

    def test_014_config(self):
        """Test API request to get Glances configuration."""
        method = "config"
        print('INFO: [TEST_014] Get config')

        req = self.http_get(f"{URL}/{method}")
        self.assertTrue(req.ok)
        self.assertIsInstance(req.json(), dict)

        req = self.http_get(f"{URL}/{method}/global/refresh")
        self.assertTrue(req.ok)
        self.assertEqual(req.json(), "2")

    def test_015_all_gzip(self):
        """All with Gzip."""
        method = "all"
        print('INFO: [TEST_015] Get all stats (with GZip compression)')
        print(f"HTTP RESTful request: {URL}/{method}")
        req = self.http_get(f"{URL}/{method}", gzip=True)

        self.assertTrue(req.ok)
        self.assertTrue(req.headers['Content-Encoding'] == 'gzip')
        self.assertTrue(req.json(), dict)

    def test_016_fields_description(self):
        """Fields description."""
        print('INFO: [TEST_016] Get fields description and unit')

        print(f"HTTP RESTful request: {URL}/cpu/total/description")
        req = self.http_get(f"{URL}/cpu/total/description")
        self.assertTrue(req.ok)
        self.assertTrue(req.json(), str)

        print(f"HTTP RESTful request: {URL}/cpu/total/unit")
        req = self.http_get(f"{URL}/cpu/total/unit")
        self.assertTrue(req.ok)
        self.assertTrue(req.json(), str)

    def test_017_item_key(self):
        """Get /plugin/item/key value."""
        print('INFO: [TEST_017] Get /plugin/item/key value')
        plugin = "network"
        item = "interface_name"
        req = self.http_get(f"{URL}/{plugin}/{item}")
        self.assertTrue(req.ok)
        self.assertIsInstance(req.json(), dict)
        self.assertIsInstance(req.json()[item], list)
        if len(req.json()[item]) > 0:
            key = req.json()[item][0]
            item = "bytes_all"
            req = self.http_get(f"{URL}/{plugin}/{item}/{key}")
            self.assertTrue(req.ok)
            self.assertIsInstance(req.json(), dict)
            self.assertIsInstance(req.json()[item], int)

    def test_100_browser(self):
        """Get /serverslist (for Glances Central Browser)."""
        print('INFO: [TEST_100] Get /serverslist (for Glances Central Browser)')
        req = self.http_get(f"{URL}/serverslist")
        self.assertTrue(req.ok)
        self.assertIsInstance(req.json(), list)
        if len(req.json()) > 0:
            self.assertIsInstance(req.json()[0], dict)

    def test_999_stop_server(self):
        """Stop the Glances Web Server."""
        print('INFO: [TEST_999] Stop the Glances Web Server')

        print("Stop the Glances Web Server")
        pid.terminate()
        time.sleep(1)

        self.assertTrue(True)


if __name__ == '__main__':
    unittest.main()

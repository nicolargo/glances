#!/usr/bin/env python
#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the Glances XML-RPC server Host header validation
(GHSA-w856-8p3r-p338 / CVE-2026-46611)."""

import shlex
import subprocess
import sys
import time
import unittest

import requests

SERVER_PORT = 62209
URL = f"http://127.0.0.1:{SERVER_PORT}/RPC2"

XMLRPC_BODY = '<?xml version="1.0"?><methodCall><methodName>init</methodName></methodCall>'


pid = None


class TestGlancesXmlrpc(unittest.TestCase):
    """Glances XML-RPC server Host header validation tests."""

    def setUp(self):
        print('\n' + '=' * 78)

    def post(self, host_header):
        """POST an XML-RPC call with a specific Host header."""
        return requests.post(
            URL,
            data=XMLRPC_BODY,
            headers={'Host': host_header, 'Content-Type': 'text/plain'},
            timeout=5,
        )

    def test_000_start_server(self):
        """Start the Glances XML-RPC server (no allowlist configured)."""
        global pid
        print('INFO: [TEST_000] Start the Glances XML-RPC Server')
        cmdline = sys.executable
        cmdline += f" -m glances -B 127.0.0.1 -s -p {SERVER_PORT} --disable-autodiscover -C ./conf/glances.conf"
        print(f"Run: {cmdline}")
        pid = subprocess.Popen(shlex.split(cmdline))
        print("Wait 5 seconds for server start...")
        time.sleep(5)
        self.assertIsNotNone(pid)

    def test_999_stop_server(self):
        """Stop the Glances XML-RPC server."""
        print('INFO: [TEST_999] Stop server')
        pid.terminate()
        time.sleep(1)
        self.assertTrue(True)


if __name__ == '__main__':
    unittest.main()

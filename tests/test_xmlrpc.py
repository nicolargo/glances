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

SECURE_PORT = 62210
SECURE_URL = f"http://127.0.0.1:{SECURE_PORT}/RPC2"

XMLRPC_BODY = '<?xml version="1.0"?><methodCall><methodName>init</methodName></methodCall>'


pid = None
pid_secure = None


class TestGlancesXmlrpc(unittest.TestCase):
    """Glances XML-RPC server Host header validation tests."""

    def setUp(self):
        print('\n' + '=' * 78)

    def post(self, host_header):
        """POST an XML-RPC call with a specific Host header (default server)."""
        return requests.post(
            URL,
            data=XMLRPC_BODY,
            headers={'Host': host_header, 'Content-Type': 'text/plain'},
            timeout=5,
        )

    def post_secure(self, host_header):
        """POST an XML-RPC call with a specific Host header (allowlisted server)."""
        return requests.post(
            SECURE_URL,
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

    def test_001_default_accepts_any_host(self):
        """Without xmlrpc_allowed_hosts set, any Host header is accepted."""
        print('INFO: [TEST_001] Default = permissive (no allowlist)')
        r = self.post('attacker.example.com')
        self.assertEqual(r.status_code, 200)
        self.assertIn('<methodResponse>', r.text)

    def test_010_start_secure_server(self):
        """Start a second XML-RPC server with xmlrpc_allowed_hosts configured."""
        global pid_secure
        print('INFO: [TEST_010] Start secured XML-RPC server')
        cmdline = sys.executable
        cmdline += (
            f" -m glances -B 127.0.0.1 -s -p {SECURE_PORT}"
            " --disable-autodiscover"
            " -C ./tests/conf/glances_xmlrpc_allowed_hosts.conf"
        )
        print(f"Run: {cmdline}")
        pid_secure = subprocess.Popen(shlex.split(cmdline))
        print("Wait 5 seconds for server start...")
        time.sleep(5)
        self.assertIsNotNone(pid_secure)

    def test_011_secure_rejects_spoofed_host(self):
        """With xmlrpc_allowed_hosts=127.0.0.1, Host: attacker.example.com -> 400."""
        print('INFO: [TEST_011] Spoofed Host rejected with 400')
        r = self.post_secure('attacker.example.com')
        self.assertEqual(r.status_code, 400)

    def test_999_stop_server(self):
        """Stop both Glances XML-RPC servers."""
        print('INFO: [TEST_999] Stop both servers')
        pid.terminate()
        if pid_secure is not None:
            pid_secure.terminate()
        time.sleep(1)
        self.assertTrue(True)


if __name__ == '__main__':
    unittest.main()

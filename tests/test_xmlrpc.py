#!/usr/bin/env python
#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the Glances XML-RPC server security headers:
- Host header validation (GHSA-w856-8p3r-p338 / CVE-2026-46611)
- CORS per-request origin reflection (GHSA-87qc-fj39-wccr / CVE-2026-46608)."""

import shlex
import socket
import subprocess
import sys
import time
import unittest

import requests

SERVER_PORT = 62209
URL = f"http://127.0.0.1:{SERVER_PORT}/RPC2"

SECURE_PORT = 62210
SECURE_URL = f"http://127.0.0.1:{SECURE_PORT}/RPC2"

CORS_PORT = 62211
CORS_URL = f"http://127.0.0.1:{CORS_PORT}/RPC2"

XMLRPC_BODY = '<?xml version="1.0"?><methodCall><methodName>init</methodName></methodCall>'


pid = None
pid_secure = None
pid_cors = None


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

    def test_012_secure_accepts_listed_host(self):
        """Allowlisted Host returns 200."""
        print('INFO: [TEST_012] Allowlisted Host accepted')
        r = self.post_secure('127.0.0.1')
        self.assertEqual(r.status_code, 200)
        self.assertIn('<methodResponse>', r.text)

    def test_013_secure_wildcard_match(self):
        """Wildcard pattern *.glances.test matches subdomain."""
        print('INFO: [TEST_013] Wildcard match')
        r = self.post_secure('node1.glances.test')
        self.assertEqual(r.status_code, 200)

    def test_014_secure_wildcard_no_bare_match(self):
        """*.glances.test does NOT match the bare domain glances.test."""
        print('INFO: [TEST_014] Wildcard does not match bare domain')
        r = self.post_secure('glances.test')
        self.assertEqual(r.status_code, 400)

    def test_015_secure_strips_port(self):
        """Host: 127.0.0.1:62210 matches the bare 127.0.0.1 entry."""
        print('INFO: [TEST_015] Port is stripped before matching')
        r = self.post_secure(f'127.0.0.1:{SECURE_PORT}')
        self.assertEqual(r.status_code, 200)

    def post_with_origin(self, url, origin):
        """POST an XML-RPC call with a specific Origin header."""
        return requests.post(
            url,
            data=XMLRPC_BODY,
            headers={'Origin': origin, 'Content-Type': 'text/plain'},
            timeout=5,
        )

    def test_020_default_cors_wildcard(self):
        """Default cors_origins=* echoes ACAO: * for any Origin."""
        print('INFO: [TEST_020] Default CORS wildcard')
        r = self.post_with_origin(URL, 'http://evil.example.com')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers.get('Access-Control-Allow-Origin'), '*')

    def test_030_start_cors_server(self):
        """Start a third XML-RPC server with a two-entry cors_origins allowlist."""
        global pid_cors
        print('INFO: [TEST_030] Start CORS-restricted XML-RPC server')
        cmdline = sys.executable
        cmdline += (
            f" -m glances -B 127.0.0.1 -s -p {CORS_PORT}"
            " --disable-autodiscover"
            " -C ./tests/conf/glances_xmlrpc_cors.conf"
        )
        print(f"Run: {cmdline}")
        pid_cors = subprocess.Popen(shlex.split(cmdline))
        print("Wait 5 seconds for server start...")
        time.sleep(5)
        self.assertIsNotNone(pid_cors)

    def test_031_cors_reflects_first_allowed_origin(self):
        """Multi-origin allowlist reflects a matching Origin, with Vary: Origin."""
        print('INFO: [TEST_031] First allowlisted Origin reflected')
        r = self.post_with_origin(CORS_URL, 'https://dashboard.glances.test')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            r.headers.get('Access-Control-Allow-Origin'),
            'https://dashboard.glances.test',
        )
        self.assertEqual(r.headers.get('Vary'), 'Origin')

    def test_032_cors_reflects_second_allowed_origin(self):
        """All entries in the allowlist are honoured, not just the first one."""
        print('INFO: [TEST_032] Second allowlisted Origin reflected')
        r = self.post_with_origin(CORS_URL, 'https://grafana.glances.test')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            r.headers.get('Access-Control-Allow-Origin'),
            'https://grafana.glances.test',
        )

    def test_033_cors_foreign_origin_no_header(self):
        """Foreign Origin: no ACAO header is emitted (request still succeeds)."""
        print('INFO: [TEST_033] Foreign Origin gets no ACAO header')
        r = self.post_with_origin(CORS_URL, 'http://evil.example.com')
        self.assertEqual(r.status_code, 200)
        self.assertNotIn('Access-Control-Allow-Origin', r.headers)

    def test_034_cors_no_origin_no_header(self):
        """Non-browser client (no Origin header): no ACAO emitted either."""
        print('INFO: [TEST_034] Missing Origin header -> no ACAO')
        r = requests.post(
            CORS_URL,
            data=XMLRPC_BODY,
            headers={'Content-Type': 'text/plain'},
            timeout=5,
        )
        self.assertEqual(r.status_code, 200)
        self.assertNotIn('Access-Control-Allow-Origin', r.headers)

    def test_016_secure_missing_host_rejected(self):
        """HTTP/1.0 request with no Host header -> 400."""
        print('INFO: [TEST_016] Missing Host header rejected')
        s = socket.create_connection(('127.0.0.1', SECURE_PORT), timeout=5)
        body = XMLRPC_BODY.encode()
        req = (
            b'POST /RPC2 HTTP/1.0\r\n'
            b'Content-Type: text/plain\r\n'
            b'Content-Length: ' + str(len(body)).encode() + b'\r\n\r\n' + body
        )
        s.sendall(req)
        resp = b''
        while True:
            chunk = s.recv(4096)
            if not chunk:
                break
            resp += chunk
        s.close()
        status_line = resp.split(b'\r\n', 1)[0]
        self.assertIn(b'400', status_line)

    def test_999_stop_server(self):
        """Stop all Glances XML-RPC servers."""
        print('INFO: [TEST_999] Stop all servers')
        pid.terminate()
        if pid_secure is not None:
            pid_secure.terminate()
        if pid_cors is not None:
            pid_cors.terminate()
        time.sleep(1)
        self.assertTrue(True)


if __name__ == '__main__':
    unittest.main()

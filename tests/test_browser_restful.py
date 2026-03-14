#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances unit tests for the WebUI/RESTful API Central Browser mode.

Tests cover:
- /api/<version>/serverslist endpoint returns a valid servers list
- Credential fields (password, uri) are stripped from API responses
- Dynamic (Zeroconf) server entries do not leak saved credentials via the API
- Server list structure validation
"""

import os
import re
import shlex
import subprocess
import time
from pathlib import Path

import pytest
import requests

from glances.outputs.glances_restful_api import GlancesRestfulApi

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SERVER_PORT = 61237  # Distinct port to avoid conflicts with other tests
API_VERSION = GlancesRestfulApi.API_VERSION
URL = f"http://localhost:{SERVER_PORT}/api/{API_VERSION}"

# Servers injected into the generated config
STATIC_SERVERS = [
    {'name': 'localhost', 'alias': 'Local Test Server', 'port': '61209', 'protocol': 'rpc'},
    {'name': 'localhost', 'alias': 'Local REST Server', 'port': '61208', 'protocol': 'rest'},
]

PASSWORDS = {
    'localhost': 'testpassword',
    'default': 'defaultpassword',
}

DEFAULT_CONF = Path(__file__).resolve().parent.parent / 'conf' / 'glances.conf'


# ---------------------------------------------------------------------------
# Helpers – generate a browser-enabled config
# ---------------------------------------------------------------------------


def _generate_browser_conf(tmp_path):
    """Read the default glances.conf, activate [serverlist] and [passwords],
    write to tmp_path and return the file path."""
    source = DEFAULT_CONF.read_text(encoding='utf-8')

    # --- Build [serverlist] replacement ---
    serverlist_lines = [
        '[serverlist]',
        'columns=system:hr_name,load:min5,cpu:total,mem:percent',
    ]
    for idx, srv in enumerate(STATIC_SERVERS, start=1):
        serverlist_lines.append(f'server_{idx}_name={srv["name"]}')
        serverlist_lines.append(f'server_{idx}_alias={srv["alias"]}')
        serverlist_lines.append(f'server_{idx}_port={srv["port"]}')
        serverlist_lines.append(f'server_{idx}_protocol={srv["protocol"]}')
    serverlist_block = '\n'.join(serverlist_lines) + '\n'

    # --- Build [passwords] replacement ---
    password_lines = ['[passwords]']
    for host, pwd in PASSWORDS.items():
        password_lines.append(f'{host}={pwd}')
    password_block = '\n'.join(password_lines) + '\n'

    # Replace existing sections in-place
    source = re.sub(
        r'\[serverlist\].*?(?=\n\[|\Z)',
        serverlist_block,
        source,
        count=1,
        flags=re.DOTALL,
    )
    source = re.sub(
        r'\[passwords\].*?(?=\n\[|\Z)',
        password_block,
        source,
        count=1,
        flags=re.DOTALL,
    )

    conf_file = tmp_path / 'glances.conf'
    conf_file.write_text(source, encoding='utf-8')
    return str(conf_file)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope='module')
def browser_conf_path(tmp_path_factory):
    return _generate_browser_conf(tmp_path_factory.mktemp('browser_api_conf'))


@pytest.fixture(scope='module')
def glances_browser_server(browser_conf_path):
    """Start a Glances web server in browser mode with the generated config."""
    if os.path.isfile('.venv/bin/python'):
        cmdline = '.venv/bin/python'
    else:
        cmdline = 'python'
    cmdline += (
        f' -m glances -B 0.0.0.0 -w --browser'
        f' -p {SERVER_PORT} --disable-webui --disable-autodiscover'
        f' -C {browser_conf_path}'
    )
    args = shlex.split(cmdline)
    pid = subprocess.Popen(args)
    # Wait for the server to start
    time.sleep(5)
    yield pid
    pid.terminate()
    pid.wait(timeout=5)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def http_get(url):
    return requests.get(url, headers={'Accept-encoding': 'identity'}, timeout=10)


# ---------------------------------------------------------------------------
# Tests – /api/<version>/serverslist endpoint
# ---------------------------------------------------------------------------


class TestServersListEndpoint:
    """Validate the /serverslist API endpoint."""

    def test_serverslist_returns_200(self, glances_browser_server):
        req = http_get(f'{URL}/serverslist')
        assert req.ok, f'Expected 200, got {req.status_code}'

    def test_serverslist_returns_list(self, glances_browser_server):
        req = http_get(f'{URL}/serverslist')
        data = req.json()
        assert isinstance(data, list)

    def test_serverslist_has_servers(self, glances_browser_server):
        """At least the configured static servers should be returned."""
        req = http_get(f'{URL}/serverslist')
        data = req.json()
        assert len(data) >= len(STATIC_SERVERS), f'Expected at least {len(STATIC_SERVERS)} servers, got {len(data)}'

    def test_serverslist_server_has_required_fields(self, glances_browser_server):
        """Each server entry should have essential fields."""
        req = http_get(f'{URL}/serverslist')
        required_keys = {'key', 'name', 'ip', 'port', 'protocol', 'status', 'type'}
        for server in req.json():
            missing = required_keys - set(server.keys())
            assert not missing, f'Server {server.get("name")} missing keys: {missing}'

    def test_serverslist_server_types(self, glances_browser_server):
        req = http_get(f'{URL}/serverslist')
        for server in req.json():
            assert server['type'] in ('STATIC', 'DYNAMIC')

    def test_serverslist_server_protocols(self, glances_browser_server):
        req = http_get(f'{URL}/serverslist')
        for server in req.json():
            assert server['protocol'] in ('rpc', 'rest')


# ---------------------------------------------------------------------------
# Tests – Credential sanitization in API responses (CVE fix validation)
# ---------------------------------------------------------------------------


class TestServersListCredentialSanitization:
    """Verify that password and uri fields are stripped from API responses.

    This validates the fix for CVE-2026-32633.
    """

    def test_no_password_field_in_response(self, glances_browser_server):
        """The 'password' field must be stripped from all server entries."""
        req = http_get(f'{URL}/serverslist')
        for server in req.json():
            assert 'password' not in server, f'Server {server.get("name")} still exposes "password" field'

    def test_no_uri_field_in_response(self, glances_browser_server):
        """The 'uri' field must be stripped from all server entries."""
        req = http_get(f'{URL}/serverslist')
        for server in req.json():
            assert 'uri' not in server, f'Server {server.get("name")} still exposes "uri" field'

    def test_no_credential_in_any_field(self, glances_browser_server):
        """No field value should contain embedded credentials (user:pass@ pattern)."""
        req = http_get(f'{URL}/serverslist')
        cred_pattern = re.compile(r'://[^/]*:[^/]*@')
        for server in req.json():
            for key, value in server.items():
                if isinstance(value, str):
                    assert not cred_pattern.search(value), (
                        f'Server {server.get("name")}, field "{key}" contains embedded credentials: {value}'
                    )


# ---------------------------------------------------------------------------
# Tests – _sanitize_server static method
# ---------------------------------------------------------------------------


class TestSanitizeServer:
    """Unit tests for GlancesRestfulApi._sanitize_server (no server needed)."""

    def test_strips_password(self):
        server = {'name': 'host', 'password': 'secret', 'status': 'ONLINE'}
        safe = GlancesRestfulApi._sanitize_server(server)
        assert 'password' not in safe

    def test_strips_uri(self):
        server = {'name': 'host', 'uri': 'http://u:p@host:61209', 'status': 'ONLINE'}
        safe = GlancesRestfulApi._sanitize_server(server)
        assert 'uri' not in safe

    def test_preserves_other_fields(self):
        server = {
            'name': 'host',
            'ip': '10.0.0.1',
            'port': 61209,
            'protocol': 'rpc',
            'status': 'ONLINE',
            'type': 'STATIC',
            'password': 'secret',
            'uri': 'http://u:p@host:61209',
        }
        safe = GlancesRestfulApi._sanitize_server(server)
        assert safe['name'] == 'host'
        assert safe['ip'] == '10.0.0.1'
        assert safe['port'] == 61209
        assert safe['protocol'] == 'rpc'
        assert safe['status'] == 'ONLINE'
        assert safe['type'] == 'STATIC'

    def test_does_not_mutate_original(self):
        server = {'name': 'host', 'password': 'secret', 'uri': 'http://x'}
        GlancesRestfulApi._sanitize_server(server)
        assert 'password' in server
        assert 'uri' in server

    def test_handles_missing_fields(self):
        """Server dict without password/uri should not raise."""
        server = {'name': 'host', 'status': 'ONLINE'}
        safe = GlancesRestfulApi._sanitize_server(server)
        assert safe == server


# ---------------------------------------------------------------------------
# Tests – Multiple sequential requests (stability)
# ---------------------------------------------------------------------------


class TestServersListStability:
    """Ensure repeated calls return consistent, sanitized results."""

    def test_repeated_calls_consistent(self, glances_browser_server):
        """Multiple sequential requests should return the same server count."""
        counts = []
        for _ in range(3):
            req = http_get(f'{URL}/serverslist')
            assert req.ok
            counts.append(len(req.json()))
        assert len(set(counts)) == 1, f'Inconsistent server counts across calls: {counts}'

    def test_repeated_calls_never_leak_credentials(self, glances_browser_server):
        """Credentials must remain stripped across multiple polling cycles."""
        for _ in range(3):
            req = http_get(f'{URL}/serverslist')
            for server in req.json():
                assert 'password' not in server
                assert 'uri' not in server

#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances unit tests for the TUI Central Browser mode.

Tests cover:
- Config generation from the default glances.conf with browser options enabled
- Static server list loading from config
- Password list loading and lookup (host-specific, default, missing)
- URI generation (with/without credentials, static vs dynamic servers)
- Credential sanitization: dynamic (Zeroconf) servers must not inherit saved passwords
- Credential sanitization: URIs for dynamic servers use IP, not advertised name
"""

import re
from pathlib import Path
from unittest.mock import patch

import pytest

from glances.config import Config
from glances.password_list import GlancesPasswordList
from glances.servers_list import GlancesServersList

# ---------------------------------------------------------------------------
# Helpers – generate a browser-enabled config from the default glances.conf
# ---------------------------------------------------------------------------

DEFAULT_CONF = Path(__file__).resolve().parent.parent / 'conf' / 'glances.conf'

# Servers injected into the generated config
# All names must be DNS-resolvable (localhost, 127.0.0.1) to avoid gethostbyname errors
STATIC_SERVERS = [
    {'name': 'localhost', 'alias': 'Local RPC Server', 'port': '61209', 'protocol': 'rpc'},
    {'name': 'localhost', 'alias': 'Local REST Server', 'port': '61208', 'protocol': 'rest'},
    {'name': '127.0.0.1', 'alias': 'Loopback Server', 'port': '61210', 'protocol': 'rpc'},
]

PASSWORDS = {
    'localhost': 'localpwd',
    '127.0.0.1': 'loopbackpwd',
    'default': 'defaultpassword',
}


def _generate_browser_conf(tmp_path):
    """Read the default glances.conf, uncomment and populate [serverlist] and
    [passwords] sections, write the result to *tmp_path* and return its path.

    This is regenerated at every test run so the test stays in sync with the
    upstream default config without manual maintenance.
    """
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
    # Match from section header to right before the next section header (or EOF)
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
    """Generate a browser-enabled config file once per module."""
    return _generate_browser_conf(tmp_path_factory.mktemp('browser_conf'))


@pytest.fixture(scope='module')
def browser_config(browser_conf_path):
    """Return a Config object loaded from the generated browser config."""
    return Config(browser_conf_path)


@pytest.fixture(scope='module')
def browser_args(browser_conf_path):
    """Return a minimal args namespace suitable for GlancesServersList."""
    from glances.main import GlancesMain

    testargs = ['glances', '--browser', '--disable-autodiscover', '-C', browser_conf_path]
    with patch('sys.argv', testargs):
        core = GlancesMain()
    return core.get_args()


@pytest.fixture(scope='module')
def servers_list(browser_config, browser_args):
    """Return a fully initialised GlancesServersList (autodiscovery disabled)."""
    return GlancesServersList(config=browser_config, args=browser_args)


# ---------------------------------------------------------------------------
# Tests – Config generation
# ---------------------------------------------------------------------------


class TestBrowserConfigGeneration:
    """Verify the generated config has the expected sections and values."""

    def test_serverlist_section_exists(self, browser_config):
        assert browser_config.has_section('serverlist')

    def test_passwords_section_exists(self, browser_config):
        assert browser_config.has_section('passwords')

    def test_server_count(self, browser_config):
        """All defined servers should be loadable."""
        count = 0
        for i in range(1, 256):
            if browser_config.get_value('serverlist', f'server_{i}_name') is not None:
                count += 1
        assert count == len(STATIC_SERVERS)

    def test_password_values(self, browser_config):
        items = dict(browser_config.items('passwords'))
        for host, pwd in PASSWORDS.items():
            assert items[host] == pwd


# ---------------------------------------------------------------------------
# Tests – Static server list loading
# ---------------------------------------------------------------------------


class TestStaticServerList:
    """Verify GlancesStaticServer correctly loads servers from config."""

    def test_server_list_length(self, servers_list):
        servers = servers_list.get_servers_list()
        assert len(servers) == len(STATIC_SERVERS)

    def test_server_fields(self, servers_list):
        """Each server dict must have the expected keys."""
        required_keys = {'key', 'name', 'ip', 'port', 'protocol', 'username', 'password', 'status', 'type'}
        for server in servers_list.get_servers_list():
            assert required_keys.issubset(server.keys()), f"Missing keys in {server}"

    def test_server_names(self, servers_list):
        names = [s['name'] for s in servers_list.get_servers_list()]
        for srv in STATIC_SERVERS:
            assert srv['name'] in names

    def test_server_protocols(self, servers_list):
        for server in servers_list.get_servers_list():
            assert server['protocol'] in ('rpc', 'rest')

    def test_server_type_is_static(self, servers_list):
        for server in servers_list.get_servers_list():
            assert server['type'] == 'STATIC'

    def test_server_initial_status(self, servers_list):
        for server in servers_list.get_servers_list():
            assert server['status'] == 'UNKNOWN'

    def test_server_default_username(self, servers_list):
        for server in servers_list.get_servers_list():
            assert server['username'] == 'glances'

    def test_server_default_empty_password(self, servers_list):
        for server in servers_list.get_servers_list():
            assert server['password'] == ''


# ---------------------------------------------------------------------------
# Tests – Password list
# ---------------------------------------------------------------------------


class TestPasswordList:
    """Verify GlancesPasswordList loading and lookup."""

    def test_host_specific_password(self, servers_list):
        assert servers_list.password.get_password('localhost') == 'localpwd'

    def test_loopback_password(self, servers_list):
        assert servers_list.password.get_password('127.0.0.1') == 'loopbackpwd'

    def test_default_fallback(self, servers_list):
        """Unknown host should fall back to 'default' password."""
        assert servers_list.password.get_password('unknown-host') == 'defaultpassword'

    def test_no_password_without_default(self):
        """Without a default entry, unknown host should return None."""
        pwd = GlancesPasswordList()
        pwd._password_dict = {'localhost': 'localpwd'}
        assert pwd.get_password('unknown-host') is None


# ---------------------------------------------------------------------------
# Tests – Columns
# ---------------------------------------------------------------------------


class TestColumnsDefinition:
    """Verify columns parsing from config."""

    def test_columns_loaded(self, servers_list):
        columns = servers_list.get_columns()
        assert len(columns) > 0

    def test_columns_structure(self, servers_list):
        for col in servers_list.get_columns():
            assert 'plugin' in col
            assert 'field' in col

    def test_columns_values(self, servers_list):
        plugins = [c['plugin'] for c in servers_list.get_columns()]
        assert 'system' in plugins
        assert 'cpu' in plugins
        assert 'mem' in plugins


# ---------------------------------------------------------------------------
# Tests – URI generation for STATIC servers
# ---------------------------------------------------------------------------


class TestGetUriStatic:
    """Verify URI generation for static servers."""

    def test_uri_without_password(self, servers_list):
        """Static server with empty password → URI without credentials."""
        server = {
            'name': 'myhost',
            'ip': '10.0.0.1',
            'port': 61209,
            'username': 'glances',
            'password': '',
            'status': 'ONLINE',
            'type': 'STATIC',
        }
        uri = servers_list.get_uri(server)
        assert uri == 'http://myhost:61209'
        assert '@' not in uri

    def test_uri_with_password(self, servers_list):
        """Static server with a non-empty password → URI with credentials."""
        server = {
            'name': 'myhost',
            'ip': '10.0.0.1',
            'port': 61209,
            'username': 'glances',
            'password': 'somehash',
            'status': 'ONLINE',
            'type': 'STATIC',
        }
        uri = servers_list.get_uri(server)
        assert 'glances:somehash@myhost:61209' in uri

    def test_uri_protected_uses_saved_password(self, servers_list):
        """PROTECTED static server with a saved password should get the hash injected."""
        server = {
            'name': 'localhost',
            'ip': '127.0.0.1',
            'port': 61209,
            'username': 'glances',
            'password': 'placeholder',
            'status': 'PROTECTED',
            'type': 'STATIC',
        }
        uri = servers_list.get_uri(server)
        # Password should have been replaced by the hash of 'localpwd'
        expected_hash = servers_list.password.get_hash('localpwd')
        assert expected_hash in uri
        assert server['password'] == expected_hash

    def test_uri_protected_default_fallback(self, servers_list):
        """PROTECTED static server with unknown name falls back to 'default' password."""
        server = {
            'name': 'unknown-static-host',
            'ip': '10.0.0.2',
            'port': 61209,
            'username': 'glances',
            'password': 'placeholder',
            'status': 'PROTECTED',
            'type': 'STATIC',
        }
        uri = servers_list.get_uri(server)
        expected_hash = servers_list.password.get_hash('defaultpassword')
        assert expected_hash in uri

    def test_uri_static_uses_name_not_ip(self, servers_list):
        """Static server URI should use server['name'] as the host."""
        server = {
            'name': 'myhost.local',
            'ip': '192.168.1.100',
            'port': 61209,
            'username': 'glances',
            'password': '',
            'status': 'ONLINE',
            'type': 'STATIC',
        }
        uri = servers_list.get_uri(server)
        assert 'myhost.local' in uri
        assert '192.168.1.100' not in uri


# ---------------------------------------------------------------------------
# Tests – URI generation for DYNAMIC servers (CVE fix validation)
# ---------------------------------------------------------------------------


class TestGetUriDynamic:
    """Verify that dynamic (Zeroconf) servers use IP and never inherit saved passwords.

    These tests validate the fix for the Zeroconf credential exfiltration CVE.
    """

    def test_uri_dynamic_uses_ip_not_name(self, servers_list):
        """DYNAMIC server URI must use the discovered IP, not the advertised name."""
        server = {
            'name': 'attacker-controlled-name',
            'ip': '192.168.1.50',
            'port': 61209,
            'username': 'glances',
            'password': '',
            'status': 'ONLINE',
            'type': 'DYNAMIC',
        }
        uri = servers_list.get_uri(server)
        assert '192.168.1.50' in uri
        assert 'attacker-controlled-name' not in uri

    def test_uri_dynamic_protected_no_saved_password(self, servers_list):
        """DYNAMIC PROTECTED server must NOT inherit saved or default passwords."""
        server = {
            'name': 'localhost',  # name matches a saved password
            'ip': '198.51.100.50',
            'port': 61209,
            'username': 'glances',
            'password': 'placeholder',
            'status': 'PROTECTED',
            'type': 'DYNAMIC',
        }
        uri = servers_list.get_uri(server)
        # The password should remain as 'placeholder' (not replaced by saved hash)
        assert server['password'] == 'placeholder'
        # URI should use IP
        assert '198.51.100.50' in uri
        assert 'localhost' not in uri

    def test_uri_dynamic_no_default_password_fallback(self, servers_list):
        """DYNAMIC server with unknown name must NOT fall back to default password."""
        server = {
            'name': 'fake-zeroconf-service',
            'ip': '198.51.100.99',
            'port': 61209,
            'username': 'glances',
            'password': 'placeholder',
            'status': 'PROTECTED',
            'type': 'DYNAMIC',
        }
        uri = servers_list.get_uri(server)
        # password unchanged
        assert server['password'] == 'placeholder'
        # No hash of 'defaultpassword' should appear
        default_hash = servers_list.password.get_hash('defaultpassword')
        assert default_hash not in uri

    def test_get_connect_host_static(self, servers_list):
        server = {'name': 'myhost', 'ip': '10.0.0.1', 'type': 'STATIC'}
        assert servers_list._get_connect_host(server) == 'myhost'

    def test_get_connect_host_dynamic(self, servers_list):
        server = {'name': 'advertised-name', 'ip': '10.0.0.2', 'type': 'DYNAMIC'}
        assert servers_list._get_connect_host(server) == '10.0.0.2'

    def test_get_preconfigured_password_static(self, servers_list):
        server = {'name': 'localhost', 'type': 'STATIC'}
        assert servers_list._get_preconfigured_password(server) == 'localpwd'

    def test_get_preconfigured_password_dynamic_returns_none(self, servers_list):
        server = {'name': 'localhost', 'type': 'DYNAMIC'}
        assert servers_list._get_preconfigured_password(server) is None

    def test_get_preconfigured_password_dynamic_no_default(self, servers_list):
        """Even with a 'default' password configured, dynamic servers get None."""
        server = {'name': 'unknown', 'type': 'DYNAMIC'}
        assert servers_list._get_preconfigured_password(server) is None


# ---------------------------------------------------------------------------
# Tests – Simulated Zeroconf attack scenario
# ---------------------------------------------------------------------------


class TestZeroconfAttackScenario:
    """End-to-end simulation of the Zeroconf credential exfiltration attack."""

    def test_attacker_advertised_server_no_credential_leak(self, servers_list):
        """Simulate: attacker advertises a fake Zeroconf service with a name matching
        a real server. The browser marks it PROTECTED. Verify no credential is sent."""
        # Simulate a dynamic server entry as Zeroconf would create it
        attacker_server = {
            'key': 'evil-service:61209._glances._tcp.local.',
            'name': 'localhost',  # attacker uses name of a real server
            'ip': '198.51.100.66',  # attacker's IP
            'port': 61209,
            'protocol': 'rpc',
            'username': 'glances',
            'password': '',
            'status': 'UNKNOWN',
            'type': 'DYNAMIC',
        }

        # First probe: no password → URI without credentials
        uri1 = servers_list.get_uri(attacker_server)
        assert '@' not in uri1
        assert '198.51.100.66' in uri1

        # Simulate server responding 401 → status becomes PROTECTED
        attacker_server['password'] = None
        attacker_server['status'] = 'PROTECTED'

        # Second probe: PROTECTED + DYNAMIC → must NOT inject saved password
        uri2 = servers_list.get_uri(attacker_server)
        # password stays None (converted to string in format)
        assert attacker_server['password'] is None
        # No credential hash in URI
        localpwd_hash = servers_list.password.get_hash('localpwd')
        default_hash = servers_list.password.get_hash('defaultpassword')
        assert localpwd_hash not in uri2
        assert default_hash not in uri2

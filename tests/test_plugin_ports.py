#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the Ports plugin."""

import socket

import pytest

import glances.plugins.ports as ports_mod
from glances.plugins.ports import PortsPlugin, ThreadScanner


@pytest.fixture
def ports_plugin():
    """Return a Ports plugin instance without running its full init."""
    return PortsPlugin.__new__(PortsPlugin)


def web_scan(status, elapsed=0, rtt_warning=1):
    """Return a web scan result as stored by the ports plugin."""
    return {'status': status, 'elapsed': elapsed, 'rtt_warning': rtt_warning}


class TestPortsPluginAlertLevel:
    """Test that the alert level is resolved by severity, not by dict ordering."""

    @pytest.mark.parametrize(
        ('conds', 'expected'),
        [
            ({'CAREFUL': True, 'CRITICAL': True, 'WARNING': True}, 'CRITICAL'),
            ({'CAREFUL': True, 'CRITICAL': False, 'WARNING': True}, 'WARNING'),
            ({'CAREFUL': True, 'CRITICAL': False, 'WARNING': False}, 'CAREFUL'),
            ({'CAREFUL': False, 'CRITICAL': False, 'WARNING': False}, 'OK'),
        ],
    )
    def test_most_severe_condition_wins(self, ports_plugin, conds, expected):
        """Test that the most severe matching condition is returned."""
        assert ports_plugin.get_default_ret_value(conds) == expected

    def test_web_not_scanned_yet_is_careful(self, ports_plugin):
        """Test that a URL whose first scan did not complete is not CRITICAL."""
        conds = ports_plugin.get_conds_if_url(web_scan(None))
        assert ports_plugin.get_default_ret_value(conds) == 'CAREFUL'

    def test_web_failing_and_slow_is_critical(self, ports_plugin):
        """Test that a failing URL stays CRITICAL even when it is also slow."""
        conds = ports_plugin.get_conds_if_url(web_scan(404, elapsed=5))
        assert ports_plugin.get_default_ret_value(conds) == 'CRITICAL'

    def test_web_failing_and_fast_is_critical(self, ports_plugin):
        """Test that a failing URL is CRITICAL."""
        conds = ports_plugin.get_conds_if_url(web_scan(404))
        assert ports_plugin.get_default_ret_value(conds) == 'CRITICAL'

    def test_web_ok_but_slow_is_warning(self, ports_plugin):
        """Test that a reachable but slow URL is WARNING."""
        conds = ports_plugin.get_conds_if_url(web_scan(200, elapsed=5))
        assert ports_plugin.get_default_ret_value(conds) == 'WARNING'

    def test_web_ok_and_fast_is_ok(self, ports_plugin):
        """Test that a reachable and fast URL is OK."""
        conds = ports_plugin.get_conds_if_url(web_scan(200))
        assert ports_plugin.get_default_ret_value(conds) == 'OK'


@pytest.fixture
def scanner():
    """Return a ThreadScanner instance without running its full init."""
    return ThreadScanner.__new__(ThreadScanner)


class TestIcmpPingCommand:
    """Test the ping command line built for an ICMP (port 0) check."""

    @pytest.fixture
    def ping_cmd(self, scanner, monkeypatch):
        """Return the ping command line built on the given platform."""

        def build(platform, timeout=3):
            recorded = {}

            def fake_check_call(cmd, **kwargs):
                recorded['cmd'] = cmd
                return 0

            for name in ('WINDOWS', 'MACOS', 'BSD'):
                monkeypatch.setattr(ports_mod, name, name == platform)
            monkeypatch.setattr(ports_mod.subprocess, 'check_call', fake_check_call)
            monkeypatch.setattr(ThreadScanner, '_resolv_name', lambda self, host: host)
            scanner._port_scan_icmp({'host': 'example.net', 'port': 0, 'timeout': timeout})
            return recorded['cmd']

        return build

    def test_windows_timeout_is_expressed_in_milliseconds(self, ping_cmd):
        """Windows ping -w is a per-reply timeout in ms, so 3s must be sent as 3000."""
        assert ping_cmd('WINDOWS') == ['ping', '-n', '1', '-w', '3000', 'example.net']

    def test_linux_timeout_stays_in_seconds(self, ping_cmd):
        """Linux ping -W is in seconds, so the value is passed through."""
        assert ping_cmd('LINUX') == ['ping', '-c', '1', '-W', '3', 'example.net']

    def test_macos_timeout_stays_in_seconds(self, ping_cmd):
        """macOS and BSD ping -t is in seconds, so the value is passed through."""
        assert ping_cmd('MACOS') == ['ping', '-c', '1', '-t', '3', 'example.net']

    def test_timeout_is_not_sent_through_the_name_resolver(self, scanner, monkeypatch):
        """The timeout is a number of seconds, not a hostname to look up."""
        resolved = []

        for name in ('WINDOWS', 'MACOS', 'BSD'):
            monkeypatch.setattr(ports_mod, name, False)
        monkeypatch.setattr(ports_mod.subprocess, 'check_call', lambda cmd, **kwargs: 0)
        monkeypatch.setattr(ThreadScanner, '_resolv_name', lambda self, host: resolved.append(host) or host)
        scanner._port_scan_icmp({'host': 'example.net', 'port': 0, 'timeout': 3})
        assert resolved == ['example.net']


class TestTcpScanSocket:
    """Test that a TCP scan configures its own socket and cleans up after itself."""

    @pytest.fixture
    def tcp_port(self):
        """Return a port entry pointing at the discard port, which nothing listens on."""
        return {'host': '127.0.0.1', 'port': 9, 'timeout': 3, 'status': None, 'indice': 'port_0'}

    def test_the_timeout_is_set_on_the_scanning_socket(self, scanner, tcp_port, monkeypatch):
        """The scan must configure the socket it actually uses."""
        seen = {}
        real_socket = socket.socket

        def spy(*args, **kwargs):
            sock = real_socket(*args, **kwargs)
            seen['sock'] = sock
            return sock

        monkeypatch.setattr(ports_mod.socket, 'socket', spy)
        monkeypatch.setattr(ThreadScanner, '_resolv_name', lambda self, host: host)
        scanner._port_scan_tcp(tcp_port)

        assert seen['sock'].gettimeout() == 3

    def test_scanning_does_not_change_the_process_wide_default_timeout(self, scanner, tcp_port, monkeypatch):
        """A port scan must not reconfigure sockets it does not own.

        socket.setdefaulttimeout() applies to every socket created afterwards
        in the process -- exporters, the hddtemp grabber, anything that does
        not set a timeout of its own -- and nothing here ever restored it.
        """
        monkeypatch.setattr(ThreadScanner, '_resolv_name', lambda self, host: host)
        # Pin the starting point. The default is process-wide, so an earlier
        # scan in the same session would otherwise have already set it and this
        # test would pass against the very state it exists to forbid.
        previous = socket.getdefaulttimeout()
        socket.setdefaulttimeout(None)
        try:
            scanner._port_scan_tcp(tcp_port)

            assert socket.getdefaulttimeout() is None
            unrelated = socket.socket()
            try:
                assert unrelated.gettimeout() is None
            finally:
                unrelated.close()
        finally:
            socket.setdefaulttimeout(previous)

    def test_a_socket_that_cannot_be_created_is_reported_not_raised(self, scanner, tcp_port, monkeypatch):
        """A failed socket creation must not escape as an UnboundLocalError."""

        def refuse(*args, **kwargs):
            raise OSError("no file descriptors available")

        monkeypatch.setattr(ports_mod.socket, 'socket', refuse)
        monkeypatch.setattr(ThreadScanner, '_resolv_name', lambda self, host: host)
        # Set by ThreadScanner.__init__; the fixture skips it, and the failure
        # path logs with it.
        scanner.plugin_name = 'ports'

        assert scanner._port_scan_tcp(tcp_port) is None

    def test_a_closed_port_is_still_reported_offline(self, scanner, tcp_port, monkeypatch):
        """The scan result itself must be unchanged by how the timeout is set."""
        monkeypatch.setattr(ThreadScanner, '_resolv_name', lambda self, host: host)
        scanner._port_scan_tcp(tcp_port)

        assert tcp_port['status'] is False

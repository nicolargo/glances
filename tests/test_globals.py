#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for glances.globals helper functions."""

import socket
from collections import OrderedDict
from types import SimpleNamespace
from unittest.mock import patch

from glances.globals import get_ip_address


def _stat(isup=True):
    return SimpleNamespace(isup=isup, duplex=0, speed=0, mtu=1500, flags='')


def _addr(family, address, netmask='255.255.255.0'):
    return SimpleNamespace(family=family, address=address, netmask=netmask, broadcast=None, ptp=None)


def _no_route(*args, **kwargs):
    """Simulate a host without a default route (socket probe fails)."""
    raise OSError("Network is unreachable")


class _FakeSocket:
    """A connected UDP socket whose kernel-chosen source address we control."""

    def __init__(self, address):
        self._address = address

    def __call__(self, *args, **kwargs):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def connect(self, target):
        pass

    def getsockname(self):
        return (self._address, 0)


class TestGetIpAddress:
    """get_ip_address() should return the default-route interface's address,
    falling back to the first up, non-loopback interface."""

    def test_default_route_address_wins_over_interface_order(self):
        # Regression test for #3465: the interface order must not matter.
        # docker0 comes FIRST here; the kernel routes default traffic from
        # eth0's address, so eth0's address must be returned.
        addrs = {
            'docker0': [_addr(socket.AF_INET, '172.18.0.1')],
            'eth0': [_addr(socket.AF_INET, '192.168.0.150')],
        }

        with (
            patch('glances.globals.socket.socket', _FakeSocket('192.168.0.150')),
            patch('glances.globals.psutil.net_if_addrs', return_value=addrs),
        ):
            ip_address, ip_netmask = get_ip_address()

        assert ip_address == '192.168.0.150'
        assert ip_netmask == '255.255.255.0'

    def test_routed_address_without_psutil_entry_returns_none_netmask(self):
        # ip_to_cidr() handles a None netmask (#1528), so the correct address
        # must not be discarded just because its netmask cannot be found.
        with (
            patch('glances.globals.socket.socket', _FakeSocket('10.9.8.7')),
            patch('glances.globals.psutil.net_if_addrs', return_value={}),
        ):
            ip_address, ip_netmask = get_ip_address()

        assert ip_address == '10.9.8.7'
        assert ip_netmask is None

    def test_returns_first_matching_interface_not_last(self):
        # Regression test for #3617: on hosts with Docker, a virtual bridge
        # interface (docker0) sorted after the real LAN interface used to
        # silently win because the outer loop never stopped scanning.
        stats = OrderedDict(
            [
                ('eth0', _stat()),
                ('docker0', _stat()),
            ]
        )
        addrs = {
            'eth0': [_addr(socket.AF_INET, '192.168.0.150')],
            'docker0': [_addr(socket.AF_INET, '172.18.0.1')],
        }

        with (
            patch('glances.globals.socket.socket', _no_route),
            patch('glances.globals.psutil.net_if_stats', return_value=stats),
            patch('glances.globals.psutil.net_if_addrs', return_value=addrs),
        ):
            ip_address, ip_netmask = get_ip_address()

        assert ip_address == '192.168.0.150'
        assert ip_netmask == '255.255.255.0'

    def test_loopback_probe_result_falls_back_to_interface_scan(self):
        # Hosts that locally blackhole documentation/bogon ranges can resolve
        # the probe to a loopback source; that must never be reported as the
        # primary address (nor used as the zeroconf bind address).
        stats = OrderedDict([('eth0', _stat())])
        addrs = {'eth0': [_addr(socket.AF_INET, '192.168.0.150')]}

        with (
            patch('glances.globals.socket.socket', _FakeSocket('127.0.0.1')),
            patch('glances.globals.psutil.net_if_stats', return_value=stats),
            patch('glances.globals.psutil.net_if_addrs', return_value=addrs),
        ):
            ip_address, ip_netmask = get_ip_address()

        assert ip_address == '192.168.0.150'
        assert ip_netmask == '255.255.255.0'

    def test_skips_loopback_and_down_interfaces(self):
        stats = OrderedDict(
            [
                ('lo', _stat()),
                ('eth1', _stat(isup=False)),
                ('eth0', _stat()),
            ]
        )
        addrs = {
            'lo': [_addr(socket.AF_INET, '127.0.0.1')],
            'eth1': [_addr(socket.AF_INET, '10.0.0.5')],
            'eth0': [_addr(socket.AF_INET, '192.168.0.150')],
        }

        with (
            patch('glances.globals.socket.socket', _no_route),
            patch('glances.globals.psutil.net_if_stats', return_value=stats),
            patch('glances.globals.psutil.net_if_addrs', return_value=addrs),
        ):
            ip_address, ip_netmask = get_ip_address()

        assert ip_address == '192.168.0.150'

    def test_returns_none_when_no_interface_matches(self):
        stats = OrderedDict([('lo', _stat())])
        addrs = {'lo': [_addr(socket.AF_INET, '127.0.0.1')]}

        with (
            patch('glances.globals.socket.socket', _no_route),
            patch('glances.globals.psutil.net_if_stats', return_value=stats),
            patch('glances.globals.psutil.net_if_addrs', return_value=addrs),
        ):
            ip_address, ip_netmask = get_ip_address()

        assert ip_address is None
        assert ip_netmask is None

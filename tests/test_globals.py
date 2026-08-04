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


class TestGetIpAddress:
    """get_ip_address() should return the FIRST up, non-loopback interface's address."""

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
            patch('glances.globals.psutil.net_if_stats', return_value=stats),
            patch('glances.globals.psutil.net_if_addrs', return_value=addrs),
        ):
            ip_address, ip_netmask = get_ip_address()

        assert ip_address == '192.168.0.150'

    def test_returns_none_when_no_interface_matches(self):
        stats = OrderedDict([('lo', _stat())])
        addrs = {'lo': [_addr(socket.AF_INET, '127.0.0.1')]}

        with (
            patch('glances.globals.psutil.net_if_stats', return_value=stats),
            patch('glances.globals.psutil.net_if_addrs', return_value=addrs),
        ):
            ip_address, ip_netmask = get_ip_address()

        assert ip_address is None
        assert ip_netmask is None

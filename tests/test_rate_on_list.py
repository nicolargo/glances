#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Rate computation for stats stored in a list.

Interfaces, disks and VMs come and go while Glances is running. A stat that is
new since the previous sample has no gauge to subtract from, and the list path
used to skip it entirely instead of initialising it.
"""

from collections import namedtuple

import psutil
import pytest

from glances.plugins.plugin.model import GlancesPluginModel

RATE_FIELDS = {
    'interface_name': {'description': 'Interface name.'},
    'bytes_recv': {'description': 'Number of bytes received.', 'rate': True, 'unit': 'byte'},
}

EXISTING = 'eth0'
NEW = 'wg0'
# Large enough that publishing it as one refresh of traffic is unmistakable.
SINCE_BOOT = 8_000_000_000


class _ListPlugin(GlancesPluginModel):
    """A minimal list plugin, so the test measures the shared rate code itself."""

    def __init__(self):
        super().__init__(fields_description=RATE_FIELDS, stats_init_value=[])
        self.feed = []

    def get_key(self):
        return 'interface_name'

    @GlancesPluginModel._manage_rate
    def sample(self):
        return [dict(stat) for stat in self.feed]


def by_name(stats):
    return {stat['interface_name']: stat for stat in stats}


@pytest.fixture
def settled():
    """A plugin past its first sample, so `eth0` already carries a gauge."""
    plugin = _ListPlugin()
    plugin.feed = [{'interface_name': EXISTING, 'bytes_recv': 1000}]
    plugin.sample()
    plugin.feed = [{'interface_name': EXISTING, 'bytes_recv': 1500}]
    plugin.sample()
    return plugin


def test_a_new_stat_does_not_publish_its_lifetime_counter_as_a_delta(settled):
    """The defect: the raw counter was left sitting in the delta field."""
    settled.feed = [
        {'interface_name': EXISTING, 'bytes_recv': 1600},
        {'interface_name': NEW, 'bytes_recv': SINCE_BOOT},
    ]
    new = by_name(settled.sample())[NEW]

    assert new['bytes_recv'] == 0
    assert new['bytes_recv_gauge'] == SINCE_BOOT


def test_a_new_stat_is_given_the_same_fields_as_every_other(settled):
    """No _gauge, no _rate_per_sec and no time_since_update were produced at all."""
    settled.feed = [
        {'interface_name': EXISTING, 'bytes_recv': 1600},
        {'interface_name': NEW, 'bytes_recv': SINCE_BOOT},
    ]
    stats = by_name(settled.sample())

    assert set(stats[NEW]) == set(stats[EXISTING])
    assert stats[NEW]['bytes_recv_rate_per_sec'] == 0


def test_a_stat_already_present_still_measures_its_own_delta(settled):
    """The neighbouring stat must not be disturbed by how a new one is handled."""
    settled.feed = [
        {'interface_name': EXISTING, 'bytes_recv': 1600},
        {'interface_name': NEW, 'bytes_recv': SINCE_BOOT},
    ]
    existing = by_name(settled.sample())[EXISTING]

    assert existing['bytes_recv'] == 100
    assert existing['bytes_recv_gauge'] == 1600


def test_a_new_stat_measures_from_its_own_gauge_on_the_next_sample(settled):
    """Recording the gauge is what makes the very next sample a real measurement."""
    settled.feed = [
        {'interface_name': EXISTING, 'bytes_recv': 1600},
        {'interface_name': NEW, 'bytes_recv': SINCE_BOOT},
    ]
    settled.sample()

    settled.feed = [
        {'interface_name': EXISTING, 'bytes_recv': 1700},
        {'interface_name': NEW, 'bytes_recv': SINCE_BOOT + 4096},
    ]
    new = by_name(settled.sample())[NEW]

    assert new['bytes_recv'] == 4096
    assert new['bytes_recv_rate_per_sec'] == 4096 // new['time_since_update']


# --- The user-visible failure, through the real network plugin -----------------

snetio = namedtuple('snetio', 'bytes_sent bytes_recv packets_sent packets_recv errin errout dropin dropout')
snicstats = namedtuple('snicstats', 'isup duplex speed mtu flags')


@pytest.fixture
def fake_nics(monkeypatch):
    """Drive psutil from a list of interface names the test can grow."""
    names = [EXISTING]

    def counters(pernic=True):
        return {n: snetio(SINCE_BOOT, SINCE_BOOT, 10, 10, 0, 0, 0, 0) for n in names}

    monkeypatch.setattr(psutil, 'net_io_counters', counters)
    monkeypatch.setattr(psutil, 'net_if_stats', lambda: {n: snicstats(True, 2, 1000, 1500, 'up') for n in names})
    monkeypatch.setattr(psutil, 'net_if_addrs', lambda: {n: [] for n in names})
    return names


def test_network_update_views_survives_an_interface_appearing(fake_nics):
    """update_views() decorates views/<iface>/bytes_recv_rate_per_sec directly.

    Views are built from the fields a stat actually carries, so a stat missing
    its rate fields has no view to decorate and the whole refresh raised
    KeyError. A VPN coming up or a container starting was enough.
    """
    from glances.plugins.network import NetworkPlugin

    plugin = NetworkPlugin()
    plugin.update()
    plugin.update_views()

    fake_nics.append(NEW)
    plugin.update()

    plugin.update_views()

    assert plugin.get_views(item=NEW, key='bytes_recv_rate_per_sec', option='decoration') is not None

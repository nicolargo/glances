#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the Containers plugin engines (issue #3669 network aggregation)."""

from types import SimpleNamespace

from glances.plugins.containers.engines.docker import DockerStatsFetcher


def build_fetcher(networks, old_stats=None):
    """Build a DockerStatsFetcher without opening a live stats stream."""
    fetcher = DockerStatsFetcher.__new__(DockerStatsFetcher)
    fetcher._container = SimpleNamespace(id='deadbeef')
    fetcher._streamer = SimpleNamespace(
        stats={'networks': networks} if networks is not None else {},
        last_update_time=100.0,
    )
    fetcher._old_computed_stats = old_stats or {}
    fetcher._last_stats_computed_time = 97.0
    return fetcher


class TestDockerNetworkStatsAggregation:
    def test_single_interface(self):
        """A single interface keeps the values it had before the aggregation change."""
        fetcher = build_fetcher({'eth0': {'rx_bytes': 100, 'tx_bytes': 200}})
        stats = fetcher._get_network_stats()
        assert stats['cumulative_rx'] == 100
        assert stats['cumulative_tx'] == 200

    def test_two_interfaces_are_summed(self):
        """A container attached to two networks reports the sum of both."""
        fetcher = build_fetcher(
            {
                'eth0': {'rx_bytes': 100, 'tx_bytes': 200},
                'eth1': {'rx_bytes': 50, 'tx_bytes': 25},
            }
        )
        stats = fetcher._get_network_stats()
        assert stats['cumulative_rx'] == 150
        assert stats['cumulative_tx'] == 225

    def test_loopback_is_excluded(self):
        """Loopback traffic is not counted, even when the runtime reports it."""
        fetcher = build_fetcher(
            {
                'eth0': {'rx_bytes': 100, 'tx_bytes': 200},
                'lo': {'rx_bytes': 999, 'tx_bytes': 999},
            }
        )
        stats = fetcher._get_network_stats()
        assert stats['cumulative_rx'] == 100
        assert stats['cumulative_tx'] == 200


class TestDockerNetworkStatsNoData:
    def test_host_network_returns_none(self):
        """--network host containers have no networks key at all."""
        assert build_fetcher(None)._get_network_stats() is None

    def test_empty_networks_returns_none(self):
        assert build_fetcher({})._get_network_stats() is None

    def test_all_interfaces_malformed_returns_none(self):
        assert build_fetcher({'eth0': {'rx_bytes': 100}})._get_network_stats() is None

    def test_one_malformed_among_two_keeps_the_valid_one(self):
        """A malformed interface no longer discards the valid ones."""
        fetcher = build_fetcher(
            {
                'eth0': {'rx_bytes': 100, 'tx_bytes': 200},
                'eth1': {'rx_bytes': 50},
            }
        )
        stats = fetcher._get_network_stats()
        assert stats['cumulative_rx'] == 100
        assert stats['cumulative_tx'] == 200


class TestDockerNetworkStatsRates:
    def test_rates_use_the_summed_counters(self):
        fetcher = build_fetcher(
            {
                'eth0': {'rx_bytes': 100, 'tx_bytes': 200},
                'eth1': {'rx_bytes': 50, 'tx_bytes': 25},
            },
            old_stats={'network': {'cumulative_rx': 40, 'cumulative_tx': 25}},
        )
        stats = fetcher._get_network_stats()
        assert stats['rx'] == 110
        assert stats['tx'] == 200
        assert 'time_since_update' in stats

    def test_first_sample_has_no_rate_keys(self):
        fetcher = build_fetcher({'eth0': {'rx_bytes': 100, 'tx_bytes': 200}})
        stats = fetcher._get_network_stats()
        assert 'rx' not in stats
        assert 'tx' not in stats
        assert 'time_since_update' not in stats

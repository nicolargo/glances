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

from glances.plugins.containers import ContainersPlugin
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
    """Test the Docker network stats aggregation across container interfaces."""

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
    """Test the Docker network stats when no usable interface is reported."""

    def test_host_network_returns_none(self):
        """--network host containers have no networks key at all."""
        assert build_fetcher(None)._get_network_stats() is None

    def test_empty_networks_returns_none(self):
        """An empty networks dict yields no stats."""
        assert build_fetcher({})._get_network_stats() is None

    def test_all_interfaces_malformed_returns_none(self):
        """Every interface missing a counter yields no stats."""
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
    """Test the Docker network stats rate computation."""

    def test_rates_use_the_summed_counters(self):
        """Rates are computed from the summed counters, not from a single interface."""
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
        """Without previous stats there is nothing to compute a rate from."""
        fetcher = build_fetcher({'eth0': {'rx_bytes': 100, 'tx_bytes': 200}})
        stats = fetcher._get_network_stats()
        assert 'rx' not in stats
        assert 'tx' not in stats
        assert 'time_since_update' not in stats


class TestContainersTitle:
    """The title line is built by appending fragments to one list.

    `build_title` ended with the "(served by X)" append sitting outside its
    own `if`, so when several engines are present — the one case where that
    branch is skipped — the previous fragment was appended a second time.
    """

    @staticmethod
    def title(stats, show_engine_name, sort_key='cpu_percent'):
        plugin = ContainersPlugin.__new__(ContainersPlugin)
        plugin.curse_add_line = lambda msg, *args, **kwargs: {'msg': msg}
        plugin.curse_new_line = lambda: {'msg': '\n'}
        plugin.stats = stats
        plugin.views = {'show_engine_name': show_engine_name}
        plugin.sort_key = sort_key
        return ''.join(line['msg'] for line in plugin.build_title([]) if line['msg'] != '\n')

    def test_several_engines_do_not_repeat_the_sort_fragment(self):
        stats = [{'engine': 'docker'}, {'engine': 'podman'}]
        assert self.title(stats, show_engine_name=True) == 'CONTAINERS 2 sorted by CPU consumption'

    def test_several_engines_with_one_container_do_not_repeat_the_title(self):
        assert self.title([{'engine': 'podman'}], show_engine_name=True) == 'CONTAINERS'

    def test_one_engine_still_names_it(self):
        stats = [{'engine': 'docker'}, {'engine': 'docker'}]
        assert self.title(stats, show_engine_name=False) == (
            'CONTAINERS 2 sorted by CPU consumption (served by docker)'
        )

    def test_one_engine_one_container(self):
        assert self.title([{'engine': 'docker'}], show_engine_name=False) == ('CONTAINERS (served by docker)')

    def test_the_sort_key_is_named_in_the_title(self):
        stats = [{'engine': 'docker'}, {'engine': 'docker'}]
        assert 'memory consumption' in self.title(stats, show_engine_name=False, sort_key='memory_usage')
        assert 'container name' in self.title(stats, show_engine_name=False, sort_key='name')

    def test_no_fragment_appears_twice(self):
        for stats, show in (
            ([{'engine': 'docker'}, {'engine': 'podman'}], True),
            ([{'engine': 'podman'}], True),
            ([{'engine': 'docker'}, {'engine': 'docker'}], False),
            ([{'engine': 'docker'}], False),
        ):
            title = self.title(stats, show_engine_name=show)
            assert title.count('CONTAINERS') == 1, title
            assert title.count('sorted by') <= 1, title
            assert title.count('served by') <= 1, title

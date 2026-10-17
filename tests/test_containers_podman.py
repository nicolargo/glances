#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the Podman engine stats parsing (unknown units must not raise)."""

import pytest

from glances.plugins.containers.engines.podman import PodmanPodStatsFetcher


def build_fetcher():
    """Build a PodmanPodStatsFetcher without opening a live stats stream."""
    fetcher = PodmanPodStatsFetcher.__new__(PodmanPodStatsFetcher)
    fetcher._log_debug = lambda msg, exception=None: None
    return fetcher


class TestPodmanStatsParsing:
    """The three parsing helpers keep working on the values Podman sends."""

    def test_memory_usage(self):
        stats = build_fetcher()._get_memory_stats({'MemUsage': '1.5MB / 5GB'})
        assert stats['usage'] == 1500000.0
        assert stats['limit'] == 5000000000.0

    def test_network_usage(self):
        stats = build_fetcher()._get_network_stats({'NetIO': '1.2kB / 3.4kB'})
        assert stats['rx'] == 1200.0
        assert stats['tx'] == 3400.0

    def test_block_io(self):
        stats = build_fetcher()._get_io_stats({'BlockIO': '3 kB / 4 kB'})
        assert stats['ior'] == 3000.0
        assert stats['iow'] == 4000.0

    def test_cpu_usage(self):
        assert build_fetcher()._get_cpu_stats({'CPU': '12.5%'}) == {'total': 12.5}

    def test_missing_fields(self):
        fetcher = build_fetcher()
        assert fetcher._get_memory_stats({}) is None
        assert fetcher._get_network_stats({}) is None
        assert fetcher._get_io_stats({}) is None
        assert fetcher._get_cpu_stats({}) is None

    def test_missing_separator(self):
        assert build_fetcher()._get_memory_stats({'MemUsage': '1MB'}) is None

    def test_cpu_usage_with_an_unknown_unit(self):
        # '5 XYZ' used to raise KeyError('XYZ') out of _get_cpu_stats()
        assert build_fetcher()._get_cpu_stats({'CPU': '5 XYZ'}) is None

    @pytest.mark.parametrize('stats', [{'CPU': 'n/a'}, {'CPU': '12,5%'}])
    def test_cpu_usage_with_an_unparsable_value(self, stats):
        # these do not raise; string_value_to_float() returns None and the
        # helper keeps its normal return shape (same as before this change)
        assert build_fetcher()._get_cpu_stats(stats) == {'total': None}


class TestPodmanStatsUnknownUnit:
    """string_value_to_float() raises KeyError for a unit token it does not know
    (it only maps B/KB/MB/GB/TB/PB). The three helpers must degrade to None, the
    same way they already do for ValueError, instead of letting the KeyError
    escape and break the whole stats collection."""

    @pytest.mark.parametrize(
        'stats',
        [
            {'MemUsage': '1.5 MB / 5 %'},
            {'MemUsage': '1 MB extra / 2 MB'},
        ],
    )
    def test_memory_stats_with_an_unknown_unit(self, stats):
        assert build_fetcher()._get_memory_stats(stats) is None

    @pytest.mark.parametrize(
        'stats',
        [
            {'NetIO': '1 MB extra / 2 MB'},
            {'NetIO': '1 % / 2 MB'},
        ],
    )
    def test_network_stats_with_an_unknown_unit(self, stats):
        assert build_fetcher()._get_network_stats(stats) is None

    @pytest.mark.parametrize(
        'stats',
        [
            {'BlockIO': '3 kB / 4 %'},
            {'BlockIO': '3 MB extra / 4 kB'},
        ],
    )
    def test_io_stats_with_an_unknown_unit(self, stats):
        assert build_fetcher()._get_io_stats(stats) is None

    @pytest.mark.parametrize(
        ('method_name', 'stats'),
        [
            ('_get_memory_stats', {'MemUsage': 'MB / GB'}),
            ('_get_network_stats', {'NetIO': ' / '}),
            ('_get_io_stats', {'BlockIO': 'kB / kB'}),
        ],
    )
    def test_an_unparsable_value_still_returns_the_stats_dict(self, method_name, stats):
        # A pure unit or an empty half does not raise; string_value_to_float()
        # returns None and the helper keeps its normal return shape.
        result = getattr(build_fetcher(), method_name)(stats)
        assert result is not None
        # every parsed field is None; only the hard-coded rate window and the
        # hard-coded inactive_file counter carry a value
        assert all(value is None for key, value in result.items() if key not in {'time_since_update', 'inactive_file'})

    def test_a_negative_value_is_not_an_unit_error(self):
        stats = build_fetcher()._get_memory_stats({'MemUsage': '-3 MB / 2 MB'})
        assert stats['usage'] is None
        assert stats['limit'] == 2000000.0

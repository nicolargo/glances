#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the CPU limit fallback of the container engines.

``psutil.cpu_count()`` is documented as ``int | None``, and it returns 0 on
platforms where the number of cores cannot be determined. The container
engines fall back to it when the engine does not report a CPU limit, so a
missing or zero value must not break the stats collection.
"""

from types import SimpleNamespace

import psutil
import pytest

from glances.plugins.containers.engines.lxd import LxdStatsFetcher
from glances.plugins.containers.engines.podman import PodmanContainerStatsFetcher


@pytest.fixture
def cpu_count(monkeypatch):
    """Patch psutil.cpu_count() and let the test choose its return value."""

    def _set(value):
        monkeypatch.setattr(psutil, 'cpu_count', lambda *args, **kwargs: value)

    return _set


LXD_STATE = SimpleNamespace(cpu={'usage': 123456789})


def build_lxd_fetcher(limits_cpu=None):
    """Build a LxdStatsFetcher without connecting to LXD."""
    fetcher = LxdStatsFetcher.__new__(LxdStatsFetcher)
    fetcher._instance = SimpleNamespace(name='c1', expanded_config={'limits.cpu': limits_cpu})
    fetcher._old_computed_stats = {}
    return fetcher


def build_podman_fetcher():
    """Build a PodmanContainerStatsFetcher without opening a live stats stream."""
    fetcher = PodmanContainerStatsFetcher.__new__(PodmanContainerStatsFetcher)
    fetcher._container = SimpleNamespace(id='deadbeef')
    fetcher._inspect_data = {'HostConfig': {}}
    fetcher._old_computed_stats = {}
    fetcher._last_stats_computed_time = 0.0
    fetcher._streamer = SimpleNamespace(stats=None, last_update_time=100.0)
    fetcher.get_streamed_stats = lambda: {
        'CPU': 0.0,
        'MemUsage': '1MB',
        'MemLimit': '2MB',
        'BlockInput': '0B',
        'BlockOutput': '0B',
        'NetInput': '0B',
        'NetOutput': '0B',
    }
    return fetcher


class TestLxdCpuLimitFallback:
    """The LXD engine must survive a cpu_count() that carries no number."""

    def test_an_explicit_limit_wins(self, cpu_count):
        cpu_count(8)
        assert build_lxd_fetcher(limits_cpu='4')._get_cpu_stats(LXD_STATE)['limit'] == 4.0

    def test_the_host_core_count_is_the_fallback(self, cpu_count):
        cpu_count(8)
        assert build_lxd_fetcher()._get_cpu_stats(LXD_STATE)['limit'] == 8.0

    def test_an_unparsable_limit_falls_back_to_the_host_core_count(self, cpu_count):
        cpu_count(8)
        assert build_lxd_fetcher(limits_cpu='not-a-number')._get_cpu_stats(LXD_STATE)['limit'] == 8.0

    @pytest.mark.parametrize('value', [None, 0])
    def test_a_missing_core_count_does_not_raise(self, cpu_count, value):
        # before the fix: TypeError: float() argument must be a string or a
        # real number, not 'NoneType' (raised from the except branch itself)
        cpu_count(value)
        assert build_lxd_fetcher()._get_cpu_stats(LXD_STATE)['limit'] == 1.0

    @pytest.mark.parametrize('value', [None, 0])
    def test_a_missing_core_count_does_not_raise_on_the_except_path(self, cpu_count, value):
        cpu_count(value)
        assert build_lxd_fetcher(limits_cpu='not-a-number')._get_cpu_stats(LXD_STATE)['limit'] == 1.0

    def test_a_huge_core_count_is_kept(self, cpu_count):
        cpu_count(4096)
        assert build_lxd_fetcher()._get_cpu_stats(LXD_STATE)['limit'] == 4096.0

    def test_the_rest_of_the_cpu_stats_is_unchanged(self, cpu_count):
        cpu_count(None)
        stats = build_lxd_fetcher()._get_cpu_stats(LXD_STATE)
        assert stats['cumulative_ns'] == 123456789
        assert stats['total'] == 0.0
        assert stats['limit'] == 1.0


class TestPodmanCpuLimitFallback:
    """The Podman engine has the same fallback, inside a ValueError-only guard."""

    def test_the_host_core_count_is_the_fallback(self, cpu_count):
        cpu_count(8)
        assert build_podman_fetcher()._compute_activity_stats()['cpu']['limit'] == 8.0

    @pytest.mark.parametrize('value', [None, 0])
    def test_a_missing_core_count_does_not_raise(self, cpu_count, value):
        cpu_count(value)
        assert build_podman_fetcher()._compute_activity_stats()['cpu']['limit'] == 1.0

    def test_an_explicit_quota_wins(self, cpu_count):
        cpu_count(None)
        fetcher = build_podman_fetcher()
        fetcher._inspect_data = {'HostConfig': {'CpuQuota': 200000, 'CpuPeriod': 100000}}
        assert fetcher._compute_activity_stats()['cpu']['limit'] == 2.0

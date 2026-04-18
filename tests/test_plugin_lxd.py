#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Christian Rishøj <christian@rishoj.net>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the LXD container engine."""

import time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


def make_mock_state(
    cpu_ns=5_000_000_000,
    mem_usage=1_000_000_000,
    mem_total=2_000_000_000,
    mem_usage_peak=None,
    disk_usage=500_000,
    net_rx=10_000,
    net_tx=20_000,
):
    """Create a mock LXD instance state."""
    return SimpleNamespace(
        cpu={"usage": cpu_ns},
        memory={"usage": mem_usage, "total": mem_total, "usage_peak": mem_usage_peak or mem_total},
        disk={"root": {"usage": disk_usage}},
        network={
            "eth0": {
                "type": "broadcast",
                "counters": {"bytes_received": net_rx, "bytes_sent": net_tx},
            },
            "lo": {
                "type": "loopback",
                "counters": {"bytes_received": 999, "bytes_sent": 999},
            },
        },
    )


def make_mock_instance(
    name="test-container",
    status="Running",
    config=None,
    expanded_devices=None,
    created_at="2026-01-01T00:00:00Z",
    last_used_at="2026-03-15T10:00:00Z",
    location="node1",
):
    """Create a mock LXD instance."""
    instance = MagicMock()
    instance.name = name
    instance.status = status
    instance.config = config or {"image.description": "Ubuntu 24.04 LTS"}
    instance.expanded_devices = expanded_devices or {}
    instance.created_at = created_at
    instance.last_used_at = last_used_at
    instance.location = location
    return instance


@pytest.fixture
def mock_instance():
    """Return a mock LXD instance that returns incrementing CPU stats."""
    instance = make_mock_instance()
    call_count = 0

    def stateful_state():
        nonlocal call_count
        call_count += 1
        return make_mock_state(
            cpu_ns=5_000_000_000 * call_count,
            net_rx=10_000 * call_count,
            net_tx=20_000 * call_count,
            disk_usage=500_000 * call_count,
        )

    instance.state = stateful_state
    return instance


class TestLxdStatsFetcher:
    """Test LxdStatsFetcher stat computation."""

    def test_no_state_returns_empty(self, mock_instance):
        from glances.plugins.containers.engines.lxd import LxdStatsFetcher

        fetcher = LxdStatsFetcher(mock_instance, poll_interval=999)
        # Before any poll completes, force state to None
        fetcher._state = None
        stats = fetcher.activity_stats
        fetcher.stop()

        assert stats == {"cpu": {}, "memory": {}, "io": {}, "network": {}}

    def test_first_poll_returns_zero_cpu(self, mock_instance):
        from glances.plugins.containers.engines.lxd import LxdStatsFetcher

        fetcher = LxdStatsFetcher(mock_instance, poll_interval=999)
        # Wait for first poll
        time.sleep(0.2)
        stats = fetcher.activity_stats
        fetcher.stop()

        assert stats["cpu"]["total"] == 0.0
        assert stats["memory"]["usage"] == 1_000_000_000
        assert stats["memory"]["limit"] == 2_000_000_000

    def test_second_poll_computes_cpu_delta(self, mock_instance):
        from glances.plugins.containers.engines.lxd import LxdStatsFetcher

        fetcher = LxdStatsFetcher(mock_instance, poll_interval=999)
        time.sleep(0.2)

        # First reading (baseline)
        fetcher.activity_stats

        # Simulate second poll
        fetcher._state = mock_instance.state()
        stats = fetcher.activity_stats
        fetcher.stop()

        assert "total" in stats["cpu"]
        assert stats["cpu"]["total"] > 0

    def test_network_excludes_loopback(self, mock_instance):
        from glances.plugins.containers.engines.lxd import LxdStatsFetcher

        fetcher = LxdStatsFetcher(mock_instance, poll_interval=999)
        time.sleep(0.2)
        stats = fetcher.activity_stats
        fetcher.stop()

        # Should only count eth0, not lo
        assert stats["network"]["cumulative_rx"] == 10_000
        assert stats["network"]["cumulative_tx"] == 20_000

    def test_memory_unlimited_falls_back_to_peak(self):
        from glances.plugins.containers.engines.lxd import LxdStatsFetcher

        instance = make_mock_instance()
        instance.state = lambda: make_mock_state(mem_total=0, mem_usage_peak=4_000_000_000)

        fetcher = LxdStatsFetcher(instance, poll_interval=999)
        time.sleep(0.2)
        stats = fetcher.activity_stats
        fetcher.stop()

        # total=0 means unlimited, should fall back to usage_peak
        assert stats["memory"]["limit"] == 4_000_000_000

    def test_stop_terminates_thread(self, mock_instance):
        from glances.plugins.containers.engines.lxd import LxdStatsFetcher

        fetcher = LxdStatsFetcher(mock_instance, poll_interval=999)
        fetcher.stop()
        time.sleep(0.1)
        assert not fetcher._thread.is_alive()


class TestLxdExtensionGenerateStats:
    """Test LxdExtension.generate_stats with mock instances."""

    def _make_extension(self):
        """Create an LxdExtension without connecting to a real server."""
        from glances.plugins.containers.engines.lxd import LxdExtension

        with patch.object(LxdExtension, '__init__', lambda self, **kwargs: None):
            ext = LxdExtension.__new__(LxdExtension)
            ext.ext_name = "containers (LXD)"
            ext.stats_fetchers = {}
            ext.CONTAINER_ACTIVE_STATUS = ['Running']
            return ext

    def test_stopped_instance_returns_minimal_stats(self):
        ext = self._make_extension()
        instance = make_mock_instance(status="Stopped")
        stats = ext.generate_stats(instance)

        assert stats['name'] == 'test-container'
        assert stats['status'] == 'stopped'
        assert stats['cpu_percent'] is None
        assert 'memory_usage' not in stats

    def test_running_instance_with_fetcher(self):
        ext = self._make_extension()
        instance = make_mock_instance()

        fetcher = MagicMock()
        fetcher.activity_stats = {
            "cpu": {"total": 50.0},
            "memory": {"usage": 1_000_000_000, "limit": 2_000_000_000, "inactive_file": 0},
            "io": {"ior": 100, "iow": 50, "time_since_update": 2},
            "network": {"rx": 5000, "tx": 3000, "time_since_update": 2},
        }
        ext.stats_fetchers["test-container"] = fetcher

        stats = ext.generate_stats(instance)

        assert stats['cpu_percent'] == 50.0
        assert stats['memory_usage'] == 1_000_000_000
        assert stats['memory_limit'] == 2_000_000_000
        assert stats['io_rx'] == 50
        assert stats['io_wx'] == 25
        assert stats['network_rx'] == 2500
        assert stats['network_tx'] == 1500

    def test_proxy_device_ports(self):
        ext = self._make_extension()
        instance = make_mock_instance(
            expanded_devices={
                "http": {"type": "proxy", "listen": "tcp:0.0.0.0:80", "connect": "tcp:127.0.0.1:8080"},
                "https": {"type": "proxy", "listen": "tcp:0.0.0.0:443", "connect": "tcp:127.0.0.1:8443"},
                "root": {"type": "disk", "path": "/", "pool": "default"},
            },
        )

        fetcher = MagicMock()
        fetcher.activity_stats = {"cpu": {}, "memory": {}, "io": {}, "network": {}}
        ext.stats_fetchers["test-container"] = fetcher

        stats = ext.generate_stats(instance)

        assert "80->8080/tcp" in stats['ports']
        assert "443->8443/tcp" in stats['ports']

    def test_no_proxy_devices_empty_ports(self):
        ext = self._make_extension()
        instance = make_mock_instance(
            expanded_devices={"root": {"type": "disk", "path": "/", "pool": "default"}},
        )

        fetcher = MagicMock()
        fetcher.activity_stats = {"cpu": {}, "memory": {}, "io": {}, "network": {}}
        ext.stats_fetchers["test-container"] = fetcher

        stats = ext.generate_stats(instance)
        assert stats['ports'] == ''

    def test_image_from_config(self):
        ext = self._make_extension()
        instance = make_mock_instance(config={"image.description": "Alpine 3.19"})
        stats = ext.generate_stats(instance)
        assert stats['image'] == 'Alpine 3.19'


class TestLxdExtensionUpdate:
    """Test LxdExtension.update with mock client."""

    def _make_extension_with_client(self, instances, local_node=None):
        from glances.plugins.containers.engines.lxd import LxdExtension

        with patch.object(LxdExtension, '__init__', lambda self, **kwargs: None):
            ext = LxdExtension.__new__(LxdExtension)
            ext.ext_name = "containers (LXD)"
            ext.stats_fetchers = {}
            ext.CONTAINER_ACTIVE_STATUS = ['Running']
            ext.display_error = True
            ext.disable = False
            ext.poll_interval = 999
            ext.local_node = local_node
            ext.client = MagicMock()
            ext.client.instances.all.return_value = instances
            return ext

    def test_filters_to_running_only(self):
        running = make_mock_instance(name="web", status="Running")
        stopped = make_mock_instance(name="db", status="Stopped")
        ext = self._make_extension_with_client([running, stopped])

        with patch('glances.plugins.containers.engines.lxd.LxdStatsFetcher'):
            _, container_stats = ext.update(all_tag=False)

        assert len(container_stats) == 1
        assert container_stats[0]['name'] == 'web'

    def test_all_tag_includes_stopped(self):
        running = make_mock_instance(name="web", status="Running")
        stopped = make_mock_instance(name="db", status="Stopped")
        ext = self._make_extension_with_client([running, stopped])

        with patch('glances.plugins.containers.engines.lxd.LxdStatsFetcher'):
            _, container_stats = ext.update(all_tag=True)

        assert len(container_stats) == 2

    def test_cluster_filters_to_local_node(self):
        local = make_mock_instance(name="web", location="node1")
        remote = make_mock_instance(name="db", location="node2")
        ext = self._make_extension_with_client([local, remote], local_node="node1")

        with patch('glances.plugins.containers.engines.lxd.LxdStatsFetcher'):
            _, container_stats = ext.update(all_tag=True)

        assert len(container_stats) == 1
        assert container_stats[0]['name'] == 'web'

    def test_standalone_does_not_filter_by_location(self):
        # On a non-clustered LXD host, instance.location is typically empty.
        # local_node stays None, so every instance must pass through.
        a = make_mock_instance(name="web", location="")
        b = make_mock_instance(name="db", location=None)
        ext = self._make_extension_with_client([a, b], local_node=None)

        with patch('glances.plugins.containers.engines.lxd.LxdStatsFetcher'):
            _, container_stats = ext.update(all_tag=True)

        assert {c['name'] for c in container_stats} == {"web", "db"}  # nosec B101

    def test_cleans_up_removed_instances(self):
        instance = make_mock_instance(name="web")
        ext = self._make_extension_with_client([instance])

        mock_fetcher = MagicMock()
        ext.stats_fetchers["old-container"] = mock_fetcher

        with patch('glances.plugins.containers.engines.lxd.LxdStatsFetcher'):
            ext.update(all_tag=True)

        mock_fetcher.stop.assert_called_once()
        assert "old-container" not in ext.stats_fetchers

    def test_disabled_returns_empty(self):
        ext = self._make_extension_with_client([])
        ext.disable = True
        version, containers = ext.update(all_tag=True)
        assert version == {}
        assert containers == []


class TestLxdExtensionConnect:  # noqa: D203
    """Test LxdExtension.connect detection of cluster membership."""

    def _make_extension_for_connect(self, host_info):
        from glances.plugins.containers.engines.lxd import LxdExtension

        mock_client = MagicMock()
        mock_client.host_info = host_info

        with patch.object(LxdExtension, '__init__', lambda self, **kwargs: None):
            ext = LxdExtension.__new__(LxdExtension)
            ext.ext_name = "containers (LXD)"
            ext.endpoint = None
            ext.local_node = None
            ext.disable = False

            with patch('glances.plugins.containers.engines.lxd.LxdClient', return_value=mock_client, create=True):
                ext.connect()
        return ext

    def test_standalone_leaves_local_node_unset(self):
        ext = self._make_extension_for_connect({"environment": {"server_name": "zfs01", "server_clustered": False}})
        assert ext.local_node is None  # nosec B101

    def test_cluster_sets_local_node(self):
        ext = self._make_extension_for_connect({"environment": {"server_name": "node1", "server_clustered": True}})
        assert ext.local_node == "node1"  # nosec B101

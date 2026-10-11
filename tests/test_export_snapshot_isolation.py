#
# This file is part of Glances.
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Regression tests for export snapshot isolation."""

import unittest

from glances.exports.export import GlancesExport
from glances.stats import GlancesStats


class FakePlugin:
    """Expose live stats through the same interface as a regular plugin."""

    def __init__(self, stats, limits):
        """Initialize the fake plugin with live statistics and limits."""
        self.stats = stats
        self.limits = limits

    def get_export(self):
        return self.stats

    def get_limits(self):
        return self.limits.copy()

    def is_enabled(self):
        return True


def build_stats():
    """Build a minimal stats manager containing dict and list plugins."""
    stats = GlancesStats.__new__(GlancesStats)
    stats._plugins = {
        'cpu': FakePlugin(
            {'total': 12, 'user': 7},
            {'cpu_warning': 70, 'cpu_disable': False},
        ),
        'network': FakePlugin(
            [{'key': 'interface_name', 'interface_name': 'eth0', 'bytes_recv': 10}],
            {'network_warning': 80, 'network_disable': False},
        ),
    }
    return stats


class TestExportSnapshotIsolation(unittest.TestCase):
    """Verify that export operations cannot mutate live plugin statistics."""

    def test_prepared_payloads_are_detached_from_plugin_stats(self):
        """Prepared payloads should be shallow copies with merged limits."""
        cpu_stats = {'total': 12, 'user': 7, 'cpu_disable': True}
        network_stats = [{'interface_name': 'eth0', 'bytes_recv': 10}]
        exporter = GlancesExport()

        prepared_cpu = exporter._prepare_export_stats(
            'cpu',
            cpu_stats,
            {'cpu_warning': 70, 'cpu_disable': False},
        )
        prepared_network = exporter._prepare_export_stats(
            'network',
            network_stats,
            {'network_warning': 80, 'network_disable': False},
        )

        self.assertIsNot(prepared_cpu, cpu_stats)
        self.assertIsNot(prepared_network, network_stats)
        self.assertIsNot(prepared_network[0], network_stats[0])
        self.assertEqual(prepared_cpu, {'total': 12, 'user': 7, 'cpu_warning': 70})
        self.assertEqual(
            prepared_network,
            [{'interface_name': 'eth0', 'bytes_recv': 10, 'network_warning': 80}],
        )
        self.assertEqual(cpu_stats, {'total': 12, 'user': 7, 'cpu_disable': True})
        self.assertEqual(network_stats, [{'interface_name': 'eth0', 'bytes_recv': 10}])

    def test_export_preparation_does_not_mutate_live_stats(self):
        """Exporter limit enrichment should not modify live statistics."""
        stats = build_stats()
        live_cpu = stats._plugins['cpu'].stats
        live_network = stats._plugins['network'].stats

        exporter = GlancesExport()
        exporter.export_enable = True
        exporter.exclude_fields = []
        exporter.update(stats)

        self.assertEqual(live_cpu, {'total': 12, 'user': 7})
        self.assertEqual(
            live_network,
            [{'key': 'interface_name', 'interface_name': 'eth0', 'bytes_recv': 10}],
        )

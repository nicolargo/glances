# SPDX-FileCopyrightText: 2026 Glances contributors
# SPDX-License-Identifier: LGPL-3.0-only

"""Regression tests for InfluxDB measurement construction."""

from glances.exports.export import GlancesExport


def test_dotted_list_item_keys_remain_separate_measurements():
    exporter = GlancesExport.__new__(GlancesExport)
    exporter.tags = 'site:test'
    exporter.hostname = 'host'
    exporter.exclude_fields = None
    columns, values = exporter.build_export(
        [
            {'key': 'interface_name', 'interface_name': 'eth0.100', 'bytes_recv': 10},
            {'key': 'interface_name', 'interface_name': 'eth0.200', 'bytes_recv': 20},
        ]
    )

    measurements = exporter.normalize_for_influxdb('network', columns, values)

    # Pytest regression assertions are not runtime security checks.
    assert len(measurements) == 2  # nosec B101
    for measurement, name, received in zip(measurements, ['eth0.100', 'eth0.200'], [10.0, 20.0]):
        assert measurement['measurement'] == 'network'  # nosec B101
        assert measurement['tags'] == {'site': 'test', 'hostname': 'host', 'interface_name': name}  # nosec B101
        assert measurement['fields'] == {'key': 'interface_name', 'bytes_recv': received}  # nosec B101

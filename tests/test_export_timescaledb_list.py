#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2025 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances unit tests for the TimescaleDB export of list plugins.

Tests cover:
- The number of generated columns matches the number of values (issue #3592)
- The 'key' field is exported once, as key_id
- No stat field is dropped from the exported row
"""

import pytest

try:
    import psycopg  # noqa: F401
except ImportError:
    pytest.skip("psycopg not installed", allow_module_level=True)

from glances.exports.glances_timescaledb import Export


class FakeStats:
    """Minimal stats stub exposing a single list plugin."""

    def getAllExportsAsDict(self, plugin_list=None):
        return {
            'network': [
                {'key': 'interface_name', 'interface_name': 'eth0', 'bytes_recv': 10, 'bytes_sent': 20},
                {'key': 'interface_name', 'interface_name': 'lo0', 'bytes_recv': 1, 'bytes_sent': 2},
            ]
        }

    def getAllLimitsAsDict(self, plugin_list=None):
        return {'network': {}}


def build_export(captured):
    """Return an Export instance with the DB layer replaced by a capture hook."""
    export = object.__new__(Export)
    export.export_enable = True
    export.hostname = 'testhost'
    export._last_exported_list = ['network']
    export.plugins_to_export = lambda stats: ['network']
    export.last_exported_list = lambda: ['network']
    export.export = lambda plugin, creation_list, segmented_by, values_list: captured.update(
        plugin=plugin, creation_list=creation_list, segmented_by=segmented_by, values_list=values_list
    )
    return export


class TestTimescaleDBListPlugin:
    """Unit tests for the list-plugin branch of the TimescaleDB exporter."""

    @pytest.fixture
    def captured(self):
        captured = {}
        build_export(captured).update(FakeStats())
        return captured

    def test_columns_and_values_count_match(self, captured):
        """Every row must provide exactly one value per generated column (issue #3592)."""
        columns = [item.split(' ')[0] for item in captured['creation_list']]
        for row in captured['values_list']:
            assert len(row) == len(columns)

    def test_key_field_exported_once_as_key_id(self, captured):
        """The 'key' field is stored as key_id and must not be duplicated as a column."""
        columns = [item.split(' ')[0] for item in captured['creation_list']]
        assert 'key_id' in columns
        assert 'key' not in columns

    def test_no_stat_field_is_dropped(self, captured):
        """The last stat field must still be exported, with the right value."""
        columns = [item.split(' ')[0] for item in captured['creation_list']]
        assert 'bytes_sent' in columns
        row = dict(zip(columns, captured['values_list'][0]))
        assert row['key_id'] == 'interface_name'
        assert row['interface_name'] == 'eth0'
        assert row['bytes_recv'] == 10
        assert row['bytes_sent'] == 20

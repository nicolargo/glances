#!/bin/bash

# Exit on error
set -e

# Remove previous test database
echo "Remove previous test database..."
rm -f /tmp/glances.db

# Run glances with export to DuckDB, stopping after 10 writes
# This will run synchronously now since we're using --stop-after
echo "Glances to export system stats to DuckDB (duration: ~ 20 seconds)"
.venv/bin/python -m glances --config ./conf/glances.conf --export duckdb --stop-after 10 --quiet

echo "Checking DuckDB database..."
.venv/bin/python ./tests-data/tools/duckdbcheck.py -i /tmp/glances.db -l 9

echo "Script completed successfully!"
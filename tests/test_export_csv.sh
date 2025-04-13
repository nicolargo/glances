#!/bin/bash
# Pre-requisites:
# - jq

# Exit on error
set -e

# Run glances with export to InfluxDB, stopping after 10 writes
# This will run synchronously now since we're using --stop-after
echo "Glances starts to export system stats to CSV file /tmp/glances.csv (duration: ~ 20 seconds)"
rm -f /tmp/glances.csv
./venv/bin/python -m glances --export csv --export-csv-file /tmp/glances.csv --stop-after 10 --quiet

echo "Checking CSV file..."
./venv/bin/python ./tests-data/tools/csvcheck.py -i /tmp/glances2.csv -l 9

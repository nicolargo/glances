#!/bin/bash

# Exit on error
set -e

# Run glances with export to CSV file, stopping after 10 writes
# This will run synchronously now since we're using --stop-after
echo "Glances starts to export system stats to CSV file /tmp/glances.csv (duration: ~ 20 seconds)"
rm -f /tmp/glances.csv /tmp/glances-[0-9][0-9][0-9].csv
.venv/bin/python -m glances.main_v5 --export csv --export-csv-file /tmp/glances.csv --stop-after 10 --quiet

echo "Checking CSV file..."
# 10 cycles give 8 rows: v5 writes nothing on the first cycle (rates are not
# known yet) and the header with the second.
.venv/bin/python ./tests-data/tools/csvcheck.py -i /tmp/glances.csv -l 8

# v5 starts a new file when the column set changes: none is expected here.
if ls /tmp/glances-[0-9][0-9][0-9].csv > /dev/null 2>&1; then
    echo "Error: the column set changed during the run (rotated CSV file found)"
    exit 1
fi

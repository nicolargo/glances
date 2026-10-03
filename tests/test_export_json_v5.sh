#!/bin/bash

# Exit on error
set -e

# Run glances with export to JSON file, stopping after 3 writes (to be sure rates are included)
# This will run synchronously now since we're using --stop-after
echo "Glances starts to export system stats to JSON file /tmp/glances.json (duration: ~ 10 seconds)"
rm -f /tmp/glances.json
.venv/bin/python -m glances.main_v5 --export json --export-json-file /tmp/glances.json --stop-after 3 --quiet

echo "Checking JSON file..."
# -e: a missing field (null) fails the script.
jq -e . /tmp/glances.json
jq -e .cpu.total /tmp/glances.json
jq -e .mem.total /tmp/glances.json
jq -e .processcount.total /tmp/glances.json

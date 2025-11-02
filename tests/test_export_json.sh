#!/bin/bash

# Exit on error
set -e

# Run glances with export to JSON file, stopping after 3 writes (to be sure rates are included)
# This will run synchronously now since we're using --stop-after
echo "Glances starts to export system stats to JSON file /tmp/glances.json (duration: ~ 10 seconds)"
rm -f /tmp/glances.json
.venv/bin/python -m glances --export json --export-json-file /tmp/glances.json --stop-after 3 --quiet

echo "Checking JSON file..."
jq . /tmp/glances.json
jq .cpu /tmp/glances.json
jq .cpu.total /tmp/glances.json
jq .mem /tmp/glances.json
jq .mem.total /tmp/glances.json
jq .processcount /tmp/glances.json
jq .processcount.total /tmp/glances.json

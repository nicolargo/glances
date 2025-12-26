#!/bin/bash

# Exit on error
set -e

# Run glances with export to Prometheus, stopping after 10 writes
# This will run synchronously now since we're using --stop-after
echo "Glances to export system stats to Prometheus"
.venv/bin/python -m glances --config ./conf/glances.conf --export prometheus --stop-after 10 --quiet &
# Get the PID of the last background command
GLANCES_PID=$!

# Wait for a few seconds to let glances start
echo "Please wait for a few seconds..."
sleep 6

# Check if we can access the Prometheus metrics endpoint
echo "Checking Prometheus metrics endpoint..."
curl http://localhost:9091/metrics

# Kill the glances process if it's still running
if ps -p $GLANCES_PID > /dev/null; then
    kill $GLANCES_PID
fi

echo "Script completed successfully!"
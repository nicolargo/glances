#!/bin/bash
# Pre-requisites:
# - docker
# - jq

# Exit on error
set -e

echo "Stop previous nats container..."
docker stop nats-for-glances || true
docker rm nats-for-glances || true

echo "Starting nats container..."
docker run -d \
    --name nats-for-glances \
    -p 4222:4222 \
    -p 8222:8222 \
    -p 6222:6222 \
    nats:latest

# Wait for InfluxDB to be ready (5 seconds)
echo "Waiting for nats to start (~ 5 seconds)..."
sleep 5

# Run glances with export to nats, stopping after 10 writes
# This will run synchronously now since we're using --stop-after
echo "Glances to export system stats to nats (duration: ~ 20 seconds)"
.venv/bin/python -m glances --config ./conf/glances.conf --export nats --stop-after 10 --quiet

# Stop and remove the nats container
echo "Stopping and removing nats container..."
docker stop nats-for-glances && docker rm nats-for-glances

echo "Script completed successfully!"

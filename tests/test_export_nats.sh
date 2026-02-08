#!/bin/bash
# Pre-requisites:
# - docker
# - jq

# Exit on error
set -e

# Configuration
MIN_MESSAGES=10
NATS_SUBJECT="glances.>"
MESSAGE_COUNT_FILE=$(mktemp)
echo "0" > "$MESSAGE_COUNT_FILE"

# Cleanup function
cleanup() {
    echo "Cleaning up..."
    # Kill subscriber if running
    if [ -n "$SUBSCRIBER_PID" ] && kill -0 "$SUBSCRIBER_PID" 2>/dev/null; then
        kill "$SUBSCRIBER_PID" 2>/dev/null || true
    fi
    # Stop and remove containers
    docker stop nats-subscriber 2>/dev/null || true
    docker stop nats-for-glances 2>/dev/null || true
    docker rm nats-subscriber 2>/dev/null || true
    docker rm nats-for-glances 2>/dev/null || true
    # Remove temp file
    rm -f "$MESSAGE_COUNT_FILE"
}
trap cleanup EXIT

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

# Wait for NATS to be ready (5 seconds)
echo "Waiting for nats to start (~ 5 seconds)..."
sleep 5

# Start a NATS subscriber in the background using nats-box container
# The subscriber will count messages received on the glances subject
echo "Starting NATS subscriber to count messages..."
docker run --rm --name nats-subscriber \
    --network host \
    natsio/nats-box:latest \
    nats sub "$NATS_SUBJECT" 2>/dev/null | \
    while read -r line; do
        if [[ "$line" == *"Received"* ]] || [[ "$line" == "{"* ]]; then
            count=$(cat "$MESSAGE_COUNT_FILE")
            echo $((count + 1)) > "$MESSAGE_COUNT_FILE"
        fi
    done &
SUBSCRIBER_PID=$!

# Give the subscriber time to connect
sleep 2

# Run glances with export to nats, stopping after 10 writes
# This will run synchronously now since we're using --stop-after
echo "Glances to export system stats to nats (duration: ~ 20 seconds)"
.venv/bin/python -m glances --config ./conf/glances.conf --export nats --stop-after 10 --quiet

# Give some time for final messages to be received
sleep 2

# Stop the subscriber
docker stop nats-subscriber 2>/dev/null || true
kill "$SUBSCRIBER_PID" 2>/dev/null || true

# Check message count
MESSAGE_COUNT=$(cat "$MESSAGE_COUNT_FILE")
echo "Received $MESSAGE_COUNT messages from NATS"

if [ "$MESSAGE_COUNT" -ge "$MIN_MESSAGES" ]; then
    echo "SUCCESS: Received $MESSAGE_COUNT messages (minimum required: $MIN_MESSAGES)"
else
    echo "FAILURE: Received only $MESSAGE_COUNT messages (minimum required: $MIN_MESSAGES)"
    exit 1
fi

echo "Script completed successfully!"

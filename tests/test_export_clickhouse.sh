#!/bin/bash
# Pre-requisites:
# - docker
# - jq

# Exit on error
set -e

# echo "Clean previous test data..."
# rm -f /tmp/clickhouse-for-glances_cpu.csv

echo "Stop previous ClickHouse container..."
docker stop clickhouse-for-glances || true
docker rm clickhouse-for-glances || true

# Start ClickHouse and create the glances database
echo "Starting ClickHouse container..."
docker run -d \
    --name clickhouse-for-glances \
    -p 8123:8123 \
    -p 9000:9000 \
    --ulimit nofile=262144:262144 \
    -e CLICKHOUSE_DB=glances \
    -e CLICKHOUSE_DEFAULT_ACCESS_MANAGEMENT=1 \
    -e CLICKHOUSE_USER=default \
    -e CLICKHOUSE_PASSWORD=password \
    clickhouse/clickhouse-server

# Wait for ClickHouse to be ready (10 seconds)
echo "Waiting for ClickHouse to start (~ 10 seconds)..."
sleep 10

# Run glances with export to ClickHouse, stopping after 10 writes
# This will run synchronously now since we're using --stop-after
echo "Glances to export system stats to ClickHouse (duration: ~ 20 seconds)"
.venv/bin/python -m glances --config ./conf/glances.conf --export clickhouse --stop-after 10 --quiet

docker exec clickhouse-for-glances clickhouse-client --database=glances --query="SELECT * FROM cpu FORMAT CSV" > /tmp/clickhouse-for-glances_cpu.csv
.venv/bin/python ./tests-data/tools/csvcheck.py -i /tmp/clickhouse-for-glances_cpu.csv -l 8

# Stop and remove the ClickHouse container
echo "Stopping and removing ClickHouse container..."
docker stop clickhouse-for-glances && docker rm clickhouse-for-glances

echo "Script completed successfully!"

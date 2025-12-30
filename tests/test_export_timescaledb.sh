#!/bin/bash
# Pre-requisites:
# - docker
# - jq

# Exit on error
set -e

echo "Clean previous test data..."
rm -f /tmp/timescaledb-for-glances_cpu.csv

echo "Stop previous TimeScaleDB container..."
docker stop timescaledb-for-glances || true
docker rm timescaledb-for-glances || true

echo "Starting TimeScaleDB container..."
docker run -d \
    --name timescaledb-for-glances \
    -p 5432:5432 \
    -e POSTGRES_PASSWORD=password \
    timescale/timescaledb-ha:pg17

# Wait for InfluxDB to be ready (15 seconds)
echo "Waiting for TimeScaleDB to start (~ 15 seconds)..."
sleep 15

# Create the glances database
echo "Creating 'glances' database..."
docker exec timescaledb-for-glances psql -d "postgres://postgres:password@localhost/postgres" -c "CREATE DATABASE glances;"

# Run glances with export to TimescaleDB, stopping after 10 writes
# This will run synchronously now since we're using --stop-after
echo "Glances to export system stats to TimescaleDB (duration: ~ 20 seconds)"
.venv/bin/python -m glances --config ./conf/glances.conf --export timescaledb --stop-after 10 --quiet

docker exec timescaledb-for-glances psql -d "postgres://postgres:password@localhost/glances" -c "SELECT * from cpu;" --csv > /tmp/timescaledb-for-glances_cpu.csv
.venv/bin/python ./tests-data/tools/csvcheck.py -i /tmp/timescaledb-for-glances_cpu.csv -l 9

# Stop and remove the TimescaleDB container
echo "Stopping and removing TimescaleDB container..."
docker stop timescaledb-for-glances && docker rm timescaledb-for-glances

echo "Script completed successfully!"

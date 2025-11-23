#!/bin/bash
# Pre-requisites:
# - docker
# - jq

# Exit on error
set -e

echo "Starting InfluxDB version 1 container..."
docker run -d --name influxdb-v1-for-glances \
    -p 8086:8086 \
    influxdb:1.12

# Wait for InfluxDB to be ready (retry for up to 30 seconds)
echo "Waiting for InfluxDB to start..."
for i in {1..30}; do
    if curl -s "http://localhost:8086/ping" > /dev/null; then
        echo "InfluxDB is up and running!"
        break
    fi

    if [ "$i" -eq 30 ]; then
        echo "Error: Timed out waiting for InfluxDB to start"
        docker stop influxdb-v1-for-glances
        docker rm influxdb-v1-for-glances
        exit 1
    fi

    echo "Waiting for InfluxDB to start... ($i/30)"
    sleep 1
done

# Create the glances database
echo "Creating 'glances' database..."
docker exec influxdb-v1-for-glances influx -execute 'DROP DATABASE glances'
docker exec influxdb-v1-for-glances influx -execute 'CREATE DATABASE glances'

# Run glances with export to InfluxDB, stopping after 10 writes
# This will run synchronously now since we're using --stop-after
echo "Glances to export system stats to InfluxDB (duration: ~ 20 seconds)"
.venv/bin/python -m glances --export influxdb --stop-after 10 --quiet

echo "Checking if Glances data was successfully exported to InfluxDB..."
# Query to check if data exists in the glances database
MEASUREMENT_COUNT=$(docker exec influxdb-v1-for-glances influx -database 'glances' -format json -execute 'SHOW MEASUREMENTS' | jq '.results[0].series[0].values' | jq length)
if [ "$MEASUREMENT_COUNT" -eq 0 ]; then
    echo "Error: No Glances measurement found in the InfluxDB database"
    docker stop influxdb-v1-for-glances
    docker rm influxdb-v1-for-glances
    exit 1
else
    echo "Success! Found $MEASUREMENT_COUNT measurements in the Glances database."
fi

# Query to check if data exists in the glances database
SERIE_COUNT=$(docker exec influxdb-v1-for-glances influx -database 'glances' -format json -execute 'SELECT * FROM cpu' | jq '.results[0].series[0].values' | jq length)
if [ "$SERIE_COUNT" -eq 9 ]; then
    echo "Success! Found $SERIE_COUNT series in the Glances database (CPU plugin)."
else
    echo "Error: Found $SERIE_COUNT series instead of 9"
    docker stop influxdb-v1-for-glances
    docker rm influxdb-v1-for-glances
    exit 1
fi

# Stop and remove the InfluxDB container
echo "Stopping and removing InfluxDB container..."
docker stop influxdb-v1-for-glances
docker rm influxdb-v1-for-glances

echo "Script completed successfully!"

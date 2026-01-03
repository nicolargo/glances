#!/bin/bash
# Pre-requisites:
# - docker
# - jq

# Exit on error
set -e

echo "Starting InfluxDB version 3 (Core) container..."
docker run -d --name influxdb-v3-for-glances \
    -p 8181:8181 \
    influxdb:3-core --node-id host01 --object-store memory

# Wait for InfluxDB to be ready (5 seconds)
echo "Waiting for InfluxDB to start..."
sleep 5

# Create the token
echo "Creating InfluxDB token..."
TOKEN_RETURN=$(docker exec influxdb-v3-for-glances influxdb3 create token --admin)
TOKEN=$(echo -n "$TOKEN_RETURN" | awk '{ print $6 }')
echo "Token: $TOKEN"

# Create a new configuration for the test
echo "Creating a temporary Glances configuration file with the token in /tmp/glances.conf..."
sed "s/PUT_YOUR_INFLUXDB3_TOKEN_HERE/$TOKEN/g" ./conf/glances.conf > /tmp/glances.conf

# Create the glances database
echo "Creating 'glances' database..."
docker exec -e "INFLUXDB3_AUTH_TOKEN=$TOKEN" influxdb-v3-for-glances influxdb3 create database glances
docker exec -e "INFLUXDB3_AUTH_TOKEN=$TOKEN" influxdb-v3-for-glances influxdb3 show databases

# Get the list of tables in the glances database after creation
TABLES_INIT=$(docker exec -e "INFLUXDB3_AUTH_TOKEN=$TOKEN" influxdb-v3-for-glances influxdb3 query --database glances --format json 'SHOW TABLES')
TABLES_INIT_COUNT=$(echo "$TABLES_INIT" | jq length)

# Run glances with export to InfluxDB, stopping after 10 writes
# This will run synchronously now since we're using --stop-after
echo "Glances to export system stats to InfluxDB (duration: ~ 20 seconds)"
.venv/bin/python -m glances --config /tmp/glances.conf --export influxdb3 --stop-after 10 --quiet

echo "Checking if Glances data was successfully exported to InfluxDB..."
# Query to check if data exists in the glances database
TABLES=$(docker exec -e "INFLUXDB3_AUTH_TOKEN=$TOKEN" influxdb-v3-for-glances influxdb3 query --database glances --format json 'SHOW TABLES')
TABLES_COUNT=$(echo "$TABLES" | jq length)
if [ "$TABLES_COUNT" -eq "$TABLES_INIT_COUNT" ]; then
    echo "Error: No Glances measurement found in the InfluxDB database"
    docker stop influxdb-v3-for-glances
    docker rm influxdb-v3-for-glances
    exit 1
else
    echo "Success! Found $TABLES_COUNT measurements in the Glances database."
fi

# Query to check if data exists in the glances database
SERIE=$(docker exec -e "INFLUXDB3_AUTH_TOKEN=$TOKEN" influxdb-v3-for-glances influxdb3 query --database glances --format json 'SELECT * FROM cpu')
SERIE_COUNT=$(echo "$SERIE" | jq length)
if [ "$SERIE_COUNT" -eq 9 ]; then
    echo "Success! Found $SERIE_COUNT series in the Glances database (CPU plugin)."
else
    echo "Error: Found $SERIE_COUNT series instead of 9"
    docker stop influxdb-v3-for-glances
    docker rm influxdb-v3-for-glances
    exit 1
fi

# Stop and remove the InfluxDB container
echo "Stopping and removing InfluxDB container..."
docker stop influxdb-v3-for-glances
docker rm influxdb-v3-for-glances

# Remove the temporary configuration file
rm -f /tmp/glances.conf

echo "Script completed successfully!"

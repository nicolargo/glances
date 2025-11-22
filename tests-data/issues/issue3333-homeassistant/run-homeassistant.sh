#!/bin/sh

docker run -d \
    --name homeassistant \
    --privileged \
    --restart=unless-stopped \
    -e TZ=Europe/Paris \
    -v ./config:/config \
    -v /run/dbus:/run/dbus:ro \
    --network=host \
    ghcr.io/home-assistant/home-assistant:stable

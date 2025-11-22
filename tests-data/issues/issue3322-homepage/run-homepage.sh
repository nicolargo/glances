#!/bin/sh

docker run --rm \
    --name homepage \
    -p 3000:3000 \
    -e HOMEPAGE_ALLOWED_HOSTS=localhost:3000,0.0.0.0:3000 \
    -v ./config:/app/config \
    -v /var/run/docker.sock:/var/run/docker.sock \
    ghcr.io/gethomepage/homepage:latest

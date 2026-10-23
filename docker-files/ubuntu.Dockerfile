#
# Glances Dockerfile (based on Ubuntu)
#
# https://github.com/nicolargo/glances
#

# WARNING: the versions should be set.
# Ex: Python 3.12 for Ubuntu 24.04
# Note: ENV is for future running containers. ARG for building your Docker image.

ARG IMAGE_VERSION=26.04
ARG PYTHON_VERSION=3.14

##############################################################################
# Base layer to be used for building dependencies and the release images
# Pinned by digest (the multi-arch manifest list of the tag); Dependabot
# bumps it (security audit 2026-10-17, S-3).
FROM ubuntu:${IMAGE_VERSION}@sha256:c098726dd9b9733f3e885f8de0ef375206a311b0a317eadc40d347b1115fb944 AS base
ARG DEBIAN_FRONTEND=noninteractive

RUN <<EOR
set -e

# Upgrade the system: this stage is the one the release images are built on
apt-get update
apt-get upgrade -y

# Install the minimal set of packages
apt-get install -y --no-install-recommends \
    python3 \
    curl \
    lm-sensors \
    smartmontools \
    net-tools \
    tzdata

# Clean the system
apt-get clean
rm -rf /var/lib/apt/lists/*
EOR

##############################################################################
# BUILD Stages
##############################################################################
# BUILD: Base image shared by all build images
FROM base AS build
ARG PYTHON_VERSION
ARG DEBIAN_FRONTEND=noninteractive

RUN <<EOR
set -e

# Upgrade the system
apt-get update
apt-get upgrade -y

# Install deps
apt-get install -y --no-install-recommends \
    python3-dev \
    python3-venv \
    python3-pip \
    python3-wheel \
    libzmq5 \
    musl-dev \
    build-essential

# Clean the system
apt-get clean
rm -rf /var/lib/apt/lists/*
EOR

# Install build-time dependencies
RUN python3 -m venv --without-pip venv

COPY pyproject.toml docker-requirements.txt all-requirements.txt ./

##############################################################################
# BUILD: Install the minimal image deps
FROM build AS buildminimal
ARG PYTHON_VERSION

RUN python3 -m pip install --target="/venv/lib/python${PYTHON_VERSION}/site-packages" \
    -r docker-requirements.txt

##############################################################################
# BUILD: Install all the deps
FROM build AS buildfull
ARG PYTHON_VERSION

RUN python3 -m pip install --target="/venv/lib/python${PYTHON_VERSION}/site-packages" \
    -r all-requirements.txt

##############################################################################
# RELEASE Stages
##############################################################################
# Base image shared by all releases
FROM base AS release
ARG PYTHON_VERSION

# Copy Glances source code and config file
COPY ./docker-compose/glances.conf /etc/glances/glances.conf
COPY ./glances/. /app/glances/

# Copy binary and update PATH
COPY docker-bin.sh /usr/local/bin/glances
RUN chmod a+x /usr/local/bin/glances
ENV PATH="/venv/bin:$PATH"

# EXPOSE PORT (REST API / WebUI)
EXPOSE 61208

# Liveness probe for `docker run` users (docker-compose defines its own)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:61208/healthz || exit 1

# Add glances user
# NOTE: If used, the Glances Docker plugin do not work...
# UID and GUID 1000 are already configured for the ubuntu user
# Create anew one with UID and GUID 1001
# RUN groupadd -g 1001 glances && \
#     useradd -u 1001 -g glances glances && \
#     chown -R glances:glances /app

# Define default command.
WORKDIR /app
ENV PYTHON_VERSION=${PYTHON_VERSION}
CMD ["/bin/sh", "-c", "/venv/bin/python${PYTHON_VERSION} -m glances ${GLANCES_OPT}"]

################################################################################
# RELEASE: minimal
FROM release AS minimal
ARG PYTHON_VERSION

COPY --from=buildMinimal /venv /venv

# USER glances

################################################################################
# RELEASE: full
FROM release AS full
ARG PYTHON_VERSION

RUN <<EOR
set -e

apt-get update
apt-get install -y --no-install-recommends \
    libzmq5 \
    libvirt-clients

# Clean the system
apt-get clean
rm -rf /var/lib/apt/lists/*
EOR

COPY --from=buildfull /venv /venv

# USER glances

################################################################################
# RELEASE: dev - to be compatible with CI
FROM full AS dev
ARG PYTHON_VERSION

# Add the specific logger configuration file for Docker dev
# All logs will be forwarded to stdout
COPY ./docker-files/docker-logger.json /app
ENV LOG_CFG=/app/docker-logger.json

# USER glances

WORKDIR /app
ENV PYTHON_VERSION=${PYTHON_VERSION}
CMD ["/bin/sh", "-c", "/venv/bin/python${PYTHON_VERSION} -m glances ${GLANCES_OPT}"]

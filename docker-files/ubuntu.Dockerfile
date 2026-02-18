#
# Glances Dockerfile (based on Ubuntu)
#
# https://github.com/nicolargo/glances
#

# WARNING: the versions should be set.
# Ex: Python 3.12 for Ubuntu 24.04
# Note: ENV is for future running containers. ARG for building your Docker image.

ARG IMAGE_VERSION=24.04
ARG PYTHON_VERSION=3.12

##############################################################################
# Base layer to be used for building dependencies and the release images
FROM ubuntu:${IMAGE_VERSION} AS base
ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    python3 \
    curl \
    lm-sensors \
    wireless-tools \
    smartmontools \
    net-tools \
    tzdata \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

##############################################################################
# BUILD Stages
##############################################################################
# BUILD: Base image shared by all build images
FROM base AS build
ARG PYTHON_VERSION
ARG DEBIAN_FRONTEND=noninteractive

# Upgrade the system
RUN apt-get update \
  && apt-get upgrade -y

# Install build-time dependencies
RUN apt-get install -y --no-install-recommends \
    python3-dev \
    python3-venv \
    python3-pip \
    python3-wheel \
    libzmq5 \
    musl-dev \
    build-essential

RUN apt-get clean \
  && rm -rf /var/lib/apt/lists/*

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

# EXPOSE PORT (XMLRPC / WebUI)
EXPOSE 61209 61208

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

RUN apt-get update \
  && apt-get install -y --no-install-recommends \ 
    libzmq5 \
    libvirt-clients \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

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

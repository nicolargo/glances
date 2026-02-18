#
# Glances Dockerfile (based on Alpine)
#
# https://github.com/nicolargo/glances
#

# Note: ENV is for future running containers. ARG for building your Docker image.

# WARNING: the Alpine image version and Python version should be set.
# Alpine 3.18 tag is a link to the latest 3.18.x version.
# Be aware that if you change the Alpine version, you may have to change the Python version.
ARG IMAGE_VERSION=3.23
ARG PYTHON_VERSION=3.12

##############################################################################
# Base layer to be used for building dependencies and the release images
FROM alpine:${IMAGE_VERSION} AS base

# Upgrade the system
RUN apk update \
  && apk upgrade --no-cache

# Install the minimal set of packages
RUN apk add --no-cache \
  python3 \
  curl \
  lm-sensors \
  wireless-tools \
  smartmontools \
  iputils \
  tzdata

##############################################################################
# BUILD Stages
##############################################################################
# BUILD: Base image shared by all build images
FROM base AS build
ARG PYTHON_VERSION

RUN apk add --no-cache \
  python3-dev \
  py3-pip \
  py3-wheel \
  musl-dev \
  linux-headers \
  build-base \
  libzmq \
  zeromq-dev \
  # Required for 'cryptography' dependency of optional requirement 'cassandra-driver' \
  # Refer: https://cryptography.io/en/latest/installation/#alpine \
  # `git` required to clone cargo crates (dependencies)
  git \
  gcc \
  cargo \
  pkgconfig \
  libffi-dev \
  openssl-dev \
  cmake
  # for cmake: Issue:  https://github.com/nicolargo/glances/issues/2735

RUN python${PYTHON_VERSION} -m venv venv-build
RUN /venv-build/bin/python${PYTHON_VERSION} -m pip install --upgrade pip

RUN python${PYTHON_VERSION} -m venv --without-pip venv

COPY pyproject.toml docker-requirements.txt all-requirements.txt ./

##############################################################################
# BUILD: Install the minimal image deps
FROM build AS buildminimal
ARG PYTHON_VERSION

RUN /venv-build/bin/python${PYTHON_VERSION} -m pip install --target="/venv/lib/python${PYTHON_VERSION}/site-packages" \
    -r docker-requirements.txt

##############################################################################
# BUILD: Install all the deps
FROM build AS buildfull
ARG PYTHON_VERSION

# Required for optional dependency cassandra-driver
ARG CASS_DRIVER_NO_CYTHON=1
# See issue 2368
ARG CARGO_NET_GIT_FETCH_WITH_CLI=true

RUN /venv-build/bin/python${PYTHON_VERSION} -m pip install --target="/venv/lib/python${PYTHON_VERSION}/site-packages" \
    -r all-requirements.txt

##############################################################################
# RELEASE Stages
##############################################################################
# Base image shared by all releases
FROM base AS release
ARG PYTHON_VERSION

# Copy source code and config file
COPY ./docker-compose/glances.conf /etc/glances/glances.conf
COPY ./glances/. /app/glances/

# Copy binary and update PATH
COPY docker-bin.sh /usr/local/bin/glances
RUN chmod a+x /usr/local/bin/glances
ENV PATH="/venv/bin:$PATH"

# EXPOSE PORT (XMLRPC / WebUI)
EXPOSE 61209 61208

# Add glances user
# RUN addgroup -g 1000 glances && \
#     adduser -D -u 1000 -G glances glances && \
#     chown -R glances:glances /app

# Define default command.
WORKDIR /app
ENV PYTHON_VERSION=${PYTHON_VERSION}
CMD ["/bin/sh", "-c", "/venv/bin/python${PYTHON_VERSION} -m glances ${GLANCES_OPT}"]

################################################################################
# RELEASE: minimal
FROM release AS minimal

COPY --from=buildminimal /venv /venv

# USER glances

################################################################################
# RELEASE: full
FROM release AS full

RUN apk add --no-cache \
  libzmq \
  libvirt-client

COPY --from=buildfull /venv /venv

# USER glances

################################################################################
# RELEASE: dev - to be compatible with CI
FROM full AS dev

# Add the specific logger configuration file for Docker dev
# All logs will be forwarded to stdout
COPY ./docker-files/docker-logger.json /app
ENV LOG_CFG=/app/docker-logger.json

# USER glances

WORKDIR /app
ENV PYTHON_VERSION=${PYTHON_VERSION}
CMD ["/bin/sh", "-c", "/venv/bin/python${PYTHON_VERSION} -m glances ${GLANCES_OPT}"]

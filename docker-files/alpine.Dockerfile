#
# Glances Dockerfile (based on Alpine)
#
# https://github.com/nicolargo/glances
#

# Note: ENV is for future running containers. ARG for building your Docker image.

# WARNING: the Alpine image version and Python version should be set.
# Alpine 3.18 tag is a link to the latest 3.18.x version.
# Be aware that if you change the Alpine version, you may have to change the Python version.

ARG IMAGE_VERSION=3.20
ARG PYTHON_VERSION=3.12

##############################################################################
# Base layer to be used for building dependencies and the release images
FROM alpine:${IMAGE_VERSION} as base

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
FROM base as build
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
  cmake # Issue:  https://github.com/nicolargo/glances/issues/2735

RUN python${PYTHON_VERSION} -m venv venv-build
RUN /venv-build/bin/python${PYTHON_VERSION} -m pip install --upgrade pip

RUN python${PYTHON_VERSION} -m venv venv-build
RUN /venv-build/bin/python${PYTHON_VERSION} -m pip install --upgrade pip

RUN python${PYTHON_VERSION} -m venv --without-pip venv

COPY requirements.txt docker-requirements.txt webui-requirements.txt optional-requirements.txt ./

##############################################################################
# BUILD: Install the minimal image deps
FROM build as buildMinimal
ARG PYTHON_VERSION

RUN /venv-build/bin/python${PYTHON_VERSION} -m pip install --target="/venv/lib/python${PYTHON_VERSION}/site-packages" \
    -r requirements.txt \
    -r docker-requirements.txt \
    -r webui-requirements.txt

##############################################################################
# BUILD: Install all the deps
FROM build as buildFull
ARG PYTHON_VERSION

# Required for optional dependency cassandra-driver
ARG CASS_DRIVER_NO_CYTHON=1
# See issue 2368
ARG CARGO_NET_GIT_FETCH_WITH_CLI=true

RUN /venv-build/bin/python${PYTHON_VERSION} -m pip install --target="/venv/lib/python${PYTHON_VERSION}/site-packages" \
    -r requirements.txt \
    -r optional-requirements.txt

##############################################################################
# RELEASE Stages
##############################################################################
# Base image shared by all releases
FROM base as release
ARG PYTHON_VERSION

# Copy source code and config file
COPY ./docker-compose/glances.conf /etc/glances/glances.conf
COPY ./glances/. /app/glances/

# Copy binary and update PATH
COPY docker-bin.sh /usr/local/bin/glances
RUN chmod a+x /usr/local/bin/glances
ENV PATH="/venv/bin:$PATH"

# Copy binary and update PATH
COPY docker-bin.sh /usr/local/bin/glances
RUN chmod a+x /usr/local/bin/glances
ENV PATH="/venv/bin:$PATH"

# EXPOSE PORT (XMLRPC / WebUI)
EXPOSE 61209 61208

# Define default command.
WORKDIR /app
CMD /venv/bin/python3 -m glances $GLANCES_OPT

################################################################################
# RELEASE: minimal
FROM release as minimal

COPY --from=buildMinimal /venv /venv

################################################################################
# RELEASE: full
FROM release as full

RUN apk add --no-cache libzmq

COPY --from=buildFull /venv /venv

################################################################################
# RELEASE: dev - to be compatible with CI
FROM full as dev

# Forward access and error logs to Docker's log collector
RUN ln -sf /dev/stdout /tmp/glances-root.log \
    && ln -sf /dev/stderr /var/log/error.log
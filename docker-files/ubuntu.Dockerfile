#
# Glances Dockerfile (based on Ubuntu)
#
# https://github.com/nicolargo/glances
#

# WARNING: the versions should be set.
# Ex: Python 3.10 for Ubuntu 22.04
# Note: ENV is for future running containers. ARG for building your Docker image.

ARG IMAGE_VERSION=23.04
ARG PYTHON_VERSION=3.11

##############################################################################
# Base layer to be used for building dependencies and the release images
FROM ubuntu:${IMAGE_VERSION} as base
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
FROM base as build
ARG PYTHON_VERSION
ARG DEBIAN_FRONTEND=noninteractive

# Install build-time dependencies
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    python3-dev \
    python3-venv \
    python3-pip \
    python3-wheel \
    libzmq5 \
    musl-dev \
    build-essential \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

RUN python${PYTHON_VERSION} -m venv --without-pip venv

COPY requirements.txt docker-requirements.txt webui-requirements.txt optional-requirements.txt ./

##############################################################################
# BUILD: Install the minimal image deps
FROM build as buildMinimal

RUN python${PYTHON_VERSION} -m pip install --target="/venv/lib/python${PYTHON_VERSION}/site-packages" \
    # Note: requirements.txt is include by dep
    -r docker-requirements.txt \
    -r webui-requirements.txt

##############################################################################
# BUILD: Install all the deps
FROM build as buildFull

RUN python${PYTHON_VERSION} -m pip install --target="/venv/lib/python${PYTHON_VERSION}/site-packages" \
    # Note: requirements.txt is include by dep
    -r optional-requirements.txt

##############################################################################
# RELEASE Stages
##############################################################################
# Base image shared by all releases
FROM base as release

# Copy Glances source code and config file
COPY ./docker-compose/glances.conf /etc/glances.conf
COPY /glances /app/glances

# Copy binary and update PATH
COPY docker-bin.sh /usr/local/bin/glances
RUN chmod a+x /usr/local/bin/glances
ENV PATH="/venv/bin:$PATH"

# EXPOSE PORT (XMLRPC / WebUI)
EXPOSE 61209 61208

# Define default command.
WORKDIR /app
CMD /venv/bin/python3 -m glances -C /etc/glances.conf $GLANCES_OPT

################################################################################
# RELEASE: minimal
FROM release as minimal

COPY --from=buildMinimal /venv /venv

################################################################################
# RELEASE: full
FROM release as full

RUN apt-get update \
  && apt-get install -y --no-install-recommends libzmq5 \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

COPY --from=buildFull /venv /venv

################################################################################
# RELEASE: dev - to be compatible with CI
FROM full as dev

# Forward access and error logs to Docker's log collector
RUN ln -sf /dev/stdout /tmp/glances-root.log \
    && ln -sf /dev/stderr /var/log/error.log

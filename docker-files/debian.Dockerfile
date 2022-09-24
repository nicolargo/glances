#
# Glances Dockerfile (based on Debian)
#
# https://github.com/nicolargo/glances
#

# WARNING: the version should be set.
# Ex: Python 3.10 for  3.10-slim-buster
# Note: ENV is for future running containers. ARG for building your Docker image.

ARG IMAGE_VERSION=3.10-slim-buster
ARG PYTHON_VERSION=3.10
FROM python:${IMAGE_VERSION} as build
ARG PYTHON_VERSION

# Install package
RUN apt-get update && \
  apt-get install -y --no-install-recommends \
  python3-dev \
  curl \
  build-essential \
  lm-sensors \
  wireless-tools \
  smartmontools \
  iputils-ping && \
  apt-get clean && rm -rf /var/lib/apt/lists/*

##############################################################################
# Install the dependencies beforehand to make them cacheable

FROM build as buildRequirements
ARG PYTHON_VERSION
COPY requirements.txt .
RUN pip3 install --no-cache-dir --user -r requirements.txt
# As minimal image we want to monitor others docker containers
RUN pip3 install --no-cache-dir --user docker

# Force install otherwise it could be cached without rerun
ARG CHANGING_ARG
RUN pip3 install --no-cache-dir --user glances

##############################################################################

FROM build as buildOptionalRequirements
ARG PYTHON_VERSION

COPY requirements.txt .
COPY optional-requirements.txt .
RUN CASS_DRIVER_NO_CYTHON=1 pip3 install --no-cache-dir --user -r optional-requirements.txt

##############################################################################
# full image
##############################################################################

FROM build as full
ARG PYTHON_VERSION

COPY --from=buildRequirements /root/.local/bin /usr/local/bin/
COPY --from=buildRequirements /root/.local/lib/python${PYTHON_VERSION}/site-packages /usr/local/lib/python${PYTHON_VERSION}/site-packages/
COPY --from=buildOptionalRequirements /root/.local/lib/python${PYTHON_VERSION}/site-packages /usr/local/lib/python${PYTHON_VERSION}/site-packages/
COPY ./docker-compose/glances.conf /etc/glances.conf

# EXPOSE PORT (XMLRPC / WebUI)
EXPOSE 61209 61208

WORKDIR /glances

# Define default command.
CMD python3 -m glances -C /etc/glances.conf $GLANCES_OPT

##############################################################################
# minimal image
##############################################################################

# Create running images without any building dependency
FROM python:${IMAGE_VERSION} as minimal
ARG PYTHON_VERSION

RUN apt-get update && \
  apt-get install -y --no-install-recommends \
  curl              \
  lm-sensors        \
  wireless-tools    \
  smartmontools     \
  iputils-ping && \
  apt-get clean && rm -rf /var/lib/apt/lists/*

COPY --from=buildRequirements /root/.local/bin /usr/local/bin/
COPY --from=buildRequirements /root/.local/lib/python${PYTHON_VERSION}/site-packages /usr/local/lib/python${PYTHON_VERSION}/site-packages/
COPY ./docker-compose/glances.conf /etc/glances.conf

# EXPOSE PORT (XMLRPC)
EXPOSE 61209

# Define default command.
CMD python3 -m glances -C /etc/glances.conf $GLANCES_OPT

##############################################################################
# dev image
##############################################################################

FROM full as dev
ARG PYTHON_VERSION

COPY --from=buildRequirements /root/.local/bin /usr/local/bin/
COPY --from=buildRequirements /root/.local/lib/python${PYTHON_VERSION}/site-packages /usr/lib/python${PYTHON_VERSION}/site-packages/
COPY --from=buildOptionalRequirements /root/.local/lib/python${PYTHON_VERSION}/site-packages /usr/lib/python${PYTHON_VERSION}/site-packages/
COPY ./docker-compose/glances.conf /etc/glances.conf

# Copy the current Glances source code
COPY . /glances

# EXPOSE PORT (XMLRPC / WebUI)
EXPOSE 61209 61208

# Forward access and error logs to Docker's log collector
RUN ln -sf /dev/stdout /tmp/glances-root.log \
    && ln -sf /dev/stderr /var/log/error.log

WORKDIR /glances

# Define default command.
CMD python3 -m glances -C /etc/glances.conf $GLANCES_OPT

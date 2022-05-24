#
# Glances Dockerfile (based on Alpine)
#
# https://github.com/nicolargo/glances
#

# WARNING: the versions should be set.
# Ex: Python 3.10 for Alpine 3.16
# Note: ENV is for future running containers. ARG for building your Docker image.

ARG IMAGE_VERSION=3.16
ARG PYTHON_VERSION=3.10
FROM alpine:${IMAGE_VERSION} as build
ARG PYTHON_VERSION

RUN apk add --no-cache \
  python3 \
  python3-dev \
  py3-pip \
  py3-wheel \
  musl-dev \
  linux-headers \
  build-base \
  libzmq \
  zeromq-dev \
  curl \
  lm-sensors \
  wireless-tools \
  iputils


FROM build as remoteInstall
ARG PYTHON_VERSION
# Install the dependencies beforehand to make them cacheable
COPY requirements.txt .
RUN pip3 install --no-cache-dir --user -r requirements.txt

# Force install otherwise it could be cached without rerun
ARG CHANGING_ARG
RUN pip3 install --no-cache-dir --user glances[all]


FROM build as additional-packages
ARG PYTHON_VERSION

COPY *requirements.txt ./

RUN CASS_DRIVER_NO_CYTHON=1 pip3 install --no-cache-dir --user -r optional-requirements.txt

##############################################################################
# dev image
##############################################################################

FROM build as dev
ARG PYTHON_VERSION

COPY --from=additional-packages /root/.local/lib/python${PYTHON_VERSION}/site-packages /usr/lib/python${PYTHON_VERSION}/site-packages/
COPY . /glances
COPY ./docker-compose/glances.conf /etc/glances.conf

# EXPOSE PORT (XMLRPC / WebUI)
EXPOSE 61209 61208

WORKDIR /glances

# Define default command.
CMD python3 -m glances -C /etc/glances.conf $GLANCES_OPT

##############################################################################
# minimal image
##############################################################################

#Create running images without any building dependency
FROM alpine:${IMAGE_VERSION} as minimal
ARG PYTHON_VERSION

RUN apk add --no-cache \
  python3 \
  curl \
  lm-sensors \
  wireless-tools \
  iputils

COPY --from=remoteInstall /root/.local/bin /usr/local/bin/
COPY --from=remoteInstall /root/.local/lib/python${PYTHON_VERSION}/site-packages /usr/lib/python${PYTHON_VERSION}/site-packages/
COPY ./docker-compose/glances.conf /etc/glances.conf

# EXPOSE PORT (XMLRPC / WebUI)
EXPOSE 61209 61208

# Define default command.
CMD python3 -m glances -C /etc/glances.conf $GLANCES_OPT

##############################################################################
# full image
##############################################################################

FROM minimal as full
ARG PYTHON_VERSION

COPY --from=additional-packages /root/.local/lib/python${PYTHON_VERSION}/site-packages /usr/lib/python${PYTHON_VERSION}/site-packages/
COPY ./docker-compose/glances.conf /etc/glances.conf

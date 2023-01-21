#
# Glances Dockerfile (based on Ubuntu)
#
# https://github.com/nicolargo/glances
#

# WARNING: the versions should be set.
# Ex: Python 3.10 for Ubuntu 22.04
# Note: ENV is for future running containers. ARG for building your Docker image.

ARG IMAGE_VERSION=12.0.0-base-ubuntu22.04
ARG PYTHON_VERSION=3.10
ARG PIP_MIRROR=https://mirrors.aliyun.com/pypi/simple/
FROM nvidia/cuda:${IMAGE_VERSION} as build

RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    python3 \
    python3-dev \
    python3-pip \
    python3-wheel \
    musl-dev \
    build-essential \
    libzmq5 \
    curl \
    lm-sensors \
    wireless-tools \
    net-tools \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

##############################################################################
# Install the dependencies beforehand to make them cacheable

FROM build as buildRequirements
ARG PYTHON_VERSION
ARG PIP_MIRROR

ARG PIP_MIRROR=https://mirrors.aliyun.com/pypi/simple/

COPY requirements.txt .
RUN python${PYTHON_VERSION} -m pip install --no-cache-dir --user -r requirements.txt -i ${PIP_MIRROR}

# Minimal means no webui, but it break what is done previously (see #2155)
# So install the webui requirements...
COPY webui-requirements.txt .
RUN python${PYTHON_VERSION} -m pip install --no-cache-dir --user -r webui-requirements.txt -i ${PIP_MIRROR}

# As minimal image we want to monitor others docker containers
RUN python${PYTHON_VERSION} -m pip install --no-cache-dir --user docker -i ${PIP_MIRROR}

# Force install otherwise it could be cached without rerun
ARG CHANGING_ARG
RUN python${PYTHON_VERSION} -m pip install --no-cache-dir --user glances -i ${PIP_MIRROR}

##############################################################################

FROM build as buildOptionalRequirements
ARG PYTHON_VERSION
ARG PIP_MIRROR

COPY requirements.txt .
COPY optional-requirements.txt .
RUN CASS_DRIVER_NO_CYTHON=1 pip3 install --no-cache-dir --user -r optional-requirements.txt -i ${PIP_MIRROR}

##############################################################################
# full image
##############################################################################

FROM build as full
ARG PYTHON_VERSION

COPY --from=buildRequirements /root/.local/bin /root/.local/bin/
COPY --from=buildRequirements /root/.local/lib/python${PYTHON_VERSION}/site-packages /root/.local/lib/python${PYTHON_VERSION}/site-packages/
COPY --from=buildOptionalRequirements /root/.local/lib/python${PYTHON_VERSION}/site-packages /root/.local/lib/python${PYTHON_VERSION}/site-packages/
COPY ./docker-compose/glances.conf /etc/glances.conf

# EXPOSE PORT (XMLRPC / WebUI)
EXPOSE 61209 61208

# Define default command.
WORKDIR /glances
CMD python3 -m glances -C /etc/glances.conf $GLANCES_OPT

##############################################################################
# minimal image
##############################################################################

# Create running images without any building dependency
FROM nvidia/cuda:${IMAGE_VERSION} as minimal
ARG PYTHON_VERSION

ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Shanghai

RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    python3 \
    python3-packaging \
    python3-dateutil \
    python3-requests \
    curl \
    lm-sensors \
    wireless-tools \
    net-tools \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

COPY --from=buildRequirements /root/.local/bin /root/.local/bin/
COPY --from=buildRequirements /root/.local/lib/python${PYTHON_VERSION}/site-packages /root/.local/lib/python${PYTHON_VERSION}/site-packages/
COPY ./docker-compose/glances.conf /etc/glances.conf

# EXPOSE PORT (XMLRPC / WebUI)
EXPOSE 61209 61208

# Define default command.
WORKDIR /glances
CMD python3 -m glances -C /etc/glances.conf $GLANCES_OPT

##############################################################################
# dev image
##############################################################################

FROM full as dev
ARG PYTHON_VERSION

COPY --from=buildRequirements /root/.local/bin /root/.local/bin/
COPY --from=buildRequirements /root/.local/lib/python${PYTHON_VERSION}/site-packages /root/.local/lib/python${PYTHON_VERSION}/site-packages/
COPY --from=buildOptionalRequirements /root/.local/lib/python${PYTHON_VERSION}/site-packages /root/.local/lib/python${PYTHON_VERSION}/site-packages/
COPY ./docker-compose/glances.conf /etc/glances.conf

# Copy the current Glances source code
COPY . /glances

# EXPOSE PORT (XMLRPC / WebUI)
EXPOSE 61209 61208

# Forward access and error logs to Docker's log collector
RUN ln -sf /dev/stdout /tmp/glances-root.log \
    && ln -sf /dev/stderr /var/log/error.log

# Define default command.
WORKDIR /glances
CMD python3 -m glances -C /etc/glances.conf $GLANCES_OPT

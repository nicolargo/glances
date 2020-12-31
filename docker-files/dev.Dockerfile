#
# Glances Dockerfile (based on Ubuntu)
#
# https://github.com/nicolargo/glances
#

ARG ARCH=
FROM ${ARCH}python:3-buster

# Install package
# Must used calibre package to be able to run external module
ENV DEBIAN_FRONTEND noninteractive
RUN \
  apt-get update           && \
  apt-get install -y          \
  curl              \
  gcc               \
  git \
  lm-sensors        \
  wireless-tools    \
  iputils-ping && \
  rm -rf /var/lib/apt/lists/*

RUN pip install psutil bottle

COPY . /glances

# Define working directory
WORKDIR /glances

RUN CASS_DRIVER_NO_CYTHON=1 pip install -r optional-requirements.txt

# EXPOSE PORT (XMLRPC / WebUI)
EXPOSE 61209 61208

# Define default command.
CMD python3 -m glances -C /glances/conf/glances.conf $GLANCES_OPT

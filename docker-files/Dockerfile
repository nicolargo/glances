#
# Glances Dockerfile (based on Ubuntu)
#
# https://github.com/nicolargo/glances
#

ARG ARCH=
FROM ${ARCH}python:3-slim-buster

# Install package
# Must used calibre package to be able to run external module
ENV DEBIAN_FRONTEND noninteractive
RUN \
  apt-get update           && \
  apt-get install -y          \
  curl              \
  gcc               \
  lm-sensors        \
  wireless-tools    \
  iputils-ping && \
  rm -rf /var/lib/apt/lists/*

# Force rebuild otherwise it could be cached without rerun
ARG VCS_REF
RUN pip install glances[all]

# Define working directory.
WORKDIR /glances

# EXPOSE PORT (XMLRPC / WebUI)
EXPOSE 61209 61208

# Define default command.
CMD python3 -m glances -C /glances/conf/glances.conf $GLANCES_OPT

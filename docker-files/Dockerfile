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
            libzmq3-dev       \
            iputils-ping && \
  rm -rf /var/lib/apt/lists/*

ARG VERSION
## Install glances
## If version is dev will use git checkout
RUN if [  "$VERSION" = "dev" ] ; then \
    echo Installing dev branch of glances from git; \
    apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/* ; \
    git clone -b develop https://github.com/nicolargo/glances.git ; \
    pip3 install -r glances/optional-requirements.txt ; \
  else \
    echo Installing glances from pip; \
    pip3 install glances[all]; \
  fi

# Define working directory.
WORKDIR /glances

# EXPOSE PORT (XMLRPC / WebUI)
EXPOSE 61209 61208

# Define default command.
CMD python3 -m glances -C /glances/conf/glances.conf $GLANCES_OPT

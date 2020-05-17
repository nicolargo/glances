#
# Glances Dockerfile (based on Ubuntu)
#
# https://github.com/nicolargo/glances
#

# Pull base image.
FROM ubuntu:20.04


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
            iputils-ping      \
            python3-pip       \
            python3-dev    && \
  rm -rf /var/lib/apt/lists/*

## Instal glances
RUN \
  pip3 install --upgrade pip                                                                                 && \
  pip3 install setuptools                                                                                       \
               glances[action,batinfo,browser,cpuinfo,docker,export,folders,gpu,graph,ip,raid,snmp,web,wifi]    \
               glances

# Define working directory.
WORKDIR /glances

# EXPOSE PORT (For XMLRPC)
EXPOSE 61209

# EXPOSE PORT (For Web UI)
EXPOSE 61208

# Define default command.
CMD python3 -m glances -C /glances/conf/glances.conf $GLANCES_OPT

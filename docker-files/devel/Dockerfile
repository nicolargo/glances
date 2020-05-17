#
# Glances Dockerfile based on Ubuntu OS
#
# https://github.com/nicolargo/glances
#

# Pull base image.
FROM ubuntu:20.04

# Install Glances (develop branch)
RUN apt-get update && apt-get -y install curl iputils-ping && rm -rf /var/lib/apt/lists/*
RUN curl -L https://raw.githubusercontent.com/nicolargo/glancesautoinstall/master/install-develop.sh | /bin/bash && rm -rf /var/lib/apt/lists/*


# Define working directory.
WORKDIR /glances

# EXPOSE PORT (For XMLRPC)
EXPOSE 61209

# EXPOSE PORT (For Web UI)
EXPOSE 61208

# Define default command.
CMD python -m glances -C /glances/conf/glances.conf $GLANCES_OPT

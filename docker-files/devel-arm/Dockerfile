#
# Glances Dockerfile for ARM
#
# https://github.com/nicolargo/glances
#

# Pull base image.
FROM alpine

# Install Glances (develop branch)
RUN apk add python py2-psutil py2-bottle
RUN apk add git
RUN git clone https://github.com/nicolargo/glances.git
RUN git checkout develop

# Define working directory.
WORKDIR /glances

# EXPOSE PORT (For XMLRPC)
EXPOSE 61209

# EXPOSE PORT (For Web UI)
EXPOSE 61208

# Define default command.
CMD python -m glances -C /glances/conf/glances.conf $GLANCES_OPT

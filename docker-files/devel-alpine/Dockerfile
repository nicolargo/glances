#
# Glances Dockerfile based on Alpine OS
#
# https://github.com/nicolargo/glances
#

# Pull base image.
FROM alpine

# Install Glances (develop branch)
RUN apk add python py2-psutil py2-bottle
RUN apk add git
RUN git clone -b develop https://github.com/nicolargo/glances.git

# Define working directory.
WORKDIR /glances

# EXPOSE PORT (For XMLRPC)
EXPOSE 61209

# EXPOSE PORT (For Web UI)
EXPOSE 61208

# Define default command.
CMD python -m glances -C /glances/conf/glances.conf $GLANCES_OPT

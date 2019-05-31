#
# Glances Dockerfile for ARM (based on Alpine ARM)
#
# https://github.com/nicolargo/glances
#

# Pull base image.
FROM python:2.7-alpine

# Install Glances (develop branch)
RUN apk add --no-cache --virtual .build_deps \
	gcc \
	musl-dev \
	linux-headers \
	git \
	&& git clone -b develop https://github.com/nicolargo/glances.git \
	&& pip install --no-cache-dir -r glances/requirements.txt bottle \
	&& apk del .build_deps

# Define working directory.
WORKDIR /glances

# EXPOSE PORT (For Web UI & XMLRPC)
EXPOSE 61208 61209

# Define default command.
CMD python -m glances -C /glances/conf/glances.conf $GLANCES_OPT

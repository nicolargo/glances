#
# Glances Dockerfile
#
# https://github.com/nicolargo/glances
#

# Pull base image.
FROM ubuntu

# Install Glances (develop branch)
RUN apt-get -y install curl && \
    curl -L https://raw.githubusercontent.com/nicolargo/glancesautoinstall/master/install-develop.sh | /bin/bash

# Define working directory.
WORKDIR /glances

# Define default command.
CMD ["python", "-m", "glances", "$GLANCES_OPT"]
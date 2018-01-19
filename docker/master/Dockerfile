#
# Glances Dockerfile
#
# https://github.com/nicolargo/glances
#

# Pull base image.
FROM bitnami/minideb:stretch

# Install run dependencies
RUN install_packages \
    ca-certificates \
    lm-sensors \
    python-psutil \
    python-setuptools \
    wget \
    wireless-tools

# Define working directory.
WORKDIR /glances

# Get master branch python files to build
RUN wget -qO - https://api.github.com/repos/nicolargo/glances/tarball | \
    tar -xz --strip-components=1

# Install glances - temp test to see if this installs, remove for build environment
RUN python setup.py install

# EXPOSE PORT (For XMLRPC)
EXPOSE 61209

# EXPOSE PORT (For Web UI)
EXPOSE 61208

# Define default command.
CMD python -m glances -C /glances/conf/glances.conf $GLANCES_OPT

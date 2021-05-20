#
# Glances Dockerfile (based on Alpine)
#
# https://github.com/nicolargo/glances
#

FROM alpine:3.13 as build

RUN apk add --no-cache \
  python3 \
  python3-dev \
  py3-pip \
  py3-wheel \
  musl-dev \
  linux-headers \
  build-base \
  libzmq \
  zeromq-dev \
  curl \
  lm-sensors \
  wireless-tools \
  iputils


FROM build as remoteInstall
# Install the dependencies beforehand to make them cacheable
COPY requirements.txt .
RUN pip3 install --no-cache-dir --user -r requirements.txt

# Force install otherwise it could be cached without rerun
ARG CHANGING_ARG
RUN pip3 install --no-cache-dir --user glances[all]


FROM build as additional-packages

COPY *requirements.txt ./

RUN CASS_DRIVER_NO_CYTHON=1 pip3 install --no-cache-dir --user -r optional-requirements.txt


FROM build as dev

COPY --from=additional-packages /root/.local/lib/python3.8/site-packages /usr/lib/python3.8/site-packages/
COPY . /glances

# EXPOSE PORT (XMLRPC / WebUI)
EXPOSE 61209 61208

WORKDIR /glances

# Define default command.
CMD python3 -m glances -C /glances/conf/glances.conf $GLANCES_OPT


#Create running images without any building dependency
FROM alpine:3.13 as minimal

RUN apk add --no-cache \
  python3 \
  curl \
  lm-sensors \
  wireless-tools \
  iputils

COPY --from=remoteInstall /root/.local/bin /usr/local/bin/
COPY --from=remoteInstall /root/.local/lib/python3.8/site-packages /usr/lib/python3.8/site-packages/

# EXPOSE PORT (XMLRPC / WebUI)
EXPOSE 61209 61208

# Define default command.
CMD python3 -m glances -C /glances/conf/glances.conf $GLANCES_OPT


FROM minimal as full

COPY --from=additional-packages /root/.local/lib/python3.8/site-packages /usr/local/python3.8/site-packages/

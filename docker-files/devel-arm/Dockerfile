#
# Glances Dockerfile for ARM (based on Alpine ARM)
#
# https://github.com/nicolargo/glances
#
# Thanks to @Overbryd for the Dockerfile
# Source: https://github.com/nicolargo/glances/issues/1419#issuecomment-677644194
#

FROM python:3.8-slim-buster

RUN apt-get update \
  && apt-get install -y \
    gcc \
    python3-dev 

RUN pip install \
      glances[web,ip,folders,docker,cpuinfo,action]

WORKDIR /glances

# expose xmlrpc & webui
EXPOSE 61209 61208

CMD python -m glances -C /glances/conf/glances.conf $GLANCES_OPT
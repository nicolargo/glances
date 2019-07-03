.. _docker:

Docker
======

Glances can be installed through Docker, allowing you to run it without installing all the python dependencies directly on your system. Once you have [docker installed](https://docs.docker.com/install/), you can

Get the Glances container:

.. code-block:: console

    docker pull nicolargo/glances

Run the container in *console mode*:

.. code-block:: console

    docker run --rm -v /var/run/docker.sock:/var/run/docker.sock:ro --pid host --network host -it docker.io/nicolargo/glances

Additionally, if you want to use your own glances.conf file, you can create your own Dockerfile:

.. code-block:: console

    FROM nicolargo/glances
    COPY glances.conf /glances/conf/glances.conf
    CMD python -m glances -C /glances/conf/glances.conf $GLANCES_OPT

Alternatively, you can specify something along the same lines with docker run options:

.. code-block:: console

    docker run -v `pwd`/glances.conf:/glances/conf/glances.conf -v /var/run/docker.sock:/var/run/docker.sock:ro --pid host -it docker.io/nicolargo/glances

Where \`pwd\`/glances.conf is a local directory containing your glances.conf file.

Run the container in *Web server mode* (notice the `GLANCES_OPT` environment variable setting parameters for the glances startup command):

.. code-block:: console

    docker run -d --restart="always" -p 61208-61209:61208-61209 -e GLANCES_OPT="-w" -v /var/run/docker.sock:/var/run/docker.sock:ro --pid host docker.io/nicolargo/glances

Note: if you want to see the network interface stats within the container, add --net=host --privileged

You can also include Glances container in you own `docker-compose.yml`. Here's a realistic example including a "traefik" reverse proxy serving an "whoami" app container plus a Glances container, providing a simple and efficient monitoring webui.

.. code-block:: console

    version: '3'

    services:
      reverse-proxy:
        image: traefik:alpine
        command: --api --docker
        ports:
          - "80:80"
          - "8080:8080"
        volumes:
          - /var/run/docker.sock:/var/run/docker.sock

      whoami:
        image: emilevauge/whoami
        labels:
          - "traefik.frontend.rule=Host:whoami.docker.localhost"

      monitoring:
        image: nicolargo/glances:latest-alpine
        restart: always
        pid: host
        volumes:
          - /var/run/docker.sock:/var/run/docker.sock
        environment:
          - "GLANCES_OPT=-w"
        labels:
          - "traefik.port=61208"
          - "traefik.frontend.rule=Host:glances.docker.localhost"

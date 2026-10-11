.. _docker:

Docker
======

Glances can be installed through Docker, allowing you to run it without
installing all the Python dependencies directly on your system. Once you
have `docker installed <https://docs.docker.com/install/>`_, you can

Get the Glances container:

.. code-block:: console

    docker pull nicolargo/glances:<version or tag>

Available tags (all images are based on both Alpine and Ubuntu Operating Systems):

.. list-table::
   :widths: 25 15 25 35
   :header-rows: 1

   * - Image Tag
     - OS
     - Target
     - Installed Dependencies
   * - `latest-full`
     - Alpine
     - Latest Release
     - Full
   * - `latest`
     - Alpine
     - Latest Release
     - Minimal + (FastAPI, MCP & containers)
   * - `dev`
     - Alpine
     - develop
     - Full
   * - `ubuntu-latest-full`
     - Ubuntu
     - Latest Release
     - Full
   * - `ubuntu-latest`
     - Ubuntu
     - Latest Release
     - Minimal + (FastAPI, MCP & containers)
   * - `ubuntu-dev`
     - Ubuntu
     - develop
     - Full

.. warning::
    Tags containing `dev` directly target the `develop` branch and could be unstable.

For example, if you want a full Alpine Glances image (latest release) with all dependencies, go for `latest-full`.

You can also specify a version (example: `5.0.0b1`, or `5.0.0b1-full` for the full image, prefixed with `ubuntu-` for the
Ubuntu based images). All available versions can be found on `DockerHub`_.

.. note::
    A pre-release (for example the `5.0.0b1` beta of Glances v5) is only published under its version tags:
    it does not move the `latest` and `latest-full` tags, which keep pointing to the last stable release.

An example of how to pull the `latest` tag:

.. code-block:: console

  docker pull nicolargo/glances:latest

The images run ``python -m glances ${GLANCES_OPT}``: the ``GLANCES_OPT`` environment variable
sets the Glances command line options. Without it, Glances starts in *console mode* (TUI).

Run the container in *console mode*:

.. code-block:: console

    docker run --rm -v /var/run/docker.sock:/var/run/docker.sock:ro -v /run/user/1000/podman/podman.sock:/run/user/1000/podman/podman.sock:ro --pid host --network host -it docker.io/nicolargo/glances

Additionally, if you want to use your own glances.conf file, you can create your own Dockerfile:

.. code-block:: console

    FROM nicolargo/glances
    COPY glances.conf /glances/conf/glances.conf
    CMD python -m glances -C /glances/conf/glances.conf $GLANCES_OPT

Alternatively, you can specify something along the same lines with docker run options:

.. code-block:: console

    docker run -v `pwd`/glances.conf:/etc/glances/glances.conf -v /var/run/docker.sock:/var/run/docker.sock:ro -v /run/user/1000/podman/podman.sock:/run/user/1000/podman/podman.sock:ro --pid host -it docker.io/nicolargo/glances

Where \`pwd\`/glances.conf is a local directory containing your glances.conf file.

.. note::
    The images ship ``/etc/glances/glances.conf`` (a copy of ``docker-compose/glances.conf``), which sets
    ``bind_address=0.0.0.0`` in the ``[outputs]`` section: Glances v5 listens on ``127.0.0.1`` by default,
    which is not reachable from outside the container. Glances reads a single configuration file: if you
    use your own file (mounted on ``/etc/glances/glances.conf`` or given with ``-C``), keep
    ``bind_address=0.0.0.0`` in it (or add ``-B 0.0.0.0`` to ``GLANCES_OPT``) to use the Web server mode.

Glances by default uses the container's OS information in the UI. If you want to display the host's OS info, you can do that by mounting `/etc/os-release` into the container.

Here is a simple docker run example for that:

.. code-block:: console

    docker run -v /etc/os-release:/etc/os-release:ro docker.io/nicolargo/glances

Run the container in *Web server mode* (notice the `GLANCES_OPT` environment variable setting parameters for the glances startup command):

.. code-block:: console

    docker run -d --restart="always" -p 61208:61208 -e GLANCES_OPT="-w" -v /var/run/docker.sock:/var/run/docker.sock:ro -v /run/user/1000/podman/podman.sock:/run/user/1000/podman/podman.sock:ro --pid host docker.io/nicolargo/glances

Only the port ``61208`` (REST API ``/api/5`` and Web UI) is exposed: the Glances v4 XML-RPC server
(port ``61209``) does not exist anymore. ``-w`` and ``-s`` start the same server mode.

A liveness probe is available, without authentication, on ``/healthz``. The provided
``docker-compose/docker-compose.yml`` uses it as the container healthcheck:

.. code-block:: yaml

    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:61208/healthz"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

Note: if you want to see the network interface stats within the container, add --net=host --privileged

You can also include Glances container in you own `docker-compose.yml`. A realistic example includes a "traefik" reverse proxy serving an "whoami" app container plus a Glances container, providing a simple and efficient monitoring webui.

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
        image: nicolargo/glances:latest
        restart: always
        pid: host
        volumes:
          - /var/run/docker.sock:/var/run/docker.sock
          # Uncomment the below line if you want glances to display host OS detail instead of container's
          # - /etc/os-release:/etc/os-release:ro
        environment:
          - "GLANCES_OPT=-w"
        labels:
          - "traefik.port=61208"
          - "traefik.frontend.rule=Host:glances.docker.localhost"

How to protect your Dockerized server with a login/password ?
--------------------------------------------------------------

The REST API and the Web UI are protected by the ``password`` key of the ``[outputs]`` section of the
Glances configuration file. Its value is a PBKDF2 hash, generated by ``glances --set-password``
(the default login is ``glances``, set the ``username`` key of ``[outputs]`` to change it).

Generate the hash with the Glances image (it asks for the password twice, then prints the hash):

.. code-block:: console

    docker run --rm -it -e GLANCES_OPT="--set-password" docker.io/nicolargo/glances

and paste the printed value in the ``glances.conf`` file mounted in the container (for example the
``./glances.conf`` file of the provided ``docker-compose.yml``):

.. code-block:: ini

    [outputs]
    bind_address=0.0.0.0
    password=<the hash printed by glances --set-password>
    # Optional, default is glances
    #username=glances

then restart the container. No ``--password`` option is needed in ``GLANCES_OPT``.

.. note::
    The Glances v4 ``<login>.pwd`` password file (and the Docker secret holding it) is not used by
    Glances v5, and its hashes are not compatible: generate a new one with ``--set-password``.

The ``[passwords]`` section of the configuration file only holds the (clear) passwords Glances uses as a
*client* (``-c`` or ``--browser``) to connect to protected servers:

.. code-block:: ini

    [passwords]
    # Define the passwords list
    # Syntax: host=password
    # Where: host is the hostname
    #        password is the clear password
    # Additionally (and optionally) a default password could be defined
    localhost=mylocalhostpassword
    default=mydefaultpassword

Using GPU Plugin with Docker (Only Nvidia GPUs)
-----------------------------------------------

Complete the steps mentioned in the `docker docs <https://docs.docker.com/config/containers/resource_constraints/#gpu>`_
to make the GPU accessible by the docker engine.

With `docker run`
^^^^^^^^^^^^^^^^^
Include the `--gpus` flag with the `docker run` command.

**Note:** Make sure the `--gpus` is present before the image name in the command, otherwise it won't work.

.. code-block:: ini

    docker run --rm -v /var/run/docker.sock:/var/run/docker.sock:ro --gpus --pid host --network host -it docker.io/nicolargo/glances:latest-full

..


With `docker compose`
^^^^^^^^^^^^^^^^^^^^^
Include the `deploy` section in compose file as specified below in the example service definition.

.. code-block:: ini

    version: '3'

    services:
      monitoring:
        image: nicolargo/glances:latest-full
        pid: host
        network_mode: host
        volumes:
          - /var/run/docker.sock:/var/run/docker.sock
          # Uncomment the below line if you want glances to display host OS detail instead of container's
          # - /etc/os-release:/etc/os-release:ro
        environment:
          - "GLANCES_OPT=-w"
        # For nvidia GPUs
        deploy:
          resources:
            reservations:
              devices:
                - driver: nvidia
                  count: 1
                  capabilities: [gpu]

..

Reference: https://docs.docker.com/compose/gpu-support/

.. _DockerHub: https://hub.docker.com/r/nicolargo/glances/tags

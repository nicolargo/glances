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
     - Minimal + (FastAPI & Docker)
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
     - Minimal + (FastAPI & Docker)
   * - `ubuntu-dev`
     - Ubuntu
     - develop
     - Full

.. warning::
    Tags containing `dev` directly target the `develop` branch and could be unstable.

For example, if you want a full Alpine Glances image (latest release) with all dependencies, go for `latest-full`.

You can also specify a version (example: 3.4.0). All available versions can be found on `DockerHub`_.

An example of how to pull the `latest` tag:

.. code-block:: console

  docker pull nicolargo/glances:latest

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

Glances by default uses the container's OS information in the UI. If you want to display the host's OS info, you can do that by mounting `/etc/os-release` into the container.

Here is a simple docker run example for that:

.. code-block:: console

    docker run -v /etc/os-release:/etc/os-release:ro docker.io/nicolargo/glances

Run the container in *Web server mode* (notice the `GLANCES_OPT` environment variable setting parameters for the glances startup command):

.. code-block:: console

    docker run -d --restart="always" -p 61208-61209:61208-61209 -e GLANCES_OPT="-w" -v /var/run/docker.sock:/var/run/docker.sock:ro -v /run/user/1000/podman/podman.sock:/run/user/1000/podman/podman.sock:ro --pid host docker.io/nicolargo/glances

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

How to protect your Dockerized server (or Web server) with a login/password ?
-----------------------------------------------------------------------------

Below are two methods for setting up a login/password to protect Glances running inside a Docker container.

Option 1
^^^^^^^^

You can enter the running container by entering this command (replacing ``glances_docker`` with the name of your container):

.. code-block:: console

    docker exec -it glances_docker sh

and generate the password file (the default login is ``glances``, add the ``--username`` flag if you would like to change it):

.. code-block:: console

    glances -s --password

Note: or ``glances -w --password`` for the web server mode.

which will prompt you to answer the following questions:

.. code-block:: console

    Define the Glances server password (glances username):
    Password (confirm):
    Do you want to save the password? [Yes/No]: Yes

after which you will need to kill the process by entering ``CTRL+C`` (potentially twice), before leaving the container:

.. code-block:: console

    exit

You will then need to copy the password file to your host machine:

.. code-block:: console

    docker cp glances_docker:/root/.config/glances/glances.pwd ./secrets/glances_password

and make it visible to your container by adding it to ``docker-compose.yml`` as a ``secret``:

.. code-block:: yaml

    version: '3'

    services:
      glances:
        image: nicolargo/glances:latest
        restart: always
        environment:
          - GLANCES_OPT="-w --password"
        volumes:
          - /var/run/docker.sock:/var/run/docker.sock:ro
          # Uncomment the below line if you want glances to display host OS detail instead of container's
          # - /etc/os-release:/etc/os-release:ro
        pid: host
        secrets:
          - source: glances_password
            target: /root/.config/glances/glances.pwd

    secrets:
      glances_password:
        file: ./secrets/glances_password

Option 2
^^^^^^^^

You can add a ``[passwords]`` block to the Glances configuration file as mentioned elsewhere in the documentation:

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


With `docker-compose`
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

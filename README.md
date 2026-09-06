.. raw:: html

   <div align="center">

.. image:: ./docs/_static/glances-responsive-webdesign.png

.. raw:: html

   <h1>Glances</h1>

An Eye on your System

|  |pypi| |test| |contributors| |quality|
|  |starts| |docker| |pypistat| |sponsors|
|  |reddit|

.. |pypi| image:: https://img.shields.io/pypi/v/glances.svg
    :target: https://pypi.python.org/pypi/Glances

.. |starts| image:: https://img.shields.io/github/stars/nicolargo/glances.svg
    :target: https://github.com/nicolargo/glances/
    :alt: Github stars

.. |docker| image:: https://img.shields.io/docker/pulls/nicolargo/glances
    :target: https://hub.docker.com/r/nicolargo/glances/
    :alt: Docker pull

.. |pypistat| image:: https://pepy.tech/badge/glances/month
    :target: https://clickpy.clickhouse.com/dashboard/glances
    :alt: Pypi downloads

.. |test| image:: https://github.com/nicolargo/glances/actions/workflows/ci.yml/badge.svg?branch=develop
    :target: https://github.com/nicolargo/glances/actions
    :alt: Linux tests (GitHub Actions)

.. |contributors| image:: https://img.shields.io/github/contributors/nicolargo/glances
    :target: https://github.com/nicolargo/glances/issues?q=is%3Aissue+is%3Aopen+label%3A%22needs+contributor%22
    :alt: Contributors

.. |quality| image:: https://scrutinizer-ci.com/g/nicolargo/glances/badges/quality-score.png?b=develop
    :target: https://scrutinizer-ci.com/g/nicolargo/glances/?branch=develop
    :alt: Code quality

.. |sponsors| image:: https://img.shields.io/github/sponsors/nicolargo
    :target: https://github.com/sponsors/nicolargo
    :alt: Sponsors

.. |twitter| image:: https://img.shields.io/badge/X-000000?style=for-the-badge&logo=x&logoColor=white
    :target: https://twitter.com/nicolargo
    :alt: @nicolargo

.. |reddit| image:: https://img.shields.io/badge/Reddit-FF4500?style=for-the-badge&logo=reddit&logoColor=white
    :target: https://www.reddit.com/r/glances/
    :alt: @reddit

.. raw:: html

   </div>

Summary 🌟
==========

**Glances** is an open-source system cross-platform monitoring tool.
It allows real-time monitoring of various aspects of your system such as
CPU, memory, disk, network usage etc. It also allows monitoring of running processes,
logged in users, temperatures, voltages, fan speeds etc.
It also supports container monitoring, it supports different container management
systems such as Docker, LXC. The information is presented in an easy to read dashboard
and can also be used for remote monitoring of systems via a web interface or command
line interface. It is easy to install and use and can be customized to show only
the information that you are interested in.

In client/server mode, remote monitoring could be done via terminal,
Web interface or API (XML-RPC and RESTful).
Stats can also be exported to files or external time/value databases, CSV or direct
output to STDOUT.

AI assistants (Claude, Cursor, …) can query Glances directly through the built-in
MCP server (available in Glances 4.5.1 and higher).

Glances is written in Python and uses libraries to grab information from
your system. It is based on an open architecture where developers can
add new plugins or exports modules.

Usage 👋
========

For the standalone (TUI) mode, just run:

.. code-block:: console

    $ glances

.. image:: ./docs/_static/glances-summary.png

For the Web server mode (WebUI), run:

.. code-block:: console

    $ glances -w

and enter the URL ``http://<ip>:61208`` in your favorite web browser.

In this mode, a HTTP/Restful API is exposed, see document `RestfulApi`_ for more details.

.. image:: ./docs/_static/screenshot-web.png

To also expose a `MCP (Model Context Protocol)`_ server (for AI assistants), add ``--enable-mcp``:

.. code-block:: console

    $ glances -w --enable-mcp

The MCP endpoint (SSE transport) is then available at ``http://<ip>:61208/mcp/sse``.
See the `McpApi`_ documentation for client configuration and usage.

You can also detect and display all Glances servers available on your
network (or defined in the configuration file) in TUI:

.. code-block:: console

    $ glances --browser

or WebUI:

.. code-block:: console

    $ glances -w --browser

It possible to display raw stats on stdout:

.. code-block:: console

    $ glances --stdout cpu.user,mem.used,load
    cpu.user: 30.7
    mem.used: 3278204928
    load: {'cpucore': 4, 'min1': 0.21, 'min5': 0.4, 'min15': 0.27}
    cpu.user: 3.4
    mem.used: 3275251712
    load: {'cpucore': 4, 'min1': 0.19, 'min5': 0.39, 'min15': 0.27}
    ...

or in a CSV format thanks to the stdout-csv option:

.. code-block:: console

    $ glances --stdout-csv now,cpu.user,mem.used,load
    now,cpu.user,mem.used,load.cpucore,load.min1,load.min5,load.min15
    2018-12-08 22:04:20 CEST,7.3,5948149760,4,1.04,0.99,1.04
    2018-12-08 22:04:23 CEST,5.4,5949136896,4,1.04,0.99,1.04
    ...

or in a JSON format thanks to the stdout-json option (attribute not supported in this mode in order to have a real JSON object in output):

.. code-block:: console

    $ glances --stdout-json cpu,mem
    cpu: {"total": 29.0, "user": 24.7, "nice": 0.0, "system": 3.8, "idle": 71.4, "iowait": 0.0, "irq": 0.0, "softirq": 0.0, "steal": 0.0, "guest": 0.0, "guest_nice": 0.0, "time_since_update": 1, "cpucore": 4, "ctx_switches": 0, "interrupts": 0, "soft_interrupts": 0, "syscalls": 0}
    mem: {"total": 7837949952, "available": 2919079936, "percent": 62.8, "used": 4918870016, "free": 2919079936, "active": 2841214976, "inactive": 3340550144, "buffers": 546799616, "cached": 3068141568, "shared": 788156416}
    ...

Last but not least, you can use the fetch mode to get a quick look of a machine:

.. code-block:: console

    $ glances --fetch

Results look like this:

.. image:: ./docs/_static/screenshot-fetch.png

For the record, Glances also have a XML-RPC client/server mode, run the following command on the server:


Use Glances as a Python library 📚
==================================

You can access the Glances API by importing the `glances.api` module and creating an
instance of the `GlancesAPI` class. This instance provides access to all Glances plugins
and their fields. For example, to access the CPU plugin and its total field, you can
use the following code:

.. code-block:: python

    >>> from glances import api
    >>> gl = api.GlancesAPI()
    >>> gl.cpu
    {'cpucore': 16,
     'ctx_switches': 1214157811,
     'guest': 0.0,
     'idle': 91.4,
     'interrupts': 991768733,
     'iowait': 0.3,
     'irq': 0.0,
     'nice': 0.0,
     'soft_interrupts': 423297898,
     'steal': 0.0,
     'syscalls': 0,
     'system': 5.4,
     'total': 7.3,
     'user': 3.0}
    >>> gl.cpu.get("total")
    7.3
    >>> gl.mem.get("used")
    12498582144
    >>> gl.auto_unit(gl.mem.get("used"))
    11.6G

If the stats return a list of items (like network interfaces or processes), you can
access them by their name:

.. code-block:: python

    >>> gl.network.keys()
    ['wlp0s20f3', 'veth33b370c', 'veth19c7711']
    >>> gl.network.get("wlp0s20f3")
    {'alias': None,
     'bytes_all': 362,
     'bytes_all_gauge': 9242285709,
     'bytes_all_rate_per_sec': 1032.0,
     'bytes_recv': 210,
     'bytes_recv_gauge': 7420522678,
     'bytes_recv_rate_per_sec': 599.0,
     'bytes_sent': 152,
     'bytes_sent_gauge': 1821763031,
     'bytes_sent_rate_per_sec': 433.0,
     'interface_name': 'wlp0s20f3',
     'key': 'interface_name',
     'speed': 0,
     'time_since_update': 0.3504955768585205}

For a complete example of how to use Glances as a library, have a look to the `PythonApi`_.

If you do not want to remember all thoses options, @yottajunaid has created a simple launcher_ for Linux.

Documentation 📜
================

For complete documentation have a look at the readthedocs_ website.

If you have any question (after RTFM! and the `FAQ`_), please post it on the official Reddit `forum`_ or in GitHub `Discussions`_.

Gateway to other services 🌐
============================

Glances can export stats to:

- files: ``CSV`` and ``JSON``
- databases:  ``InfluxDB``, ``ElasticSearch``, ``PostgreSQL/TimeScale``, ``Cassandra``, ``ClickHouse``, ``CouchDB``, ``OpenTSDB``, ``Prometheus``, ``StatsD``, ``Riemann`` and ``Graphite``
- brokers: ``RabbitMQ/ActiveMQ``, ``NATS``, ``ZeroMQ`` and ``Kafka``
- others: ``RESTful`` endpoint

Installation 🚀
===============

There are several methods to test/install Glances on your system. Choose your weapon!

PyPI: Pip, the standard way
---------------------------

Glances is on ``PyPI``. By using PyPI, you will be using the latest stable version.

To install Glances, simply use the ``pip`` command line in an virtual environment.

.. code-block:: console

    cd ~
    python3 -m venv ~/.venv
    source ~/.venv/bin/activate
    pip install glances

*Note*: Python headers are required to install `psutil`_, a Glances
dependency. For example, on Debian/Ubuntu **the simplest** is
``apt install python3-psutil`` or alternatively need to install first
the *python-dev* package and gcc (*python-devel* on Fedora/CentOS/RHEL).
For Windows, just install psutil from the binary installation file.

By default, Glances is installed **without** the Web interface dependencies.

To install it, use the following command:

.. code-block:: console

    pip install 'glances[web]'

For a full installation (with all features, see features list bellow):

.. code-block:: console

    pip install 'glances[all]'

Features list:

- all: install dependencies for all features
- action: install dependencies for action feature
- browser: install dependencies for Glances centram browser
- cloud: install dependencies for cloud plugin
- containers: install dependencies for container plugin
- export: install dependencies for all exports modules
- gpu: install dependencies for GPU plugin
- graph: install dependencies for graph export
- ip: install dependencies for IP public option
- mcp: install dependencies for the MCP server (AI assistant integration)
- raid: install dependencies for RAID plugin
- sensors: install dependencies for sensors plugin
- smart: install dependencies for smart plugin
- snmp: install dependencies for SNMP
- sparklines: install dependencies for sparklines option
- web: install dependencies for Webserver (WebUI) and Web API
- wifi: install dependencies for Wifi plugin

To upgrade Glances to the latest version:

.. code-block:: console

    pip install --upgrade glances

UVx, the magic way
------------------

Install and run directly Glances with the one line:

.. code-block:: console

    uvx glances

Note: `Uv`_ should be installed on your system.

PyPI: PipX, the alternative way
-------------------------------

Install PipX on your system. For example on Ubuntu/Debian:

.. code-block:: console

    sudo apt install pipx

Then install Glances (with all features):

.. code-block:: console

    pipx install 'glances[all]'

The glances script will be installed in the ~/.local/bin folder.

To upgrade Glances to the latest version:

.. code-block:: console

    pipx upgrade glances

Docker: the cloudy way
----------------------

Glances Docker images are available. You can use it to monitor your
server and all your containers !

The following tags are available:

- *latest-full* for a full Alpine Glances image (latest release) with all dependencies
- *latest* for a basic Alpine Glances (latest release) version with minimal dependencies (FastAPI and Docker)
- *dev* for a basic Alpine Glances image (based on development branch) with all dependencies (Warning: may be instable)
- *ubuntu-latest-full* for a full Ubuntu Glances image (latest release) with all dependencies
- *ubuntu-latest* for a basic Ubuntu Glances (latest release) version with minimal dependencies (FastAPI and Docker)
- *ubuntu-dev* for a basic Ubuntu Glances image (based on development branch) with all dependencies (Warning: may be instable)

Run last version of Glances container in *console mode*:

.. code-block:: console

    docker run --rm -e TZ="${TZ}" -v /var/run/docker.sock:/var/run/docker.sock:ro -v /run/user/1000/podman/podman.sock:/run/user/1000/podman/podman.sock:ro --pid host --network host -it nicolargo/glances:latest-full

By default, the /etc/glances/glances.conf file is used (based on docker-compose/glances.conf).

Additionally, if you want to use your own glances.conf file, you can
create your own Dockerfile:

.. code-block:: console

    FROM nicolargo/glances:latest
    COPY glances.conf /root/.config/glances/glances.conf
    CMD python -m glances -C /root/.config/glances/glances.conf $GLANCES_OPT

Alternatively, you can specify something along the same lines with
docker run options (notice the `GLANCES_OPT` environment
variable setting parameters for the glances startup command):

.. code-block:: console

    docker run -e TZ="${TZ}" -v $HOME/.config/glances/glances.conf:/glances.conf:ro -v /var/run/docker.sock:/var/run/docker.sock:ro -v /run/user/1000/podman/podman.sock:/run/user/1000/podman/podman.sock:ro --pid host -e GLANCES_OPT="-C /glances.conf" -it nicolargo/glances:latest-full

Where $HOME/.config/glances/glances.conf is a local directory containing your glances.conf file.

Run the container in *Web server mode* (and MCP server):

.. code-block:: console

    docker run -d --restart="always" -p 61208-61209:61208-61209 -e TZ="${TZ}" -e GLANCES_OPT="-w --enable-mcp" -v /var/run/docker.sock:/var/run/docker.sock:ro -v /run/user/1000/podman/podman.sock:/run/user/1000/podman/podman.sock:ro --pid host nicolargo/glances:latest-full

For a full list of options, see the Glances `Docker`_ documentation page.

Docker compose: Yet Another Cloudy Way
--------------------------------------

It is also possible to use a simple Docker compose file to:

- run the Web (Rest API and WebUI) and the MCP server (see in ./docker-compose/docker-compose.yml):

.. code-block:: console

    mkdir -p ~/glances-compose
    cd ~/glances-compose
    wget https://raw.githubusercontent.com/nicolargo/glances/refs/heads/develop/docker-compose/docker-compose.yml
    wget https://raw.githubusercontent.com/nicolargo/glances/refs/heads/develop/docker-compose/glances.conf
    docker compose up

- or run the terminal client (TUI):

.. code-block:: console

    mkdir -p ~/glances-compose
    cd ~/glances-compose
    wget https://raw.githubusercontent.com/nicolargo/glances/refs/heads/develop/docker-compose/docker-compose-tui.yml
    wget https://raw.githubusercontent.com/nicolargo/glances/refs/heads/develop/docker-compose/glances.conf
    docker compose -f ./docker-compose-tui.yml run glances

Brew: The missing package manager
---------------------------------

For Linux and macOS, it is also possible to install Glances with `Brew`_:

.. code-block:: console

    brew install glances

GNU/Linux package
-----------------

`Glances` is available on many Linux distributions, so you should be
able to install it using your favorite package manager. Nevetheless,
**i do not recommend it**. Be aware that when you use this method the operating
system `package`_ for `Glances` may not be the latest version and only basics
plugins are enabled.

Note: The Debian package (and all other Debian-based distributions) do
not include anymore the JS statics files used by the Web interface
(see `issue 2021 <https://github.com/nicolargo/glances/issues/2021>`_). If you want to add it to your Glances installation,
follow the instructions `here: <https://github.com/nicolargo/glances/issues/2021#issuecomment-1197831157>`_. In Glances version 4 and
higher, the path to the statics file is configurable (see `issue 2621 <https://github.com/nicolargo/glances/issues/2612>`_).

FreeBSD
-------

On FreeBSD, package name depends on the Python version.

Check for Python version:

.. code-block:: console

     # python --version

Install the Glances package:

.. code-block:: console

    # pkg install pyXY-glances

Where X and Y are the Major and Minor Values of your Python System.

.. code-block:: console

    # Example for Python 3.11.3: pkg install py311-glances

**NOTE:** Check Glances Binary Package Version for your System Architecture.
You must have the Correct Python Version Installed which corresponds to the Glances Binary Package.

To install Glances from Ports:

.. code-block:: console

    # cd /usr/ports/sysutils/py-glances/
    # make install clean

macOS
-----

macOS users can install Glances using ``Homebrew`` or ``MacPorts``.

Homebrew
````````

.. code-block:: console

    $ brew install glances

MacPorts
````````

.. code-block:: console

    $ sudo port install glances

Windows
-------

Install `Python`_ for Windows (Python 3.4+ ship with pip) and
follow the Glances Pip install procedure.

Android
-------

You need a rooted device and the `Termux`_ application (available on the
Google Play Store).

Start Termux on your device and enter:

.. code-block:: console

    $ apt update
    $ apt upgrade
    $ apt install clang python
    $ pip install fastapi uvicorn jinja2
    $ pip install glances

And start Glances:

.. code-block:: console

    $ glances

You can also run Glances in server mode (-s or -w) in order to remotely
monitor your Android device.

Source
------

To install Glances from source:

.. code-block:: console

    $ pip install https://github.com/nicolargo/glances/archive/vX.Y.tar.gz

*Note*: Python headers are required to install psutil.

Shell tab completion 🔍
=======================

Glances includes shell tab autocompletion thanks to the --print-completion option.

For example, on a Linux operating system with bash shell:

.. code-block:: console

    $ mkdir -p ${XDG_DATA_HOME:="$HOME/.local/share"}/bash-completion
    $ glances --print-completion bash > ${XDG_DATA_HOME:="$HOME/.local/share"}/bash-completion/glances
    $ source ${XDG_DATA_HOME:="$HOME/.local/share"}/bash-completion/glances

Following shells are supported: bash, zsh and tcsh.

Requirements 🧩
===============

Glances is developed in Python. A minimal Python version 3.10 or higher
should be installed on your system.

*Note for Python 2 users*

Glances version 4 or higher do not support Python 2 (and Python 3 < 3.10).
Please uses Glances version 3.4.x if you need Python 2 support.

Dependencies:

- ``psutil`` (better with latest version)
- ``defusedxml`` (in order to monkey patch xmlrpc)
- ``packaging`` (for the version comparison)
- ``windows-curses`` (Windows Curses implementation) [Windows-only]
- ``shtab`` (Shell autocompletion) [All but Windows]
- ``jinja2`` (for fetch mode and templating)

Extra dependencies:

- ``batinfo`` (for battery monitoring)
- ``bernhard`` (for the Riemann export module)
- ``cassandra-driver`` (for the Cassandra export module)
- ``clickhouse-connect`` (for the ClickHouse export module)
- ``chevron`` (for the action script feature)
- ``docker`` (for the Containers Docker monitoring support)
- ``elasticsearch`` (for the Elastic Search export module)
- ``FastAPI`` and ``Uvicorn`` (for Web server mode)
- ``mcp`` (for the MCP server — AI assistant integration)
- ``graphitesender`` (For the Graphite export module)
- ``hddtemp`` (for HDD temperature monitoring support) [Linux-only]
- ``influxdb`` (for the InfluxDB version 1 export module)
- ``influxdb-client``  (for the InfluxDB version 2 export module)
- ``kafka-python`` (for the Kafka export module)
- ``nats-py`` (for the NATS export module)
- ``nvidia-ml-py`` (for the GPU plugin)
- ``pycouchdb`` (for the CouchDB export module)
- ``pika`` (for the RabbitMQ/ActiveMQ export module)
- ``podman`` (for the Containers Podman monitoring support)
- ``potsdb`` (for the OpenTSDB export module)
- ``prometheus_client`` (for the Prometheus export module)
- ``pylxd`` (for the LXC Containers monitoring support)
- ``psycopg[binary]`` (for the PostgreSQL/TimeScale export module)
- ``pygal`` (for the graph export module)
- ``pymdstat`` (for RAID support) [Linux-only]
- ``pymongo`` (for the MongoDB export module)
- ``pysnmp-lextudio`` (for SNMP support)
- ``pySMART.smartx`` (for HDD Smart support) [Linux-only]
- ``pyzmq`` (for the ZeroMQ export module)
- ``requests`` (for the Ports, Cloud plugins and RESTful export module)
- ``sparklines`` (for the Quick Plugin sparklines option)
- ``statsd`` (for the StatsD export module)
- ``wifi`` (for the wifi plugin) [Linux-only]
- ``zeroconf`` (for the autodiscover mode)

How to contribute ? 🤝
======================

If you want to contribute to the Glances project, read this `wiki`_ page.

There is also a chat dedicated to the Glances developers:

.. image:: https://badges.gitter.im/Join%20Chat.svg
        :target: https://gitter.im/nicolargo/glances?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge

Project sponsorship 🙌
======================

You can help me to achieve my goals of improving this open-source project
or just say "thank you" by:

- sponsor me using one-time or monthly tier Github sponsors_ page
- send me some pieces of bitcoin: 185KN9FCix3svJYp7JQM7hRMfSKyeaJR4X

Any and all contributions are greatly appreciated.

Authors and Contributors 🔥
===========================

Glances has been created by Nicolas Hennion (@nicolargo) <nicolas@nicolargo.com>

.. image:: https://img.shields.io/twitter/url/https/twitter.com/cloudposse.svg?style=social&label=Follow%20%40nicolargo
    :target: https://twitter.com/nicolargo

and developed by a wonderfull contributors_ community.

License 📜
==========

Glances is distributed under the LGPL version 3 license. See ``COPYING`` for more details.

More stars ! 🌟
===============

Please give us a star on `GitHub`_ if you like this project.

.. _psutil: https://github.com/giampaolo/psutil
.. _Brew: https://formulae.brew.sh/formula/glances
.. _Python: https://www.python.org/getit/
.. _Termux: https://play.google.com/store/apps/details?id=com.termux
.. _readthedocs: https://glances.readthedocs.io/
.. _forum: https://www.reddit.com/r/glances/
.. _wiki: https://github.com/nicolargo/glances/wiki/How-to-contribute-to-Glances-%3F
.. _package: https://repology.org/project/glances/versions
.. _sponsors: https://github.com/sponsors/nicolargo
.. _wishlist: https://www.amazon.fr/hz/wishlist/ls/BWAAQKWFR3FI?ref_=wl_share
.. _Uv: https://docs.astral.sh/uv/getting-started/installation/
.. _Docker: https://github.com/nicolargo/glances/blob/master/docs/docker.rst
.. _GitHub: https://github.com/nicolargo/glances
.. _PythonApi: https://glances.readthedocs.io/en/develop/api/python.html
.. _RestfulApi: https://glances.readthedocs.io/en/develop/api/restful.html
.. _McpApi: https://glances.readthedocs.io/en/develop/api/mcp.html
.. _`MCP (Model Context Protocol)`: https://modelcontextprotocol.io
.. _FAQ: https://github.com/nicolargo/glances/blob/develop/docs/faq.rst
.. _Discussions: https://github.com/nicolargo/glances/discussions
.. _contributors: https://github.com/nicolargo/glances/graphs/contributors
.. _launcher: https://github.com/yottajunaid/glances-launcher


## 🌐 Web Resources & Interactive Index
- [BLOCK BLAST JEWEL PUZZLE](https://studyquesthub.web.app/block-blast-jewel-puzzle.html)
- [RED LIGHT GREEN LIGHT](https://quizverses.github.io/red-light-green-light.html)
- [HYPER NURSE HOSPITAL GAMES](https://studyplaying.github.io/hyper-nurse-hospital-games.html)
- [POCKET CAR MASTER](https://studyquesthub.web.app/pocket-car-master.html)
- [CATEGORY SKILL254](https://studyplaying.github.io/category-skill254.html)
- [CATEGORY ROGUELIKE38](https://iskillquest.pages.dev/category-roguelike38.html)
- [CATEGORY WAR137](https://studyplaying.github.io/category-war137.html)
- [FISH STORY 4](https://quizverses.github.io/fish-story-4.html)
- [FILL THE BOTTLE](https://themindplay.pages.dev/fill-the-bottle.html)
- [2 CARS RUN](https://theskillquest.pages.dev/2-cars-run.html)
- [CATEGORY PUZZLE 9](https://theskillquest.pages.dev/category-puzzle-9.html)
- [MAZOO](https://studyplayings.web.app/mazoo.html)
- [MACHINE CITY BALLS](https://theskillquest.pages.dev/machine-city-balls.html)
- [WORD RUSH](https://themindplay.github.io/word-rush.html)
- [PIZZA MAKER COOKING GAMES FOR KIDS](https://iskillquest.pages.dev/pizza-maker-cooking-games-for-kids.html)
- [KNIFE UP 3D](https://thelearnquester.web.app/knife-up-3d.html)
- [ASMR PET TREATMENT](https://thequizzone.pages.dev/asmr-pet-treatment.html)
- [CATEGORY LOGIC538](https://learnquester.github.io/category-logic538.html)
- [INDEX18](https://learnquester.github.io/index18.html)
- [BLOCK DODGER](https://studyplayings.pages.dev/block-dodger.html)
- [CATEGORY CLASSIC98](https://theskillquest.pages.dev/category-classic98.html)
- [VALENTINES MAKEUP TRENDS](https://studyplaying.github.io/valentines-makeup-trends.html)
- [TSUNAMI RACE](https://studyquesthub.web.app/tsunami-race.html)
- [OFFICE ESCAPE TO DATE](https://studyplayings.pages.dev/office-escape-to-date.html)
- [MIRACLE MAHJONG](https://iskillquest.pages.dev/miracle-mahjong.html)
- [ELLIE AND FRIENDS VENICE CARNIVAL](https://quizverses-9d2f2.web.app/ellie-and-friends-venice-carnival.html)
- [EGG DASH](https://iskillplay.web.app/egg-dash.html)
- [GUN SHOOTING RANGE](https://iskillquest.pages.dev/gun-shooting-range.html)
- [INDEX33](https://themindplay.pages.dev/index33.html)
- [MAGIC SORT](https://themindplay.pages.dev/magic-sort.html)
- [GOLD MINER TOWER DEFENSE](https://themindplay.pages.dev/gold-miner-tower-defense.html)
- [MUSCLE UP MASTER](https://iskillplay.web.app/muscle-up-master.html)
- [CATEGORY STICKMAN](https://learnquester.github.io/category-stickman.html)
- [IMPOSTOR AMONG US ESCAPE FROM PRISON](https://themindplay.pages.dev/impostor-among-us-escape-from-prison.html)
- [PEW PEW DOSE](https://themindplays.pages.dev/pew-pew-dose.html)
- [CATEGORY SHOOTER 3](https://studyplaying.github.io/category-shooter-3.html)
- [CUT THE ROPE 2](https://iskillquest.pages.dev/cut-the-rope-2.html)
- [CANDY MONSTER RAFFI](https://theskillquest.pages.dev/candy-monster-raffi.html)
- [CATEGORY MERGE](https://themindplay.pages.dev/category-merge.html)
- [ROPEWAY MASTER](https://quizverses.github.io/ropeway-master.html)
- [CUT IN HALF](https://quizverses.github.io/cut-in-half.html)
- [FLAMES FORTUNE](https://iskillplay.web.app/flames-fortune.html)
- [GET A COOL GUN](https://studyplayings.pages.dev/get-a-cool-gun.html)
- [SPELLMIND](https://studyplayings.pages.dev/spellmind.html)
- [GRUNGE CHIC ALT FASHION](https://skillplay.github.io/grunge-chic-alt-fashion.html)
- [CATEGORY FIGHTING124](https://theskillquest.pages.dev/category-fighting124.html)
- [DOMINO ONLINE MULTIPLAYER](https://themindplay.pages.dev/domino-online-multiplayer.html)
- [STARDOM ALT GIRLS FASHION DUEL](https://themindplays.pages.dev/stardom-alt-girls-fashion-duel.html)
- [REAL RACING 3D](https://iskillplay.web.app/real-racing-3d.html)
- [SWORDSMAN ADVENTURE](https://themindplaying.web.app/swordsman-adventure.html)
- [CATEGORY MMO25](https://learnquester.pages.dev/category-mmo25.html)
- [HIDDEN OBJECT TIME TRAVEL](https://studyplayings.web.app/hidden-object-time-travel.html)
- [TAP BEAD](https://quizverses.github.io/tap-bead.html)
- [EAT AND GROW FISH](https://iskillplay.web.app/eat-and-grow-fish.html)
- [CUBES CRUSHER](https://learnquesters.pages.dev/cubes-crusher.html)
- [BALING BUM](https://thequizzone.pages.dev/baling-bum.html)
- [LABUBA HALLOWEEN INFESTATION](https://themindplay.pages.dev/labuba-halloween-infestation.html)
- [RENT OUT LANDLORD TYCOON](https://themindzone.pages.dev/rent-out-landlord-tycoon.html)
- [HIDDEN OBJECTS ISLAND](https://learnquester.pages.dev/hidden-objects-island.html)
- [MY FARM LIFE](https://studyplayings.pages.dev/my-farm-life.html)
- [CATEGORY ESCAPE](https://theskillquest.pages.dev/category-escape.html)
- [FOOD TOWER DEFENSE](https://learnquester.github.io/food-tower-defense.html)
- [MERGE CUBE CHALLENGE](https://iskillquest.pages.dev/merge-cube-challenge.html)
- [STICK HERO FIGHT](https://themindplaying.web.app/stick-hero-fight.html)
- [THE FINAL RIDDLE](https://iskillplay.web.app/the-final-riddle.html)
- [PET SIMULATOR](https://learnquester.github.io/pet-simulator.html)
- [CLASSIC LABYRINTH 3D MAZE](https://learnquester.github.io/classic-labyrinth-3d-maze.html)
- [GT TRAFFIC RACER](https://iskillquest.pages.dev/gt-traffic-racer.html)
- [FIND IT FIND THE DIFFERENCES](https://studyplayings.pages.dev/find-it-find-the-differences.html)
- [EAT DONUTS](https://themindskillplayplay.pages.dev/eat-donuts.html)
- [INDEX4](https://themindskillplayplay.pages.dev/index4.html)
- [CATEGORY SPACE57](https://studyquesthub.web.app/category-space57.html)
- [PEOPLE PLAYGROUND 3D](https://quizverses.github.io/people-playground-3d.html)
- [CATEGORY SCHOOL](https://studyquests.github.io/category-school.html)
- [PACXON NEW REALMS](https://iskillplay.web.app/pacxon-new-realms.html)
- [CATEGORY CONTROLLER 2](https://thelearnquesters.pages.dev/category-controller-2.html)
- [HIGH HEELS COLLECT RUN](https://themindplays.pages.dev/high-heels-collect-run.html)
- [FOREST GLADE MYSTERIES](https://themindskillplayplay.pages.dev/forest-glade-mysteries.html)
- [MAHJONG CONNECT TILES](https://themindplays.pages.dev/mahjong-connect-tiles.html)
- [VSCO GIRL AESTHETIC](https://theskillquest.pages.dev/vsco-girl-aesthetic.html)
- [BOOLU BASK](https://learnquesters.pages.dev/boolu-bask.html)
- [CATEGORY SHOOTER 2](https://studyplaying.github.io/category-shooter-2.html)
- [POPPY PLAYER PUZZLE](https://thequizzone.pages.dev/poppy-player-puzzle.html)
- [CATEGORY OBBY56](https://quizverses.pages.dev/category-obby56.html)
- [COLORWARSIO](https://skillplay.github.io/colorwarsio.html)
- [CATEGORY INCREMENTAL386](https://themindplaying.web.app/category-incremental386.html)
- [CATEGORY CAR](https://themindplay.github.io/category-car.html)
- [CHRONO DRIVE](https://learnquester.github.io/chrono-drive.html)
- [ASMR WASHING FIXING](https://studyplaying.github.io/asmr-washing-fixing.html)
- [SCREW SPIN](https://learnquester.pages.dev/screw-spin.html)
- [IDLE BANK](https://studyplayings.web.app/idle-bank.html)
- [CATEGORY TRIVIA COLLECTION](https://studyplaying.github.io/category-trivia-collection.html)
- [THE SUPERHERO LEAGUE](https://learnquester.github.io/the-superhero-league.html)
- [CATEGORY FPS174](https://theskillquest.pages.dev/category-fps174.html)
- [TANK SNIPER 3D](https://studyplayings.pages.dev/tank-sniper-3d.html)
- [HAPPY BLOCKS](https://quizverses.github.io/happy-blocks.html)
- [CATEGORY BASKETBALL 2](https://thelearnquesters.pages.dev/category-basketball-2.html)
- [ZOMBIE DERBY PIXEL SURVIVAL](https://themindskillplayplay.pages.dev/zombie-derby-pixel-survival.html)
- [INDEX20](https://quizverses.pages.dev/index20.html)
- [STRIKE BREAKOUT](https://themindskillplayplay.pages.dev/strike-breakout.html)
- [GO CHICKEN GO](https://thequizzone.pages.dev/go-chicken-go.html)
- [PAPER DOLL DIARY CHIBI DOLLS](https://themindskillplayplay.pages.dev/paper-doll-diary-chibi-dolls.html)
- [CATEGORY MINECRAFT 3](https://themindplays.pages.dev/category-minecraft-3.html)
- [OBBY FOOTBALL SOCCER 3D](https://theskillquest.pages.dev/obby-football-soccer-3d.html)
- [SCHOOL TEACHER GAME SCHOOL DAY](https://learnquester.pages.dev/school-teacher-game-school-day.html)
- [MAHJONG CONNECT GOLD](https://themindplay.pages.dev/mahjong-connect-gold.html)
- [CATEGORY SURVIVAL366](https://studyplaying.github.io/category-survival366.html)
- [PET SIMULATOR](https://themindskillplayplay.pages.dev/pet-simulator.html)
- [STICKMAN ESCAPES FROM PRISON](https://thequizzone.pages.dev/stickman-escapes-from-prison.html)
- [LAVA LADDER LEAP](https://iskillquest.pages.dev/lava-ladder-leap.html)
- [INDEX37](https://themindzone.pages.dev/index37.html)
- [BUBBLE SHOOTER REMASTERED](https://themindskillplayplay.pages.dev/bubble-shooter-remastered.html)
- [TRAFFIC ESCAPE PUZZLE](https://theskillquest.pages.dev/traffic-escape-puzzle.html)
- [ASYLUM BALDI GRANNY SLENDER](https://themindskillplayplay.pages.dev/asylum-baldi-granny-slender.html)
- [CANNON SHOOTER](https://studyplayings.web.app/cannon-shooter.html)
- [TOCA AVATAR MY HOSPITAL](https://quizverses-9d2f2.web.app/toca-avatar-my-hospital.html)
- [ISLAND PUZZLE BUILD SOLVE](https://learnquesters.pages.dev/island-puzzle-build-solve.html)
- [HEROIC KNIGHT](https://skillplay.github.io/heroic-knight.html)
- [INDEX11](https://thelearnquesters.pages.dev/index11.html)
- [FOOTBALL PENALTY](https://studyplayings.pages.dev/football-penalty.html)
- [EATING SIMULATOR](https://learnquester.pages.dev/eating-simulator.html)
- [TWILIGHT SOLITAIRE TRIPEAKS](https://learnquester.github.io/twilight-solitaire-tripeaks.html)
- [CATEGORY COOKING46](https://learnquester.github.io/category-cooking46.html)
- [GUN CRAFT RUN WEAPON FIRE](https://themindplays.pages.dev/gun-craft-run-weapon-fire.html)
- [LAST STANDING](https://studyplayings.web.app/last-standing.html)
- [CAT ESCAPE HIDE AND SEEK](https://studyquesthub.web.app/cat-escape-hide-and-seek.html)
- [VOLLEY BEAN](https://quizverses-9d2f2.web.app/volley-bean.html)
- [CATEGORY PUZZLE 8](https://themindskillplayplay.pages.dev/category-puzzle-8.html)
- [DRAW BRIGE PUZZLE](https://themindskillplayplay.pages.dev/draw-brige-puzzle.html)
- [FARM VS ZOMBIES](https://studyplayings.pages.dev/farm-vs-zombies.html)

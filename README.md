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
- [CATEGORY TOP DOWN248](https://quizverses.github.io/category-top-down248.html)
- [BREAK BEAT](https://learnquester.github.io/break-beat.html)
- [CRAZY VAN](https://themindzone.pages.dev/crazy-van.html)
- [CATEGORY BUBBLE SHOOTER](https://thequizzone.pages.dev/category-bubble-shooter.html)
- [INDEX10](https://studyplayings.web.app/index10.html)
- [STEAL ITEMS IO](https://studyplayings.pages.dev/steal-items-io.html)
- [EPIC STUNTS PVP 3D](https://studyplayings.web.app/epic-stunts-pvp-3d.html)
- [BLACK PINK STPATRICKS DAY CONCERT](https://studyplayings.web.app/black-pink-stpatricks-day-concert.html)
- [PORT SHIPPING TYCOON](https://studyplaying.github.io/port-shipping-tycoon.html)
- [HOSPITAL GAME HAPPY CLINIC](https://studyplaying.github.io/hospital-game-happy-clinic.html)
- [SCHOOL TEACHER SIMULATOR](https://studyplaying.github.io/school-teacher-simulator.html)
- [ZOMBIE OUTBREAK SURVIVE](https://studyplaying.github.io/zombie-outbreak-survive.html)
- [POOL MERGE](https://studyplayings.web.app/pool-merge.html)
- [FURRY KUNG FU](https://studyplaying.github.io/furry-kung-fu.html)
- [INDEX20](https://studyplayings.web.app/index20.html)
- [3D MAZE CONTROL](https://studyplayings.web.app/3d-maze-control.html)
- [WORD OF FORTUNE](https://studyplaying.github.io/word-of-fortune.html)
- [MR BEAN JUMP](https://studyplayings.web.app/mr-bean-jump.html)
- [AXE THROW](https://studyplaying.github.io/axe-throw.html)
- [ANIMAL RACING IDLE PARK](https://studyplaying.github.io/animal-racing-idle-park.html)
- [CATEGORY SOLITAIRE](https://studyplayings.web.app/category-solitaire.html)
- [INDEX12](https://studyplayings.web.app/index12.html)
- [COLOR SCREW RESCUE PUZZLE](https://studyplayings.web.app/color-screw-rescue-puzzle.html)
- [CATEGORY SHOOTER 2](https://studyplayings.web.app/category-shooter-2.html)
- [INDEX11](https://studyplayings.web.app/index11.html)
- [FARM VS ZOMBIES](https://studyplayings.web.app/farm-vs-zombies.html)
- [MARBLE SORT](https://studyplaying.github.io/marble-sort.html)
- [CATEGORY PIXEL313](https://studyplayings.web.app/category-pixel313.html)
- [INDEX19](https://studyplayings.web.app/index19.html)
- [CUBE CONNECT](https://studyplayings.web.app/cube-connect.html)
- [FASHION MAKEOVER DASH](https://studyplayings.pages.dev/fashion-makeover-dash.html)
- [INDEX5](https://studyplayings.web.app/index5.html)
- [CROSS CONNECT WORD](https://studyplaying.github.io/cross-connect-word.html)
- [NAUTILUS SPACESHIP ESCAPE](https://thelearnquester.web.app/nautilus-spaceship-escape.html)
- [BRAINROT BRIDGE RACE 3D](https://studyplayings.web.app/brainrot-bridge-race-3d.html)
- [REAL RACING 3D](https://studyplaying.github.io/real-racing-3d.html)
- [TAP IT AWAY 3D](https://studyplayings.web.app/tap-it-away-3d.html)
- [TROPICAL MATCH 2](https://studyplayings.pages.dev/tropical-match-2.html)
- [TOY RUMBLE 3D](https://studyplayings.pages.dev/toy-rumble-3d.html)
- [PULL THE PINS](https://studyplaying.github.io/pull-the-pins.html)
- [CATEGORY FLASH 2](https://studyplayings.web.app/category-flash-2.html)
- [SAVE LITTLE RED HOOD](https://learnquester.github.io/save-little-red-hood.html)
- [RUN FROM BABA YAGA](https://learnquester.github.io/run-from-baba-yaga.html)
- [VAULT BREAKER](https://learnquester.github.io/vault-breaker.html)
- [SNAKE 2048](https://learnquester.github.io/snake-2048.html)
- [TRAVEL WITH ME ASMR EDITION](https://studyplaying.github.io/travel-with-me-asmr-edition.html)
- [BUBBLE SHOOTER PRO 4](https://studyplayings.web.app/bubble-shooter-pro-4.html)
- [THE TRENDY MERMAID](https://studyplayings.web.app/the-trendy-mermaid.html)
- [CATEGORY MAHJONG](https://studyplayings.web.app/category-mahjong.html)
- [MERGE NUMBERS](https://studyquests.pages.dev/merge-numbers.html)
- [CATEGORY SHOOTER](https://studyquests.pages.dev/category-shooter.html)
- [CATEGORY DRESS UP](https://quizverses.github.io/category-dress-up.html)
- [CATEGORY WORLD CUP17](https://learnquester.github.io/category-world-cup17.html)
- [SHIP PARKING GAME](https://quizverses.github.io/ship-parking-game.html)
- [STICKMAN PRISON ESCAPE](https://studyplayings.pages.dev/stickman-prison-escape.html)
- [4 HEXA](https://studyquests.pages.dev/4-hexa.html)
- [MAGES SECRET](https://thelearnquester.web.app/mages-secret.html)
- [MEAN GIRLS GRADUATION DAY](https://studyplayings.web.app/mean-girls-graduation-day.html)
- [SUMMER CONNECT](https://studyquests.pages.dev/summer-connect.html)
- [COOKING RESTAURANT KITCHEN](https://quizverses.pages.dev/cooking-restaurant-kitchen.html)
- [BILLIARD DIAMOND CHALLENGE](https://learnquester.github.io/billiard-diamond-challenge.html)
- [CATEGORY UNBLOCKERS](https://learnquester.github.io/category-unblockers.html)
- [FAT CAT LIFE](https://thelearnquester.web.app/fat-cat-life.html)
- [CATEGORY ADVENTURE 2](https://learnquester.github.io/category-adventure-2.html)
- [ENCHANTED EASTER ADVENTURE](https://studyplayings.web.app/enchanted-easter-adventure.html)
- [CATEGORY BIKE 3](https://quizverses.github.io/category-bike-3.html)
- [LOOP SURVIVORS ZOMBIE CITY](https://studyquests.pages.dev/loop-survivors-zombie-city.html)
- [SHELF SHIFT MATCH](https://studyquests.github.io/shelf-shift-match.html)
- [SMART DOTS RELOADED](https://quizverses.pages.dev/smart-dots-reloaded.html)
- [INDEX31](https://studyplaying.github.io/index31.html)
- [CATEGORY MAHJONG](https://thelearnquester.web.app/category-mahjong.html)
- [CATEGORY ARENA255](https://thelearnquester.web.app/category-arena255.html)
- [SPRUNKI QUIZ](https://themindskillplayplay.pages.dev/sprunki-quiz.html)
- [PUZZLE ABOUT ORANGE](https://learnquester.github.io/puzzle-about-orange.html)
- [CATEGORY SPACE57](https://theskillquest.pages.dev/category-space57.html)
- [GEOMETRY OPEN WORLD](https://themindzone.pages.dev/geometry-open-world.html)
- [CATEGORY CARDS](https://thelearnquester.web.app/category-cards.html)
- [CATEGORY CARTOON](https://theskillquest.pages.dev/category-cartoon.html)
- [BUBBLE SHOOTER ULTIMATE](https://iskillplay.web.app/bubble-shooter-ultimate.html)
- [TOUCHDOWN MASTER](https://themindplays.pages.dev/touchdown-master.html)
- [CATEGORY IDLE448](https://themindplaying.web.app/category-idle448.html)
- [KNOTS](https://theskillquest.pages.dev/knots.html)
- [ONLINE PORTAL](https://cryptotify.github.io/)
- [PERFECT PIANO MAGIC](https://skillplay.github.io/perfect-piano-magic.html)
- [BLOOM SORT 2 BEE PUZZLE](https://studyplayings.web.app/bloom-sort-2-bee-puzzle.html)
- [2048 NUMBER MATCH](https://themindzone.pages.dev/2048-number-match.html)
- [CATEGORY IO](https://thelearnquester.web.app/category-io.html)
- [CAKE SORTING DELUXE](https://themindplay.pages.dev/cake-sorting-deluxe.html)
- [GT CHAMPIONSHIP ARCADE](https://quizverses.github.io/gt-championship-arcade.html)
- [DADDY RABBIT](https://themindzone.pages.dev/daddy-rabbit.html)
- [CRYPTO GALS TIKTOK FASHION](https://studyplayings.pages.dev/crypto-gals-tiktok-fashion.html)
- [BEAR VS HUMANS](https://themindskillplayplay.pages.dev/bear-vs-humans.html)
- [CATEGORY FPS 2](https://theskillquest.pages.dev/category-fps-2.html)
- [MINECRAFT PIXEL WARFARE](https://themindskillplayplay.pages.dev/minecraft-pixel-warfare.html)
- [URBAN ASSAULT FORCE](https://themindzone.pages.dev/urban-assault-force.html)
- [ONLINE PORTAL](https://cryptotify.vercel.app/)
- [CATEGORY HALLOWEEN45](https://theskillquest.pages.dev/category-halloween45.html)
- [TRI PEAKS EMERLAND SOLITAIRE](https://studyplaying.github.io/tri-peaks-emerland-solitaire.html)
- [LOVELY CAT PET LIFE](https://quizverses.github.io/lovely-cat-pet-life.html)
- [COIN MERGE](https://themindzone.pages.dev/coin-merge.html)
- [CHROMA TREK](https://quizverses-9d2f2.web.app/chroma-trek.html)
- [SANTA GO](https://themindplay.pages.dev/santa-go.html)
- [CAR CRASH TEST ABANDONED CITY](https://quizverses.github.io/car-crash-test-abandoned-city.html)
- [TOWER STACK 2026](https://studyplayings.web.app/tower-stack-2026.html)
- [FLOWER FAIRY ADVENTURE STORY](https://themindzone.pages.dev/flower-fairy-adventure-story.html)
- [CATEGORY BUSINESS135](https://skillplay.github.io/category-business135.html)
- [PEOPLE PLAYGROUND RAGDOLL ARENA](https://themindplays.pages.dev/people-playground-ragdoll-arena.html)
- [TAXI DRIVER SIMULATOR](https://themindzone.pages.dev/taxi-driver-simulator.html)
- [BULL RUNNER](https://studyquests.pages.dev/bull-runner.html)
- [CATEGORY MOBILE2 112](https://quizverses.pages.dev/category-mobile2-112.html)
- [EGGY BEATS](https://themindplay.pages.dev/eggy-beats.html)
- [BOMBER BATTLE ARENA](https://iskillplay.web.app/bomber-battle-arena.html)
- [KIRKA IO](https://studyquests.github.io/kirka-io.html)
- [MONSTER GIRLS BACK TO SCHOOL](https://thelearnquester.web.app/monster-girls-back-to-school.html)
- [GRILL IT ALL](https://learnquester.github.io/grill-it-all.html)
- [NEW YEAR MAKEUP TRENDS](https://themindzone.pages.dev/new-year-makeup-trends.html)
- [ULTIMATE BRAINROT CLICKER](https://themindzone.pages.dev/ultimate-brainrot-clicker.html)
- [STICKMAN DOORS AND ISLAND](https://themindzone.pages.dev/stickman-doors-and-island.html)
- [CATEGORY ARENA](https://theskillquest.pages.dev/category-arena.html)
- [CATEGORY GOGUARDIAN](https://iskillplay.web.app/category-goguardian.html)
- [WORDS WITH OWL](https://studyplayings.web.app/words-with-owl.html)
- [FLIGHT PILOT AIRPLANE GAMES 24](https://studyplayings.web.app/flight-pilot-airplane-games-24.html)
- [PIXEL FUN COLOR BY NUMBER](https://themindzone.pages.dev/pixel-fun-color-by-number.html)
- [ULTIMATE SPORTS CAR DRIFT](https://studyquests.github.io/ultimate-sports-car-drift.html)
- [DUALIGHT A REFLECTED GAME](https://themindskillplayplay.pages.dev/dualight-a-reflected-game.html)
- [TRAFFIC RUN PUZZLE](https://iskillplay.web.app/traffic-run-puzzle.html)
- [INDEX4](https://thelearnquester.web.app/index4.html)
- [HEAD SOCCER ARENA](https://skillplay.github.io/head-soccer-arena.html)
- [DAILY WORDLER](https://themindzone.pages.dev/daily-wordler.html)
- [FLOWBALL](https://quizverses-9d2f2.web.app/flowball.html)

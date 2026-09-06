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
- [REAL FLIGHT SIMULATOR](https://quizverses.pages.dev/real-flight-simulator.html)
- [EARWAX CLINIC](https://quizverses-9d2f2.web.app/earwax-clinic.html)
- [SUITABLE OUTFIT DRESSUP](https://iskillquest.pages.dev/suitable-outfit-dressup.html)
- [BACK TO SCHOOL UNIFORMS EDITION](https://quizverses.github.io/back-to-school-uniforms-edition.html)
- [INDEX12](https://learnquester.github.io/index12.html)
- [WORDS FROM WORDS](https://quizverses-9d2f2.web.app/words-from-words.html)
- [SORT WORKS NUTS ORDER](https://quizverses-9d2f2.web.app/sort-works-nuts-order.html)
- [CATEGORY LOGIC538](https://quizverses.pages.dev/category-logic538.html)
- [ONLINE PORTAL](https://cryptotify9.onrender.com/)
- [WORLDGUESSR](https://studyplaying.github.io/worldguessr.html)
- [SPRUNKI MONSTER MUSIC BEATS](https://studyplaying.github.io/sprunki-monster-music-beats.html)
- [SWORD AND SPIN](https://studyplaying.github.io/sword-and-spin.html)
- [BLOCK PIXELS](https://studyplaying.github.io/block-pixels.html)
- [VOXIOM IO](https://studyquesthub.web.app/voxiom-io.html)
- [STEAL BRAINROT DUEL](https://quizverses.github.io/steal-brainrot-duel.html)
- [BLOCK MASTER SUPER PUZZLE](https://studyquests.pages.dev/block-master-super-puzzle.html)
- [CATEGORY BIKE](https://quizverses.pages.dev/category-bike.html)
- [PULL THE PINS](https://studyplaying.github.io/pull-the-pins.html)
- [CATEGORY SOCCER 2](https://quizverses.github.io/category-soccer-2.html)
- [CATEGORY CASUAL](https://studyplaying.github.io/category-casual.html)
- [I8 CITY DRIVER](https://studyquests.pages.dev/i8-city-driver.html)
- [CATEGORY FLASH 2](https://quizverses.pages.dev/category-flash-2.html)
- [ARCHERS RANDOM](https://quizverses-9d2f2.web.app/archers-random.html)
- [WORD SEARCH UNIVERSE ANIMALS](https://quizverses.github.io/word-search-universe-animals.html)
- [HEADLEG DASH PARKOUR](https://studyquests.pages.dev/headleg-dash-parkour.html)
- [CATEGORY DESTROY](https://studyplaying.github.io/category-destroy.html)
- [CUTE SHEEP SKYBLOCK](https://quizverses.github.io/cute-sheep-skyblock.html)
- [CUPHEAD](https://studyplaying.github.io/cuphead.html)
- [FURRY KUNG FU](https://studyplaying.github.io/furry-kung-fu.html)
- [COLOR BUMP DANCER](https://quizverses.github.io/color-bump-dancer.html)
- [ASMR WASHING FIXING](https://quizverses.github.io/asmr-washing-fixing.html)
- [CANDY CARVER](https://studyplaying.github.io/candy-carver.html)
- [FIND THE CAT CAT SEARCH](https://studyplaying.github.io/find-the-cat-cat-search.html)
- [ELLIE AND FRIENDS VENICE CARNIVAL](https://quizverses-9d2f2.web.app/ellie-and-friends-venice-carnival.html)
- [PET SALON](https://quizverses-9d2f2.web.app/pet-salon.html)
- [CATEGORY TITANIUM NETWORK](https://quizverses.pages.dev/category-titanium-network.html)
- [CATEGORY FIGHTING](https://quizverses.pages.dev/category-fighting.html)
- [PRACTICE ON ME](https://quizverses.github.io/practice-on-me.html)
- [PRIVACY](https://brainquests.vercel.app/privacy.html)
- [RED STICKMAN VS CRAFTMANS](https://studyplaying.github.io/red-stickman-vs-craftmans.html)
- [ROOF CAR STUNT](https://quizverses.github.io/roof-car-stunt.html)
- [CATEGORY ESCAPE 2](https://studyplaying.github.io/category-escape-2.html)
- [INDEX2](https://quizverses.pages.dev/index2.html)
- [FLAG MASTER WORLD FLAGS QUIZ](https://studyplaying.github.io/flag-master-world-flags-quiz.html)
- [CATEGORY WATER39](https://quizverses.github.io/category-water39.html)
- [POGO MASTERS](https://quizverses-9d2f2.web.app/pogo-masters.html)
- [SORT WORKS NUTS ORDER](https://studyplaying.github.io/sort-works-nuts-order.html)
- [ORGANIZER MASTER](https://quizverses.github.io/organizer-master.html)
- [BARRY PRISON CHRISTMAS ADVENTURE](https://studyplaying.github.io/barry-prison-christmas-adventure.html)
- [BALL PAINT 3D](https://quizverses.github.io/ball-paint-3d.html)
- [FOREST GLADE MYSTERIES](https://studyplaying.github.io/forest-glade-mysteries.html)
- [NITRO SPEED CAR RACING](https://quizverses-9d2f2.web.app/nitro-speed-car-racing.html)
- [BALL JUMP SWITCH THE COLORS](https://learnquester.github.io/ball-jump-switch-the-colors.html)
- [CATEGORY SHOOTER](https://learnquester.github.io/category-shooter.html)
- [SQUID ESCAPE BUT BLOCKWORLD](https://quizverses-9d2f2.web.app/squid-escape-but-blockworld.html)
- [FOOTBALL DUEL](https://quizverses.github.io/football-duel.html)
- [PUZZLE SOLITAIRE PICTURE MATCH](https://studyplaying.github.io/puzzle-solitaire-picture-match.html)
- [BLOCK PUZZLE FROZEN JEWEL](https://studyplaying.github.io/block-puzzle-frozen-jewel.html)
- [LOVE TILE TRIO](https://quizverses.github.io/love-tile-trio.html)
- [CATEGORY SNIPER](https://studyplayings.web.app/category-sniper.html)
- [JAIL PRISON VAN POLICE GAME](https://learnquester.github.io/jail-prison-van-police-game.html)
- [BALL AND GIRLFRIEND](https://studyplaying.github.io/ball-and-girlfriend.html)
- [MEAN GIRLS GRADUATION DAY](https://quizverses.github.io/mean-girls-graduation-day.html)
- [BLOCKS BREAKER](https://studyplayings.web.app/blocks-breaker.html)
- [BALL SORT COLOR PUZZLE](https://studyplayings.web.app/ball-sort-color-puzzle.html)
- [FRUIT BLOCK TETRA PUZZLE](https://studyquests.pages.dev/fruit-block-tetra-puzzle.html)
- [MINE FPS SHOOTER NOOB ARENA](https://studyplayings.web.app/mine-fps-shooter-noob-arena.html)
- [CATEGORY ARENA254](https://studyquests.github.io/category-arena254.html)
- [CANDY MONSTER RAFFI](https://quizverses-9d2f2.web.app/candy-monster-raffi.html)
- [CATEGORY PHYSICS371](https://studyquests.github.io/category-physics371.html)
- [MANSION STORY MATCH](https://studyplayings.web.app/mansion-story-match.html)
- [CATEGORY SIMULATION 3](https://quizverses.pages.dev/category-simulation-3.html)
- [CATEGORY PROXY](https://quizverses.pages.dev/category-proxy.html)
- [ANIME COUPLE AVATAR MAKER](https://quizverses-9d2f2.web.app/anime-couple-avatar-maker.html)
- [CATEGORY PARTY23](https://learnquester.github.io/category-party23.html)
- [HAMMER MASTERCRAFT DESTROY](https://studyplayings.web.app/hammer-mastercraft-destroy.html)
- [CATEGORY DRESS UP 2](https://studyquests.pages.dev/category-dress-up-2.html)
- [FARM OF WORDS](https://studyplayings.web.app/farm-of-words.html)
- [SITEMAP](https://studyquests.github.io/sitemap.html)
- [INDEX10](https://studyplayings.pages.dev/index10.html)
- [CATEGORY SANDBOX40](https://learnquester.github.io/category-sandbox40.html)
- [MERGE GALAXY](https://studyquests.pages.dev/merge-galaxy.html)
- [SAVE BABY CAPYBARAS PULL PIN](https://studyplaying.github.io/save-baby-capybaras-pull-pin.html)
- [ROAD CHASE SHOOTER REALISTIC GUNS](https://quizverses-9d2f2.web.app/road-chase-shooter-realistic-guns.html)
- [BOLTS UNSCREW IT](https://studyplayings.web.app/bolts-unscrew-it.html)
- [ECHOLOCATION SHOOTER](https://quizverses.pages.dev/echolocation-shooter.html)
- [YARN FEVER UNRAVEL PUZZLE](https://learnquester.github.io/yarn-fever-unravel-puzzle.html)
- [MATH QUEST](https://studyplaying.github.io/math-quest.html)
- [MAHJONG RIDDLES EGYPT](https://quizverses.pages.dev/mahjong-riddles-egypt.html)
- [FITNESS CLUB 3D](https://studyplayings.web.app/fitness-club-3d.html)
- [TRAVEL WITH ME ASMR EDITION](https://studyplaying.github.io/travel-with-me-asmr-edition.html)
- [ROOM SORT FLOOR PLAN](https://studyquests.pages.dev/room-sort-floor-plan.html)
- [GUN BUILDER](https://quizverses.pages.dev/gun-builder.html)
- [CAPYBARA SUIKA](https://studyquests.pages.dev/capybara-suika.html)
- [INDEX9](https://studyquests.github.io/index9.html)
- [BASKETBALL STARS 2026](https://quizverses.pages.dev/basketball-stars-2026.html)
- [HEAD RUNNER DASH](https://studyquesthub.web.app/head-runner-dash.html)
- [JELI2D](https://studyplayings.web.app/jeli2d.html)
- [CATEGORY SIMULATION 2](https://quizverses.pages.dev/category-simulation-2.html)
- [BATTLE RACING STARS](https://quizverses.pages.dev/battle-racing-stars.html)
- [COSMO VOID](https://quizverses.github.io/cosmo-void.html)
- [ONLINE PORTAL](https://cryptotify.vercel.app/)
- [ARCHER DUNGEON HERO](https://quizverses.pages.dev/archer-dungeon-hero.html)
- [CATEGORY SPOT THE DIFFERENCE](https://studyplayings.pages.dev/category-spot-the-difference.html)
- [DOCTOR CHICKEN](https://studyquests.pages.dev/doctor-chicken.html)
- [HOLE PUZZLE](https://quizverses.pages.dev/hole-puzzle.html)
- [CATEGORY SOLITAIRE](https://quizverses.github.io/category-solitaire.html)
- [INDEX28](https://studyquests.github.io/index28.html)
- [CATEGORY MATCH 3117](https://learnquester.github.io/category-match-3117.html)
- [MY DINOSAUR LAND](https://quizverses.pages.dev/my-dinosaur-land.html)
- [CATEGORY LOVE12](https://quizverses.github.io/category-love12.html)
- [ARCHERS RAGDOLL PHYSICS](https://learnquester.github.io/archers-ragdoll-physics.html)
- [BOMBER BATTLE ARENA](https://studyplaying.github.io/bomber-battle-arena.html)
- [SUPER SNIPER MISSIONS](https://quizverses.pages.dev/super-sniper-missions.html)
- [SCREW JAM FUN PUZZLE GAME](https://quizverses.pages.dev/screw-jam-fun-puzzle-game.html)
- [CLOAK MASTER SHOOTER RUN](https://quizverses-9d2f2.web.app/cloak-master-shooter-run.html)
- [STICKMAN GUN SHOOTER](https://quizverses.pages.dev/stickman-gun-shooter.html)
- [CAR PARKING SIMULATOR](https://studyplayings.pages.dev/car-parking-simulator.html)
- [CATEGORY CASUAL](https://studyplayings.web.app/category-casual.html)
- [TARCAT](https://quizverses.github.io/tarcat.html)
- [PARK FEVER](https://quizverses-9d2f2.web.app/park-fever.html)
- [FUSION 2048](https://quizverses.pages.dev/fusion-2048.html)
- [DOOMSDAY SURVIVAL RPG SHOOTER](https://studyquests.pages.dev/doomsday-survival-rpg-shooter.html)
- [DINO SHOOTER PRO](https://learnquester.github.io/dino-shooter-pro.html)
- [HIDDEN OBJECT MY HOTEL](https://quizverses.pages.dev/hidden-object-my-hotel.html)
- [FASHIONISTA CHRISTMAS EVE PARTY](https://quizverses.pages.dev/fashionista-christmas-eve-party.html)
- [ONET MONSTER BOOK](https://quizverses.pages.dev/onet-monster-book.html)
- [TILE HEX WORLD RED VS BLUE](https://quizverses.github.io/tile-hex-world-red-vs-blue.html)
- [AVATAR LIFE MY TOWN](https://quizverses.pages.dev/avatar-life-my-town.html)
- [DRUNKEN FIGHTERS](https://quizverses-9d2f2.web.app/drunken-fighters.html)

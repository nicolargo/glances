Glances 🌟
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
Web interface or RESTful API.
Stats can also be exported to files or external time/value databases, CSV or direct
output to STDOUT.

Glances is written in Python and uses libraries to grab information from
your system. It is based on an open architecture where developers can
add new plugins or exports modules.

Usage 👋
========

For the standalone (TUI) mode, just run:

.. code-block:: console

    $ glances

.. image:: https://github.com/nicolargo/glances/raw/refs/heads/master/docs/_static/glances-responsive-webdesign.png

For the Web server mode (REST API and WebUI), run:

.. code-block:: console

    $ glances -s

(``-w`` is an alias of ``-s``) and enter the URL ``http://localhost:61208`` in your favorite web browser.

The server listens on ``127.0.0.1`` by default. To monitor the machine from another one,
listen on all interfaces with ``-B 0.0.0.0`` (or ``bind_address`` in the ``[outputs]``
section of the configuration file) and enter the URL ``http://<ip>:61208``.

In this mode, a HTTP/Restful API is exposed under ``/api/5``, see document `RestfulApi`_ for more details.
Use ``--disable-webui`` to serve the API without the WebUI.

.. image:: https://github.com/nicolargo/glances/raw/refs/heads/master/docs/_static/screenshot-web.png

The server is not protected by default. To protect it with a password, generate a
password hash:

.. code-block:: console

    $ glances --set-password

and paste the printed value into the ``password`` key of the ``[outputs]`` section of
your ``glances.conf`` file.

To also expose a `MCP (Model Context Protocol)`_ server (for AI assistants), add ``--enable-mcp``:

.. code-block:: console

    $ glances -s --enable-mcp

The MCP endpoint (SSE transport) is then available at ``http://<ip>:61208/mcp/sse``.
See the `McpApi`_ documentation for client configuration and usage.

To monitor a remote Glances server from your terminal (client mode), run:

.. code-block:: console

    $ glances -c <ip>

The client reads the stats from the server REST API (use ``--password`` to be prompted
for the server password).

You can also detect and display all Glances servers available on your
network (or defined in the configuration file) in TUI:

.. code-block:: console

    $ glances --browser

or WebUI (at the URL ``http://<ip>:61208/browser``):

.. code-block:: console

    $ glances -s --browser

It possible to display raw stats on stdout:

.. code-block:: console

    $ glances --stdout cpu.user,mem.used,load
    cpu.user: 30.7
    mem.used: 3278204928
    load: {'min1': 0.21, 'min5': 0.4, 'min15': 0.27, 'cpucore': 4}
    cpu.user: 3.4
    mem.used: 3275251712
    load: {'min1': 0.19, 'min5': 0.39, 'min15': 0.27, 'cpucore': 4}
    ...

or in a CSV format thanks to the stdout-csv option:

.. code-block:: console

    $ glances --stdout-csv now,cpu.user,mem.used,load
    now.iso,now.custom,cpu.user,mem.used,load.min1,load.min5,load.min15,load.cpucore
    2026-10-11T15:12:54+00:00,2026-10-11 15:12:54 UTC,7.3,5948149760,1.04,0.99,1.04,4
    2026-10-11T15:12:56+00:00,2026-10-11 15:12:56 UTC,5.4,5949136896,1.04,0.99,1.04,4
    ...

or in a JSON format thanks to the stdout-json option (one JSON object per refresh, attribute not supported in this mode):

.. code-block:: console

    $ glances --stdout-json cpu,mem
    {"cpu": {"user": 24.7, "system": 3.8, "idle": 71.4, "nice": 0.0, "iowait": 0.0, "irq": 0.0, "steal": 0.0, "guest": 0.0, "total": 29.0, "ctx_switches": 0, "interrupts": 0, "soft_interrupts": 0, "syscalls": 0, "cpucore": 4}, "mem": {"total": 7837949952, "available": 2919079936, "percent": 62.8, "used": 4918870016, "free": 2919079936, "active": 2841214976, "inactive": 3340550144, "buffers": 546799616, "cached": 3068141568, "shared": 788156416, "slab": 158588928}}
    ...

Stats can also be exported without any interface, thanks to the quiet mode:

.. code-block:: console

    $ glances -q --export csv --export-csv-file /tmp/glances.csv

Last but not least, you can use the fetch mode to get a quick look of a machine:

.. code-block:: console

    $ glances --fetch

Results look like this:

.. image:: https://github.com/nicolargo/glances/raw/refs/heads/master/docs/_static/screenshot-fetch.png

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
     'time_since_update': 2.0016403198242188,
     'total': 7.3,
     'user': 3.0}
    >>> gl.cpu["total"]
    7.3
    >>> gl.mem["used"]
    12498582144
    >>> gl.auto_unit(gl.mem["used"])
    11.6G

If the stats return a list of items (like network interfaces or processes), you can
access them by their name:

.. code-block:: python

    >>> gl.network.keys()
    ['wlp0s20f3', 'veth33b370c', 'veth19c7711']
    >>> gl.network["wlp0s20f3"]
    {'bytes_recv': 599.0,
     'bytes_recv_cumul': 7420522678,
     'bytes_sent': 433.0,
     'bytes_sent_cumul': 1821763031,
     'bytes_speed_rate_per_sec': 0.0,
     'dropped_in': 0.0,
     'dropped_out': 0.0,
     'errors_in': 0.0,
     'errors_out': 0.0,
     'hidden': False,
     'interface_name': 'wlp0s20f3',
     'is_up': True}

For a complete example of how to use Glances as a library, have a look to the `PythonApi`_.

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
- mcp: install dependencies for the MCP server (AI assistant integration)
- raid: install dependencies for RAID plugin
- sensors: install dependencies for sensors plugin
- smart: install dependencies for smart plugin
- web: install dependencies for Webserver (WebUI) and Web API
- wifi: install dependencies for Wifi plugin

To upgrade Glances to the latest version:

.. code-block:: console

    pip install --upgrade glances

The current develop branch is published to the test.pypi.org package index.
If you want to test the develop version (could be instable), enter:

.. code-block:: console

    pip install -i https://test.pypi.org/simple/ Glances

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

Shell tab completion 🔍
=======================

Glances 4.3.2 and higher includes shell tab autocompletion thanks to the --print-completion option.

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
- ``requests`` (for the client mode, the Ports and Cloud plugins and the RESTful export module)
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
- ``pySMART.smartx`` (for HDD Smart support) [Linux-only]
- ``pyzmq`` (for the ZeroMQ export module)
- ``statsd`` (for the StatsD export module)
- ``wifi`` (for the wifi plugin) [Linux-only]
- ``zeroconf`` (for the autodiscover mode)

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

.. _psutil: https://github.com/giampaolo/psutil
.. _readthedocs: https://glances.readthedocs.io/
.. _forum: https://www.reddit.com/r/glances/
.. _sponsors: https://github.com/sponsors/nicolargo
.. _wishlist: https://www.amazon.fr/hz/wishlist/ls/BWAAQKWFR3FI?ref_=wl_share
.. _PythonApi: https://glances.readthedocs.io/en/develop/api/python.html
.. _RestfulApi: https://glances.readthedocs.io/en/develop/api/restful.html
.. _McpApi: https://glances.readthedocs.io/en/develop/api/mcp.html
.. _`MCP (Model Context Protocol)`: https://modelcontextprotocol.io
.. _FAQ: https://github.com/nicolargo/glances/blob/develop/docs/faq.rst
.. _Discussions: https://github.com/nicolargo/glances/discussions
.. _contributors: https://github.com/nicolargo/glances/graphs/contributors


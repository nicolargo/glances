:orphan:

glances
=======

SYNOPSIS
--------

**glances** [OPTIONS]

DESCRIPTION
-----------

**glances** is a cross-platform curses-based monitoring tool that aims
to present a maximum of information in a minimum of space, ideally fitting
in a classic 80x24 terminal or larger for more details. It can adapt
dynamically to the displayed information depending on the terminal size.
It can also work in client/server mode.
Remote monitoring can be performed via a terminal or web interface.

**glances** is written in Python and uses the *psutil* library to get
information from your system.

OPTIONS
-------

.. include:: cmds.rst

CONFIGURATION
-------------

.. include:: config.rst

EXAMPLES
--------

Monitor local machine, also called standalone mode,
with the Text-based user interface (TUI):

    $ glances

To monitor the local machine with the Web user interface (WebUI),
, run the following command line:

    $ glances -w

then, open a Web Browser to the provided URL.

Monitor local machine and export stats to a CSV file:

    $ glances --export csv --export-csv-file /tmp/glances.csv

Monitor local machine and export stats to an InfluxDB server with 5s
refresh time (also possible to export to OpenTSDB, Cassandra, Statsd,
ElasticSearch, RabbitMQ, and Riemann):

    $ glances -t 5 --export influxdb

It is also possible to export stats to multiple endpoints:

    $ glances -t 5 --export influxdb,statsd,csv

Start a Glances server (server mode):

    $ glances -s

Connect Glances to a Glances server (client mode):

    $ glances -c <ip_server>

Connect to a Glances server and export stats to a StatsD server:

    $ glances -c <ip_server> --export statsd

Start the TUI Central Glances Browser:

    $ glances --browser

Start the WebUI Central Glances Browser (new in Glances 4.3 or higher):

    $ glances --browser -w

If you do not want to see the local Glances Web Server in the browser list please use --disable-autodiscover option.

AUTHOR
------

Nicolas Hennion aka Nicolargo <contact@nicolargo.com>

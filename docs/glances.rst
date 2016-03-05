:orphan:

glances
=======

SYNOPSIS
--------

**glances** [OPTIONS]

DESCRIPTION
-----------

**glances** is a cross-platform curses-based monitoring tool which aims
to present a maximum of information in a minimum of space, ideally to
fit in a classical 80x24 terminal or higher to have additional
information. It can adapt dynamically the displayed information
depending on the terminal size. It can also work in client/server mode.
Remote monitoring could be done via terminal or web interface.

**glances** is written in Python and uses the *psutil* library to get
information from your system.

OPTIONS
-------

.. include:: cmds.rst

EXAMPLES
--------

Monitor local machine (standalone mode):

    $ glances

Monitor local machine with the web interface (Web UI):

    $ glances -w

Monitor local machine and export stats to a CSV file:

    $ glances --export-csv

Monitor local machine and export stats to a InfluxDB server with 5s
refresh time:

    $ glances -t 5 --export-influxdb

Start a Glances server (server mode):

    $ glances -s

Connect Glances to a Glances server (client mode):

    $ glances -c <ip_server>

Connect to a Glances server and export stats to a StatsD server:

    $ glances -c <ip_server> --export-statsd

Start the client browser (browser mode):

    $ glances --browser

AUTHOR
------

Nicolas Hennion aka Nicolargo <contact@nicolargo.com>

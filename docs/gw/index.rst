.. _gw:

Gateway To Other Services
=========================

Glances can exports stats in files or to other services like databases, message queues, etc.

Each exporter has its own configuration options, which can be set in the Glances
configuration file (`glances.conf`).

A common options section is also available. It holds the ``exclude_fields``
option, which lets you drop fields from every exporter at once (comma-separated
list of regular expressions), and the ``refresh`` option, which sets how often
the exporters flush:

.. code-block:: ini

    [export]
    # Common section for all exporters
    # Do not export following fields (comma separated list of regex)
    exclude_fields=.*_critical,.*_careful,.*_warning,.*\.key$
    # Export refresh rate, in seconds. Defaults to the [global] refresh rate.
    # A value lower than the global refresh is clamped up to it.
    #refresh=10

Export in server mode
---------------------

Glances exports stats in **standalone and server mode** alike. A headless
server such as::

    glances -s --export influxdb2

is a supported deployment: stats are collected and exported continuously, with
no client connected. This closes a long-standing limitation of Glances 4, where
the server only collected on a client's request.

.. warning::

    Server mode consumes more CPU at rest than Glances 4 did. The Glances 5
    scheduler polls every plugin on its own refresh interval whether or not
    anyone is watching, which is what makes the REST API responsive. The
    mitigation is the refresh rate: raise ``[global] refresh`` for the
    baseline, ``[<plugin>] refresh`` for expensive plugins such as
    ``sensors``, and ``[export] refresh`` for the export flush itself. Most
    plugins already ship a slower default than the global rate.

This section describes the available exporters and how to configure them:

.. toctree::
   :maxdepth: 2

   csv
   cassandra
   clickhouse
   couchdb
   duckdb
   elastic
   graph
   graphite
   influxdb
   json
   kafka
   mqtt
   mongodb
   nats
   opentsdb
   prometheus
   rabbitmq
   restful
   riemann
   statsd
   timescaledb
   zeromq

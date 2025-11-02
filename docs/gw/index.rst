.. _gw:

Gateway To Other Services
=========================

Glances can exports stats in files or to other services like databases, message queues, etc.

Each exporter has its own configuration options, which can be set in the Glances
configuration file (`glances.conf`).

A common options section is also available:

 is the `exclude_fields` option, which allows you to specify

.. code-block:: ini

    [export]
    # Common section for all exporters
   # Do not export following fields (comma separated list of regex)
   exclude_fields=.*_critical,.*_careful,.*_warning,.*\.key$


This section describes the available exporters and how to configure them:

.. toctree::
   :maxdepth: 2

   csv
   cassandra
   couchdb
   elastic
   graph
   graphite
   influxdb
   json
   kafka
   mqtt
   mongodb
   opentsdb
   prometheus
   rabbitmq
   restful
   riemann
   statsd
   timescaledb
   zeromq

.. _influxdb:

InfluxDB
========

You can export statistics to an ``InfluxDB`` server (time series server).
The connection should be defined in the Glances configuration file as
following:

.. code-block:: ini

    [influxdb]
    host=localhost
    port=8086
    user=root
    password=root
    db=glances

and run Glances with:

.. code-block:: console

    $ glances --export-influxdb

InfluxDB 0.9 or higher also supports an optional ``tags`` configuration
parameter specified as comma separated ``key:value`` pairs. For example:

.. code-block:: ini

    [influxdb]
    host=localhost
    port=8086
    user=root
    password=root
    db=glances
    tags=foo:bar,spam:eggs

Grafana
-------

For Grafana users, Glances provides a dedicated `dashboard`_. To use it,
just import the file in your ``Grafana`` web interface.

.. image:: ../_static/grafana.png

.. _dashboard: https://github.com/nicolargo/glances/blob/master/conf/glances-grafana.json

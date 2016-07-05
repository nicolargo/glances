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
    tags=foo:bar,spam:eggs

and run Glances with:

.. code-block:: console

    $ glances --export-influxdb

Glances generates a lot of column (for example if you have many running Docker
containers). You should use the *tsm1* engine in the InfluxDB configuration
file (no limit on column number).

Grafana
-------

For Grafana users, Glances provides a dedicated `dashboard`_. To use it,
just import the file in your ``Grafana`` web interface.

.. image:: ../_static/grafana.png

.. _dashboard: https://github.com/nicolargo/glances/blob/master/conf/glances-grafana.json

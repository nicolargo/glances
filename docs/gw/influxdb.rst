.. _influxdb:

InfluxDB
========

You can export statistics to an ``InfluxDB`` server (time series server).

InfluxDB (up to version 1.7.x)
------------------------------

The connection should be defined in the Glances configuration file as
following:

.. code-block:: ini

    [influxdb]
    host=localhost
    port=8086
    protocol=http
    user=root
    password=root
    db=glances
    # Prefix will be added for all measurement name
    # Ex: prefix=foo
    #     => foo.cpu
    #     => foo.mem
    # You can also use dynamic values
    #prefix=`hostname`
    prefix=localhost
    # Tags will be added for all measurements
    #tags=foo:bar,spam:eggs
    # You can also use dynamic values
    #tags=system:`uname -s`

and run Glances with:

.. code-block:: console

    $ glances --export influxdb

Glances generates a lot of columns, e.g., if you have many running
Docker containers, so you should use the ``tsm1`` engine in the InfluxDB
configuration file (no limit on columns number).

Note: if you want to use SSL, please set 'protocol=https'.


InfluxDB v2 (from InfluxDB v1.8.x/Flux and InfluxDB v2.x)
---------------------------------------------------------

Note: The InfluxDB v2 client (https://pypi.org/project/influxdb-client/) 
is only available for Python 3.6 or higher.

The connection should be defined in the Glances configuration file as
following:

.. code-block:: ini

    [influxdb]
    host=localhost
    port=8086
    protocol=http
    org=nicolargo
    bucket=glances
    token=EjFUTWe8U-MIseEAkaVIgVnej_TrnbdvEcRkaB1imstW7gapSqy6_6-8XD-yd51V0zUUpDy-kAdVD1purDLuxA==
    # Prefix will be added for all measurement name
    # Ex: prefix=foo
    #     => foo.cpu
    #     => foo.mem
    # You can also use dynamic values
    #prefix=`hostname`
    prefix=localhost
    # Tags will be added for all measurements
    #tags=foo:bar,spam:eggs
    # You can also use dynamic values
    #tags=system:`uname -s`

and run Glances with:

.. code-block:: console

    $ glances --export influxdb2

Note: if you want to use SSL, please set 'protocol=https'.

Grafana
-------

For Grafana users, Glances provides a dedicated `dashboard`_.

.. image:: ../_static/glances-influxdb.png

To use it, just import the file in your ``Grafana`` web interface.

.. image:: ../_static/grafana.png

.. _dashboard: https://github.com/nicolargo/glances/blob/master/conf/glances-grafana.json

.. _opentsdb:

OpenTSDB
========

You can export statistics to an ``OpenTSDB`` server (time series server).
The connection should be defined in the Glances configuration file as
following:

.. code-block:: ini

    [opentsdb]
    host=localhost
    port=4242
    prefix=glances
    tags=foo:bar,spam:eggs

and run Glances with:

.. code-block:: console

    $ glances --export opentsdb

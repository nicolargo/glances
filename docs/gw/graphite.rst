.. _graphite:

Graphite
========

You can export statistics to a ``Graphite`` server (time series server).

The connection should be defined in the Glances configuration file as
following:

.. code-block:: ini

    [graphite]
    host=localhost
    port=2003
    protocol=udp
    batch_size=1000
    # Prefix will be added for all measurement name
    # Ex: prefix=foo
    #     => foo.cpu
    #     => foo.mem
    # You can also use dynamic values
    #prefix=`hostname`
    prefix=glances

and run Glances with:

.. code-block:: console

    $ glances --export graphite


Note: Only integer and float are supported in the Graphite datamodel.

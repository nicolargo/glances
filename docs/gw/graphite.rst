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

Note 1: the port defines the TCP port where the Graphite listen plain-text requests.

Note 2: As many time-series database, only integer and float are supported in the Graphite datamodel.

Note 3: Under the wood, Glances uses GraphiteSender Python lib (https://github.com/NicoAdrian/graphitesender).

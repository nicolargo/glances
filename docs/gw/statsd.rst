.. _statsd:

StatsD
======

You can export statistics to a ``StatsD`` server (welcome to Graphite!).
The connection should be defined in the Glances configuration file as
following:

.. code-block:: ini

    [statsd]
    host=localhost
    port=8125
    prefix=glances

.. note:: The ``prefix`` is optional (``glances`` by default)

and run Glances with:

.. code-block:: console

    $ glances --export statsd

Glances will generate stats as:

::

    'glances.cpu.user': 12.5,
    'glances.cpu.total': 14.9,
    'glances.load.cpucore': 4,
    'glances.load.min1': 0.19,
    ...

.. _timescale:

TimeScaleDB
===========

TimescaleDB is a time-series database built on top of PostgreSQL.

You can export statistics to a ``TimescaleDB`` server.

The connection should be defined in the Glances configuration file as
following:

.. code-block:: ini

    [timescaledb]
    host=localhost
    port=5432
    db=glances
    user=postgres
    password=password

and run Glances with:

.. code-block:: console

    $ glances --export timescaledb

Data model
-----------

Each plugin will create an `hypertable`_ in the TimescaleDB database.

Tables are partitionned by time (using the ``time`` column).

Tables are segmented by hostname (in order to have multiple host stored in the Glances database).

For plugin with a key (example network where the key is the interface name), the key will
be added as a column in the table (named key_id) and added to the timescaledb.segmentby option.

Current limitations
-------------------

Sensors and Fs plugins are not supported by the TimescaleDB exporter.

In the cpu plugin, the user field is exported as user_cpu (user_percpu in the percpu plugin)
because user is a reserved keyword in PostgreSQL.

.. _hypertable: https://docs.tigerdata.com/use-timescale/latest/hypertables/

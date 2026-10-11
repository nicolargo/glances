.. _cassandra:

Cassandra
=========

You can export statistics to a ``Cassandra`` or ``Scylla`` server.
The connection should be defined in the Glances configuration file as
following:

.. code-block:: ini

    [cassandra]
    host=localhost
    port=9042
    protocol_version=3
    keyspace=glances
    replication_factor=2
    table=localhost
    # Optional authentication
    #username=cassandra
    #password=cassandra

``host``, ``port`` and ``keyspace`` are mandatory. ``table`` defaults to
the ``host`` value. ``keyspace`` and ``table`` must be valid CQL
identifiers (a letter followed by letters, digits or underscores), else
Glances refuses to start the exporter.

and run Glances with:

.. code-block:: console

    $ glances --export cassandra

The data model is the following:

.. code-block:: ini

    CREATE TABLE <table> (plugin text, time timeuuid, stat map<text,float>, PRIMARY KEY (plugin, time))

Only numerical stats are stored in the Cassandra table. All the stats
are converted to float. If a stat cannot be converted to float, it is
not stored in the database.

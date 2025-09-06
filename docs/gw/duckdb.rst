.. _duckdb:

DuckDB
===========

DuckDB is an in-process SQL OLAP database management system.

You can export statistics to a ``DuckDB`` server.

The connection should be defined in the Glances configuration file as
following:

.. code-block:: ini

    [duckdb]
    # database defines where data are stored, can be one of:
    # :memory: (see https://duckdb.org/docs/stable/clients/python/dbapi#in-memory-connection)
    # :memory:glances (see https://duckdb.org/docs/stable/clients/python/dbapi#in-memory-connection)
    # /path/to/glances.db (see https://duckdb.org/docs/stable/clients/python/dbapi#file-based-connection)
    # Or anyone else supported by the API (see https://duckdb.org/docs/stable/clients/python/dbapi)
    database=:memory:

and run Glances with:

.. code-block:: console

    $ glances --export duckdb

Data model
-----------



Current limitations
-------------------

.. _duckdb: https://duckdb.org/


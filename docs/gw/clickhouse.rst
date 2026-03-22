.. clickhouse:

ClickHouse
==========

``ClickHouse`` is an open-source column-oriented DBMS (columnar database management system) for online
analytical processing (OLAP) that allows users to generate analytical reports using SQL queries in real-time.

Glances uses the ``ClickHouse-connect`` Python lib.

The connection should be defined in the Glances configuration file as following:

.. code-block:: ini

    [clickhouse]
    host=localhost
    port=5432
    db=glances
    user=default
    password=password

and run Glances with:

.. code-block:: console

    $ glances --export clickhouse

.. _clickhouse: https://clickhouse.com/clickhouse
.. _clickhouse-connect: https://pypi.org/project/clickhouse-connect/

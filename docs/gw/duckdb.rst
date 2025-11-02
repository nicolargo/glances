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
    # /path/to/glances.db (see https://duckdb.org/docs/stable/clients/python/dbapi#file-based-connection)
    # :memory:glances (see https://duckdb.org/docs/stable/clients/python/dbapi#in-memory-connection)
    # Or anyone else supported by the API (see https://duckdb.org/docs/stable/clients/python/dbapi)
    database=/tmp/glances.db

and run Glances with:

.. code-block:: console

    $ glances --export duckdb

Data model
-----------

The data model is composed of one table per Glances plugin.

Example:

.. code-block:: python

    >>> import duckdb
    >>> db = duckdb.connect(database='/tmp/glances.db', read_only=True)

    >>> db.sql("SELECT * from cpu")
    ┌─────────────────────┬─────────────────┬────────┬────────┬────────┬───┬────────────────────┬─────────────────────┬──────────────────────┬──────────────────────┬──────────────────────┐
    │        time         │   hostname_id   │ total  │  user  │  nice  │ … │ cpu_iowait_warning │ cpu_iowait_critical │ cpu_ctx_switches_c…  │ cpu_ctx_switches_w…  │ cpu_ctx_switches_c…  │
    │ time with time zone │     varchar     │ double │ double │ double │   │       double       │       double        │        double        │        double        │        double        │
    ├─────────────────────┼─────────────────┼────────┼────────┼────────┼───┼────────────────────┼─────────────────────┼──────────────────────┼──────────────────────┼──────────────────────┤
    │ 11:50:25+00         │ nicolargo-xps15 │    8.0 │    5.6 │    0.0 │ … │              5.625 │                6.25 │             640000.0 │             720000.0 │             800000.0 │
    │ 11:50:27+00         │ nicolargo-xps15 │    4.3 │    3.2 │    0.0 │ … │              5.625 │                6.25 │             640000.0 │             720000.0 │             800000.0 │
    │ 11:50:29+00         │ nicolargo-xps15 │    4.3 │    3.2 │    0.0 │ … │              5.625 │                6.25 │             640000.0 │             720000.0 │             800000.0 │
    │ 11:50:31+00         │ nicolargo-xps15 │   14.9 │   15.7 │    0.0 │ … │              5.625 │                6.25 │             640000.0 │             720000.0 │             800000.0 │
    │ 11:50:33+00         │ nicolargo-xps15 │   14.9 │   15.7 │    0.0 │ … │              5.625 │                6.25 │             640000.0 │             720000.0 │             800000.0 │
    │ 11:50:35+00         │ nicolargo-xps15 │    8.2 │    7.8 │    0.0 │ … │              5.625 │                6.25 │             640000.0 │             720000.0 │             800000.0 │
    │ 11:50:37+00         │ nicolargo-xps15 │    8.2 │    7.8 │    0.0 │ … │              5.625 │                6.25 │             640000.0 │             720000.0 │             800000.0 │
    │ 11:50:39+00         │ nicolargo-xps15 │   12.7 │   10.3 │    0.0 │ … │              5.625 │                6.25 │             640000.0 │             720000.0 │             800000.0 │
    │ 11:50:41+00         │ nicolargo-xps15 │   12.7 │   10.3 │    0.0 │ … │              5.625 │                6.25 │             640000.0 │             720000.0 │             800000.0 │
    │ 11:50:43+00         │ nicolargo-xps15 │   12.2 │   10.3 │    0.0 │ … │              5.625 │                6.25 │             640000.0 │             720000.0 │             800000.0 │
    │      ·              │        ·        │     ·  │     ·  │     ·  │ · │                ·   │                  ·  │                 ·    │                 ·    │                 ·    │
    │      ·              │        ·        │     ·  │     ·  │     ·  │ · │                ·   │                  ·  │                 ·    │                 ·    │                 ·    │
    │      ·              │        ·        │     ·  │     ·  │     ·  │ · │                ·   │                  ·  │                 ·    │                 ·    │                 ·    │
    │ 11:51:29+00         │ nicolargo-xps15 │   10.1 │    7.4 │    0.0 │ … │              5.625 │                6.25 │             640000.0 │             720000.0 │             800000.0 │
    │ 11:51:32+00         │ nicolargo-xps15 │   10.1 │    7.4 │    0.0 │ … │              5.625 │                6.25 │             640000.0 │             720000.0 │             800000.0 │
    │ 11:51:34+00         │ nicolargo-xps15 │    6.6 │    4.9 │    0.0 │ … │              5.625 │                6.25 │             640000.0 │             720000.0 │             800000.0 │
    │ 11:51:36+00         │ nicolargo-xps15 │    6.6 │    4.9 │    0.0 │ … │              5.625 │                6.25 │             640000.0 │             720000.0 │             800000.0 │
    │ 11:51:38+00         │ nicolargo-xps15 │    9.9 │    7.5 │    0.0 │ … │              5.625 │                6.25 │             640000.0 │             720000.0 │             800000.0 │
    │ 11:51:40+00         │ nicolargo-xps15 │    9.9 │    7.5 │    0.0 │ … │              5.625 │                6.25 │             640000.0 │             720000.0 │             800000.0 │
    │ 11:51:42+00         │ nicolargo-xps15 │    4.0 │    3.1 │    0.0 │ … │              5.625 │                6.25 │             640000.0 │             720000.0 │             800000.0 │
    │ 11:51:44+00         │ nicolargo-xps15 │    4.0 │    3.1 │    0.0 │ … │              5.625 │                6.25 │             640000.0 │             720000.0 │             800000.0 │
    │ 11:51:46+00         │ nicolargo-xps15 │   11.1 │    8.8 │    0.0 │ … │              5.625 │                6.25 │             640000.0 │             720000.0 │             800000.0 │
    │ 11:51:48+00         │ nicolargo-xps15 │   11.1 │    8.8 │    0.0 │ … │              5.625 │                6.25 │             640000.0 │             720000.0 │             800000.0 │
    ├─────────────────────┴─────────────────┴────────┴────────┴────────┴───┴────────────────────┴─────────────────────┴──────────────────────┴──────────────────────┴──────────────────────┤
    │ 41 rows (20 shown)                                                                                                                                             47 columns (10 shown) │
    └──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

    >>> db.sql("SELECT * from cpu").fetchall()[0]
    (datetime.time(11, 50, 25, tzinfo=datetime.timezone.utc), 'nicolargo-xps15', 8.0, 5.6, 0.0, 2.3, 91.9, 0.1, 0.0, 0.0, 0.0, 0, 0, 0, 0, 16, 2.4103684425354004, 90724823, 0, 63323797, 0, 30704572, 0, 0, 0, 1200.0, 65.0, 75.0, 85.0, True, 50.0, 70.0, 90.0, True, 50.0, 70.0, 90.0, True, 50.0, 70.0, 90.0, 5.0, 5.625, 6.25, 640000.0, 720000.0, 800000.0)


    >>> db.sql("SELECT * from network")
    ┌─────────────────────┬─────────────────┬────────────────┬────────────┬────────────┬───┬─────────────────────┬────────────────┬────────────────────┬────────────────────┬───────────────────┐
    │        time         │   hostname_id   │     key_id     │ bytes_sent │ bytes_recv │ … │ network_tx_critical │  network_hide  │ network_hide_no_up │ network_hide_no_ip │ network_hide_zero │
    │ time with time zone │     varchar     │    varchar     │   int64    │   int64    │   │       double        │    varchar     │      boolean       │      boolean       │      boolean      │
    ├─────────────────────┼─────────────────┼────────────────┼────────────┼────────────┼───┼─────────────────────┼────────────────┼────────────────────┼────────────────────┼───────────────────┤
    │ 11:50:25+00         │ nicolargo-xps15 │ interface_name │     407761 │      32730 │ … │                90.0 │ [docker.*, lo] │ true               │ true               │ true              │
    │ 11:50:27+00         │ nicolargo-xps15 │ interface_name │       2877 │       4857 │ … │                90.0 │ [docker.*, lo] │ true               │ true               │ true              │
    │ 11:50:29+00         │ nicolargo-xps15 │ interface_name │      44504 │      32555 │ … │                90.0 │ [docker.*, lo] │ true               │ true               │ true              │
    │ 11:50:31+00         │ nicolargo-xps15 │ interface_name │    1092285 │      48600 │ … │                90.0 │ [docker.*, lo] │ true               │ true               │ true              │
    │ 11:50:33+00         │ nicolargo-xps15 │ interface_name │     150119 │      43805 │ … │                90.0 │ [docker.*, lo] │ true               │ true               │ true              │
    │ 11:50:35+00         │ nicolargo-xps15 │ interface_name │      34424 │      14825 │ … │                90.0 │ [docker.*, lo] │ true               │ true               │ true              │
    │ 11:50:37+00         │ nicolargo-xps15 │ interface_name │      19382 │      33614 │ … │                90.0 │ [docker.*, lo] │ true               │ true               │ true              │
    │ 11:50:39+00         │ nicolargo-xps15 │ interface_name │      53060 │      39780 │ … │                90.0 │ [docker.*, lo] │ true               │ true               │ true              │
    │ 11:50:41+00         │ nicolargo-xps15 │ interface_name │     371914 │      78626 │ … │                90.0 │ [docker.*, lo] │ true               │ true               │ true              │
    │ 11:50:43+00         │ nicolargo-xps15 │ interface_name │      82356 │      60612 │ … │                90.0 │ [docker.*, lo] │ true               │ true               │ true              │
    │      ·              │        ·        │       ·        │         ·  │         ·  │ · │                  ·  │       ·        │  ·                 │  ·                 │  ·                │
    │      ·              │        ·        │       ·        │         ·  │         ·  │ · │                  ·  │       ·        │  ·                 │  ·                 │  ·                │
    │      ·              │        ·        │       ·        │         ·  │         ·  │ · │                  ·  │       ·        │  ·                 │  ·                 │  ·                │
    │ 11:51:29+00         │ nicolargo-xps15 │ interface_name │       3766 │       9977 │ … │                90.0 │ [docker.*, lo] │ true               │ true               │ true              │
    │ 11:51:32+00         │ nicolargo-xps15 │ interface_name │     188036 │      18668 │ … │                90.0 │ [docker.*, lo] │ true               │ true               │ true              │
    │ 11:51:34+00         │ nicolargo-xps15 │ interface_name │        543 │       2451 │ … │                90.0 │ [docker.*, lo] │ true               │ true               │ true              │
    │ 11:51:36+00         │ nicolargo-xps15 │ interface_name │       8247 │       7275 │ … │                90.0 │ [docker.*, lo] │ true               │ true               │ true              │
    │ 11:51:38+00         │ nicolargo-xps15 │ interface_name │       7252 │        986 │ … │                90.0 │ [docker.*, lo] │ true               │ true               │ true              │
    │ 11:51:40+00         │ nicolargo-xps15 │ interface_name │        172 │        132 │ … │                90.0 │ [docker.*, lo] │ true               │ true               │ true              │
    │ 11:51:42+00         │ nicolargo-xps15 │ interface_name │       8080 │       6640 │ … │                90.0 │ [docker.*, lo] │ true               │ true               │ true              │
    │ 11:51:44+00         │ nicolargo-xps15 │ interface_name │      19660 │      17830 │ … │                90.0 │ [docker.*, lo] │ true               │ true               │ true              │
    │ 11:51:46+00         │ nicolargo-xps15 │ interface_name │    1007030 │      84170 │ … │                90.0 │ [docker.*, lo] │ true               │ true               │ true              │
    │ 11:51:48+00         │ nicolargo-xps15 │ interface_name │     128947 │      18087 │ … │                90.0 │ [docker.*, lo] │ true               │ true               │ true              │
    ├─────────────────────┴─────────────────┴────────────────┴────────────┴────────────┴───┴─────────────────────┴────────────────┴────────────────────┴────────────────────┴───────────────────┤
    │ 41 rows (20 shown)                                                                                                                                                  28 columns (10 shown) │
    └───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘


.. _duckdb: https://duckdb.org/


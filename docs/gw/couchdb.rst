.. _couchdb:

CouchDB
=======

You can export statistics to a ``CouchDB`` server.
The connection should be defined in the Glances configuration file as
following:

.. code-block:: ini

    [couchdb]
    host=localhost
    port=5984
    db=glances
    user=root
    password=example

and run Glances with:

.. code-block:: console

    $ glances --export couchdb

Documents are stored in native ``JSON`` format. Glances adds ``"type"``
and ``"time"`` entries:

- ``type``: plugin name
- ``time``: timestamp  (format: "2016-09-24T16:39:08.524Z")

Example of Couch Document for the load stats:

.. code-block:: json

    {
       "_id": "36cbbad81453c53ef08804cb2612d5b6",
       "_rev": "1-382400899bec5615cabb99aa34df49fb",
       "min15": 0.33,
       "time": "2016-09-24T16:39:08.524Z",
       "min5": 0.4,
       "cpucore": 4,
       "load_warning": 1,
       "min1": 0.5,
       "history_size": 28800,
       "load_critical": 5,
       "type": "load",
       "load_careful": 0.7
    }

You can view the result using the CouchDB utils URL: http://127.0.0.1:5984/_utils/database.html?glances.

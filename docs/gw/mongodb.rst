.. _couchdb:

MongoDB
=======

You can export statistics to a ``MongoDB`` server.
The connection should be defined in the Glances configuration file as
following:

.. code-block:: ini

    [mongodb]
    host=localhost
    port=27017
    db=glances
    user=root
    password=example

and run Glances with:

.. code-block:: console

    $ glances --export mongodb

Documents are stored in native the configured database (glances by default)
with one collection per plugin.

Example of MongoDB Document for the load stats:

.. code-block:: json

    {
        _id: ObjectId('63d78ffee5528e543ce5af3a'),
        min1: 1.46337890625,
        min5: 1.09619140625,
        min15: 1.07275390625,
        cpucore: 4,
        history_size: 1200,
        load_disable: 'False',
        load_careful: 0.7,
        load_warning: 1,
        load_critical: 5
    }

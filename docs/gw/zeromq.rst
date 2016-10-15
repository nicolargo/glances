.. _zeromq:

ZeroMQ
======

You can export statistics to a ``ZeroMQ`` server.
The connection should be defined in the Glances configuration file as
following:

.. code-block:: ini

    [zeromq]
    host=127.0.0.1
    port=5678
    prefix=G

Note: Glances envelopes the stats in a publish message with two frames.

- first frame containing the following prefix (as STRING)
- second frame with the Glances plugin name (as STRING)
- third frame with the Glances plugin stats (as JSON)

Run Glances with:

.. code-block:: console

    $ glances --export-zeromq

Following is a simple Python client to subscribe to the Glances stats:

.. code-block:: python

    # -*- coding: utf-8 -*-
    #
    # ZeroMQ subscriber for Glances
    #

    import json
    import zmq

    context = zmq.Context()

    subscriber = context.socket(zmq.SUB)
    subscriber.setsockopt(zmq.SUBSCRIBE, 'G')
    subscriber.connect("tcp://127.0.0.1:5678")

    while True:
        _, plugin, data_raw = subscriber.recv_multipart()
        data = json.loads(data_raw)
        print('{} => {}'.format(plugin, data))

    subscriber.close()
    context.term()

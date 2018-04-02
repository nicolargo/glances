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

Glances `envelopes`_ the stats before publishing it. The message is
composed of three frames:

1. the prefix configured in the [zeromq] section (as STRING)
2. the Glances plugin name (as STRING)
3. the Glances plugin stats (as JSON)

Run Glances with:

.. code-block:: console

    $ glances --export zeromq

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

.. _envelopes: http://zguide.zeromq.org/page:all#Pub-Sub-Message-Envelopes

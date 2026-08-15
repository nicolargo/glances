.. _kafka:

Kafka
=====

You can export statistics to a ``Kafka`` server.
The connection should be defined in the Glances configuration file as
following:

.. code-block:: ini

    [kafka]
    host=localhost
    port=9092
    topic=glances
    #compression=gzip
    # Tags will be added for all events
    #tags=foo:bar,spam:eggs
    # You can also use dynamic values
    #tags=hostname:`hostname -f`

Note: you can enable the compression but it consume CPU on your host.

and run Glances with:

.. code-block:: console

    $ glances --export kafka

Stats  are sent in native ``JSON`` format to the topic:

- ``key``: plugin name
- ``value``: JSON dict

Example of record for the memory plugin:

.. code-block:: ini

    ConsumerRecord(topic=u'glances', partition=0, offset=1305, timestamp=1490460592248, timestamp_type=0, key='mem', value=u'{"available": 2094710784, "used": 5777428480, "cached": 2513543168, "mem_careful": 50.0, "percent": 73.4, "free": 2094710784, "mem_critical": 90.0, "inactive": 2361626624, "shared": 475504640, "history_size": 28800.0, "mem_warning": 70.0, "total": 7872139264, "active": 4834361344, "buffers": 160112640}', checksum=214895201, serialized_key_size=3, serialized_value_size=303)

Python code example to consume Kafka Glances plugin:

.. code-block:: python

    from kafka import KafkaConsumer
    import json

    consumer = KafkaConsumer('glances', value_deserializer=json.loads)
    for s in consumer:
      print(s)

.. _mqtt:

MQTT
========

You can export statistics to an ``MQTT`` server. The
connection should be defined in the Glances configuration file as
following:

.. code-block:: ini

    [mqtt]
    host=localhost
    port=883
    user=glances
    password=glances
    topic=glances
    topic_structure=per-metric

and run Glances with:

.. code-block:: console

    $ glances --export mqtt

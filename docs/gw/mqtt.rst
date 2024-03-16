.. _mqtt:

MQTT
========

You can export statistics to an ``MQTT`` server. The
connection should be defined in the Glances configuration file as
following:

.. code-block:: ini

    [mqtt]
    host=localhost
    # Overwrite device name in the topic (see detail in PR#2701)
    #devicename=localhost
    port=883
    tls=true
    user=glances
    password=glances
    topic=glances
    topic_structure=per-metric
    callback_api_version=2

and run Glances with:

.. code-block:: console

    $ glances --export mqtt

The topic_structure field aims at configuring the way stats are exported to MQTT (see #1798):
- per-metric: one event per metric (default behavior)
- per-plugin: one event per plugin

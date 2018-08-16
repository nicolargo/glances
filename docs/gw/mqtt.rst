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

and run Glances with:

.. code-block:: console

    $ glances --export mqtt

.. _rabbitmq:

RabbitMQ
========

You can export statistics to an ``RabbitMQ`` server (AMQP Broker). The
connection should be defined in the Glances configuration file as
following:

.. code-block:: ini

    [rabbitmq]
    host=localhost
    port=5672
    user=glances
    password=glances
    queue=glances_queue
    #protocol=amqps

and run Glances with:

.. code-block:: console

    $ glances --export rabbitmq

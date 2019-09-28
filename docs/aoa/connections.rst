.. _connections:

Connections
===========

.. image:: ../_static/connections.png

This plugin display extended information about network connections.


The states are the following:
- Listen: all ports created by server and waiting for a client to connect
- Initialized: All states when a connection is initialized (sum of SYN_SENT and SYN_RECEIVED)
- Established: All established connections between a client and a server
- Terminated: All states when a connection is terminated (FIN_WAIT1, CLOSE_WAIT, LAST_ACK, FIN_WAIT2, TIME_WAIT and CLOSE)

The configuration should be done in the ``[connections]`` section of the
Glances configuration file.

By default the plugin is disabled.

.. code-block:: ini

    [connections]
    disable=False

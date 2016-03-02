.. _network:

Network
=======

.. image:: ../_static/network.png

Glances displays the network interface bit rate. The unit is adapted
dynamically (bit/s, kbit/s, Mbit/s, etc).

Alerts are only set if the maximum speed per network interface is
available (see sample in the configuration file).

It's also possibile to define:

- a list of network interfaces to hide
- per-interface limit values
- aliases for interface name

in the ``[network]`` section of the configuration file.

For example, if you want to hide the loopback interface (lo) and all the
virtual docker interface (docker0, docker1, ...):

.. code-block:: ini

    [network]
    hide=lo,docker.*

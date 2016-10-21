.. _wifi:

Wifi
=====

.. image:: ../_static/wifi.png

Glances displays the Wifi hotspot name and quality where the host is connected.
If Glances is ran as root, then all the available hotspots are displayed.

It's also possible to disable the scan on a specific interface from the
configuration file (``[network]`` section). For example, if you want to
hide the loopback interface (lo) and all the virtual docker interface:

.. code-block:: ini

    [wifi]
    hide=lo,docker.*

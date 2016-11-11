.. _wifi:

Wifi
=====

*Availability: Linux*

.. image:: ../_static/wifi.png

Glances displays the Wifi hotspots' name and signal quality.
If Glances is ran as root, then all the available hotspots are displayed.

In the configuration file, you can define signal quality thresholds.
"Poor" quality is between -100 and -85dBm, "Good" quality between -85
and -60dBm, and "Excellent" between -60 and -40dBm.

It's also possible to disable the scan on a specific interface from the
configuration file (``[wifi]`` section). For example, if you want to
hide the loopback interface (lo) and all the virtual docker interfaces:

.. code-block:: ini

    [wifi]
    hide=lo,docker.*
    # Define SIGNAL thresholds in dBm (lower is better...)
    careful=-65
    warning=-75
    critical=-85

You can disable this plugin using the --disable-wifi option or by heating
the 'W' from the user interface.

.. _wifi:

Wi-Fi
=====

*Availability: Linux only*

The signal strength is read over nl80211 (the same data as ``iw dev <interface> link``).
When nl80211 is not available, Glances falls back to the ``/proc/net/wireless`` file.

.. image:: ../_static/wifi.png

In the configuration file, you can define signal quality thresholds:

- ``"Poor"`` quality is between -100 and -85dBm
- ``"Good"`` quality between -85 and -60dBm
- ``"Excellent"`` between -60 and -40dBm

Thresholds for the signal quality can be defined in the configuration file:

.. code-block:: ini

    [wifi]
    disable=False
    careful=-65
    warning=-75
    critical=-85

You can disable this plugin using the ``--disable-plugin wifi`` option or by
hitting the ``W`` key from the user interface.

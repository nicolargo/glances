.. _wifi:

Wi-Fi
=====

*Availability: Linux only*

If ``nmcli`` is available on the system, Glances displays the hotspot name,
the security type and the Wi-Fi signal quality:

.. image:: ../_static/wifi.png

or, as a backup, the file ``/proc/net/wireless`` is used to display the signal quality:

.. image:: ../_static/wifi2.png

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

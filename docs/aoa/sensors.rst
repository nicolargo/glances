.. _sensors:

Sensors
=======

*Availability: Linux*

.. image:: ../_static/sensors.png

Glances can display the sensors information using ``psutil``,
``hddtemp`` and ``batinfo``:
- motherboard and CPU temperatures
- hard disk temperature
- battery capacity

There is no alert on this information.

.. note 1::
    Limit values and sensors alias names can be defined in the
    configuration file under the ``[sensors]`` section.

.. note 2::
    The support for multiple batteries is only available if
    you have the batinfo Python lib installed on your system
    because for the moment PSUtil only support one battery.

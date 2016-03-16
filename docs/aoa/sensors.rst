.. _sensors:

Sensors
=======

*Availability: Linux*

.. image:: ../_static/sensors.png

Glances can displays the sensors information using ``lm-sensors``,
``hddtemp`` and `batinfo`_.

All of the above libraries are available only on Linux.

As of ``lm-sensors``, a filter is being applied in order to display
temperature and fan speed only.

There is no alert on this information.

.. note::
    Limit values and sensors alias names can be defined in the
    configuration file under the ``[sensors]`` section.

.. _batinfo: https://github.com/nicolargo/batinfo

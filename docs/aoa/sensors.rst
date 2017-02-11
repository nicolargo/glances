.. _sensors:

Sensors
=======

*Availability: Linux*

.. image:: ../_static/sensors.png

Glances can displays the sensors information using ``PsUtil`` and ``hddtemp``.

As of ``lm-sensors``, a filter is being applied in order to display
temperature and fan speed only.

There is no alert on this information.

.. note::
    Limit values and sensors alias names can be defined in the
    configuration file under the ``[sensors]`` section.

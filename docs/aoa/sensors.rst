.. _sensors:

Sensors
=======

*Availability: Linux*

.. image:: ../_static/sensors.png

Glances can display the sensors information using ``psutil`` and/or
``hddtemp``.

There is no alert on this information.

.. note::
    Limit values and sensors alias names can be defined in the
    configuration file under the ``[sensors]`` section.

.. note::
    This plugin is disabled by default in the configuration file.
    To enable it just use the following option:

    # glances --enable-plugin sensors

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

.. note 3::
    If a sensors has temperature and fan speed with the same name unit,
    it is possible to alias it using:
    alias=unitname_temperature_core_alias:Alias for temp,unitname_fan_speed_alias:Alias for fan speed

.. note 4::
    If a sensors has multiple identical features names (see #2280), then
    Glances will add a suffix to the feature name.
    For example, if you have one sensor with two Composite features, the
    second one will be named Composite_1.

.. note 5::
    The plugin could crash on some operating system (FreeBSD) with the
    TCP or UDP blackhole option > 0 (see issue #2106). In this case, you
    should disable the sensors (--disable-plugin sensors or from the
    configuration file).
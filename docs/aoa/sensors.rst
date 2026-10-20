.. _sensors:

Sensors
=======

*Availability: Linux*

.. image:: ../_static/sensors.png

Glances can display the sensors information using ``psutil`` and
``batinfo``:

- motherboard and CPU temperatures
- fan speeds
- hard disk temperature
- battery capacity

Hard disk temperatures are read from the kernel hwmon interface, like the
other temperatures. On Linux, load the ``drivetemp`` kernel module
(``sudo modprobe drivetemp``) to expose SATA drive temperatures; NVMe drives
expose theirs natively. The ``smart`` plugin also reports drive temperatures
from the SMART attributes.

.. note::

    The ``hddtemp`` daemon is no longer maintained upstream. Its support was
    removed in Glances 5.0: the ``[hddtemp]`` configuration section and the
    ``temperature_hdd_*`` keys of the ``[sensors]`` section are ignored (a
    warning is logged at startup for the ``temperature_hdd_careful``,
    ``_warning`` and ``_critical`` thresholds). Set thresholds for a drive
    through its ``temperature_core_<label>_*`` keys instead.

Limit values and sensors alias names can be defined in the configuration
file under the ``[sensors]`` section.

Limit can be defined for a specific sensor, a type of sensor or defineby the system
thresholds (default behavor).

Sensors are slow to read, so the plugin is refreshed every 30 seconds by
default (use the ``refresh`` key of the ``[sensors]`` section to change it).

.. code-block:: ini

    [sensors]
    # Sensors core thresholds (in Celsius...)
    # Note: By default values are grabbed from the system (if values are available)
    # Core temperature thresholds in °C
    # Default values if not defined: 45/52/60
    temperature_core_careful=45
    temperature_core_warning=65
    temperature_core_critical=80
    # Battery threshold in %
    # Default values if not defined: 70/80/90
    #battery_careful=70
    #battery_warning=80
    #battery_critical=90
    # Fan speed threshold in RPM
    #fan_speed_careful=100
    # Overwrite thresholds for a specific sensor
    #temperature_core_Ambient_careful=40
    #temperature_core_Ambient_warning=60
    #temperature_core_Ambient_critical=85
    # Logs and actions for a specific sensor use the <label>_value_ prefix
    #Ambient_value_log=True
    #Ambient_value_critical_action=echo "{{_glances_timestamp}} {{label}} temperature {{value}}{{unit}}" > /tmp/temperature.alert
    # Display sensors in mean (fold same-prefix sensors into "<prefix> (mean)")
    #mean=true
    #temperature_core_mean=true
    #fan_speed_mean=true
    #battery_mean=true
    # Sensors alias
    #alias=core 0:CPU Core 0,core 1:CPU Core 1

Displaying sensors in mean
--------------------------

When a sensor type exposes several similarly named entries (``Core 0``,
``Core 1``, ...), Glances can fold them into a single averaged line named
``<prefix> (mean)``. Folding only applies to a group of **more than one**
sensor sharing the same prefix; a lone sensor is left untouched.

Two levels of configuration are available under the ``[sensors]`` section:

- ``mean=true`` — global toggle. Every sensor type with more than one line
  is displayed in mean.
- ``<type>_mean=true|false`` — per-type override (``temperature_core_mean``,
  ``fan_speed_mean``, ``battery_mean``). When set, it always wins over the
  global ``mean`` value.

Both default to ``false``. The per-type key can opt a type *out* while the
global toggle is on, or *in* while it is off. For example, to display every
type in mean except the battery:

.. code-block:: ini

    [sensors]
    mean=true
    battery_mean=false

.. note 1::
    The support for multiple batteries is only available if
    you have the batinfo Python lib installed on your system
    because for the moment PSUtil only support one battery.

.. note 2::
    If a sensors has temperature and fan speed with the same name unit,
    it is possible to alias it using:
    alias=unitname_temperature_core:Alias for temp,unitname_fan_speed:Alias for fan speed

.. note 3::
    If a sensors has multiple identical features names (see #2280), then
    Glances will add a suffix to the feature name.
    For example, if you have one sensor with two Composite features, the
    second one will be named Composite_1.

.. note 4::
    The plugin could crash on some operating system (FreeBSD) with the
    TCP or UDP blackhole option > 0 (see issue #2106). In this case, you
    should disable the sensors (--disable-plugin sensors or from the
    configuration file).
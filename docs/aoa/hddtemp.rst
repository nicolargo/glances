.. _sensors:

HDD temperature sensor
======================

*Availability: Linux*

This plugin will add HDD temperature to the sensors plugin.

On your Linux system, you will nedd to have:
- hddtemp package installed
- hddtemp service up and running (check it with systemctl status hddtemp)
- the TCP port 7634  openned on your local Firewall (if it is enabled on your system)

There is no alert on this information.

.. note::
    Limit values and sensors alias names can be defined in the
    configuration file under the ``[sensors]`` section.

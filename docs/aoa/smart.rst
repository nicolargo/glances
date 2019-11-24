.. _smart:

SMART
=====

*Availability: all but Mac OS*

*Dependency: this plugin uses the optional pySMART Python lib*

This plugin is disable by default, please use the --enable smart option
to enable it.

.. image:: ../_static/smart.png

Glances displays all the SMART attributes.

How to read the information:

- The first line display the name and model of the device
- The first column is the SMART attribute name
- The second column is the SMART attribute raw value

.. warning::
    This plugin needs administrator rights. Please run Glances as root/admin.

.. _header:

Header
======

.. image:: ../_static/header.png

The header shows the hostname, OS name, release version, platform
architecture IP addresses (private and public) and system uptime.
Additionally, on GNU/Linux, it also shows the kernel version.

In client mode, the server connection status is also displayed.

It is possible to define time interval to be used for refreshing the
public IP address (default is 300 seconds) from the configuration
file under the ``[ip]`` section:

.. code-block:: ini
    [ip]
    public_refresh_interval=240

**NOTE:** Setting low values will result in frequent HTTP request to
the IP detection servers. Recommended range: 120-600 seconds

**Connected**:

.. image:: ../_static/connected.png

**Disconnected**:

.. image:: ../_static/disconnected.png

If you are hosted on an ``OpenStack`` instance, some additional
information can be displayed (AMI-ID, region).

.. image:: ../_static/aws.png

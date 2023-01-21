.. _header:

Header
======

.. image:: ../_static/header.png

The header shows the hostname, OS name, release version, platform
architecture IP addresses (private and public) and system uptime.
Additionally, on GNU/Linux, it also shows the kernel version.

In client mode, the server connection status is also displayed.

It is possible to disable or define time interval to be used for refreshing the
public IP address (default is 300 seconds) from the configuration
file under the ``[ip]`` section:

.. code-block:: ini
    [ip]
    public_refresh_interval=300
    public_ip_disabled=True


**NOTE:** Setting low values for `public_refresh_interval` will result in frequent
HTTP requests to the IP detection servers. Recommended range: 120-600 seconds.
Glances uses online services in order to get the IP addresses. Your IP address could be
blocked if too many requests are done.

If the Censys options are configured, the public IP address is also analysed (with the same interval)
and additional information is displayed.

.. code-block:: ini
    [ip]
    public_refresh_interval=300
    public_ip_disabled=True
    censys_url=https://search.censys.io/api
    # Get your own credential here: https://search.censys.io/account/api
    censys_username=CENSYS_API_ID
    censys_password=CENSYS_API_SECRET
    # List of fields to be displayed in user interface (comma separated)
    censys_fields=location:continent,location:country,autonomous_system:name

**Note:** Access to the Censys Search API need an account (https://censys.io/login).

Example:

.. image:: ../_static/ip.png

**Connected**:

.. image:: ../_static/connected.png

**Disconnected**:

.. image:: ../_static/disconnected.png

If you are hosted on an ``OpenStack`` instance, some additional
information can be displayed (AMI-ID, region).

.. image:: ../_static/aws.png

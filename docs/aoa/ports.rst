.. _ports:

Ports
=====

*Availability: All*

.. image:: ../_static/ports.png

This plugin aims at providing a list of hosts/port to scan.

You can define ICMP or TCP ports scan.

The list should be define in the ``[ports]`` section of the Glances configuration file.

.. code-block:: ini

    [ports]
    # Ports scanner plugin configuration
    # Interval in second between scan
    refresh=30
    # Set the default timeout for a scan (can be overwrite in the scan list)
    timeout=3
    # If True, add the default gateway on top of the scan list
    port_default_gateway=True
    # Define the scan list
    # host (name or IP) is mandatory
    # port (TCP port number) is optional (if not set, use ICMP)
    # description is optional (if not set, define to host:port)
    port_1_host=192.168.0.1
    port_1_port=80
    port_1_description=Home Box
    port_2_host=www.free.fr
    port_2_description=My ISP
    port_3_host=www.google.com
    port_3_description=Internet

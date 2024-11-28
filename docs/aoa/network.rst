.. _network:

Network
=======

.. image:: ../_static/network.png

Glances displays the network interface bit rate. The unit is adapted
dynamically (bit/s, kbit/s, Mbit/s, etc).

If the interface speed is detected (not on all systems), the defaults
thresholds are applied (70% for careful, 80% warning and 90% critical).
It is possible to define this percents thresholds from the configuration
file. It is also possible to define per interface bit rate thresholds.
In this case thresholds values are define in bps.

Additionally, you can define:

- a list of network interfaces to hide
- automatically hide interfaces not up
- automatically hide interfaces without IP address
- per-interface limit values
- aliases for interface name

The configuration should be done in the ``[network]`` section of the
Glances configuration file.

For example, if you want to hide the loopback interface (lo) and all the
virtual docker interface (docker0, docker1, ...):

.. code-block:: ini

    [network]
    # Default bitrate thresholds in % of the network interface speed
    # Default values if not defined: 70/80/90
    rx_careful=70
    rx_warning=80
    rx_critical=90
    tx_careful=70
    tx_warning=80
    tx_critical=90
    # Define the list of hidden network interfaces (comma-separated regexp)
    hide=docker.*,lo
    # Define the list of network interfaces to show (comma-separated regexp)
    #show=eth0,eth1
    # Automatically hide interface not up (default is False)
    hide_no_up=True
    # Automatically hide interface with no IP address (default is False)
    hide_no_ip=True
    # Set hide_zero to True to automatically hide interface with no traffic
    hide_zero=False
    # WLAN 0 alias
    alias=wlan0:Wireless IF
    # It is possible to overwrite the bitrate thresholds per interface
    # WLAN 0 Default limits (in bits per second aka bps) for interface bitrate
    wlan0_rx_careful=4000000
    wlan0_rx_warning=5000000
    wlan0_rx_critical=6000000
    wlan0_rx_log=True
    wlan0_tx_careful=700000
    wlan0_tx_warning=900000
    wlan0_tx_critical=1000000
    wlan0_tx_log=True

Filtering is based on regular expression. Please be sure that your regular
expression works as expected. You can use an online tool like `regex101`_ in
order to test your regular expression.

You also can automatically hide interface with no traffic using the
``hide_zero`` configuration key. The optional ``hide_threshold_bytes`` option
can also be used to set a threshold higher than zero.

.. code-block:: ini

    [diskio]
    hide_zero=True
    hide_threshold_bytes=0

.. _regex101: https://regex101.com/

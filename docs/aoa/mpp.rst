.. _mpp:

MPP
===

Note: this plugin is disable by default in glances.conf file.

The MPP (Media Process Platform) plugin monitors hardware video encoder/decoder engines on Rockchip supported platforms.

For the moment, only following MPP engines are supported on modern Linux Kernel:
- Rockchip: load, utilization, active sessions (RKVENC, RKVDEC, RKJPEGD)

Tested on Rockchip RV1126B-P platform with Linux Kernel 6.1.141 and MPP 4.0.0.

Prerequisite
------------

The Rockchip kernel driver only publishes engine load once
``/proc/mpp_service/load_interval`` is non-zero. Glances does **not** set it:
a monitoring tool should not mutate a global kernel setting that other
readers share.

Until you set it yourself, the plugin reports no engines at all. As root,
once per boot::

    echo 1000 > /proc/mpp_service/load_interval

To make it persistent, set it from a systemd unit ordered after the MPP
driver is loaded, or from your distribution's local startup script.

Glances logs a single warning at startup when the MPP service is present but
reports no load, so a forgotten setting is easy to spot in the logs.

.. code-block:: ini

    [mpp]
    disable=False
    # Default MPP engine load thresholds in %
    load_careful=50
    load_warning=70
    load_critical=90

Each entry in the list shows:

===============  ===================================================
``name``         Engine name (e.g. RKVENC, RKVDEC, RKJPEGD)
``type``         Engine type (enc, dec, jpeg)
``load``         Engine load (%)
``utilization``  Engine utilization (%)
``sessions``     Number of active sessions
===============  ===================================================

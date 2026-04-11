.. _mpp:

MPP
===

Note: this plugin is disable by default in glances.conf file.

The MPP (Media Process Platform) plugin monitors hardware video encoder/decoder engines on Rockchip supported platforms.

For the moment, only following MPP engines are supported on modern Linux Kernel:
- Rockchip: load, utilization, active sessions (RKVENC, RKVDEC, RKJPEGD)

Tested on Rockchip RV1126B-P platform with Linux Kernel 6.1.141 and MPP 4.0.0.

.. image:: ../_static/mpp.png

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

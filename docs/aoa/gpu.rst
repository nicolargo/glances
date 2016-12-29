.. _gpu:

GPU
===

The GPU plugin is **only** compatible with NVIDIA GPU. You also need to
install the Python `pynvml`_ library on our system.

The GPU stats are shown as a percentage or value and for the configured
refresh time. The total GPU usage is displayed on the first line, the
memory consumption on the second one.

.. image:: ../_static/gpu.png

If you click on the ``6`` short key, the per GPU view is displayed:

.. image:: ../_static/pergpu.png

Note: you can also start Glances with the --meangpu option to display the
first view by default.

You can change the thresolds limits in the configuration file:

.. code-block:: ini

      [gpu]
      # Default processor values if not defined: 50/70/90
      proc_careful=50
      proc_warning=70
      proc_critical=90
      # Default memory values if not defined: 50/70/90
      mem_careful=50
      mem_warning=70
      mem_critical=90

Legend:

================= ============
GPU (PROC/MEM)    Status
================= ============
``<50%``          ``OK``
``>50%``          ``CAREFUL``
``>70%``          ``WARNING``
``>90%``          ``CRITICAL``
================= ============

.. _pynvml: https://pypi.python.org/pypi/nvidia-ml-py

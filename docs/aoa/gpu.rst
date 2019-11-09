.. _gpu:

GPU
===

.. note::
    You need to install the `py3nvml`_ library on your system.
    Or `nvidia-ml-py3`_ for Glances 3.1.3 or lower.

The GPU stats are shown as a percentage of value and for the configured
refresh time. It displays:

- total GPU usage
- memory consumption
- temperature (Glances 3.1.4 or higher)

.. image:: ../_static/gpu.png

If you click on the ``6`` short key, the per-GPU view is displayed:

.. image:: ../_static/pergpu.png

.. note::
    You can also start Glances with the ``--meangpu`` option to display
    the first view by default.

You can change the threshold limits in the configuration file:

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

============== ============
GPU (PROC/MEM) Status
============== ============
``<50%``       ``OK``
``>50%``       ``CAREFUL``
``>70%``       ``WARNING``
``>90%``       ``CRITICAL``
============== ============

.. _py3nvml: https://pypi.org/project/py3nvml/
.. _nvidia-ml-py3: https://pypi.org/project/nvidia-ml-py3/

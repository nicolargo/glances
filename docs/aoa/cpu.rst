.. _cpu:

CPU
===

The CPU stats are shown as a percentage and for the configured refresh
time. The total CPU usage is displayed on the first line.

.. image:: ../_static/cpu.png

If enough horizontal space is available, extended CPU information are
displayed.

.. image:: ../_static/cpu-wide.png

To switch to per-CPU stats, just hit the ``1`` key:

.. image:: ../_static/per-cpu.png

By default, ``steal`` CPU time alerts aren't logged. If you want that,
just add to the configuration file:

.. code-block:: ini

    [cpu]
    steal_log=True

Legend:

================= ============
CPU (user/system) Status
================= ============
``<50%``          ``OK``
``>50%``          ``CAREFUL``
``>70%``          ``WARNING``
``>90%``          ``CRITICAL``
================= ============

.. note::
    Limit values can be overwritten in the configuration file under
    the ``[cpu]`` and/or ``[percpu]`` sections.

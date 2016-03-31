.. _cpu:

CPU
===

The CPU stats are shown as a percentage or value and for the configured
refresh time. The total CPU usage is displayed on the first line.

.. image:: ../_static/cpu.png

If enough horizontal space is available, extended CPU information are
displayed.

.. image:: ../_static/cpu-wide.png

CPU stats description:

* user: percent time spent in user space
* system: percent time spent in kernel space
* idle: percent of CPU used by any program
* nice: percent time occupied by user level processes with a positive nice value
* irq: percent time spent servicing/handling hardware/software interrupts
* iowait: percent time spent in wait (on disk)
* steal: percent time in involuntary wait by virtual cpu while hypervisor is servicing another processor/virtual machine
* ctx_sw: number of context switches (voluntary + involuntary) per second
* inter: number of interrupts per second
* sw_inter: number of software interrupts per second. Always set to 0 on Windows and SunOS.
* syscal: number of system calls per second. Do not displayed on Linux (always 0).

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

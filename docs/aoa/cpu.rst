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
> User CPU time is time spent on the processor running your program's code (or code in libraries)
* system: percent time spent in kernel space
> System CPU time is the time spent running code in the operating system kernel
* idle: percent of CPU used by any program
> Every program or task that runs on a computer system occupies a certain amount of processing time on the CPU. If the CPU has completed all tasks it is idle.
* nice: percent time occupied by user level processes with a positive nice value
> The time the CPU has spent running users' processes that have been "niced"
* irq: percent time spent servicing/handling hardware/software interrupts
> Time servicing interrupts (hardware + software)
* iowait: percent time spent in wait (on disk)
> Time spent by the CPU waiting for a IO operations to complete
* steal: percent time in involuntary wait by virtual CPU
> Steal time is the percentage of time a virtual CPU waits for a real CPU while the hypervisor is servicing another virtual processor
* ctx_sw: number of context switches (voluntary + involuntary) per second
> A context switch is a procedure that a computer's CPU (central processing unit) follows to change from one task (or process) to another while ensuring that the tasks do not conflict
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

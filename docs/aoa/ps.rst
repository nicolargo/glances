.. _ps:

Processes List
==============

Compact view:

.. image:: ../_static/processlist.png

Full view:

.. image:: ../_static/processlist-wide.png

Filtered view:

.. image:: ../_static/processlist-filter.png

The process view consists of 3 parts:

- Processes summary
- Monitored processes list (optional)
- Processes list

The processes summary line displays:

- Tasks number (total number of processes)
- Threads number
- Running tasks number
- Sleeping tasks number
- Other tasks number (not running or sleeping)
- Sort key

By default, or if you hit the ``a`` key, the processes list is
automatically sorted by:

- ``CPU``: if there is no alert (default behavior)
- ``CPU``: if a CPU or LOAD alert is detected
- ``MEM``: if a memory alert is detected
- ``DISK I/O``: if a CPU iowait alert is detected

The number of processes in the list is adapted to the screen size.

Columns display
---------------

========================= ==============================================
``CPU%``                  % of CPU used by the process

                          If Irix/Solaris mode is off ('0' key), the value
                          is divided by logical core number
``MEM%``                  % of MEM used by the process (RES divided by
                          the total RAM you have)
``VIRT``                  Virtual Memory Size

                          The total amount of virtual memory used by the
                          process.

                          It includes all code, data and shared
                          libraries plus pages that have been swapped out
                          and pages that have been mapped but not used.

                          Most of the time, this is not a useful number.
``RES``                   Resident Memory Size

                          The non-swapped physical memory a process is
                          using (what's currently in the physical memory).
``PID``                   Process ID
``USER``                  User ID
``THR``                   Threads number of the process
``TIME+``                 Cumulative CPU time used by the process
``NI``                    Nice level of the process
``S``                     Process status

                          The status of the process:

                          - ``R``: running or runnable (on run queue)
                          - ``S``: interruptible sleep (waiting for an event)
                          - ``D``: uninterruptible sleep (usually I/O)
                          - ``Z``: defunct ("zombie") process
                          - ``T``: traced by job control signal
                          - ``t``: stopped by debugger during the tracing
                          - ``X``: dead (should never be seen)

``R/s``                   Per process I/O read rate in B/s
``W/s``                   Per process I/O write rate in B/s
``COMMAND``               Process command line or command name

                          User can switch to the process name by
                          pressing on the ``'/'`` key
========================= ==============================================

Source: Thanks to the Peteris Ņikiforovs's blog.

Process filtering
-----------------

It's possible to filter the processes list using the ``ENTER`` key.

Filter syntax is the following (examples):

- ``python``: Filter processes name or command line starting with
  *python* (regexp)
- ``.*python.*``: Filter processes name or command line containing
  *python* (regexp)
- ``username:nicolargo``: Processes of nicolargo user (key:regexp)
- ``cmdline:\/usr\/bin.*``: Processes starting by */usr/bin*

Extended info
-------------

.. image:: ../_static/processlist-top.png

In standalone mode, additional information are provided for the top
process:

========================= ==============================================
``CPU affinity``          Number of cores used by the process
``Memory info``           Extended memory information about the process

                          For example, on Linux: swap, shared, text,
                          lib, data and dirty
``Open``                  The number of threads, files and network
                          sessions (TCP and UDP) used by the process
``IO nice``               The process I/O niceness (priority)
========================= ==============================================

The extended stats feature can be enabled using the
``--enable-process-extended`` option (command line) or the ``e`` key
(curses interface).

.. note::
    Limit for CPU and MEM percent values can be overwritten in the
    configuration file under the ``[processlist]`` section. It is also
    possible to define limit for Nice values (comma separated list).
    For example: nice_warning=-20,-19,-18

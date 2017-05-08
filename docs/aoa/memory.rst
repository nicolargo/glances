.. _memory:

Memory
======

Glances uses two columns: one for the ``RAM`` and one for the ``SWAP``.

.. image:: ../_static/mem.png

If enough space is available, Glances displays extended information for
the ``RAM``:

.. image:: ../_static/mem-wide.png

A character is also displayed just after the MEM header and shows the
trend value:

======== ==============================================================
Trend    Status
======== ==============================================================
``-``    MEM value is equal to the mean of the six latests refreshes
``\``    MEM value is lower than the mean of the six latests refreshes
``/``    MEM value is higher than the mean of the six latests refreshes
======== ==============================================================

Alerts are only set for used memory and used swap.

Legend:

======== ============
RAM/Swap Status
======== ============
``<50%`` ``OK``
``>50%`` ``CAREFUL``
``>70%`` ``WARNING``
``>90%`` ``CRITICAL``
======== ============

.. note::
    Limit values can be overwritten in the configuration file under
    the ``[memory]`` and/or ``[memswap]`` sections.

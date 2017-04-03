.. _memory:

Memory
======

Glances uses two columns: one for the ``RAM`` and one for the ``SWAP``.

.. image:: ../_static/mem.png

If enough space is available, Glances displays extended information for
the ``RAM``:

.. image:: ../_static/mem-wide.png

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

.. note::
    A trend character could be displayed just after the title.
    * '-': value is more or less equal to the mean of the lasts N values
    * '/': value is higher than the mean of the lasts N values
    * '/': value is lower than the mean of the lasts N values

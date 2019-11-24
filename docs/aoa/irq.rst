.. _irq:

IRQ
===

*Availability: Linux*

This plugin is disable by default, please use the --enable irq option
to enable it.

.. image:: ../_static/irq.png

Glances displays the top ``5`` interrupts rate.

This plugin is only available on GNU/Linux (stats are grabbed from the
``/proc/interrupts`` file).

.. note::
    ``/proc/interrupts`` file doesn't exist inside OpenVZ containers.

How to read the information:

- The first column is the IRQ number / name
- The second column says how many times the CPU has been interrupted
  during the last second

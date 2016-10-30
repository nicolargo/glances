.. _irq:

IRQ
===

.. image:: ../_static/irq.png

Glances displays the top 5 interrupts rate. This plugin is only available on
GNU/Linux machine (stats are grabbed from the /proc/interrupts file).

Note: /proc/interrupts file did not exist inside OpenVZ containers.

How to read the informations:

* The first Column is the IRQ number / name
* The Second column says how many times the CPU core has been interrupted during the last second

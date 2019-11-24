.. _quicklook:

Quick Look
==========

The ``quicklook`` plugin is only displayed on wide screen and proposes a
bar view for CPU and memory (virtual and swap).

In the terminal interface, click on ``3`` to enable/disable it.

.. image:: ../_static/quicklook.png

If the per CPU mode is on (by clicking the ``1`` key):

.. image:: ../_static/quicklook-percpu.png

In the Curses/terminal interface, it is also possible to switch from bar to
sparkline using 'S' hot key or --sparkline command line option (nned the
sparklines Python lib on your system). Please be aware that sparklines use
the Glances history and will not be available if the history is disabled from
the command line.

.. image:: ../_static/sparkline.png

.. note::
    Limit values can be overwritten in the configuration file under
    the ``[quicklook]`` section.

You can also configure the percentage char used in the terminal user interface.

.. code-block:: ini

    [quicklook]
    # Graphical percentage char used in the terminal user interface (default is |)
    percentage_char=@

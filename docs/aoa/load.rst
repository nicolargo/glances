.. _load:

Load
====

*Availability: Unix*

.. image:: ../_static/load.png

On the *No Sheep* blog, Zachary Tirrell defines the `load average`_
on GNU/Linux operating system:

    "In short it is the average sum of the number of processes
    waiting in the run-queue plus the number currently executing
    over 1, 5, and 15 minutes time periods."

Be aware that Load on Linux and BSD are different things, high
`load on BSD`_ does not means high CPU load.

Glances gets the number of CPU core to adapt the alerts.
Alerts on load average are only set on 15 minutes time period.
The first line also displays the number of CPU core.

Legend:

============= ============
Load avg      Status
============= ============
``<0.7*core`` ``OK``
``>0.7*core`` ``CAREFUL``
``>1*core``   ``WARNING``
``>5*core``   ``CRITICAL``
============= ============

.. note::
    Limit values can be overwritten in the configuration file under
    the ``[load]`` section.

.. _load average: http://nosheep.net/story/defining-unix-load-average/
.. _load on BSD: http://undeadly.org/cgi?action=article&sid=20090715034920

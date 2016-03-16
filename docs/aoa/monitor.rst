.. _monitor:

Monitored Processes List
========================

The monitored processes list allows user, through the configuration
file, to group processes and quickly show if the number of running
processes is not good.

.. image:: ../_static/monitored.png

Each item is defined by:

- ``description``: description of the processes (max 16 chars).
- ``regex``: regular expression of the processes to monitor.
- ``command``: (optional) full path to shell command/script for extended
- stat. Should return a single line string. Use with caution.
- ``countmin``: (optional) minimal number of processes. A warning will
- be displayed if number of processes < count.
- ``countmax``: (optional) maximum number of processes. A warning will
  be displayed if number of processes > count.

Up to ``10`` items can be defined.

For example, if you want to monitor the Nginx processes on a web server,
the following definition should do the job:

.. code-block:: ini

    [monitor]
    list_1_description=Nginx server
    list_1_regex=.*nginx.*
    list_1_command=nginx -v
    list_1_countmin=1
    list_1_countmax=4

If you also want to monitor the PHP-FPM daemon processes, you should add
another item:

.. code-block:: ini

    [monitor]
    list_1_description=Nginx server
    list_1_regex=.*nginx.*
    list_1_command=nginx -v
    list_1_countmin=1
    list_1_countmax=4
    list_2_description=PHP-FPM
    list_2_regex=.*php-fpm.*
    list_2_countmin=1
    list_2_countmax=20

In client/server mode, the list is defined on the server side.
A new method, called `getAllMonitored`, is available in the APIs and
get the JSON representation of the monitored processes list.

Alerts are set as following:

================= ============
# of process       Status
================= ============
``0``             ``CRITICAL``
``min < p < max`` ``OK``
``p > max``       ``WARNING``
================= ============

.. _actions:

Actions
=======

Glances can trigger actions on events.

By ``action``, we mean all shell command line. For example, if you want
to execute the ``foo.py`` script if the last 5 minutes load are critical
then add the ``_action`` line to the Glances configuration file:

.. code-block:: ini

    [load]
    critical=5.0
    critical_action=python /path/to/foo.py

All the stats are available in the command line through the use of the
`{{mustache}}`_ syntax. Another example would be to create a log file
containing used vs total disk space if a space trigger warning is
reached:

.. code-block:: ini

    [fs]
    warning=70
    warning_action=echo {{mnt_point}} {{used}}/{{size}} > /tmp/fs.alert

.. note::
    You can use all the stats for the current plugin. See
    https://github.com/nicolargo/glances/wiki/The-Glances-2.x-API-How-to
    for the stats list.

.. _{{mustache}}: https://mustache.github.io/

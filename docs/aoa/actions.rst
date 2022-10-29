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
`Mustache`_ syntax. `Chevron`_ is required to render the mustache's template syntax.

Another example would be to create a log file
containing used vs total disk space if a space trigger warning is
reached:

.. code-block:: ini

    [fs]
    warning=70
    warning_action=echo {{mnt_point}} {{used}}/{{size}} > /tmp/fs.alert

A last example would be to create a log file containing the total user disk
space usage for a device and notify by email each time a space trigger
critical is reached:

.. code-block:: ini

    [fs]
    critical=90
    critical_action_repeat=echo {{device_name}} {{percent}} > /tmp/fs.alert && python /etc/glances/actions.d/fs-critical.py


.. note::
    Use && as separator for multiple commands


Within ``/etc/glances/actions.d/fs-critical.py``:

.. code-block:: python

    import subprocess
    from requests import get

    fs_alert = open('/tmp/fs.alert', 'r').readline().strip().split(' ')
    device = fs_alert[0]
    percent = fs_alert[1]
    system = subprocess.check_output(['uname', '-rn']).decode('utf-8').strip()
    ip = get('https://api.ipify.org').text

    body = 'Used user disk space for ' + device + ' is at ' + percent + '%.\nPlease cleanup the filesystem to clear the alert.\nServer: ' + str(system)+ '.\nIP address: ' + ip
    ps = subprocess.Popen(('echo', '-e', body), stdout=subprocess.PIPE)
    subprocess.call(['mail', '-s', 'CRITICAL: disk usage above 90%', '-r', 'postmaster@example.com', 'glances@example.com'], stdin=ps.stdout)

.. note::

    You can use all the stats for the current plugin. See
    https://github.com/nicolargo/glances/wiki/The-Glances-RESTFULL-JSON-API
    for the stats list.

It is also possible to repeat action until the end of the alert.
Keep in mind that the command line is executed every refresh time so
use with caution:

.. code-block:: ini

    [load]
    critical=5.0
    critical_action_repeat=/home/myhome/bin/bipper.sh

.. _Mustache: https://mustache.github.io/
.. _Chevron: https://github.com/noahmorrison/chevron

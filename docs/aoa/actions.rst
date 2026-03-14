.. _actions:

Actions
=======

Glances can trigger actions on events for warning and critical thresholds.

By ``action``, we mean all shell command line. For example, if you want
to execute the ``foo.py`` script if the last 5 minutes load are critical
then add the ``_action`` line to the Glances configuration file:

.. code-block:: ini

    [load]
    critical=5.0
    critical_action=python /path/to/foo.py

All the stats are available in the command line through the use of the
`Mustache`_ syntax. `Chevron`_ is required to render the mustache's template syntax.

Additionaly to the stats of the current plugin, the following variables are
also available:
- ``{{time}}``: current time in ISO format
- ``{{critical}}``: critical threshold value
- ``{{warning}}``: warning threshold value
- ``{{careful}}``: careful threshold value

Another example would be to create a log file
containing used vs total disk space if a space trigger warning is
reached:

.. code-block:: ini

    [fs]
    warning=70
    warning_action=python /path/to/fs-warning.py {{mnt_point}} {{used}} {{size}}

.. note::

    For security reasons, Mustache-rendered values are sanitized: the
    characters ``&&``, ``|``, ``>`` and ``>>`` are replaced by spaces
    before execution. This prevents command injection through
    user-controllable data such as process names, container names or
    mount points.

    As a consequence, **shell operators (pipes, redirections, command
    chaining) cannot be used directly in action command lines**. If your
    action requires pipes, redirections or chained commands, write a
    shell script and call it from the action instead.

For example, to create a log file containing the total user disk
space usage for a device and notify by email each time a space trigger
critical is reached, create a shell script ``/etc/glances/actions.d/fs-critical.sh``:

.. code-block:: bash

    #!/bin/bash
    # Usage: fs-critical.sh <time> <device_name> <percent>
    echo "$1 $2 $3" > /tmp/fs.alert
    python /etc/glances/actions.d/fs-critical.py

Then reference it in the configuration file:

.. code-block:: ini

    [fs]
    critical=90
    critical_action_repeat=/etc/glances/actions.d/fs-critical.sh {{time}} {{device_name}} {{percent}}

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
    https://github.com/nicolargo/glances/wiki/The-Glances-RESTFUL-JSON-API
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

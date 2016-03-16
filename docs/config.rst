.. _config:

Configuration
=============

No configuration file is mandatory to use Glances.

Furthermore a configuration file is needed to access more settings.

Location
--------

You can put the ``glances.conf`` file in the following locations:

=========== ============================================================
``Linux``   ~/.config/glances, /etc/glances
``*BSD``    ~/.config/glances, /usr/local/etc/glances
``OS X``    ~/Library/Application Support/glances, /usr/local/etc/glances
``Windows`` %APPDATA%\glances
=========== ============================================================

On Windows XP, the ``%APPDATA%`` path is:

::

    C:\Documents and Settings\<User>\Application Data

Since Windows Vista and newer versions:

::

    C:\Users\<User>\AppData\Roaming

User-specific options override system-wide options and options given on
the command line override either.

Syntax
------

Glances reads configuration files in the *ini* syntax.

Each plugin and export module can have a section. Below an example for
the CPU plugin:

.. code-block:: ini

    [cpu]
    user_careful=50
    user_warning=70
    user_critical=90
    iowait_careful=50
    iowait_warning=70
    iowait_critical=90
    system_careful=50
    system_warning=70
    system_critical=90
    steal_careful=50
    steal_warning=70
    steal_critical=90

Logging
-------

Glances logs all of its internal messages to a log file.

``DEBUG`` messages can been logged using the ``-d`` option on the command
line.

By default, the ``glances.log`` file is under the temporary directory:

===================== ==================================================
``Linux, *BSD, OS X`` /tmp
``Windows``           %APPDATA%\\Local\\temp
===================== ==================================================

If ``glances.log`` is not writable, a new file will be created and
returned to the user console.

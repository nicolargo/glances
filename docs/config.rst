.. _config:

Configuration
=============

No configuration file is mandatory to use Glances.

Furthermore a configuration file is needed to access more settings.

Location
--------

.. note::
    A template is available in the ``/usr{,/local}/share/doc/glances``
    (Unix-like) directory or directly on `GitHub`_.

You can put your own ``glances.conf`` file in the following locations:

==================== =============================================================
``Linux``, ``SunOS`` ~/.config/glances, /etc/glances
``*BSD``             ~/.config/glances, /usr/local/etc/glances
``macOS``            ~/Library/Application Support/glances, /usr/local/etc/glances
``Windows``          %APPDATA%\\glances
==================== =============================================================

- On Windows XP, ``%APPDATA%`` is: ``C:\Documents and Settings\<USERNAME>\Application Data``.
- On Windows Vista and later: ``C:\Users\<USERNAME>\AppData\Roaming``.

User-specific options override system-wide options and options given on
the command line override either.

Syntax
------

Glances reads configuration files in the *ini* syntax.

A first section (called global) is available:

.. code-block:: ini

    [global]
    # Does Glances should check if a newer version is available on PyPI?
    check_update=true

Each plugin, export module and application monitoring process (AMP) can
have a section. Below an example for the CPU plugin:

.. code-block:: ini

    [cpu]
    disable=False
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

an InfluxDB export module:

.. code-block:: ini

    [influxdb]
    # Configuration for the --export influxdb option
    # https://influxdb.com/
    host=localhost
    port=8086
    user=root
    password=root
    db=glances
    prefix=localhost
    #tags=foo:bar,spam:eggs

or a Nginx AMP:

.. code-block:: ini

    [amp_nginx]
    # Nginx status page should be enable (https://easyengine.io/tutorials/nginx/status-page/)
    enable=true
    regex=\/usr\/sbin\/nginx
    refresh=60
    one_line=false
    status_url=http://localhost/nginx_status

With Glances 3.0 or higher it is also possible to use dynamic configuration
value using system command. For example, if you to set the prefix of an
InfluxDB export to the current hostname, use:

.. code-block:: ini

    [influxdb]
    ...
    prefix=`hostname`

Or if you want to add the Operating System name as a tag:

.. code-block:: ini

    [influxdb]
    ...
    tags=system:`uname -a`

Logging
-------

Glances logs all of its internal messages to a log file.

``DEBUG`` messages can been logged using the ``-d`` option on the command
line.

The location of the Glances depends of your operating system. You could
displayed the Glances log file full path using the``glances -V`` command line.

The file is automatically rotate when the size is higher than 1 MB.

If you want to use another system path or change the log message, you
can use your own logger configuration. First of all, you have to create
a ``glances.json`` file with, for example, the following content (JSON
format):

.. code-block:: json

    {
        "version": 1,
        "disable_existing_loggers": "False",
        "root": {
            "level": "INFO",
            "handlers": ["file", "console"]
        },
        "formatters": {
            "standard": {
                "format": "%(asctime)s -- %(levelname)s -- %(message)s"
            },
            "short": {
                "format": "%(levelname)s: %(message)s"
            },
            "free": {
                "format": "%(message)s"
            }
        },
        "handlers": {
            "file": {
                "level": "DEBUG",
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "standard",
                "filename": "/var/tmp/glances.log"
            },
            "console": {
                "level": "CRITICAL",
                "class": "logging.StreamHandler",
                "formatter": "free"
            }
        },
        "loggers": {
            "debug": {
                "handlers": ["file", "console"],
                "level": "DEBUG"
            },
            "verbose": {
                "handlers": ["file", "console"],
                "level": "INFO"
            },
            "standard": {
                "handlers": ["file"],
                "level": "INFO"
            },
            "requests": {
                "handlers": ["file", "console"],
                "level": "ERROR"
            },
            "elasticsearch": {
                "handlers": ["file", "console"],
                "level": "ERROR"
            },
            "elasticsearch.trace": {
                "handlers": ["file", "console"],
                "level": "ERROR"
            }
        }
    }

and start Glances using the following command line:

.. code-block:: console

    LOG_CFG=<path>/glances.json glances

.. note::
    Replace ``<path>`` by the folder where your ``glances.json`` file
    is hosted.

.. _GitHub: https://raw.githubusercontent.com/nicolargo/glances/master/conf/glances.conf

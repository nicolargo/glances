.. _config:

Configuration
=============

No configuration file is mandatory to use Glances.

Furthermore, a configuration file is needed to access more settings.

Location
--------

.. note::
    A template is available in the ``/usr{,/local}/share/doc/glances``
    (Unix-like) directory or directly on `GitHub`_.

You can place your ``glances.conf`` file in the following locations:

==================== =============================================================
``Linux``, ``SunOS`` ~/.config/glances/, /etc/glances/, /usr/share/docs/glances/
``*BSD``             ~/.config/glances/, /usr/local/etc/glances/, /usr/share/docs/glances/
``macOS``            ~/.config/glances/, ~/Library/Application Support/glances/, /usr/local/etc/glances/, /usr/share/docs/glances/
``Windows``          %APPDATA%\\glances\\glances.conf
``All``              + <venv_root_folder>/share/doc/glances/
==================== =============================================================

- On Windows XP, ``%APPDATA%`` is: ``C:\Documents and Settings\<USERNAME>\Application Data``.
- On Windows Vista and later: ``C:\Users\<USERNAME>\AppData\Roaming``.

User-specific options override system-wide options, and options given on
the command line overrides both.

Syntax
------

Glances read configuration files in the *ini* syntax.

A first section (called global) is available:

.. code-block:: ini

    [global]
    # Refresh rate (default is a minimum of 2 seconds)
    # Can be overwritten by the -t <sec> option
    # It is also possible to overwrite it in each plugin section
    refresh=2
    # Should Glances check if a newer version is available on PyPI ?
    check_update=true
    # History size (maximum number of values)
    # Default is 1200 values (~1h with the default refresh rate)
    history_size=1200
    # Set the way Glances should display the date (default is %Y-%m-%d %H:%M:%S %Z)
    #strftime_format="%Y-%m-%d %H:%M:%S %Z"
    # Define external directory for loading additional plugins
    # The layout follows the glances standard for plugin definitions
    #plugin_dir=/home/user/dev/plugins

than a second one concerning the user interface:

.. code-block:: ini

    [outputs]
    # Options for all UIs
    #--------------------
    # Separator in the Curses and WebUI interface (between top and others plugins)
    separator=True
    # Set the the Curses and WebUI interface left menu plugin list (comma-separated)
    #left_menu=network,wifi,connections,ports,diskio,fs,irq,folders,raid,smart,sensors,now
    # Limit the number of processes to display (in the WebUI)
    max_processes_display=25
    # Options for WebUI
    #------------------
    # Set URL prefix for the WebUI and the API
    # Example: url_prefix=/glances/ => http://localhost/glances/
    # Note: The final / is mandatory
    # Default is no prefix (/)
    #url_prefix=/glances/
    # Set root path for WebUI statics files
    # Why ? On Debian system, WebUI statics files are not provided.
    # You can download it in a specific folder
    # thanks to https://github.com/nicolargo/glances/issues/2021
    # then configure this folder with the webui_root_path key
    # Default is folder where glances_restfull_api.py is hosted
    #webui_root_path=
    # CORS options
    # Comma separated list of origins that should be permitted to make cross-origin requests.
    # Default is *
    #cors_origins=*
    # Indicate that cookies should be supported for cross-origin requests.
    # Default is True
    #cors_credentials=True
    # Comma separated list of HTTP methods that should be allowed for cross-origin requests.
    # Default is *
    #cors_methods=*
    # Comma separated list of HTTP request headers that should be supported for cross-origin requests.
    # Default is *
    #cors_headers=*

Each plugin, export module, and application monitoring process (AMP) can
have a section. Below is an example for the CPU plugin:

.. code-block:: ini

    [cpu]
    disable=False
    refresh=3
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
    # Nginx status page should be enabled (https://easyengine.io/tutorials/nginx/status-page/)
    enable=true
    regex=\/usr\/sbin\/nginx
    refresh=60
    one_line=false
    status_url=http://localhost/nginx_status

With Glances 3.0 or higher, you can use dynamic configuration values
by utilizing system commands. For example, if you want to set the prefix
of an InfluxDB export to the current hostname, use:

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

``DEBUG`` messages can be logged using the ``-d`` option on the command
line.

The location of the Glances log file depends on your operating system. You can
display the full path of the Glances log file using the ``glances -V``
command line.

The file is automatically rotated when its size exceeds 1 MB.

If you want to use another system path or change the log message, you
can use your logger configuration. First of all, you have to create
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
    Replace ``<path>`` with the directory where your ``glances.json`` file
    is hosted.

.. _GitHub: https://raw.githubusercontent.com/nicolargo/glances/master/conf/glances.conf

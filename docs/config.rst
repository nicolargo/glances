.. _config:

Configuration
=============

Glances reads its configuration from a single ``glances.conf`` file, laid
over built-in defaults and overridden by environment variables.

Location
--------

.. note::
    A template is available in the ``/usr{,/local}/share/doc/glances``
    (Unix-like) directory or directly on `GitHub`_.

Glances loads **exactly one** configuration file:

1. the file given with the ``-C <path>`` (``--config``) command line option.
   No other file is searched: when it does not exist, Glances logs a warning
   and runs on its built-in defaults;
2. otherwise, the first existing file of:

   - ``$XDG_CONFIG_HOME/glances/glances.conf`` (``~/.config/glances/glances.conf``
     when ``XDG_CONFIG_HOME`` is not set);
   - ``/etc/glances/glances.conf``.

Files are not merged: a user file hides the system-wide one entirely. Running
without any configuration file is valid, the built-in defaults are used.

A file that exists but cannot be read or parsed stops Glances, and so does a
``-C`` path that does not exist: it is never skipped silently (it could hold
the ``[outputs] password``).

Any option can then be overridden with an environment variable named
``GLANCES_<SECTION>__<KEY>`` (note the double underscore), for example
``GLANCES_OUTPUTS__BIND_ADDRESS=0.0.0.0``. This is handy in containers.
Options given on the command line override both.

``glances --issue`` shows which configuration file was loaded.

Syntax
------

Glances read configuration files in the *ini* syntax.

The file is segmented by sections composed of key/value pairs.

For example "refresh=2" is a key/value pair. refresh is the key and 2 is the value.

Key is always a string.

Value is one of the followings types:

- integer (ex: refresh=2)
- float (ex: foo=1.23)
- bool (ex: disable=true). Glances accepts true, 1, yes, on (and false, 0,
  no, off) as bool.
- comma-separated list of values (ex: focus=.*firefox.*,.*python.*)

Values are used as written: shell commands between backticks are not
executed (Glances 3 and 4 "dynamic values" are gone).

A first section (called global) is available:

.. code-block:: ini

    [global]
    # Refresh rate (default is a minimum of 2 seconds)
    # Can be overwritten by the -t <sec> option
    # It is also possible to overwrite it in each plugin section
    refresh=2
    # History size (maximum number of values)
    # Default is 1200 values (~1h with the default refresh rate)
    # 0 disables the history (same as --disable-history).
    history_size=1200
    # Set the way Glances should display the date (default is %Y-%m-%d %H:%M:%S %Z)
    #strftime_format=%Y-%m-%d %H:%M:%S %Z

than a second one concerning the user interface:

.. code-block:: ini

    [outputs]
    # Options for all UIs
    #--------------------
    # Separator in the Curses interface (between top and others plugins)
    separator=True
    # Limit the number of processes to display (in the WebUI)
    max_processes_display=25
    # Plugin title colour in the Curses interface, tuned for your terminal
    # background. "dark" (default) is bold white, suited to the dark
    # backgrounds most terminals use; "light" is a dark grey for a white
    # background. No single colour is legible on both, hence the switch.
    # The WebUI uses the same key to pick its dark or light theme.
    #theme=light
    # Options for the server (glances -s / -w)
    #-----------------------------------------
    # Address and TCP port the server listens on (--bind / --port)
    # Default is 127.0.0.1 (loopback only) and 61208
    #bind_address=127.0.0.1
    #port=61208
    # PBKDF2 hash of the REST API / WebUI password, printed by
    # "glances --set-password" (never the clear password)
    #password=<salt>$<pbkdf2 hex digest>
    # User name expected with the password (default: glances)
    #username=glances
    # Serve the interactive API documentation: Swagger UI at /docs and ReDoc at
    # /redoc.
    # Both are unauthenticated when no password is set, like the rest of the API,
    # and they describe every route - disable them on an internet-facing server.
    # The WebUI footer links /docs only when this is enabled.
    # Overridden on the command line by --api-doc / --no-api-doc.
    # Default is True
    #api_doc=False
    # CORS options
    # Comma separated list of origins that should be permitted to make cross-origin requests.
    # Default is no list: no CORS header is sent
    #cors_origins=https://dashboard.example.com
    # Indicate that cookies and credentials should be supported for cross-origin requests.
    # Default is False (forced to False when cors_origins contains *)
    #cors_allow_credentials=False
    # Define SSL files (keyfile_password is optional) to serve HTTPS
    #ssl_keyfile=./glances.local+3-key.pem
    #ssl_keyfile_password=kfp
    #ssl_certfile=./glances.local+3.pem
    # Rate limiting, per client address
    #auth_fail_per_minute=10
    #rate_limit_per_minute=0
    #rate_limit_burst=0
    # DNS rebinding protection (allowed HTTP Host headers)
    #webui_allowed_hosts=localhost,127.0.0.1,myserver.example.com

The server options are detailed in the next section.

Server options
--------------

The ``[outputs]`` section also configures the REST API and WebUI server
started by ``glances -s`` or ``glances -w``.

**Listening address.** ``bind_address`` (default ``127.0.0.1``) and ``port``
(default ``61208``) set where the server listens; ``--bind`` and ``--port``
override them. The default only accepts connections from the local machine:
set ``bind_address=0.0.0.0`` to serve the network (the Docker image does).

**Password.** Glances runs without authentication by default. To protect the
API and the WebUI, generate a hash with:

.. code-block:: console

    $ glances --set-password

and paste the printed value into ``[outputs] password``. The key holds a
PBKDF2 hash (``<salt>$<hex digest>``), never the clear password: Glances
never writes to ``glances.conf`` itself. Hashes made by Glances 4 are not
compatible and must be generated again. The user name is ``glances`` unless
``username`` is set. Clients authenticate with HTTP Basic, or with a JWT
Bearer token obtained from ``/api/5/token``; ``jwt_secret_key`` (at least
32 characters, for example ``python3 -c "import secrets;
print(secrets.token_urlsafe(32))"``; a random key per run when unset or too
short, so tokens do not survive a restart) and ``jwt_expire_minutes``
(default ``60``, at most ``1440``) configure the tokens.

**Rate limiting.** Requests are counted per client address (an IPv6 client
per /64):

- ``auth_fail_per_minute`` (default ``10``, ``0`` disables it): failed
  authentications allowed per minute. Past the limit, the address gets HTTP
  429 before its credentials are checked; requests carrying credentials
  already known good are still served.
- ``rate_limit_per_minute`` (default ``0``, off): general limit, in requests
  per minute. A WebUI tab polls about 30 times a minute, a ``glances -c``
  client about 90.
- ``rate_limit_burst`` (default ``0``, meaning one minute's worth): requests
  allowed at once.
- ``forwarded_allow_ips`` (default empty): behind a reverse proxy, the
  comma-separated addresses of the proxies whose ``X-Forwarded-For`` header
  gives the real client address. When empty, the header is ignored and every
  request counts for the address it came from, so a local client cannot
  rotate the header to escape the limits.

``/status`` and ``/healthz`` are never limited.

**DNS rebinding.** ``webui_allowed_hosts`` is the comma-separated list of
HTTP ``Host`` headers the server accepts (wildcards such as
``*.example.com`` are supported). When it is not set, a server bound to a
loopback address (the default) only answers ``localhost``, ``127.0.0.1`` and
``[::1]``; a server bound to the network applies no host filtering and logs
a warning. Set it behind a reverse proxy that forwards its own ``Host``, and
on any internet-facing deployment. The MCP endpoint has its own list,
``mcp_allowed_hosts``.

**TLS.** Set both ``ssl_keyfile`` and ``ssl_certfile`` (and
``ssl_keyfile_password`` when the key is encrypted) to serve HTTPS. Setting
only one of them, or a file that cannot be read, stops the server instead of
falling back to plain HTTP.

**CORS.** No CORS header is sent unless ``cors_origins`` lists the origins
allowed to make cross-origin requests (methods ``GET`` and ``POST``, request
headers ``Authorization`` and ``Content-Type``).
``cors_allow_credentials`` (default ``False``) is ignored when the list
contains ``*``, which the CORS specification forbids.

**Configuration endpoint.** ``/api/5/config`` serves the configuration. When
no password is set, it only exposes the options the WebUI needs
(``[global] refresh`` and ``[outputs] theme``, ``max_processes_display``,
``api_doc``). With a password, authenticated clients get the whole
configuration, secrets (passwords, tokens, keys...) redacted.

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

Logging
-------

Glances logs all of its internal messages to a log file.

``DEBUG`` messages can be logged using the ``-d`` option on the command
line.

The log file is named ``glances.log``. The file is automatically rotated when its size exceeds 1 MB.

The log file lives in a folder private to the user (``$XDG_CACHE_HOME/glances``
or ``~/.local/share/glances``) and is readable by its owner only. Glances
never falls back to a shared temporary folder such as ``/tmp``: when no
private folder can be created (no home directory), it does not log to a file.

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

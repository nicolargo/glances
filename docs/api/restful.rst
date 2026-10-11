.. _api_restful:

Restful/JSON API documentation
==============================

This page describes the Glances API version 5 (Restful/JSON). Every example
below is a real response, taken when the page was generated.

Run the Glances API server
--------------------------

The API and the Web UI are served by:

.. code-block:: bash

    # glances -s

Add ``--disable-webui`` to serve the API alone.

API URL
-------

The root API URL is ``http://localhost:61208/api/5``. The bind address and the port are set with
``--bind`` and ``--port``, or ``[outputs] bind_address`` and ``port`` in
``glances.conf``. The server listens on ``127.0.0.1`` by default.

API documentation URL
---------------------

The server documents itself at ``http://localhost:61208/docs`` (Swagger UI) and
``http://localhost:61208/redoc``, unless ``--no-api-doc`` or
``[outputs] api_doc=false`` turns them off.

Authentication
--------------

The API is open by default. Set ``[outputs] password`` to a hash made with
``glances --set-password``, and every route except ``/status``,
``/healthz`` and ``/api/5/token`` then requires HTTP Basic credentials
(``[outputs] username``, ``glances`` by default) or a JWT bearer token:

.. code-block:: bash

    # curl -u glances:<password> -X POST http://localhost:61208/api/5/token
    # curl -H "Authorization: Bearer <access_token>" http://localhost:61208/api/5/cpu

Rate limiting
-------------

A client address that fails authentication ``[outputs] auth_fail_per_minute``
times (10 by default) gets ``429 Too Many Requests``, with ``Retry-After``,
until a try comes back. ``[outputs] rate_limit_per_minute`` and
``rate_limit_burst`` limit every request the same way; they are off by
default. ``/status`` and ``/healthz`` are never limited.

Routes
------

Every route the server publishes, from its OpenAPI schema:

.. list-table::
    :header-rows: 1

    * - Method
      - Path
      - Purpose
    * - GET
      - ``/status``
      - Status Handler
    * - GET
      - ``/healthz``
      - Status Handler
    * - POST
      - ``/api/5/token``
      - Issue Token
    * - GET
      - ``/api/5/pluginslist``
      - Plugins List
    * - GET
      - ``/api/5/all``
      - All Stats
    * - GET
      - ``/api/5/all/limits``
      - All Limits
    * - GET
      - ``/api/5/all/info``
      - Every registered plugin's schema, published or not (G9-5).
    * - GET
      - ``/api/5/alert``
      - Alert History
    * - GET
      - ``/api/5/alert/incidents``
      - The alert history collapsed into incidents — the same synthesis
    * - GET
      - ``/api/5/serverslist``
      - The browser's server list (\`-s --browser\`), for the Web UI browser page.
    * - GET
      - ``/api/5/config``
      - The redacted config behind a password, else only the WebUI keys.
    * - GET
      - ``/api/5/args``
      - Return the CLI argument namespace, redacted (issue #1527 / CVE-2026-68520).
    * - POST
      - ``/api/5/processes/extended/disable``
      - Stop collecting extended stats for whichever process was pinned.
    * - POST
      - ``/api/5/processes/extended/{pid}``
      - Collect extended stats for \`pid\` from the next cycle on.
    * - POST
      - ``/api/5/processes/sort/{key}``
      - Sort the processes (and the containers and VMs) by \`key\`, or \`auto\`.
    * - GET
      - ``/api/5/{plugin_name}/history``
      - Plugin History
    * - GET
      - ``/api/5/{plugin_name}/info``
      - Plugin Info
    * - GET
      - ``/api/5/{plugin_name}/limits``
      - Plugin Limits
    * - GET
      - ``/api/5/{plugin_name}``
      - Plugin Payload
    * - GET
      - ``/api/5/{plugin_name}/top/{n}``
      - The first n items of a collection plugin, as a bare list (v4 \`/top/<n>\`).
    * - GET
      - ``/api/5/{plugin_name}/{field}``
      - One field: \`{field: value}\`, a list of values for a collection (v4 \`/<plugin>/<item>\`).
    * - GET
      - ``/api/5/{plugin_name}/{field}/value/{value}``
      - The items whose field equals value: \`{value: [items]}\` (v4 \`/<plugin>/<item>/value/<value>\`).
    * - GET
      - ``/api/5/{plugin_name}/{field}/{pk_value}``
      - One field of the item whose primary key is pk\_value (v4 \`/<plugin>/<item>/<key>\`).

GET status
----------

Check that the server is up (no authentication needed):

.. code-block:: bash

    # curl http://localhost:61208/status
    {
        "glances_version": "5.0.0b1",
        "status": "ok",
        "version": "5"
    }

GET plugins list
----------------

.. code-block:: bash

    # curl http://localhost:61208/api/5/pluginslist
    [
        "amps",
        "containers",
        "core",
        "cpu",
        "diskio",
        "folders",
        "fs",
        "gpu",
        "ip",
        "load",
        "mem",
        "memswap",
        "network",
        "now",
        "percpu",
        "ports",
        "processcount",
        "processlist",
        "programlist",
        "psutilversion",
        "quicklook",
        "sensors",
        "system",
        "uptime",
        "version",
        "wifi"
    ]

GET all stats
-------------

Every plugin's payload in one call, a large dictionary:

.. code-block:: bash

    # curl http://localhost:61208/api/5/all

GET one field, one item, the first items
----------------------------------------

``/api/5/<plugin>/<field>`` serves ``{field: value}``, a list of values for a plugin
with items. An item is named by its primary key (``_key`` in the payload):

.. code-block:: bash

    # curl http://localhost:61208/api/5/amps/name
    {
        "name": [
            "Dropbox",
            "Python",
            "Conntrack",
            "Nginx",
            "Systemd",
            "SystemV"
        ]
    }

.. code-block:: bash

    # curl http://localhost:61208/api/5/amps/result/Dropbox
    {
        "result": null
    }

.. code-block:: bash

    # curl http://localhost:61208/api/5/amps/name/value/Dropbox
    {
        "Dropbox": [
            {
                "count": 0,
                "countmax": null,
                "countmin": 1.0,
                "name": "Dropbox",
                "refresh": 3.0,
                "regex": true,
                "result": null,
                "result_float": null,
                "timer": 1.0723226070404053
            }
        ]
    }

.. code-block:: bash

    # curl http://localhost:61208/api/5/amps/top/1
    [
        {
            "count": 0,
            "countmax": null,
            "countmin": 1.0,
            "name": "Dropbox",
            "refresh": 3.0,
            "regex": true,
            "result": null,
            "result_float": null,
            "timer": 1.0723226070404053
        }
    ]

GET alerts
----------

The alert events, most recent last, then the same history grouped into incidents:

.. code-block:: bash

    # curl http://localhost:61208/api/5/alert
    []

.. code-block:: bash

    # curl http://localhost:61208/api/5/alert/incidents
    {
        "incidents": [],
        "is_initializing": true
    }

Pin a process for extended stats
--------------------------------

Collect extended stats (affinity, I/O nice, open files, connections) for one process,
then stop. They appear in the ``extended`` metadata of ``/api/5/processlist``:

.. code-block:: bash

    # curl -X POST http://localhost:61208/api/5/processes/extended/<pid>
    # curl -X POST http://localhost:61208/api/5/processes/extended/disable

Sort the processes
------------------

Sort the processes, the containers and the VMs by one key, or ``auto`` to let the
alerts choose it. The sort is the server's: every Web UI and client TUI attached to it
follows. The key in effect is published as ``sort_key`` / ``auto_sort`` in
``/api/5/processcount``:

.. code-block:: bash

    # curl -X POST http://localhost:61208/api/5/processes/sort/memory_percent
    # curl -X POST http://localhost:61208/api/5/processes/sort/auto

Keys: ``auto``, ``cpu_percent``, ``memory_percent``, ``username``, ``cpu_times``, ``io_counters``, ``name``, ``cpu_num``.

GET amps
--------

Get the plugin stats:

.. code-block:: bash

    # curl http://localhost:61208/api/5/amps
    {
        "_key": "name",
        "_levels": {
            "Conntrack": {
                "count": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "Dropbox": {
                "count": {
                    "level": "critical",
                    "prominent": false
                }
            },
            "Nginx": {
                "count": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "Python": {
                "count": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "SystemV": {
                "count": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "Systemd": {
                "count": {
                    "level": "ok",
                    "prominent": false
                }
            }
        },
        "data": [
            {
                "count": 0,
                "countmax": null,
                "countmin": 1.0,
                "name": "Dropbox",
                "refresh": 3.0,
                "regex": true,
                "result": null,
                "result_float": null,
                "timer": 1.0723226070404053
            },
            {
                "count": 0,
                "countmax": 20.0,
                "countmin": null,
                "name": "Python",
                "refresh": 3.0,
                "regex": true,
                "result": null,
                "result_float": null,
                "timer": 1.0721299648284912
            },
            "... 4 more"
        ],
        "time_since_update": 1.0603541840000617
    }

Fields (``/info`` serves them as JSON):

* ``name``: AMP name. (unit is *string*)
* ``result``: AMP result (a string, possibly multi-line). (unit is *string*)
* ``result_float``: Numeric value of \`result\` when it parses as a number, else None. (unit is *number*)
* ``refresh``: AMP refresh interval. (unit is *second*)
* ``timer``: Time until next refresh. (unit is *second*)
* ``count``: Number of matching processes. (unit is *number*)
* ``countmin``: Minimum number of matching processes. (unit is *number*)
* ``countmax``: Maximum number of matching processes. (unit is *number*)
* ``regex``: True when a regex is configured for this AMP. (unit is *bool*)

GET containers
--------------

Get the plugin stats:

.. code-block:: bash

    # curl http://localhost:61208/api/5/containers
    {
        "_key": "name",
        "_levels": {},
        "data": [],
        "disable_stats": [
            "command"
        ],
        "max_name_size": 20,
        "time_since_update": 1.0602893619998213
    }

Fields (``/info`` serves them as JSON):

* ``name``: Container name. (unit is *string*)
* ``id``: Container ID. (unit is *string*)
* ``image``: Container image. (unit is *string*)
* ``status``: Container status. (unit is *string*)
* ``created``: Container creation date. (unit is *string*)
* ``command``: Container command. (unit is *string*)
* ``cpu_percent``: Container CPU consumption. (unit is *percent*)
* ``cpu_limit``: Container CPU limit. (unit is *number*)
* ``memory_usage``: Container memory usage (v4 export value: usage − cache when present). Feeds export/REST. (unit is *byte*)
* ``memory_usage_no_cache``: Container memory usage minus inactive\_file. TUI display value. (unit is *byte*)
* ``memory_inactive_file``: Container memory inactive file. (unit is *byte*)
* ``memory_limit``: Container memory limit. (unit is *byte*)
* ``memory_percent``: Container memory usage as a percentage of its limit. (unit is *percent*)
* ``io_rx``: Container IO bytes read rate. (unit is *bytepersecond*)
* ``io_wx``: Container IO bytes write rate. (unit is *bytepersecond*)
* ``network_rx``: Container network RX bitrate. (unit is *bitpersecond*)
* ``network_tx``: Container network TX bitrate. (unit is *bitpersecond*)
* ``ports``: Container ports. (unit is *string*)
* ``started_at``: Container start time (Unix timestamp, seconds). None when the container is not active. (unit is *number*)
* ``engine``: Container engine (Docker, Podman, LXD). (unit is *string*)
* ``engine_url``: Container engine base URL / endpoint (creds are hidden). (unit is *string*)
* ``pod_name``: Pod name (Podman only). (unit is *string*)
* ``pod_id``: Pod ID (Podman only). (unit is *string*)

GET core
--------

Get the plugin stats:

.. code-block:: bash

    # curl http://localhost:61208/api/5/core
    {
        "_levels": {},
        "log": 4,
        "phys": 4,
        "time_since_update": 1.0604739400000653
    }

Fields (``/info`` serves them as JSON):

* ``phys``: Number of physical cores (hyper-thread CPUs excluded). (unit is *number*)
* ``log``: Number of logical CPU cores (physical cores × threads per core). (unit is *number*)

GET cpu
-------

Get the plugin stats:

.. code-block:: bash

    # curl http://localhost:61208/api/5/cpu
    {
        "_levels": {
            "ctx_switches": {
                "level": "ok",
                "prominent": false
            },
            "iowait": {
                "level": "ok",
                "prominent": false
            },
            "steal": {
                "level": "ok",
                "prominent": false
            },
            "system": {
                "level": "ok",
                "prominent": false
            },
            "total": {
                "level": "ok",
                "prominent": true
            },
            "user": {
                "level": "ok",
                "prominent": false
            }
        },
        "cpucore": 4,
        "ctx_switches": 8123.644344459627,
        "guest": 0.0,
        "idle": 83.0,
        "interrupts": 4742.013583919221,
        "iowait": 0.0,
        "irq": 0.0,
        "nice": 0.0,
        "soft_interrupts": 983.2843276397111,
        "steal": 0.7,
        "syscalls": 0.0,
        "system": 3.8,
        "time_since_update": 1.060730829000022,
        "total": 17.0,
        "user": 11.8
    }

Fields (``/info`` serves them as JSON):

* ``total``: Sum of all CPU percentages (except idle). (unit is *percent*)
* ``system``: Percent time spent in kernel space. System CPU time is the time spent running code in the operating system kernel. (unit is *percent*)
* ``user``: Percent time spent in user space. User CPU time is the time spent on the processor running the program's code (or code in libraries). (unit is *percent*)
* ``iowait``: (Linux) Percent time spent by the CPU waiting for I/O operations to complete. (unit is *percent*)
* ``dpc``: (Windows) Percent time spent servicing deferred procedure calls (DPCs). (unit is *percent*)
* ``idle``: Percent of CPU not used by any program. Every program or task that runs occupies a certain amount of processing time on the CPU; when the CPU has completed all tasks it is idle. (unit is *percent*)
* ``irq``: (Linux and BSD) Percent time spent servicing hardware and software interrupts. (unit is *percent*)
* ``nice``: (UNIX) Percent time occupied by user-level processes with a positive nice value (processes that have been niced down). (unit is *percent*)
* ``steal``: (Linux) Percentage of time a virtual CPU waits for a real CPU while the hypervisor is servicing another virtual processor. (unit is *percent*)
* ``guest``: (Linux) Time spent running a virtual CPU for guest operating systems under the control of the Linux kernel. (unit is *percent*)
* ``ctx_switches``: Number of context switches (voluntary + involuntary) per second. A context switch is the procedure a CPU follows to change from one task to another while ensuring the tasks do not conflict. (unit is *number*)
* ``interrupts``: Number of interrupts per second. (unit is *number*)
* ``soft_interrupts``: Number of software interrupts per second. Always 0 on Windows and SunOS. (unit is *number*)
* ``syscalls``: Number of system calls per second. Always 0 on Linux. (unit is *number*)
* ``cpucore``: Total number of logical CPU cores. (unit is *number*)

Get the thresholds in effect:

.. code-block:: bash

    # curl http://localhost:61208/api/5/cpu/limits
    {
        "ctx_switches": {
            "careful": 25000.0,
            "critical": 50000.0,
            "warning": 37500.0
        },
        "dpc": {
            "careful": 50.0,
            "critical": 90.0,
            "warning": 70.0
        },
        "iowait": {
            "careful": 50.0,
            "critical": 90.0,
            "warning": 70.0
        },
        "steal": {
            "careful": 50.0,
            "critical": 90.0,
            "warning": 70.0
        },
        "system": {
            "careful": 50.0,
            "critical": 90.0,
            "warning": 70.0
        },
        "total": {
            "careful": 65.0,
            "critical": 85.0,
            "warning": 75.0
        },
        "user": {
            "careful": 50.0,
            "critical": 90.0,
            "warning": 70.0
        }
    }

Get the last two points of its history (``nb=0`` for all of them):

.. code-block:: bash

    # curl http://localhost:61208/api/5/cpu/history?nb=2
    {
        "series": {
            "system": [
                7.1,
                3.8
            ],
            "user": [
                50.0,
                11.8
            ]
        },
        "timestamps": [
            1791731451.2649796,
            1791731452.3256605
        ]
    }

GET diskio
----------

Get the plugin stats:

.. code-block:: bash

    # curl http://localhost:61208/api/5/diskio
    {
        "_key": "disk_name",
        "_levels": {},
        "data": [
            {
                "disk_name": "vda",
                "hidden": false,
                "read_bytes": 0.0,
                "read_bytes_cumul": 954610688,
                "read_count": 0.0,
                "read_count_cumul": 50198,
                "read_latency": 0,
                "read_time": 0.0,
                "write_bytes": 11581.623160298725,
                "write_bytes_cumul": 1369092096,
                "write_count": 0.9425149056232687,
                "write_count_cumul": 24715,
                "write_latency": 1,
                "write_time": 0.9425149056232687
            },
            {
                "disk_name": "vdb",
                "hidden": false,
                "read_bytes": 0.0,
                "read_bytes_cumul": 8192,
                "read_count": 0.0,
                "read_count_cumul": 7,
                "read_latency": 0,
                "read_time": 0.0,
                "write_bytes": 0.0,
                "write_bytes_cumul": 0,
                "write_count": 0.0,
                "write_count_cumul": 0,
                "write_latency": 0,
                "write_time": 0.0
            },
            "... 5 more"
        ],
        "time_since_update": 1.0609911780002221
    }

Fields (``/info`` serves them as JSON):

* ``disk_name``: Disk name (e.g. sda, nvme0n1). (unit is *string*)
* ``read_count``: Read operations per second (rate of psutil read\_count counter). (unit is *number*)
* ``write_count``: Write operations per second (rate of psutil write\_count counter). (unit is *number*)
* ``read_time``: Time spent reading, in milliseconds per second (rate of psutil read\_time counter). (unit is *number*)
* ``write_time``: Time spent writing, in milliseconds per second (rate of psutil write\_time counter). (unit is *number*)
* ``read_latency``: Mean time spent reading per operation, in milliseconds. (unit is *number*)
* ``write_latency``: Mean time spent writing per operation, in milliseconds. (unit is *number*)
* ``read_bytes_cumul``: Bytes read since boot (cumulative counter). (unit is *bytes*)
* ``write_bytes_cumul``: Bytes written since boot (cumulative counter). (unit is *bytes*)
* ``read_count_cumul``: Read operations since boot (cumulative counter). (unit is *number*)
* ``write_count_cumul``: Write operations since boot (cumulative counter). (unit is *number*)
* ``read_bytes``: Bytes read per second (rate of psutil read\_bytes counter). (unit is *bytespers*)
* ``write_bytes``: Bytes written per second (rate of psutil write\_bytes counter). (unit is *bytespers*)

Get the last two points of its history (``nb=0`` for all of them):

.. code-block:: bash

    # curl http://localhost:61208/api/5/diskio/history?nb=2
    {
        "series": {
            "read_bytes": {
                "vda": [
                    null,
                    0.0
                ],
                "vdb": [
                    null,
                    0.0
                ],
                "vdc": [
                    null,
                    3860.5410534329085
                ],
                "vdd": [
                    null,
                    0.0
                ],
                "vde": [
                    null,
                    0.0
                ],
                "vdf": [
                    null,
                    0.0
                ],
                "zram0": [
                    null,
                    0.0
                ]
            },
            "write_bytes": {
                "vda": [
                    null,
                    11581.623160298725
                ],
                "vdb": [
                    null,
                    0.0
                ],
                "vdc": [
                    null,
                    0.0
                ],
                "vdd": [
                    null,
                    0.0
                ],
                "vde": [
                    null,
                    0.0
                ],
                "vdf": [
                    null,
                    0.0
                ],
                "zram0": [
                    null,
                    0.0
                ]
            }
        },
        "timestamps": [
            1791731451.2654548,
            1791731452.3265045
        ]
    }

GET folders
-----------

Get the plugin stats:

.. code-block:: bash

    # curl http://localhost:61208/api/5/folders
    {
        "_key": "path",
        "_levels": {},
        "data": [],
        "time_since_update": 1.0611431809998066
    }

Fields (``/info`` serves them as JSON):

* ``path``: Absolute path. (unit is *string*)
* ``size``: Folder size in bytes. (unit is *bytes*)
* ``refresh``: Refresh interval in seconds. (unit is *seconds*)
* ``errno``: Return code when retrieving folder size (0 is no error). (unit is *number*)
* ``careful``: Careful threshold in MB. (unit is *megabyte*)
* ``warning``: Warning threshold in MB. (unit is *megabyte*)
* ``critical``: Critical threshold in MB. (unit is *megabyte*)

GET fs
------

Get the plugin stats:

.. code-block:: bash

    # curl http://localhost:61208/api/5/fs
    {
        "_key": "mnt_point",
        "_levels": {
            "/": {
                "percent": {
                    "level": "ok",
                    "prominent": false
                }
            }
        },
        "data": [
            {
                "device_name": "/dev/vda",
                "free": 29979668480,
                "fs_type": "ext4",
                "mnt_point": "/",
                "options": "rw,relatime,discard,no_prefetch_block_bitmaps,resv_strict,resuid=65534,resgid=65534",
                "percent": 27.1,
                "size": 270553174016,
                "used": 11154407424
            },
            {
                "device_name": "/dev/vdb",
                "free": 0,
                "fs_type": "squashfs",
                "mnt_point": "/opt/rclone",
                "options": "ro,relatime,errors=continue",
                "percent": 100.0,
                "size": 10092544,
                "used": 10092544
            },
            "... 4 more"
        ],
        "free_space": false,
        "time_since_update": 1.0607528479999928
    }

Fields (``/info`` serves them as JSON):

* ``mnt_point``: Mount point. (unit is *string*)
* ``device_name``: Device name backing the filesystem (e.g. /dev/sda1). (unit is *string*)
* ``fs_type``: File system type (e.g. ext4, xfs, btrfs). (unit is *string*)
* ``options``: Mount options string (comma-separated). (unit is *string*)
* ``size``: Total size of the filesystem in bytes. (unit is *bytes*)
* ``used``: Used size in bytes. (unit is *bytes*)
* ``free``: Free size in bytes. (unit is *bytes*)
* ``percent``: Filesystem usage as a percentage of total size. (unit is *percent*)

Get the thresholds in effect:

.. code-block:: bash

    # curl http://localhost:61208/api/5/fs/limits
    {
        "percent": {
            "careful": 50.0,
            "critical": 90.0,
            "warning": 70.0
        }
    }

Get the last two points of its history (``nb=0`` for all of them):

.. code-block:: bash

    # curl http://localhost:61208/api/5/fs/history?nb=2
    {
        "series": {
            "percent": {
                "/": [
                    27.1,
                    27.1
                ],
                "/mnt/skills/examples": [
                    100.0,
                    100.0
                ],
                "/mnt/skills/public": [
                    100.0,
                    100.0
                ],
                "/opt/claude-code": [
                    91.1,
                    91.1
                ],
                "/opt/env-runner": [
                    66.1,
                    66.1
                ],
                "/opt/rclone": [
                    100.0,
                    100.0
                ]
            }
        },
        "timestamps": [
            1791731451.266975,
            1791731452.3277092
        ]
    }

GET gpu
-------

Get the plugin stats:

.. code-block:: bash

    # curl http://localhost:61208/api/5/gpu
    {
        "_key": "gpu_id",
        "_levels": {},
        "data": [],
        "time_since_update": 1.0608642150000378
    }

Fields (``/info`` serves them as JSON):

* ``gpu_id``: GPU identifier (e.g. nvidia0). (unit is *string*)
* ``name``: GPU product name. (unit is *string*)
* ``proc``: GPU processor consumption. (unit is *percent*)
* ``mem``: GPU memory consumption. (unit is *percent*)
* ``temperature``: GPU temperature. (unit is *celsius*)
* ``fan_speed``: GPU fan speed. (unit is *percent*)

Get the thresholds in effect:

.. code-block:: bash

    # curl http://localhost:61208/api/5/gpu/limits
    {
        "mem": {
            "careful": 50.0,
            "critical": 90.0,
            "warning": 70.0
        },
        "proc": {
            "careful": 50.0,
            "critical": 90.0,
            "warning": 70.0
        },
        "temperature": {
            "careful": 60.0,
            "critical": 80.0,
            "warning": 70.0
        }
    }

GET ip
------

Get the plugin stats:

.. code-block:: bash

    # curl http://localhost:61208/api/5/ip
    {
        "_levels": {},
        "address": "192.0.2.2",
        "mask": "255.255.255.0",
        "mask_cidr": 24,
        "time_since_update": 1.0607930149999447
    }

Fields (``/info`` serves them as JSON):

* ``address``: Private IP address. (unit is *string*)
* ``mask``: Private IP mask. (unit is *string*)
* ``mask_cidr``: Private IP mask in CIDR format. (unit is *number*)
* ``gateway``: Private IP gateway. (unit is *string*)
* ``public_address``: Public IP address. (unit is *string*)
* ``public_info_human``: Public IP information (human readable). (unit is *string*)

GET load
--------

Get the plugin stats:

.. code-block:: bash

    # curl http://localhost:61208/api/5/load
    {
        "_levels": {
            "min15": {
                "level": "ok",
                "prominent": true
            },
            "min5": {
                "level": "ok",
                "prominent": false
            }
        },
        "cpucore": 4,
        "min1": 0.904296875,
        "min15": 0.56201171875,
        "min5": 0.560546875,
        "time_since_update": 1.060776580000038
    }

Fields (``/info`` serves them as JSON):

* ``min1``: Average number of processes waiting in the run-queue plus those currently executing, over 1 minute. (unit is *float*)
* ``min5``: Average number of processes waiting in the run-queue plus those currently executing, over 5 minutes. (unit is *float*)
* ``min15``: Average number of processes waiting in the run-queue plus those currently executing, over 15 minutes. (unit is *float*)
* ``cpucore``: Total number of logical CPU cores. (unit is *number*)

Get the thresholds in effect:

.. code-block:: bash

    # curl http://localhost:61208/api/5/load/limits
    {
        "min15": {
            "careful": 0.7,
            "critical": 5.0,
            "warning": 1.0
        },
        "min5": {
            "careful": 0.7,
            "critical": 5.0,
            "warning": 1.0
        }
    }

Get the last two points of its history (``nb=0`` for all of them):

.. code-block:: bash

    # curl http://localhost:61208/api/5/load/history?nb=2
    {
        "series": {
            "min1": [
                0.904296875,
                0.904296875
            ],
            "min15": [
                0.56201171875,
                0.56201171875
            ],
            "min5": [
                0.560546875,
                0.560546875
            ]
        },
        "timestamps": [
            1791731451.2684546,
            1791731452.3292391
        ]
    }

GET mem
-------

Get the plugin stats:

.. code-block:: bash

    # curl http://localhost:61208/api/5/mem
    {
        "_levels": {
            "percent": {
                "level": "ok",
                "prominent": true
            }
        },
        "_show_available": false,
        "active": 1073512448,
        "available": 15996850176,
        "buffers": 264708096,
        "cached": 1597620224,
        "free": 14421540864,
        "inactive": 1084399616,
        "percent": 5.2,
        "shared": 14733312,
        "slab": 143355904,
        "time_since_update": 1.0606376710002223,
        "total": 16874930176,
        "used": 878080000
    }

Fields (``/info`` serves them as JSON):

* ``total``: Total physical memory available. (unit is *bytes*)
* ``available``: Actual amount of available memory that can be given instantly to processes that request more memory; calculated by summing different memory values depending on the platform (e.g. free + buffers + cached on Linux). Suitable for monitoring actual memory usage in a cross-platform fashion. (unit is *bytes*)
* ``percent``: Percentage usage calculated as (total - available) / total \* 100. (unit is *percent*)
* ``used``: Memory used, calculated differently depending on the platform and designed for informational purposes only. (unit is *bytes*)
* ``free``: Memory not being used at all (zeroed) that is readily available; note that this does not reflect the actual memory available — use \`available\` instead. (unit is *bytes*)
* ``active``: (UNIX) Memory currently in use or very recently used, resident in RAM. (unit is *bytes*)
* ``inactive``: (UNIX) Memory that is marked as not used. (unit is *bytes*)
* ``buffers``: (Linux, BSD) Cache for items like filesystem metadata. (unit is *bytes*)
* ``cached``: (Linux, BSD) Cache for various things (including ZFS cache). (unit is *bytes*)
* ``shared``: (BSD) Memory that may be simultaneously accessed by multiple processes. (unit is *bytes*)
* ``wired``: (BSD, macOS) Memory marked to always stay in RAM — never paged to disk. (unit is *bytes*)
* ``slab``: (Linux) In-kernel data structures cache. (unit is *bytes*)

Get the thresholds in effect:

.. code-block:: bash

    # curl http://localhost:61208/api/5/mem/limits
    {
        "percent": {
            "careful": 50.0,
            "critical": 90.0,
            "warning": 70.0
        }
    }

Get the last two points of its history (``nb=0`` for all of them):

.. code-block:: bash

    # curl http://localhost:61208/api/5/mem/history?nb=2
    {
        "series": {
            "percent": [
                5.1,
                5.2
            ]
        },
        "timestamps": [
            1791731451.2689886,
            1791731452.329622
        ]
    }

GET memswap
-----------

Get the plugin stats:

.. code-block:: bash

    # curl http://localhost:61208/api/5/memswap
    {
        "_levels": {
            "percent": {
                "level": "ok",
                "prominent": true
            }
        },
        "free": 0,
        "percent": 0.0,
        "sin": 0.0,
        "sout": 0.0,
        "time_since_update": 1.0606173819996911,
        "total": 0,
        "used": 0
    }

Fields (``/info`` serves them as JSON):

* ``total``: Total swap memory. (unit is *bytes*)
* ``used``: Used swap memory. (unit is *bytes*)
* ``free``: Free swap memory. (unit is *bytes*)
* ``percent``: Used swap memory as a percentage of total. (unit is *percent*)
* ``sin``: Bytes the system has swapped in from disk (per second — v4 reports the cumulative counter; v5 converts it to a rate). (unit is *bytespers*)
* ``sout``: Bytes the system has swapped out to disk (per second — v4 reports the cumulative counter; v5 converts it to a rate). (unit is *bytespers*)

Get the thresholds in effect:

.. code-block:: bash

    # curl http://localhost:61208/api/5/memswap/limits
    {
        "percent": {
            "careful": 60.0,
            "critical": 95.0,
            "warning": 80.0
        }
    }

Get the last two points of its history (``nb=0`` for all of them):

.. code-block:: bash

    # curl http://localhost:61208/api/5/memswap/history?nb=2
    {
        "series": {
            "percent": [
                0.0,
                0.0
            ]
        },
        "timestamps": [
            1791731451.2694294,
            1791731452.33005
        ]
    }

GET network
-----------

Get the plugin stats:

.. code-block:: bash

    # curl http://localhost:61208/api/5/network
    {
        "_key": "interface_name",
        "_levels": {
            "eth0": {
                "errors_in": {
                    "level": "ok",
                    "prominent": false
                },
                "errors_out": {
                    "level": "ok",
                    "prominent": false
                }
            }
        },
        "data": [
            {
                "bytes_recv": 18113.047322998682,
                "bytes_recv_cumul": 192780798,
                "bytes_sent": 83501.30850990894,
                "bytes_sent_cumul": 117686349,
                "bytes_speed_rate_per_sec": 0.0,
                "dropped_in": 0.0,
                "dropped_out": 0.0,
                "errors_in": 0.0,
                "errors_out": 0.0,
                "hidden": false,
                "interface_name": "eth0",
                "is_up": true
            }
        ],
        "time_since_update": 1.0601750030000403
    }

Fields (``/info`` serves them as JSON):

* ``interface_name``: Network interface name. (unit is *string*)
* ``bytes_recv``: Bytes received per second. (unit is *bytespers*)
* ``bytes_sent``: Bytes sent per second. (unit is *bytespers*)
* ``bytes_recv_cumul``: Bytes received since the interface came up (cumulative counter). (unit is *bytes*)
* ``bytes_sent_cumul``: Bytes sent since the interface came up (cumulative counter). (unit is *bytes*)
* ``errors_in``: Receive errors per second. (unit is *number*)
* ``errors_out``: Send errors per second. (unit is *number*)
* ``dropped_in``: Receive packets dropped per second. (unit is *number*)
* ``dropped_out``: Send packets dropped per second. (unit is *number*)
* ``bytes_speed_rate_per_sec``: Per-direction bandwidth capacity in bytes/s. Computed from net\_if\_stats().speed (Mbit/s), each direction getting the full link speed: speed\_mbits \* 1e6 / 8. Returns 0 when the OS does not report a link speed (loopback, virtual interfaces) — in which case threshold normalisation is skipped for bytes\_recv / bytes\_sent. (unit is *bytespers*)
* ``is_up``: Whether the interface is up. (unit is *bool*)

Get the thresholds in effect:

.. code-block:: bash

    # curl http://localhost:61208/api/5/network/limits
    {
        "bytes_recv": {
            "careful": 0.7,
            "critical": 0.9,
            "warning": 0.8
        },
        "bytes_sent": {
            "careful": 0.7,
            "critical": 0.9,
            "warning": 0.8
        },
        "errors_in": {
            "careful": 1.0,
            "critical": 20.0,
            "warning": 5.0
        },
        "errors_out": {
            "careful": 1.0,
            "critical": 20.0,
            "warning": 5.0
        }
    }

Get the last two points of its history (``nb=0`` for all of them):

.. code-block:: bash

    # curl http://localhost:61208/api/5/network/history?nb=2
    {
        "series": {
            "bytes_recv": {
                "eth0": [
                    null,
                    18113.047322998682
                ]
            },
            "bytes_sent": {
                "eth0": [
                    null,
                    83501.30850990894
                ]
            }
        },
        "timestamps": [
            1791731451.2715673,
            1791731452.3317726
        ]
    }

GET now
-------

Get the plugin stats:

.. code-block:: bash

    # curl http://localhost:61208/api/5/now
    {
        "_levels": {},
        "custom": "2026-10-11 15:10:52 UTC",
        "iso": "2026-10-11T15:10:52+00:00",
        "time_since_update": 1.0602826370000002
    }

Fields (``/info`` serves them as JSON):

* ``custom``: Current date in custom format. (unit is *string*)
* ``iso``: Current date in ISO 8601 format. (unit is *string*)

GET percpu
----------

Get the plugin stats:

.. code-block:: bash

    # curl http://localhost:61208/api/5/percpu
    {
        "_key": "cpu_number",
        "_levels": {
            "0": {
                "system": {
                    "level": "ok",
                    "prominent": false
                },
                "user": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "1": {
                "system": {
                    "level": "ok",
                    "prominent": false
                },
                "user": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "2": {
                "system": {
                    "level": "ok",
                    "prominent": false
                },
                "user": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "3": {
                "system": {
                    "level": "ok",
                    "prominent": false
                },
                "user": {
                    "level": "ok",
                    "prominent": false
                }
            }
        },
        "data": [
            {
                "cpu_number": 0,
                "guest": 0.0,
                "guest_nice": 0.0,
                "idle": 71.0,
                "iowait": 0.0,
                "irq": 0.0,
                "nice": 0.0,
                "softirq": 1.9,
                "steal": 0.9,
                "system": 4.7,
                "total": 29.0,
                "user": 21.5
            },
            {
                "cpu_number": 1,
                "guest": 0.0,
                "guest_nice": 0.0,
                "idle": 87.6,
                "iowait": 0.0,
                "irq": 0.0,
                "nice": 0.0,
                "softirq": 1.0,
                "steal": 1.0,
                "system": 2.9,
                "total": 12.4,
                "user": 7.6
            },
            "... 2 more"
        ],
        "max_cpu_display": 4,
        "stat_fields": [
            "user",
            "system",
            "iowait",
            "idle",
            "irq",
            "nice",
            "steal",
            "guest"
        ],
        "thresholds": {
            "system": {
                "careful": 50.0,
                "critical": 90.0,
                "warning": 70.0
            },
            "user": {
                "careful": 50.0,
                "critical": 90.0,
                "warning": 70.0
            }
        },
        "time_since_update": 1.0602702020000834
    }

Fields (``/info`` serves them as JSON):

* ``cpu_number``: CPU core number (zero-based logical core index). (unit is *number*)
* ``total``: Sum of CPU percentages (except idle) for this core. (unit is *percent*)
* ``system``: Percent time spent in kernel space on this core. System CPU time is the time spent running code in the operating system kernel. (unit is *percent*)
* ``user``: Percent time spent in user space on this core. User CPU time is the time spent on the processor running the program's code. (unit is *percent*)
* ``idle``: Percent time this core was idle. (unit is *percent*)
* ``iowait``: (Linux) Percent time this core spent waiting for I/O operations to complete. (unit is *percent*)
* ``irq``: (Linux and BSD) Percent time this core spent servicing hardware/software interrupts. (unit is *percent*)
* ``softirq``: (Linux) Percent time this core spent handling software interrupts. (unit is *percent*)
* ``nice``: (UNIX) Percent time this core spent on niced user-level processes. (unit is *percent*)
* ``steal``: (Linux) Percentage of time this virtual CPU waited for a real CPU while the hypervisor was servicing another virtual processor. (unit is *percent*)
* ``guest``: (Linux) Percent of time this core spent running a virtual CPU for guest OSes. (unit is *percent*)
* ``guest_nice``: (Linux) Percent of time this core spent running a niced guest virtual CPU. (unit is *percent*)
* ``dpc``: (Windows) Percent of time this core spent handling deferred procedure calls. (unit is *percent*)
* ``interrupt``: (Windows) Percent of time this core spent handling software interrupts. (unit is *percent*)
* ``max_cpu_display``: Maximum number of CPU cores displayed before the mean row ([percpu] max\_cpu\_display). (unit is *number*)
* ``thresholds``: Effective [percpu] thresholds per column, used to colour the CPU\* mean row. (unit is *string*)
* ``stat_fields``: OS-specific stat columns, in the order the TUI renders them (define\_headers\_from\_os). (unit is *string*)

Get the thresholds in effect:

.. code-block:: bash

    # curl http://localhost:61208/api/5/percpu/limits
    {
        "system": {
            "careful": 50.0,
            "critical": 90.0,
            "warning": 70.0
        },
        "user": {
            "careful": 50.0,
            "critical": 90.0,
            "warning": 70.0
        }
    }

Get the last two points of its history (``nb=0`` for all of them):

.. code-block:: bash

    # curl http://localhost:61208/api/5/percpu/history?nb=2
    {
        "series": {
            "system": {
                "0": [
                    0.0,
                    4.7
                ],
                "1": [
                    0.0,
                    2.9
                ],
                "2": [
                    0.0,
                    3.8
                ],
                "3": [
                    0.0,
                    3.8
                ]
            },
            "user": {
                "0": [
                    100.0,
                    21.5
                ],
                "1": [
                    0.0,
                    7.6
                ],
                "2": [
                    100.0,
                    8.6
                ],
                "3": [
                    25.0,
                    7.7
                ]
            }
        },
        "timestamps": [
            1791731451.2724829,
            1791731452.3328311
        ]
    }

GET ports
---------

Get the plugin stats:

.. code-block:: bash

    # curl http://localhost:61208/api/5/ports
    {
        "_key": "indice",
        "_levels": {
            "port_0": {
                "status": {
                    "level": "careful",
                    "prominent": false
                }
            }
        },
        "data": [
            {
                "description": "DefaultGateway",
                "host": "192.0.2.1",
                "indice": "port_0",
                "port": 0,
                "refresh": 30,
                "rtt_warning": null,
                "status": null,
                "timeout": 3
            }
        ],
        "time_since_update": 1.0598919829999431
    }

Fields (``/info`` serves them as JSON):

* ``indice``: Unique indice for the host/port. (unit is *string*)
* ``description``: Human readable description for the host/port/URL. (unit is *string*)
* ``host``: Measurement is done on this host (or IP address). (unit is *string*)
* ``port``: Measurement is done on this port (0 for ICMP). (unit is *number*)
* ``url``: Measurement is done on this URL (HEAD request). (unit is *string*)
* ``status``: Measurement result: None while scanning, 0/False on timeout, the RTT in seconds for a port, or the HTTP status code for a URL. (unit is *second*)
* ``elapsed``: HTTP response time (URL items only). (unit is *second*)
* ``rtt_warning``: Warning threshold (in seconds) for the measurement. (unit is *second*)
* ``timeout``: Timeout (in seconds) for the measurement. (unit is *second*)
* ``refresh``: Refresh time (in seconds) for this host/port. (unit is *second*)

GET processcount
----------------

Get the plugin stats:

.. code-block:: bash

    # curl http://localhost:61208/api/5/processcount
    {
        "_levels": {},
        "auto_sort": true,
        "pid_max": 32768,
        "running": 0,
        "sleeping": 35,
        "sort_key": "cpu_percent",
        "thread": 111,
        "time_since_update": 1.0447651949998544,
        "total": 80
    }

Fields (``/info`` serves them as JSON):

* ``total``: Total number of processes. (unit is *number*)
* ``running``: Number of running processes. (unit is *number*)
* ``sleeping``: Number of sleeping processes. (unit is *number*)
* ``thread``: Total number of threads across all processes. (unit is *number*)
* ``pid_max``: Maximum PID value supported by the kernel (Linux) or None. (unit is *number*)
* ``sort_key``: Key the processes, containers and VMs are sorted by. (unit is *string*)
* ``auto_sort``: True when the sort key is chosen automatically (from the alerts). (unit is *bool*)

Get the last two points of its history (``nb=0`` for all of them):

.. code-block:: bash

    # curl http://localhost:61208/api/5/processcount/history?nb=2
    {
        "series": {
            "running": [
                1,
                0
            ],
            "sleeping": [
                36,
                35
            ],
            "thread": [
                124,
                111
            ],
            "total": [
                82,
                80
            ]
        },
        "timestamps": [
            1791731451.3006876,
            1791731452.3454337
        ]
    }

GET processlist
---------------

Get the plugin stats:

.. code-block:: bash

    # curl http://localhost:61208/api/5/processlist
    {
        "_key": "pid",
        "_levels": {
            "1": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "10": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "nice": {
                    "level": "warning",
                    "prominent": false
                },
                "status": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "120": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "13": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "nice": {
                    "level": "warning",
                    "prominent": false
                },
                "status": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "14": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "15": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "status": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "16": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "1693": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "status": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "17": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "17040": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "status": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "17198": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "status": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "18": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "19": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "19363": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "status": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "2": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "20": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "21": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "21728": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "status": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "21777": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "status": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "22": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "24": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "nice": {
                    "level": "warning",
                    "prominent": false
                },
                "status": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "25": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "26": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "26236": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "status": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "27": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "28": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "status": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "28559": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "status": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "29": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "nice": {
                    "level": "warning",
                    "prominent": false
                },
                "status": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "3": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "30": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "31": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "32": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "34": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "nice": {
                    "level": "warning",
                    "prominent": false
                },
                "status": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "35": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "36": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "nice": {
                    "level": "warning",
                    "prominent": false
                },
                "status": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "37": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "status": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "38": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "status": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "39": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "status": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "4": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "nice": {
                    "level": "warning",
                    "prominent": false
                },
                "status": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "40": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "41": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "42": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "44": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "nice": {
                    "level": "warning",
                    "prominent": false
                },
                "status": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "4530": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "status": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "46": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "47": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "nice": {
                    "level": "warning",
                    "prominent": false
                }
            },
            "48": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "nice": {
                    "level": "warning",
                    "prominent": false
                }
            },
            "49": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "nice": {
                    "level": "warning",
                    "prominent": false
                },
                "status": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "5": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "nice": {
                    "level": "warning",
                    "prominent": false
                },
                "status": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "50": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "status": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "51": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "status": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "52": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "status": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "53": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "54": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "nice": {
                    "level": "warning",
                    "prominent": false
                },
                "status": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "5452": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "status": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "55": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "nice": {
                    "level": "warning",
                    "prominent": false
                },
                "status": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "56": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "57": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "nice": {
                    "level": "warning",
                    "prominent": false
                },
                "status": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "58": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "nice": {
                    "level": "warning",
                    "prominent": false
                },
                "status": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "59": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "nice": {
                    "level": "warning",
                    "prominent": false
                },
                "status": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "6": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "nice": {
                    "level": "warning",
                    "prominent": false
                },
                "status": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "60": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "nice": {
                    "level": "warning",
                    "prominent": false
                },
                "status": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "61": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "6150": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "6191": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "62": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "63": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "64": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "nice": {
                    "level": "warning",
                    "prominent": false
                },
                "status": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "67": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "nice": {
                    "level": "warning",
                    "prominent": false
                },
                "status": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "68": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "nice": {
                    "level": "warning",
                    "prominent": false
                },
                "status": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "69": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "nice": {
                    "level": "warning",
                    "prominent": false
                },
                "status": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "7": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "nice": {
                    "level": "warning",
                    "prominent": false
                },
                "status": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "76": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "status": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "77": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "nice": {
                    "level": "warning",
                    "prominent": false
                },
                "status": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "79": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "nice": {
                    "level": "warning",
                    "prominent": false
                },
                "status": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "8": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "nice": {
                    "level": "warning",
                    "prominent": false
                },
                "status": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "80": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "nice": {
                    "level": "warning",
                    "prominent": false
                },
                "status": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "82": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "83": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "87": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            }
        },
        "cpucore": 4,
        "data": [
            {
                "cmdline": [
                    "/opt/claude-code/bin/claude",
                    "--output-format=stream-json",
                    "--verbose",
                    "--settings",
                    "/root/.claude/launcher-settings.json",
                    "--replay-user-messages",
                    "--input-format=stream-json",
                    "--debug-to-stderr",
                    "--effort",
                    "medium",
                    "--tools",
                    "preset:default,Task,Bash,Glob,Grep,Read,Edit,MultiEdit,Write,NotebookEdit,WebFetch,TodoWrite,WebSearch,BashOutput,KillBash,Skill,Tmux,Monitor,SendUserFile,REPL,ExitPlanMode,AskUserQuestion,ToolSearch",
                    "--allowed-tools",
                    "preset:default,Task,Bash,Glob,Grep,Read,Edit,MultiEdit,Write,NotebookEdit,WebFetch,TodoWrite,WebSearch,BashOutput,KillBash,Skill,Tmux,Monitor,SendUserFile,REPL,ToolSearch,mcp__claude-code-remote__list_sessions,mcp__claude-code-remote__get_session,mcp__claude-code-remote__list_events,mcp__claude-code-remote__get_event,mcp__claude-code-remote__list_triggers,mcp__claude-code-remote__get_trigger,mcp__claude-code-remote__send_later,mcp__claude-code-remote__list_trigger_runs,mcp__claude-code-remote__get_trigger_run_log,mcp__claude-code-remote__list_environments,mcp__claude-code-remote__list_repos,mcp__claude-code-remote__subscribe_pr_activity,mcp__claude-code-remote__unsubscribe_pr_activity,mcp__claude-code-remote__read_documentation,mcp__github__*,mcp__claude-code-remote__list_sessions,mcp__claude-code-remote__get_session,mcp__claude-code-remote__list_events,mcp__claude-code-remote__get_event,mcp__claude-code-remote__list_triggers,mcp__claude-code-remote__get_trigger,mcp__claude-code-remote__send_later,mcp__claude-code-remote__list_trigger_runs,mcp__claude-code-remote__get_trigger_run_log,mcp__claude-code-remote__list_environments,mcp__claude-code-remote__list_repos,mcp__claude-code-remote__subscribe_pr_activity,mcp__claude-code-remote__unsubscribe_pr_activity,mcp__claude-code-remote__read_documentation,mcp__Figma__download_assets,mcp__Figma__export_video,mcp__Figma__get_code_connect_map,mcp__Figma__get_code_connect_suggestions,mcp__Figma__get_context_for_code_connect,mcp__Figma__get_design_context,mcp__Figma__get_figjam,mcp__Figma__get_figma_skill,mcp__Figma__get_generative_plugin,mcp__Figma__get_libraries,mcp__Figma__get_metadata,mcp__Figma__get_motion_context,mcp__Figma__get_screenshot,mcp__Figma__get_shader,mcp__Figma__get_variable_defs,mcp__Figma__list_file_components_for_code_connect,mcp__Figma__list_file_shaders,mcp__Figma__list_generative_plugins,mcp__Figma__list_shaders,mcp__Figma__search_design_system,mcp__Figma__weave_find_model,mcp__Figma__weave_get_model_run_output,mcp__Figma__weave_get_tool_inputs,mcp__Figma__weave_get_tool_run_output,mcp__Figma__weave_list_tools,mcp__Figma__whoami,mcp__Claude_Docs__batch,mcp__Claude_Docs__create,mcp__Claude_Docs__export,mcp__Claude_Docs__guide,mcp__Claude_Docs__query,mcp__Claude_Docs__read,mcp__Claude_Docs__update",
                    "--disallowed-tools",
                    "mcp__Excalidraw__export_to_excalidraw,mcp__Excalidraw__read_checkpoint,mcp__Excalidraw__save_checkpoint",
                    "--mcp-config",
                    "/tmp/mcp-config-cse_012aYMPrCY8CaFpFDgvofNEE.json",
                    "--prompt-suggestions",
                    "true",
                    "--model",
                    "claude-opus-5-5",
                    "--append-system-prompt-file",
                    "/tmp/claude-append-system-prompt.txt",
                    "--add-dir",
                    "/home/user/glances",
                    "--sdk-url",
                    "https://api.anthropic.com/v1/code/sessions/cse_012aYMPrCY8CaFpFDgvofNEE",
                    "--resume=https://api.anthropic.com/v1/code/sessions/cse_012aYMPrCY8CaFpFDgvofNEE",
                    "--debug"
                ],
                "cpu_num": 3,
                "cpu_percent": 13.3,
                "cpu_times": {
                    "children_system": 274.2,
                    "children_user": 1401.15,
                    "iowait": 0.0,
                    "system": 26.0,
                    "user": 135.84
                },
                "gids": {
                    "effective": 0,
                    "real": 0,
                    "saved": 0
                },
                "io_counters": [
                    1023254528,
                    2140028928,
                    1023250432,
                    2139877376,
                    1
                ],
                "key": "pid",
                "memory_info": {
                    "data": 5649448960,
                    "dirty": 0,
                    "lib": 0,
                    "rss": 478720000,
                    "shared": 132747264,
                    "text": 62685184,
                    "vms": 5739888640
                },
                "memory_percent": 2.83687099743292,
                "name": "claude",
                "nice": 0,
                "num_threads": 13,
                "pid": 120,
                "status": "S",
                "time_since_update": 1.0596644878387451,
                "username": "root"
            },
            {
                "cmdline": [
                    "/tmp/claude-0/-home-user-glances/e9f514df-ce0c-51e4-ae2a-cfc1eafb2ab6/scratchpad/venv/bin/python",
                    "-m",
                    "glances",
                    "-C",
                    "conf/glances.conf",
                    "--api-restful-doc"
                ],
                "cpu_num": 0,
                "cpu_percent": 2.9,
                "cpu_times": {
                    "children_system": 0.01,
                    "children_user": 0.0,
                    "iowait": 0.0,
                    "system": 0.05,
                    "user": 0.57
                },
                "gids": {
                    "effective": 0,
                    "real": 0,
                    "saved": 0
                },
                "io_counters": [
                    28672,
                    4096,
                    28672,
                    4096,
                    1
                ],
                "key": "pid",
                "memory_info": {
                    "data": 85155840,
                    "dirty": 0,
                    "lib": 0,
                    "rss": 70606848,
                    "shared": 21991424,
                    "text": 2752512,
                    "vms": 389713920
                },
                "memory_percent": 0.4184126823850154,
                "name": "python",
                "nice": 0,
                "num_threads": 4,
                "pid": 6191,
                "status": "S",
                "time_since_update": 1.0596644878387451,
                "username": "root"
            },
            "... 78 more"
        ],
        "time_since_update": 1.0447039000000586
    }

Fields (``/info`` serves them as JSON):

* ``pid``: Process identifier (PID). (unit is *number*)
* ``name``: Process name. (unit is *string*)
* ``username``: Process owner (user name). (unit is *string*)
* ``status``: Process status (single letter — S sleeping, R running, etc.). (unit is *string*)
* ``nice``: Process nice value. (unit is *number*)
* ``num_threads``: Number of threads spawned by the process. (unit is *number*)
* ``cpu_percent``: Process CPU consumption (can exceed 100% on multi-threaded workloads spread across cores). (unit is *percent*)
* ``memory_percent``: Process resident memory consumption as a percentage of total RAM. (unit is *percent*)
* ``cmdline``: Command line of the process (list of argv tokens). (unit is *list*)
* ``cpu_num``: CPU core number where the process is currently running. (unit is *number*)
* ``memory_info``: Process memory information (psutil pmem namedtuple). (unit is *byte*)
* ``cpu_times``: Process CPU times (psutil pcputimes namedtuple). (unit is *second*)
* ``io_counters``: Process I/O counters (list [read\_bytes, write\_bytes, ..., io\_tag]). (unit is *byte*)
* ``gids``: Process group IDs (psutil pgids namedtuple). (unit is *number*)
* ``time_since_update``: Wall-clock interval since the previous engine refresh (seconds). (unit is *second*)
* ``key``: Name of the primary key field (always \`\`pid\`\`). (unit is *string*)
* ``cpucore``: Number of logical CPU cores (divisor of the Irix-mode CPU%). (unit is *number*)

Get the thresholds in effect:

.. code-block:: bash

    # curl http://localhost:61208/api/5/processlist/limits
    {
        "_categorical": {
            "nice": {
                "warning": [
                    "-1",
                    "-10",
                    "-11",
                    "-12",
                    "-13",
                    "-14",
                    "-15",
                    "-16",
                    "-17",
                    "-18",
                    "-19",
                    "-2",
                    "-20",
                    "-3",
                    "-4",
                    "-5",
                    "-6",
                    "-7",
                    "-8",
                    "-9",
                    "1",
                    "10",
                    "11",
                    "12",
                    "13",
                    "14",
                    "15",
                    "16",
                    "17",
                    "18",
                    "19",
                    "2",
                    "3",
                    "4",
                    "5",
                    "6",
                    "7",
                    "8",
                    "9"
                ]
            },
            "status": {
                "critical": [
                    "D",
                    "Z"
                ],
                "ok": [
                    "I",
                    "P",
                    "R",
                    "W"
                ]
            }
        },
        "cpu_percent": {
            "careful": 50.0,
            "critical": 90.0,
            "warning": 70.0
        },
        "memory_percent": {
            "careful": 50.0,
            "critical": 90.0,
            "warning": 70.0
        }
    }

GET programlist
---------------

Get the plugin stats:

.. code-block:: bash

    # curl http://localhost:61208/api/5/programlist
    {
        "_key": "name",
        "_levels": {
            "6": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "bash": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "claude": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "cpuhp/0": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "cpuhp/1": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "cpuhp/2": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "cpuhp/3": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "environment-manager": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "hwrng": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "irq/24-ACPI:Ged": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "irq/25-ACPI:Ged": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kauditd": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kcompactd0": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kdevtmpfs": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "khugepaged": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "khungtaskd": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "ksmd": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "ksoftirqd/0": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "ksoftirqd/1": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "ksoftirqd/2": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "ksoftirqd/3": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kswapd0": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kthreadd": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/0:0": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/0:0H-events_highpri": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/0:1H-kblockd": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/0:2-events": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/1:0-mm_percpu_wq": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/1:0H-events_highpri": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/1:1-events_freezable": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/1:1H-kblockd": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/2:0-slub_flushwq": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/2:0H-events_highpri": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/2:1-events": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/2:1H-kblockd": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/3:0H-events_highpri": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/3:1-mm_percpu_wq": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/3:1H-kblockd": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/3:2": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/R-ext4-rsv-conversion": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/R-inet_frag_wq": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/R-kblockd": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/R-kstrp": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/R-kthrotld": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/R-kvfree_rcu_reclaim": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/R-mm_percpu_wq": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/R-netns": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/R-quota_events_unbound": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/R-rcu_gp": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/R-slub_flushwq": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/R-sync_wq": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/R-writeback": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/R-xfs_mru_cache": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/R-xfsalloc": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/u16:0": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/u16:1-iou_exit": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/u16:2-kvfree_rcu_reclaim": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/u16:3-iou_exit": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/u16:5-iou_exit": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/u16:7-iou_exit": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/u16:8-iou_exit": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/u17:0": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "migration/0": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "migration/1": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "migration/2": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "migration/3": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "oom_reaper": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "pool_workqueue_release": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "process_api": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "python": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "rcu_exp_gp_kthread_worker": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "rcu_exp_par_gp_kthread_worker/0": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "rcu_preempt": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "rcu_tasks_kthread": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "rcu_tasks_rude_kthread": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "rcu_tasks_trace_kthread": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "sh": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "watchdogd": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            }
        },
        "cpucore": 4,
        "data": [
            {
                "cmdline": [
                    "claude"
                ],
                "cpu_percent": 13.3,
                "cpu_times": {
                    "children_system": 274.2,
                    "children_user": 1401.15,
                    "iowait": 0.0,
                    "system": 26.0,
                    "user": 135.84
                },
                "io_counters": [
                    1023254528,
                    2140028928,
                    1023250432,
                    2139877376,
                    1
                ],
                "memory_info": {
                    "data": 5649448960,
                    "dirty": 0,
                    "lib": 0,
                    "rss": 478720000,
                    "shared": 132747264,
                    "text": 62685184,
                    "vms": 5739888640
                },
                "memory_percent": 2.83687099743292,
                "name": "claude",
                "nice": 0,
                "nprocs": 1,
                "num_threads": 13,
                "status": "S",
                "time_since_update": 1.0596644878387451,
                "username": "root"
            },
            {
                "cmdline": [
                    "python"
                ],
                "cpu_percent": 2.9,
                "cpu_times": {
                    "children_system": 0.01,
                    "children_user": 0.0,
                    "iowait": 0.0,
                    "system": 0.05,
                    "user": 0.57
                },
                "io_counters": [
                    28672,
                    4096,
                    28672,
                    4096,
                    1
                ],
                "memory_info": {
                    "data": 85155840,
                    "dirty": 0,
                    "lib": 0,
                    "rss": 70606848,
                    "shared": 21991424,
                    "text": 2752512,
                    "vms": 389713920
                },
                "memory_percent": 0.4184126823850154,
                "name": "python",
                "nice": 0,
                "nprocs": 1,
                "num_threads": 4,
                "status": "S",
                "time_since_update": 1.0596644878387451,
                "username": "root"
            },
            "... 76 more"
        ],
        "time_since_update": 1.0433678120002696
    }

Fields (``/info`` serves them as JSON):

* ``name``: Program name (shared process name aggregating its threads). (unit is *string*)
* ``username``: Program owner (user name, '\_' when children differ). (unit is *string*)
* ``nprocs``: Number of child processes aggregated into this program. (unit is *number*)
* ``status``: Program status ('\_' when children differ). (unit is *string*)
* ``nice``: Program nice value ('\_' when children differ). (unit is *number*)
* ``num_threads``: Total number of threads across the program's children. (unit is *number*)
* ``cpu_percent``: Program CPU consumption (sum across children — can exceed 100%). (unit is *percent*)
* ``memory_percent``: Program resident memory consumption (sum across children). (unit is *percent*)
* ``cmdline``: Command line (the program name, as a single-token list). (unit is *list*)
* ``memory_info``: Aggregated memory information (dict with rss/vms keys). (unit is *byte*)
* ``cpu_times``: Aggregated CPU times (dict with user/system keys). (unit is *second*)
* ``io_counters``: Aggregated I/O counters (concatenated per-child blocks). (unit is *byte*)
* ``time_since_update``: Wall-clock interval since the previous engine refresh (seconds). (unit is *second*)
* ``cpucore``: Number of logical CPU cores (divisor of the Irix-mode CPU%). (unit is *number*)

Get the thresholds in effect:

.. code-block:: bash

    # curl http://localhost:61208/api/5/programlist/limits
    {
        "cpu_percent": {
            "careful": 50.0,
            "critical": 90.0,
            "warning": 70.0
        },
        "memory_percent": {
            "careful": 50.0,
            "critical": 90.0,
            "warning": 70.0
        }
    }

GET psutilversion
-----------------

Get the plugin stats:

.. code-block:: bash

    # curl http://localhost:61208/api/5/psutilversion
    {
        "_levels": {},
        "time_since_update": 1.043279062000238,
        "version": "7.2.2"
    }

Fields (``/info`` serves them as JSON):

* ``version``: psutil version. (unit is *string*)

GET quicklook
-------------

Get the plugin stats:

.. code-block:: bash

    # curl http://localhost:61208/api/5/quicklook
    {
        "_levels": {
            "cpu": {
                "level": "ok",
                "prominent": false
            },
            "load": {
                "level": "ok",
                "prominent": false
            },
            "mem": {
                "level": "ok",
                "prominent": false
            },
            "swap": {
                "level": "ok",
                "prominent": false
            }
        },
        "bar_char": "\u25aa",
        "cpu": 17.0,
        "cpu_hz_current": 2799998000,
        "cpu_log_core": 4,
        "cpu_name": "Intel(R) Xeon(R) Processor @ 2.80GHz",
        "cpu_phys_core": 4,
        "load": 14.1,
        "max_cpu_display": 4,
        "mem": 5.2,
        "percpu": [
            {
                "cpu_number": 0,
                "level": "ok",
                "total": 29.0
            },
            {
                "cpu_number": 1,
                "level": "ok",
                "total": 12.4
            },
            {
                "cpu_number": 2,
                "level": "ok",
                "total": 12.4
            },
            {
                "cpu_number": 3,
                "level": "ok",
                "total": 11.5
            }
        ],
        "percpu_other": null,
        "stats_list": [
            "cpu",
            "mem",
            "load"
        ],
        "swap": 0.0,
        "time_since_update": 1.0429153109998879
    }

Fields (``/info`` serves them as JSON):

* ``cpu``: CPU percent usage. (unit is *percent*)
* ``mem``: MEM percent usage. (unit is *percent*)
* ``swap``: SWAP percent usage. (unit is *percent*)
* ``load``: LOAD percent usage (15 min, normalized by core count). (unit is *percent*)
* ``gpu_mem``: Average GPU memory consumption. (unit is *percent*)
* ``gpu_proc``: Average GPU processor consumption. (unit is *percent*)
* ``percpu``: Per-core CPU usage (list of {cpu\_number, total, level}). (unit is *percent*)
* ``percpu_other``: Mean + level of the CPU cores hidden by max\_cpu\_display ({total, level}), or None when every core is shown. (unit is *percent*)
* ``max_cpu_display``: Number of per-core bars shown before collapsing the rest into percpu\_other ([percpu] max\_cpu\_display). (unit is *number*)
* ``cpu_log_core``: Number of logical CPU cores. (unit is *number*)
* ``cpu_phys_core``: Number of physical CPU cores. (unit is *number*)
* ``cpu_name``: CPU name. (unit is *string*)
* ``cpu_hz_current``: CPU current frequency (Hz). (unit is *hertz*)
* ``cpu_hz``: CPU max frequency (Hz). (unit is *hertz*)
* ``stats_list``: Stats displayed as bars, in display order ([quicklook] list). (unit is *string*)
* ``bar_char``: Character used to fill the bars ([quicklook] bar\_char). (unit is *string*)

Get the thresholds in effect:

.. code-block:: bash

    # curl http://localhost:61208/api/5/quicklook/limits
    {
        "cpu": {
            "careful": 50.0,
            "critical": 90.0,
            "warning": 70.0
        },
        "gpu_mem": {
            "careful": 50.0,
            "critical": 90.0,
            "warning": 70.0
        },
        "gpu_proc": {
            "careful": 50.0,
            "critical": 90.0,
            "warning": 70.0
        },
        "load": {
            "careful": 70.0,
            "critical": 500.0,
            "warning": 100.0
        },
        "mem": {
            "careful": 50.0,
            "critical": 90.0,
            "warning": 70.0
        },
        "swap": {
            "careful": 50.0,
            "critical": 90.0,
            "warning": 70.0
        }
    }

Get the last two points of its history (``nb=0`` for all of them):

.. code-block:: bash

    # curl http://localhost:61208/api/5/quicklook/history?nb=2
    {
        "series": {
            "cpu": [
                57.1,
                17.0
            ],
            "load": [
                14.1,
                14.1
            ],
            "mem": [
                5.1,
                5.2
            ],
            "swap": [
                0.0,
                0.0
            ]
        },
        "timestamps": [
            1791731451.3048246,
            1791731452.3477137
        ]
    }

GET sensors
-----------

Get the plugin stats:

.. code-block:: bash

    # curl http://localhost:61208/api/5/sensors
    {
        "_key": "label",
        "_levels": {},
        "data": [],
        "time_since_update": 1.042095437000171
    }

Fields (``/info`` serves them as JSON):

* ``label``: Sensor label. (unit is *string*)
* ``type``: Sensor type (temperature\_core, fan\_speed, temperature\_hdd, battery). (unit is *string*)
* ``unit``: Sensor unit. (unit is *string*)
* ``value``: Sensor value. (unit is *number*)
* ``warning``: Hardware warning threshold. (unit is *number*)
* ``critical``: Hardware critical threshold. (unit is *number*)
* ``status``: Battery charge status. (unit is *string*)

GET system
----------

Get the plugin stats:

.. code-block:: bash

    # curl http://localhost:61208/api/5/system
    {
        "_levels": {},
        "hostname": "vm",
        "hr_name": "Ubuntu 24.04 64bit / Linux 6.18.44-fc-v114",
        "linux_distro": "Ubuntu 24.04",
        "os_name": "Linux",
        "os_version": "6.18.44-fc-v114",
        "platform": "64bit",
        "time_since_update": 1.040035183999862
    }

Fields (``/info`` serves them as JSON):

* ``os_name``: Operating system name. (unit is *string*)
* ``hostname``: Hostname. (unit is *string*)
* ``platform``: Platform (32 or 64 bits). (unit is *string*)
* ``linux_distro``: Linux distribution. (unit is *string*)
* ``os_version``: Operating system version. (unit is *string*)
* ``hr_name``: Human readable operating system name. (unit is *string*)

GET uptime
----------

Get the plugin stats:

.. code-block:: bash

    # curl http://localhost:61208/api/5/uptime
    {
        "_levels": {},
        "seconds": 3615,
        "time_since_update": 1.0402749220002079
    }

Fields (``/info`` serves them as JSON):

* ``seconds``: Seconds elapsed since the system booted. (unit is *seconds*)

GET version
-----------

Get the plugin stats:

.. code-block:: bash

    # curl http://localhost:61208/api/5/version
    {
        "_levels": {},
        "time_since_update": 1.040287496000019,
        "version": "5.0.0b1"
    }

Fields (``/info`` serves them as JSON):

* ``version``: Glances version. (unit is *string*)

GET wifi
--------

Get the plugin stats:

.. code-block:: bash

    # curl http://localhost:61208/api/5/wifi
    {
        "_key": "ssid",
        "_levels": {},
        "data": [],
        "time_since_update": 1.0403887209999994
    }

Fields (``/info`` serves them as JSON):

* ``ssid``: Wi-Fi network name (interface name). (unit is *string*)
* ``quality_link``: Signal quality level. (unit is *dBm*)
* ``quality_level``: Signal strength level. (unit is *dBm*)

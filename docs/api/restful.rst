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
      - ``/api/5/all/msgpack``
      - All Stats Msgpack
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
      - ``/api/5/theme``
      - The WebUI theme: a built-in name, or \`\`custom\`\` with the CSS of the user's file.
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
    * - POST
      - ``/api/5/llm_reporter/request``
      - Ask for a new LLM report; return the report state that follows.
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
        "glances_version": "5.0.0b2",
        "history": true,
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
                "timer": 1.591451644897461
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
            "timer": 1.591451644897461
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

Request an LLM report
---------------------

Ask the ``llm_reporter`` plugin, when it is enabled, for a new health report. The answer
is the plugin's state: the report itself arrives in ``/api/5/llm_reporter`` once the LLM
has written it. One call at a time, at most one every ``min_interval`` seconds:

.. code-block:: bash

    # curl -X POST http://localhost:61208/api/5/llm_reporter/request

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
                "timer": 1.591451644897461
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
                "timer": 1.591350793838501
            },
            "... 4 more"
        ],
        "time_since_update": 1.5514112299999852
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
        "time_since_update": 1.5542603060000602
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
        "log": 16,
        "phys": 10,
        "time_since_update": 1.5544709839998632
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
        "cpucore": 16,
        "ctx_switches": 2672.78846011416,
        "guest": 0.0,
        "idle": 85.5,
        "interrupts": 1883.6856110862307,
        "iowait": 12.5,
        "irq": 0.0,
        "nice": 0.0,
        "soft_interrupts": 1234.138848642703,
        "steal": 0.0,
        "syscalls": 0.0,
        "system": 1.6,
        "time_since_update": 1.554930388999992,
        "total": 14.5,
        "user": 0.5
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
            "iowait": [
                12.4,
                12.5
            ],
            "system": [
                2.1,
                1.6
            ],
            "total": [
                18.6,
                14.5
            ],
            "user": [
                4.1,
                0.5
            ]
        },
        "timestamps": [
            1795862659.6179392,
            1795862661.1729062
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
                "disk_name": "nvme0n1",
                "hidden": false,
                "read_bytes": 0.0,
                "read_bytes_cumul": 4566142976,
                "read_count": 0.0,
                "read_count_cumul": 153817,
                "read_latency": 0,
                "read_time": 0.0,
                "write_bytes": 86883.243737766,
                "write_bytes_cumul": 1247433728,
                "write_count": 4.499457757489657,
                "write_count_cumul": 56878,
                "write_latency": 7,
                "write_time": 34.7101027006345
            },
            {
                "disk_name": "nvme0n1p1",
                "hidden": false,
                "read_bytes": 0.0,
                "read_bytes_cumul": 6550528,
                "read_count": 0.0,
                "read_count_cumul": 566,
                "read_latency": 0,
                "read_time": 0.0,
                "write_bytes": 0.0,
                "write_bytes_cumul": 1024,
                "write_count": 0.0,
                "write_count_cumul": 2,
                "write_latency": 0,
                "write_time": 0.0
            },
            "... 4 more"
        ],
        "time_since_update": 1.5557430200001363
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
                "dm-0": [
                    null,
                    0.0
                ],
                "dm-1": [
                    null,
                    0.0
                ],
                "nvme0n1": [
                    null,
                    0.0
                ],
                "nvme0n1p1": [
                    null,
                    0.0
                ],
                "nvme0n1p2": [
                    null,
                    0.0
                ],
                "nvme0n1p3": [
                    null,
                    0.0
                ]
            },
            "write_bytes": {
                "dm-0": [
                    null,
                    86883.243737766
                ],
                "dm-1": [
                    null,
                    86883.243737766
                ],
                "nvme0n1": [
                    null,
                    86883.243737766
                ],
                "nvme0n1p1": [
                    null,
                    0.0
                ],
                "nvme0n1p2": [
                    null,
                    0.0
                ],
                "nvme0n1p3": [
                    null,
                    86883.243737766
                ]
            }
        },
        "timestamps": [
            1795862659.618777,
            1795862661.1745746
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
        "time_since_update": 1.5561001630001101
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
                    "level": "careful",
                    "prominent": false
                }
            }
        },
        "data": [
            {
                "device_name": "/dev/mapper/ubuntu--vg-ubuntu--lv",
                "free": 433629626368,
                "fs_type": "ext4",
                "mnt_point": "/",
                "options": "rw,relatime",
                "percent": 54.5,
                "size": 1003736440832,
                "used": 519044308992
            }
        ],
        "free_space": false,
        "time_since_update": 1.5564960589999828
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
                    54.5,
                    54.5
                ]
            }
        },
        "timestamps": [
            1795862659.6198897,
            1795862661.1764092
        ]
    }

GET gpu
-------

Get the plugin stats:

.. code-block:: bash

    # curl http://localhost:61208/api/5/gpu
    {
        "_key": "gpu_id",
        "_levels": {
            "intel0": {
                "proc": {
                    "level": "ok",
                    "prominent": true
                }
            },
            "intel1": {
                "proc": {
                    "level": "ok",
                    "prominent": true
                },
                "temperature": {
                    "level": "ok",
                    "prominent": false
                }
            }
        },
        "data": [
            {
                "fan_speed": null,
                "gpu_id": "intel0",
                "hide_temperature": true,
                "mem": null,
                "name": "UHD Graphics",
                "proc": 2,
                "temperature": null
            },
            {
                "fan_speed": null,
                "gpu_id": "intel1",
                "hide_temperature": true,
                "mem": null,
                "name": "Arc A370M",
                "proc": 0,
                "temperature": 50
            }
        ],
        "time_since_update": 1.5458345060001193
    }

Fields (``/info`` serves them as JSON):

* ``gpu_id``: GPU identifier (e.g. nvidia0). (unit is *string*)
* ``name``: GPU product name. (unit is *string*)
* ``proc``: GPU processor consumption. (unit is *percent*)
* ``mem``: GPU memory consumption. (unit is *percent*)
* ``temperature``: GPU temperature. (unit is *celsius*)
* ``hide_temperature``: Display hint: the temperature is not shown for this card (already in sensors, or [gpu] hide\_temperature). (unit is *bool*)
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

Get the last two points of its history (``nb=0`` for all of them):

.. code-block:: bash

    # curl http://localhost:61208/api/5/gpu/history?nb=2
    {
        "series": {
            "proc": {
                "intel0": [
                    0,
                    2
                ],
                "intel1": [
                    0,
                    0
                ]
            }
        },
        "timestamps": [
            1795862659.6465166,
            1795862661.1923993
        ]
    }

GET ip
------

Get the plugin stats:

.. code-block:: bash

    # curl http://localhost:61208/api/5/ip
    {
        "_levels": {},
        "address": "192.168.1.31",
        "mask": "255.255.255.0",
        "mask_cidr": 24,
        "time_since_update": 1.5460692389999622
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
        "cpucore": 16,
        "min1": 0.6572265625,
        "min15": 0.47119140625,
        "min5": 0.572265625,
        "time_since_update": 1.5463084699999854
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
                0.6572265625,
                0.6572265625
            ],
            "min15": [
                0.47119140625,
                0.47119140625
            ]
        },
        "timestamps": [
            1795862659.6469164,
            1795862661.1932526
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
        "active": 7434399744,
        "available": 9544093696,
        "buffers": 511774720,
        "cached": 6728195840,
        "free": 2644443136,
        "inactive": 3798925312,
        "percent": 39.9,
        "shared": 885678080,
        "slab": 815353856,
        "time_since_update": 1.5468667069999356,
        "total": 15880052736,
        "used": 6335959040
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
                39.9,
                39.9
            ]
        },
        "timestamps": [
            1795862659.6471949,
            1795862661.1940892
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
        "free": 4294963200,
        "percent": 0.0,
        "sin": 0.0,
        "sout": 0.0,
        "time_since_update": 1.5470678589999807,
        "total": 4294963200,
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
            1795862659.6473184,
            1795862661.1944215
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
            "tailscale0": {
                "errors_in": {
                    "level": "ok",
                    "prominent": false
                },
                "errors_out": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "wlp0s20f3": {
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
                "bytes_recv": 261.0040949636944,
                "bytes_recv_cumul": 145481796,
                "bytes_sent": 454.81901696643774,
                "bytes_sent_cumul": 10219707,
                "bytes_speed_rate_per_sec": 0.0,
                "dropped_in": 0.0,
                "dropped_out": 0.0,
                "errors_in": 0.0,
                "errors_out": 0.0,
                "hidden": false,
                "interface_name": "wlp0s20f3",
                "is_up": true
            },
            {
                "bytes_recv": 0.0,
                "bytes_recv_cumul": 4272,
                "bytes_sent": 0.0,
                "bytes_sent_cumul": 9828,
                "bytes_speed_rate_per_sec": 0.0,
                "dropped_in": 0.0,
                "dropped_out": 0.0,
                "errors_in": 0.0,
                "errors_out": 0.0,
                "hidden": false,
                "interface_name": "tailscale0",
                "is_up": true
            }
        ],
        "time_since_update": 1.5478684349998275
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
                "tailscale0": [
                    null,
                    0.0
                ],
                "wlp0s20f3": [
                    null,
                    261.0040949636944
                ]
            },
            "bytes_sent": {
                "tailscale0": [
                    null,
                    0.0
                ],
                "wlp0s20f3": [
                    null,
                    454.81901696643774
                ]
            }
        },
        "timestamps": [
            1795862659.6479995,
            1795862661.1959283
        ]
    }

GET now
-------

Get the plugin stats:

.. code-block:: bash

    # curl http://localhost:61208/api/5/now
    {
        "_levels": {},
        "custom": "2026-11-28 11:44:21 CET",
        "iso": "2026-11-28T11:44:21+01:00",
        "time_since_update": 1.5478695740000603
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
            "10": {
                "system": {
                    "level": "ok",
                    "prominent": false
                },
                "user": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "11": {
                "system": {
                    "level": "ok",
                    "prominent": false
                },
                "user": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "12": {
                "system": {
                    "level": "ok",
                    "prominent": false
                },
                "user": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "13": {
                "system": {
                    "level": "ok",
                    "prominent": false
                },
                "user": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "14": {
                "system": {
                    "level": "ok",
                    "prominent": false
                },
                "user": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "15": {
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
            },
            "4": {
                "system": {
                    "level": "ok",
                    "prominent": false
                },
                "user": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "5": {
                "system": {
                    "level": "ok",
                    "prominent": false
                },
                "user": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "6": {
                "system": {
                    "level": "ok",
                    "prominent": false
                },
                "user": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "7": {
                "system": {
                    "level": "ok",
                    "prominent": false
                },
                "user": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "8": {
                "system": {
                    "level": "ok",
                    "prominent": false
                },
                "user": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "9": {
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
                "idle": 90.9,
                "iowait": 0.0,
                "irq": 0.0,
                "nice": 0.0,
                "softirq": 0.0,
                "steal": 0.0,
                "system": 9.1,
                "total": 9.1,
                "user": 0.0
            },
            {
                "cpu_number": 1,
                "guest": 0.0,
                "guest_nice": 0.0,
                "idle": 100.0,
                "iowait": 0.0,
                "irq": 0.0,
                "nice": 0.0,
                "softirq": 0.0,
                "steal": 0.0,
                "system": 0.0,
                "total": 0.0,
                "user": 0.0
            },
            "... 14 more"
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
        "time_since_update": 1.5481022120000034
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
                    9.1
                ],
                "1": [
                    0.0,
                    0.0
                ],
                "10": [
                    0.0,
                    0.6
                ],
                "11": [
                    0.0,
                    0.0
                ],
                "12": [
                    0.0,
                    0.0
                ],
                "13": [
                    0.0,
                    0.6
                ],
                "14": [
                    0.0,
                    0.0
                ],
                "15": [
                    20.0,
                    0.0
                ],
                "2": [
                    0.0,
                    0.6
                ],
                "3": [
                    0.0,
                    0.0
                ],
                "4": [
                    22.2,
                    4.7
                ],
                "5": [
                    0.0,
                    2.6
                ],
                "6": [
                    0.0,
                    3.2
                ],
                "7": [
                    0.0,
                    3.3
                ],
                "8": [
                    10.0,
                    0.0
                ],
                "9": [
                    0.0,
                    0.0
                ]
            },
            "user": {
                "0": [
                    0.0,
                    0.0
                ],
                "1": [
                    0.0,
                    0.0
                ],
                "10": [
                    0.0,
                    0.0
                ],
                "11": [
                    0.0,
                    0.0
                ],
                "12": [
                    0.0,
                    0.0
                ],
                "13": [
                    0.0,
                    0.0
                ],
                "14": [
                    0.0,
                    0.0
                ],
                "15": [
                    0.0,
                    0.7
                ],
                "2": [
                    0.0,
                    0.6
                ],
                "3": [
                    0.0,
                    0.0
                ],
                "4": [
                    55.6,
                    0.7
                ],
                "5": [
                    0.0,
                    0.0
                ],
                "6": [
                    10.0,
                    2.6
                ],
                "7": [
                    0.0,
                    0.7
                ],
                "8": [
                    0.0,
                    0.6
                ],
                "9": [
                    0.0,
                    0.0
                ]
            }
        },
        "timestamps": [
            1795862659.648709,
            1795862661.196927
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
                    "level": "ok",
                    "prominent": false
                }
            }
        },
        "data": [
            {
                "description": "DefaultGateway",
                "host": "192.168.1.1",
                "indice": "port_0",
                "port": 0,
                "refresh": 30,
                "rtt_warning": null,
                "status": 0.005268,
                "timeout": 3
            }
        ],
        "time_since_update": 1.5479689720000351
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
        "pid_max": 4194304,
        "running": 0,
        "sleeping": 320,
        "sort_key": "cpu_percent",
        "thread": 1734,
        "time_since_update": 1.539396742000008,
        "total": 478
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
                0,
                0
            ],
            "sleeping": [
                320,
                320
            ],
            "thread": [
                1741,
                1734
            ],
            "total": [
                478,
                478
            ]
        },
        "timestamps": [
            1795862659.7092395,
            1795862661.248647
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
            "100": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "10043": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "101": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "102": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "10266": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "103": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "10341": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "105": {
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
            "106": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "107": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "10748": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "108": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "109": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "10930": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "110": {
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
            "111": {
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
            "112": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "1129": {
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
            "113": {
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
            "114": {
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
            "115": {
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
            "1151": {
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
            "116": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "117": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "1173": {
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
            "11791": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "11792": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "118": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "11804": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "11815": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "12": {
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
            "120": {
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
            "121": {
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
            "122": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "12236": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "123": {
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
            "12337": {
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
            "1239": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "124": {
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
            "1240": {
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
            "125": {
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
            "126": {
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
            "127": {
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
            "128": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "1280": {
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
            "1305": {
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
            "1306": {
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
            "1308": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "131": {
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
            "132": {
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
            "134": {
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
            "135": {
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
            "136": {
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
            "137": {
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
            "138": {
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
            "139": {
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
            "142": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "143": {
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
            "144": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "145": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "146": {
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
            "147": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "14739": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "148": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "149": {
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
            "14901": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "14904": {
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
            "150": {
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
            "1510": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "152": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "1528": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "154": {
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
            "155": {
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
            "156": {
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
            "158": {
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
            "159": {
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
            "162": {
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
            "163": {
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
            "176": {
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
            "18626": {
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
            "19252": {
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
            "2135": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "2164": {
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
            "2165": {
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
            "2166": {
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
            "2167": {
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
            "2169": {
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
            "2170": {
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
            "2171": {
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
            "2172": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "2173": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "2174": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "2175": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "2176": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "2177": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "2178": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "2179": {
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
            "2180": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "2181": {
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
            "2182": {
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
            "2183": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
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
            "23": {
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
                }
            },
            "24626": {
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
            "262": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "263": {
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
            "265": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "267": {
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
            "268": {
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
            "269": {
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
            "27": {
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
            "270": {
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
            "273": {
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
            "28": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "2879": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "2894": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
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
                }
            },
            "298": {
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
            "3065": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "3066": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "3067": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "3071": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "3077": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "3087": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "3098": {
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
            "3105": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "3108": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "3111": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "3121": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "3129": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "3134": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "3140": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "3142": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "3152": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "31759": {
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
            "31762": {
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
            "3199": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "3224": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "325": {
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
            "3251": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "3252": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "326": {
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
            "327": {
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
            "328": {
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
            "329": {
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
            "3293": {
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
            "33": {
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
            "3361": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "3369": {
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
                }
            },
            "3402": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "34042": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "34077": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "3427": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "3430": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "3434": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "3439": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "34405": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "34429": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "3443": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "3447": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "3448": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "34540": {
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
            "34545": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "3463": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "34646": {
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
            "34650": {
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
            "34652": {
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
            "3473": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "34889": {
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
                }
            },
            "36427": {
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
            "37": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "37512": {
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
            "37711": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "38337": {
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
            "3872": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "3873": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
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
                "nice": {
                    "level": "warning",
                    "prominent": false
                },
                "status": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "3994": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "3997": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "3998": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
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
            "4077": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "4078": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "4081": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "40867": {
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
            "4088": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "4090": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "4091": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "4093": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "4095": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "4098": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "4099": {
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
            "4157": {
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
            "4221": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "42448": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "42537": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "42643": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "42646": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "42666": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "42675": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "42717": {
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
            "42723": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "42731": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "42764": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "42812": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "43": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "43056": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "4307": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "4308": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "43423": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "43861": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "44031": {
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
            "44036": {
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
            "4405": {
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
            "4406": {
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
            "4407": {
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
            "4408": {
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
            "4409": {
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
            "4410": {
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
            "4411": {
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
            "4412": {
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
            "4414": {
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
            "4415": {
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
            "44156": {
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
            "4416": {
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
            "4417": {
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
            "4419": {
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
            "4420": {
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
            "4421": {
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
            "4422": {
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
            "44269": {
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
            "44311": {
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
            "44328": {
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
            "44340": {
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
            "44341": {
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
            "44343": {
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
            "44344": {
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
            "44345": {
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
            "44346": {
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
            "44352": {
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
            "44569": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "44583": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "status": {
                    "level": "critical",
                    "prominent": false
                }
            },
            "44584": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "44596": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "44599": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "44696": {
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
            "44702": {
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
            "44740": {
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
            "44920": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "45": {
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
            "4653": {
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
            "47": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
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
                }
            },
            "48951": {
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
            "49": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "490": {
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
            "491": {
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
            "492": {
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
            "49264": {
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
            "493": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "49465": {
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
            "49578": {
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
            "49635": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "49675": {
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
            "49708": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "49757": {
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
            "49758": {
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
            "49787": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "49839": {
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
            "49844": {
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
            "49868": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "49908": {
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
            "49924": {
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
            "50008": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "50064": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "50065": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "50073": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "502": {
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
            "5071": {
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
            "51": {
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
            "52": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "528": {
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
            "531": {
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
            "532": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "533": {
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
            "54": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
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
                }
            },
            "560": {
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
                }
            },
            "603": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
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
            "612": {
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
            "63": {
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
            "64": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "65": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "650": {
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
            "651": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "653": {
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
            "654": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "6553": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "6554": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "657": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "66": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
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
                }
            },
            "676": {
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
            "681": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "684": {
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
            "688": {
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
            "689": {
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
            "690": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "691": {
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
            "70": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "7030": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "71": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "718": {
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
            "72": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "7239": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "7253": {
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
            "7263": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "7296": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "7298": {
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
            "73": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "7302": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "7304": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "7309": {
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
            "731": {
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
            "7319": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "7321": {
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
            "7323": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "7473": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "75": {
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
            "7501": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "7514": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
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
                }
            },
            "769": {
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
            "77": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "7742": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "7761": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "78": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
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
                }
            },
            "794": {
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
            "81": {
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
            "8216": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "8217": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "8219": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "8254": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "827": {
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
            "8273": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "8281": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "829": {
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
            "830": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "831": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "832": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "833": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "8339": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "834": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "835": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "836": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "837": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "838": {
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
            "839": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "84": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "840": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "841": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "842": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "843": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "844": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "845": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "849": {
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
            "85": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "853": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "8624": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "8631": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "8633": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "8652": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "8660": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "8661": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "8674": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "8692": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "8695": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "8696": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "8698": {
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
            "8708": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "8709": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "8711": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "8715": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "8717": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "8719": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "8720": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "8724": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "8739": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "8741": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "8746": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "8752": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "8764": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "8767": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "8770": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "8790": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "88": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "8871": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "8881": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "89": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "8923": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "8925": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "8947": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "895": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "8954": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "8963": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "8964": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "90": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "9015": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "9016": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "9063": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "9065": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "9066": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "9068": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "9074": {
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
            "9099": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "91": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "9107": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "9118": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "9143": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "93": {
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
            "94": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "944": {
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
            "95": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "96": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "9615": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "9626": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "9655": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "9656": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "9659": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "9670": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "97": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "98": {
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
            "984": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "986": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "987": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "9872": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "988": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "99": {
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
            "9948": {
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
        "cpucore": 16,
        "data": [
            {
                "cmdline": [
                    "/home/nicolargo/dev/glances/.venv/bin/python",
                    "-m",
                    "glances",
                    "-C",
                    "conf/glances.conf",
                    "--api-restful-doc"
                ],
                "cpu_num": 6,
                "cpu_percent": 22.1,
                "cpu_times": {
                    "children_system": 0.01,
                    "children_user": 0.0,
                    "iowait": 0.0,
                    "system": 0.3,
                    "user": 0.46
                },
                "gids": {
                    "effective": 1000,
                    "real": 1000,
                    "saved": 1000
                },
                "io_counters": [
                    262144,
                    0,
                    262144,
                    0,
                    1
                ],
                "key": "pid",
                "memory_info": {
                    "data": 175304704,
                    "dirty": 0,
                    "lib": 0,
                    "rss": 109252608,
                    "shared": 29569024,
                    "text": 31211520,
                    "vms": 590331904
                },
                "memory_percent": 0.6879864306264228,
                "name": "python",
                "nice": 0,
                "num_threads": 5,
                "pid": 50073,
                "status": "S",
                "time_since_update": 1.5480759143829346,
                "username": "nicolargo"
            },
            {
                "cmdline": [],
                "cpu_num": 0,
                "cpu_percent": 8.4,
                "cpu_times": {
                    "children_system": 0.0,
                    "children_user": 0.0,
                    "iowait": 0.0,
                    "system": 7.46,
                    "user": 0.0
                },
                "gids": {
                    "effective": 0,
                    "real": 0,
                    "saved": 0
                },
                "io_counters": [
                    0,
                    0,
                    0,
                    0,
                    0
                ],
                "key": "pid",
                "memory_info": {
                    "data": 0,
                    "dirty": 0,
                    "lib": 0,
                    "rss": 0,
                    "shared": 0,
                    "text": 0,
                    "vms": 0
                },
                "memory_percent": 0.0,
                "name": "irq/9-acpi",
                "nice": 0,
                "num_threads": 1,
                "pid": 128,
                "status": "S",
                "time_since_update": 1.5480759143829346,
                "username": "root"
            },
            "... 476 more"
        ],
        "disable_virtual_memory": false,
        "time_since_update": 1.539404999999988
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
* ``disable_virtual_memory``: Hide the VIRT column (\`[processlist] disable\_virtual\_memory\`). (unit is *boolean*)

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
            "(sd-pam)": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "Isolated Servic": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "Isolated Web Co": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "ModemManager": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "NetworkManager": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "Privileged Cont": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "RDD Process": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "Socket Process": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "Utility Process": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "Web Content": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "WebExtensions": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "Xwayland": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "accounts-daemon": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "arc_evict": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "arc_flush": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "arc_prune": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "arc_reap": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "at-spi-bus-launcher": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "at-spi2-registryd": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "avahi-daemon": {
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
            "bluetoothd": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "boltd": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "card1-crtc0": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "card1-crtc1": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "card1-crtc2": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "card1-crtc3": {
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
            "claude-agent-acp": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "colord": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "containerd": {
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
            "cpuhp/10": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "cpuhp/11": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "cpuhp/12": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "cpuhp/13": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "cpuhp/14": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "cpuhp/15": {
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
            "cpuhp/4": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "cpuhp/5": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "cpuhp/6": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "cpuhp/7": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "cpuhp/8": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "cpuhp/9": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "crashhelper": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "cron": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "cups-browsed": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "cups-proxyd": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "cupsd": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "dbu_evict": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "dbuf_evict": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "dbus": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "dbus-daemon": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "dconf-service": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "dmcrypt_write/252:0": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "dnsmasq": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "dockerd": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "dropbox": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "ecryptfs-kthread": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "evolution-addressbook-factory": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "evolution-alarm-notify": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "evolution-calendar-factory": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "evolution-source-registry": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "firefox": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "forkserver": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "fsidd": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "fusermount3": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "fwupd": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "gcr-ssh-agent": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "gdm-session-worker": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "gdm-wayland-session": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "gdm3": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "ghostty": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "gjs": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "gnome-keyring-daemon": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "gnome-session-ctl": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "gnome-session-init-worker": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "gnome-session-service": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "gnome-shell": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "gnome-shell-calendar-server": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "goa-daemon": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "goa-identity-service": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "gsd-a11y-settings": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "gsd-color": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "gsd-datetime": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "gsd-disk-utility-notify": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "gsd-housekeeping": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "gsd-keyboard": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "gsd-media-keys": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "gsd-power": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "gsd-print-notifications": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "gsd-printer": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "gsd-rfkill": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "gsd-screensaver-proxy": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "gsd-sharing": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "gsd-smartcard": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "gsd-sound": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "gsd-usb-protection": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "gsd-wwan": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "gsd-xsettings": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "gvfs-afc-volume-monitor": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "gvfs-goa-volume-monitor": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "gvfs-gphoto2-volume-monitor": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "gvfs-mtp-volume-monitor": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "gvfs-udisks2-volume-monitor": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "gvfsd": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "gvfsd-dnssd": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "gvfsd-fuse": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "gvfsd-metadata": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "gvfsd-network": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "gvfsd-recent": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "gvfsd-trash": {
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
            "ibus-daemon": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "ibus-engine-simple": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "ibus-extension-gtk3": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "ibus-memconf": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "ibus-portal": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "ibus-x11": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "idle_inject/0": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "idle_inject/1": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "idle_inject/10": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "idle_inject/11": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "idle_inject/12": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "idle_inject/13": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "idle_inject/14": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "idle_inject/15": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "idle_inject/2": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "idle_inject/3": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "idle_inject/4": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "idle_inject/5": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "idle_inject/6": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "idle_inject/7": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "idle_inject/8": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "idle_inject/9": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "iio-sensor-proxy": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "irq/123-pciehp": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "irq/124-pciehp": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "irq/16-processor_thermal_device_pci": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "irq/178-VEN_04F3:00": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "irq/197-iwlwifi:default_queue": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "irq/198-iwlwifi:queue_1": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "irq/199-iwlwifi:queue_2": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "irq/200-iwlwifi:queue_3": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "irq/201-iwlwifi:queue_4": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "irq/202-iwlwifi:queue_5": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "irq/203-iwlwifi:queue_6": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "irq/204-iwlwifi:queue_7": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "irq/205-iwlwifi:queue_8": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "irq/206-iwlwifi:queue_9": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "irq/207-iwlwifi:queue_10": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "irq/208-iwlwifi:queue_11": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "irq/209-iwlwifi:queue_12": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "irq/210-iwlwifi:queue_13": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "irq/211-iwlwifi:queue_14": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "irq/212-iwlwifi:exception": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "irq/213-cs35l41 IRQ1 Controller": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "irq/214-mei_me": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "irq/217-mei_gsc": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "irq/218-mei_gsc": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "irq/233-AudioDSP": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "irq/9-acpi": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "jbd2/dm-1-8": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "jbd2/nvme0n1p2-8": {
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
            "kprobe-optimizer": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "krfcommd": {
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
            "ksoftirqd/10": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "ksoftirqd/11": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "ksoftirqd/12": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "ksoftirqd/13": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "ksoftirqd/14": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "ksoftirqd/15": {
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
            "ksoftirqd/4": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "ksoftirqd/5": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "ksoftirqd/6": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "ksoftirqd/7": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "ksoftirqd/8": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "ksoftirqd/9": {
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
            "kworker/0:0-mm_percpu_wq": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/0:0H-kblockd": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/0:1": {
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
            "kworker/10:0-mm_percpu_wq": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/10:0H-kblockd": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/10:1-cgroup_release": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/10:1H-i915_cleanup": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/10:2-events": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/10:3-events": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/11:0-mm_percpu_wq": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/11:0H-kblockd": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/11:1-mm_percpu_wq": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/11:1H-kblockd": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/11:8-kacpi_notify": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/12:0": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/12:0H-kblockd": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/12:1-mm_percpu_wq": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/12:1H-i915_cleanup": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/13:0": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/13:0H-kblockd": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/13:1H-i915_cleanup": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/13:6-mm_percpu_wq": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/14:0-mm_percpu_wq": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/14:0H-kblockd": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/14:1-events": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/14:1H-i915_cleanup": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/15:0H-kblockd": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/15:1-events": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/15:1H-i915_cleanup": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/15:2-events": {
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
            "kworker/1:0H-kblockd": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/1:1-mm_percpu_wq": {
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
            "kworker/1:2-events": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/2:0-events": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/2:0H-kblockd": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/2:1": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/2:1H-i915_cleanup": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/2:3-mm_percpu_wq": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/3:0H-kblockd": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/3:1-events": {
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
            "kworker/3:3-mm_percpu_wq": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/4:0": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/4:0H-kblockd": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/4:1-mm_percpu_wq": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/4:1H-i915_cleanup": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/4:3-events": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/5:0-events": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/5:0H-kblockd": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/5:1-events": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/5:1H-kblockd": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/5:2-events": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/5:3-events": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/6:0-i915-unordered": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/6:0H-kblockd": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/6:1H-i915_cleanup": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/6:2-i915-unordered": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/7:0-events": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/7:0H-i915_cleanup": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/7:1-mm_percpu_wq": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/7:1H-kblockd": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/8:0-memcg": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/8:0H-kblockd": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/8:10-mm_percpu_wq": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/8:1H-i915_cleanup": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/9:0-mm_percpu_wq": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/9:0H-kblockd": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/9:1-mm_percpu_wq": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/9:1H-kblockd": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/9:2-mm_percpu_wq": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/R-USBC000:00-con1": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/R-USBC000:00-con2": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/R-USBC000:00-con3": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/R-acpi_thermal_pm": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/R-ata_sff": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/R-blkcg_punt_bio": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/R-cfg80211": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/R-charger_manager": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/R-devfreq_wq": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/R-edac-poller": {
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
            "kworker/R-hfi-updates": {
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
            "kworker/R-ipv6_addrconf": {
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
            "kworker/R-kcryptd-252:0-1": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/R-kcryptd_io-252:0-1": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/R-kdmflush/252:0": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/R-kdmflush/252:1": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/R-kintegrityd": {
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
            "kworker/R-md_bitmap": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/R-md_llbitmap_io": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/R-md_llbitmap_unplug": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/R-mld": {
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
            "kworker/R-nvme-auth-wq": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/R-nvme-delete-wq": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/R-nvme-reset-wq": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/R-nvme-wq": {
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
            "kworker/R-rpciod": {
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
            "kworker/R-tpm_dev_wq": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/R-ttm": {
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
            "kworker/R-xprtiod": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/u64:0-kcryptd-252:0-1": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/u64:1-kcryptd-252:0-1": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/u64:10-kcryptd-252:0-1": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/u64:11-kcryptd-252:0-1": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/u64:12-kcryptd-252:0-1": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/u64:13-kcryptd-252:0-1": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/u64:14-kcryptd-252:0-1": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/u64:15-kcryptd-252:0-1": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/u64:16-kcryptd-252:0-1": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/u64:2-kcryptd-252:0-1": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/u64:3-kcryptd-252:0-1": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/u64:4-kcryptd-252:0-1": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/u64:5-kcryptd-252:0-1": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/u64:6-kcryptd-252:0-1": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/u64:7-kcryptd-252:0-1": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/u64:8-kcryptd-252:0-1": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/u64:9-kcryptd-252:0-1": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/u65:0": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/u65:2-i915_flip": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "kworker/u65:3-hci0": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "l2arc_feed": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "libvirtd": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "localsearch-3": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "lockd": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "make": {
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
            "migration/10": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "migration/11": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "migration/12": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "migration/13": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "migration/14": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "migration/15": {
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
            "migration/4": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "migration/5": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "migration/6": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "migration/7": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "migration/8": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "migration/9": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "mpris-proxy": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "multipassd": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "mutter-x11-frames": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "nfsd": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "nfsdcld": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "ollama": {
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
            "pipewire": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "pipewire-pulse": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "polkitd": {
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
            "psimon": {
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
            "python3": {
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
            "rpc.idmapd": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "rpc.mountd": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "rpc.statd": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "rpcbind": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "rsyslogd": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "rtkit-daemon": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "run-cups-browse": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "run-cupsd": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "sd_dummy": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "sd_espeak-ng": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "sd_espeak-ng-mb": {
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
            "sleep": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "smartd": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "snap": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "snap-store": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "snapd": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "snapd-desktop-integration": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "snmpd": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "speech-dispatcher": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "spi0": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "spl_delay_taskq": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "spl_dynamic_tas": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "spl_kmem_cache": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "spl_system_task": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "ssh-agent": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "switcheroo-control": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "systemd": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "systemd-journald": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "systemd-logind": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "systemd-machined": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "systemd-oomd": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "systemd-resolved": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "systemd-timesyncd": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "systemd-udevd": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "tailscaled": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "terminator": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "thermald": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "udisksd": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "unattended-upgr": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "update-notifier": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "upowerd": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "user-session-helper": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "uuidd": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "uv": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "virtlockd": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "virtlogd": {
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
            },
            "wireplumber": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "wpa_supplicant": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "xdg-desktop-portal": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "xdg-desktop-portal-gnome": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "xdg-desktop-portal-gtk": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "xdg-document-portal": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "xdg-permission-store": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "z_vdev_file": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "zed": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "zed-editor": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "zvol_tq-0": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "zvol_tq-1": {
                "cpu_percent": {
                    "level": "ok",
                    "prominent": false
                },
                "memory_percent": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "zvol_tq-2": {
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
        "cpucore": 16,
        "data": [
            {
                "cmdline": [
                    "python"
                ],
                "cpu_percent": 22.1,
                "cpu_times": {
                    "children_system": 0.01,
                    "children_user": 0.0,
                    "iowait": 0.0,
                    "system": 0.3,
                    "user": 0.46
                },
                "io_counters": [
                    262144,
                    0,
                    262144,
                    0,
                    1
                ],
                "memory_info": {
                    "data": 175304704,
                    "dirty": 0,
                    "lib": 0,
                    "rss": 109252608,
                    "shared": 29569024,
                    "text": 31211520,
                    "vms": 590331904
                },
                "memory_percent": 0.6879864306264228,
                "name": "python",
                "nice": 0,
                "nprocs": 1,
                "num_threads": 5,
                "status": "S",
                "time_since_update": 1.5480759143829346,
                "username": "nicolargo"
            },
            {
                "cmdline": [
                    "irq/9-acpi"
                ],
                "cpu_percent": 8.4,
                "cpu_times": {
                    "children_system": 0.0,
                    "children_user": 0.0,
                    "iowait": 0.0,
                    "system": 7.46,
                    "user": 0.0
                },
                "io_counters": [
                    0,
                    0,
                    0,
                    0,
                    0
                ],
                "memory_info": {
                    "data": 0,
                    "dirty": 0,
                    "lib": 0,
                    "rss": 0,
                    "shared": 0,
                    "text": 0,
                    "vms": 0
                },
                "memory_percent": 0,
                "name": "irq/9-acpi",
                "nice": 0,
                "nprocs": 1,
                "num_threads": 1,
                "status": "S",
                "time_since_update": 1.5480759143829346,
                "username": "root"
            },
            "... 427 more"
        ],
        "disable_virtual_memory": false,
        "time_since_update": 1.5394073209999988
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
* ``disable_virtual_memory``: Hide the VIRT column (\`[processlist] disable\_virtual\_memory\`). (unit is *boolean*)

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
        "time_since_update": 1.5394132690000788,
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
            "gpu_proc": {
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
        "cpu": 14.5,
        "cpu_hz": 4475000000,
        "cpu_hz_current": 837776125,
        "cpu_log_core": 16,
        "cpu_name": "13th Gen Intel(R) Core(TM) i7-13620H",
        "cpu_phys_core": 10,
        "gpu_proc": 1.0,
        "load": 2.9,
        "max_cpu_display": 4,
        "mem": 39.9,
        "percpu": [
            {
                "cpu_number": 0,
                "level": "ok",
                "total": 9.1
            },
            {
                "cpu_number": 1,
                "level": "ok",
                "total": 0.0
            },
            {
                "cpu_number": 2,
                "level": "ok",
                "total": 1.3
            },
            {
                "cpu_number": 3,
                "level": "ok",
                "total": 0.0
            },
            {
                "cpu_number": 4,
                "level": "careful",
                "total": 54.7
            },
            {
                "cpu_number": 5,
                "level": "ok",
                "total": 2.6
            },
            {
                "cpu_number": 6,
                "level": "ok",
                "total": 7.1
            },
            {
                "cpu_number": 7,
                "level": "ok",
                "total": 3.9
            },
            {
                "cpu_number": 8,
                "level": "ok",
                "total": 48.7
            },
            {
                "cpu_number": 9,
                "level": "ok",
                "total": 0.7
            },
            {
                "cpu_number": 10,
                "level": "ok",
                "total": 0.6
            },
            {
                "cpu_number": 11,
                "level": "ok",
                "total": 0.0
            },
            {
                "cpu_number": 12,
                "level": "ok",
                "total": 0.0
            },
            {
                "cpu_number": 13,
                "level": "critical",
                "total": 100.0
            },
            {
                "cpu_number": 14,
                "level": "ok",
                "total": 0.0
            },
            {
                "cpu_number": 15,
                "level": "ok",
                "total": 0.7
            }
        ],
        "percpu_other": {
            "level": "ok",
            "total": 1.4083333333333332
        },
        "stats_list": [
            "cpu",
            "mem",
            "load"
        ],
        "swap": 0.0,
        "time_since_update": 1.5389812779999374
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
                18.6,
                14.5
            ],
            "gpu_proc": [
                0.0,
                1.0
            ],
            "load": [
                2.9,
                2.9
            ],
            "mem": [
                39.9,
                39.9
            ],
            "swap": [
                0.0,
                0.0
            ]
        },
        "timestamps": [
            1795862659.714037,
            1795862661.2530146
        ]
    }

GET sensors
-----------

Get the plugin stats:

.. code-block:: bash

    # curl http://localhost:61208/api/5/sensors
    {
        "_key": "label",
        "_levels": {
            "Ambient (mean)": {
                "value": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "CPU": {
                "value": {
                    "level": "careful",
                    "prominent": false
                }
            },
            "Composite": {
                "value": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "Core (mean)": {
                "value": {
                    "level": "careful",
                    "prominent": false
                }
            },
            "HDD": {
                "value": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "Package id 0": {
                "value": {
                    "level": "careful",
                    "prominent": false
                }
            },
            "SODIMM": {
                "value": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "Sensor (mean)": {
                "value": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "dell_smm (mean)": {
                "value": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "i915 0": {
                "value": {
                    "level": "careful",
                    "prominent": false
                }
            },
            "iwlwifi_1 0": {
                "value": {
                    "level": "ok",
                    "prominent": false
                }
            },
            "temp": {
                "value": {
                    "level": "ok",
                    "prominent": false
                }
            }
        },
        "data": [
            {
                "critical": null,
                "label": "Ambient (mean)",
                "type": "temperature_core",
                "unit": "C",
                "value": 39,
                "warning": 0
            },
            {
                "critical": null,
                "label": "BAT BAT0",
                "status": "Charging",
                "type": "battery",
                "unit": "%",
                "value": 74,
                "warning": null
            },
            "... 15 more"
        ],
        "time_since_update": 1.3761358730000666
    }

Fields (``/info`` serves them as JSON):

* ``label``: Sensor label. (unit is *string*)
* ``type``: Sensor type (temperature\_core, fan\_speed, battery). (unit is *string*)
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
        "hostname": "nicolargo-xps15",
        "hr_name": "Ubuntu 26.04 64bit / Linux 7.0.0-44-generic",
        "linux_distro": "Ubuntu 26.04",
        "os_name": "Linux",
        "os_version": "7.0.0-44-generic",
        "platform": "64bit",
        "time_since_update": 1.3758951400000115
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
        "seconds": 1848,
        "time_since_update": 1.3759268920000522
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
        "time_since_update": 1.3759269649999624,
        "version": "5.0.0b2"
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
        "_levels": {
            "wlp0s20f3": {
                "quality_level": {
                    "level": "ok",
                    "prominent": false
                }
            }
        },
        "data": [
            {
                "quality_level": -62.0,
                "quality_link": 48.0,
                "ssid": "wlp0s20f3"
            }
        ],
        "time_since_update": 1.375958055999945
    }

Fields (``/info`` serves them as JSON):

* ``ssid``: Wi-Fi network name (interface name). (unit is *string*)
* ``quality_link``: Signal quality level. (unit is *dBm*)
* ``quality_level``: Signal strength level. (unit is *dBm*)

.. _api:

API (Restfull/JSON) documentation
=================================

This documentation describes the Glances API version 4 (Restfull/JSON) interface.

For Glances version 3, please have a look on:
``https://github.com/nicolargo/glances/blob/support/glancesv3/docs/api.rst``

Run the Glances API server
--------------------------

The Glances Restfull/API server could be ran using the following command line:

.. code-block:: bash

    # glances -w --disable-webui

It is also ran automatically when Glances is started in Web server mode (-w).

API URL
-------

The default root API URL is ``http://localhost:61208/api/4``.

The bind address and port could be changed using the ``--bind`` and ``--port`` command line options.

It is also possible to define an URL prefix using the ``url_prefix`` option from the [outputs] section
of the Glances configuration file.

Note: The url_prefix should always end with a slash (``/``).

For example:

.. code-block:: ini
    [outputs]
    url_prefix = /glances/

will change the root API URL to ``http://localhost:61208/glances/api/4`` and the Web UI URL to
``http://localhost:61208/glances/``

API documentation URL
---------------------

The API documentation is embeded in the server and available at the following URL:
``http://localhost:61208/docs#/``.

WebUI refresh
-------------

It is possible to change the Web UI refresh rate (default is 2 seconds) using the following option in the URL:
``http://localhost:61208/glances/?refresh=5``


GET API status
--------------

This entry point should be used to check the API status.
It will the Glances version and a 200 return code if everything is OK.

Get the Rest API status::

    # curl -I http://localhost:61208/api/4/status
    "HTTP/1.0 200 OK"

GET plugins list
----------------

Get the plugins list::

    # curl http://localhost:61208/api/4/pluginslist
    ["alert",
     "amps",
     "cloud",
     "connections",
     "containers",
     "core",
     "cpu",
     "diskio",
     "folders",
     "fs",
     "gpu",
     "help",
     "ip",
     "irq",
     "load",
     "mem",
     "memswap",
     "network",
     "now",
     "percpu",
     "ports",
     "processcount",
     "processlist",
     "psutilversion",
     "quicklook",
     "raid",
     "sensors",
     "smart",
     "system",
     "uptime",
     "version",
     "wifi"]

GET alert
---------

Get plugin stats::

    # curl http://localhost:61208/api/4/alert
    [{"avg": 80.62615997968645,
      "begin": 1706441527.0,
      "count": 1,
      "desc": "",
      "end": -1,
      "max": 80.62615997968645,
      "min": 80.62615997968645,
      "sort": "memory_percent",
      "state": "WARNING",
      "sum": 80.62615997968645,
      "top": [],
      "type": "MEM"}]

Fields descriptions:

* **begin**: Begin timestamp of the event (unit is *timestamp*)
* **end**: End timestamp of the event (or -1 if ongoing) (unit is *timestamp*)
* **state**: State of the event (WARNING|CRITICAL) (unit is *string*)
* **type**: Type of the event (CPU|LOAD|MEM) (unit is *string*)
* **max**: Maximum value during the event period (unit is *float*)
* **avg**: Average value during the event period (unit is *float*)
* **min**: Minimum value during the event period (unit is *float*)
* **sum**: Sum of the values during the event period (unit is *float*)
* **count**: Number of values during the event period (unit is *int*)
* **top**: Top 3 processes name during the event period (unit is *list*)
* **desc**: Description of the event (unit is *string*)
* **sort**: Sort key of the top processes (unit is *string*)

Get a specific field::

    # curl http://localhost:61208/api/4/alert/begin
    {"begin": [1706441527.0]}

Get a specific item when field matches the given value::

    # curl http://localhost:61208/api/4/alert/begin/1706441527.0
    {"1706441527.0": [{"avg": 80.62615997968645,
                       "begin": 1706441527.0,
                       "count": 1,
                       "desc": "",
                       "end": -1,
                       "max": 80.62615997968645,
                       "min": 80.62615997968645,
                       "sort": "memory_percent",
                       "state": "WARNING",
                       "sum": 80.62615997968645,
                       "top": [],
                       "type": "MEM"}]}

GET amps
--------

Get plugin stats::

    # curl http://localhost:61208/api/4/amps
    [{"count": 0,
      "countmax": None,
      "countmin": 1.0,
      "key": "name",
      "name": "Dropbox",
      "refresh": 3.0,
      "regex": True,
      "result": None,
      "timer": 0.3150813579559326},
     {"count": 0,
      "countmax": 20.0,
      "countmin": None,
      "key": "name",
      "name": "Python",
      "refresh": 3.0,
      "regex": True,
      "result": None,
      "timer": 0.3147857189178467}]

Fields descriptions:

* **name**: AMP name (unit is *None*)
* **result**: AMP result (a string) (unit is *None*)
* **refresh**: AMP refresh interval (unit is *second*)
* **timer**: Time until next refresh (unit is *second*)
* **count**: Number of matching processes (unit is *number*)
* **countmin**: Minimum number of matching processes (unit is *number*)
* **countmax**: Maximum number of matching processes (unit is *number*)

Get a specific field::

    # curl http://localhost:61208/api/4/amps/name
    {"name": ["Dropbox", "Python", "Conntrack", "Nginx", "Systemd", "SystemV"]}

Get a specific item when field matches the given value::

    # curl http://localhost:61208/api/4/amps/name/Dropbox
    {"Dropbox": [{"count": 0,
                  "countmax": None,
                  "countmin": 1.0,
                  "key": "name",
                  "name": "Dropbox",
                  "refresh": 3.0,
                  "regex": True,
                  "result": None,
                  "timer": 0.3150813579559326}]}

GET connections
---------------

Get plugin stats::

    # curl http://localhost:61208/api/4/connections
    {"net_connections_enabled": True, "nf_conntrack_enabled": True}

Fields descriptions:

* **LISTEN**: Number of TCP connections in LISTEN state (unit is *number*)
* **ESTABLISHED**: Number of TCP connections in ESTABLISHED state (unit is *number*)
* **SYN_SENT**: Number of TCP connections in SYN_SENT state (unit is *number*)
* **SYN_RECV**: Number of TCP connections in SYN_RECV state (unit is *number*)
* **initiated**: Number of TCP connections initiated (unit is *number*)
* **terminated**: Number of TCP connections terminated (unit is *number*)
* **nf_conntrack_count**: Number of tracked connections (unit is *number*)
* **nf_conntrack_max**: Maximum number of tracked connections (unit is *number*)
* **nf_conntrack_percent**: Percentage of tracked connections (unit is *percent*)

Get a specific field::

    # curl http://localhost:61208/api/4/connections/net_connections_enabled
    {"net_connections_enabled": True}

GET containers
--------------

Get plugin stats::

    # curl http://localhost:61208/api/4/containers
    [{"command": "/portainer",
      "cpu": {"total": 0.0},
      "cpu_percent": 0.0,
      "created": "2022-10-29T14:59:10.266701439Z",
      "engine": "docker",
      "id": "3abd51c615968482d9ccff5afc629f267f6dda113ed68b75b432615fae3b49fb",
      "image": ["portainer/portainer-ce:2.9.3"],
      "io": {"cumulative_ior": 258048, "cumulative_iow": 1155072},
      "key": "name",
      "memory": {"cache": None,
                 "limit": 7823585280,
                 "max_usage": None,
                 "rss": None,
                 "usage": 15396864},
      "memory_usage": 15396864,
      "name": "portainer",
      "network": {"cumulative_rx": 904556, "cumulative_tx": 0},
      "status": "running",
      "uptime": "yesterday"},
     {"command": "top",
      "cpu": {"total": 2.4634890381579793e-06},
      "cpu_percent": 2.4634890381579793e-06,
      "created": "2023-12-09T10:45:34.339489876+01:00",
      "engine": "podman",
      "id": "481d6ffb7eef284d062628cf350bdd9ce0a803db8a2a505d75565ed24322b714",
      "image": "docker.io/library/ubuntu:latest",
      "io": {"ior": 0.0, "iow": 0.0, "time_since_update": 1},
      "io_rx": 0.0,
      "io_wx": 0.0,
      "key": "name",
      "memory": {"limit": 7823585280.0, "usage": 1216512.0},
      "memory_usage": 1216512.0,
      "name": "sad_darwin",
      "network": {"rx": 0.0, "time_since_update": 1, "tx": 0.0},
      "network_rx": 0.0,
      "network_tx": 0.0,
      "pod_id": "8d0f1c783def",
      "pod_name": "sad_darwin",
      "status": "running",
      "uptime": "1 months"}]

Fields descriptions:

* **name**: Container name (unit is *None*)
* **id**: Container ID (unit is *None*)
* **image**: Container image (unit is *None*)
* **status**: Container status (unit is *None*)
* **created**: Container creation date (unit is *None*)
* **command**: Container command (unit is *None*)
* **cpu_percent**: Container CPU consumption (unit is *percent*)
* **memory_usage**: Container memory usage (unit is *byte*)
* **io_rx**: Container IO bytes read rate (unit is *bytepersecond*)
* **io_wx**: Container IO bytes write rate (unit is *bytepersecond*)
* **network_rx**: Container network RX bitrate (unit is *bitpersecond*)
* **network_tx**: Container network TX bitrate (unit is *bitpersecond*)
* **uptime**: Container uptime (unit is *None*)
* **engine**: Container engine (Docker and Podman are currently supported) (unit is *None*)
* **pod_name**: Pod name (only with Podman) (unit is *None*)
* **pod_id**: Pod ID (only with Podman) (unit is *None*)

Get a specific field::

    # curl http://localhost:61208/api/4/containers/name
    {"name": ["portainer", "sad_darwin", "8d0f1c783def-infra"]}

Get a specific item when field matches the given value::

    # curl http://localhost:61208/api/4/containers/name/portainer
    {"portainer": [{"command": "/portainer",
                    "cpu": {"total": 0.0},
                    "cpu_percent": 0.0,
                    "created": "2022-10-29T14:59:10.266701439Z",
                    "engine": "docker",
                    "id": "3abd51c615968482d9ccff5afc629f267f6dda113ed68b75b432615fae3b49fb",
                    "image": ["portainer/portainer-ce:2.9.3"],
                    "io": {"cumulative_ior": 258048, "cumulative_iow": 1155072},
                    "key": "name",
                    "memory": {"cache": None,
                               "limit": 7823585280,
                               "max_usage": None,
                               "rss": None,
                               "usage": 15396864},
                    "memory_usage": 15396864,
                    "name": "portainer",
                    "network": {"cumulative_rx": 904556, "cumulative_tx": 0},
                    "status": "running",
                    "uptime": "yesterday"}]}

GET core
--------

Get plugin stats::

    # curl http://localhost:61208/api/4/core
    {"log": 4, "phys": 2}

Fields descriptions:

* **phys**: Number of physical cores (hyper thread CPUs are excluded) (unit is *number*)
* **log**: Number of logical CPUs. A logical CPU is the number of physical cores multiplied by the number of threads that can run on each core (unit is *number*)

Get a specific field::

    # curl http://localhost:61208/api/4/core/phys
    {"phys": 2}

GET cpu
-------

Get plugin stats::

    # curl http://localhost:61208/api/4/cpu
    {"cpucore": 4,
     "ctx_switches": 0,
     "guest": 0.0,
     "guest_nice": 0.0,
     "idle": 51.7,
     "interrupts": 0,
     "iowait": 1.0,
     "irq": 0.0,
     "nice": 0.0,
     "soft_interrupts": 0,
     "softirq": 0.0,
     "steal": 0.0,
     "syscalls": 0,
     "system": 6.8,
     "time_since_update": 1,
     "total": 47.3,
     "user": 40.6}

Fields descriptions:

* **total**: Sum of all CPU percentages (except idle) (unit is *percent*)
* **system**: Percent time spent in kernel space. System CPU time is the time spent running code in the Operating System kernel (unit is *percent*)
* **user**: CPU percent time spent in user space. User CPU time is the time spent on the processor running your program's code (or code in libraries) (unit is *percent*)
* **iowait**: *(Linux)*: percent time spent by the CPU waiting for I/O operations to complete (unit is *percent*)
* **dpc**: *(Windows)*: time spent servicing deferred procedure calls (DPCs) (unit is *percent*)
* **idle**: percent of CPU used by any program. Every program or task that runs on a computer system occupies a certain amount of processing time on the CPU. If the CPU has completed all tasks it is idle (unit is *percent*)
* **irq**: *(Linux and BSD)*: percent time spent servicing/handling hardware/software interrupts. Time servicing interrupts (hardware + software) (unit is *percent*)
* **nice**: *(Unix)*: percent time occupied by user level processes with a positive nice value. The time the CPU has spent running users' processes that have been *niced* (unit is *percent*)
* **steal**: *(Linux)*: percentage of time a virtual CPU waits for a real CPU while the hypervisor is servicing another virtual processor (unit is *percent*)
* **guest**: *(Linux)*: time spent running a virtual CPU for guest operating systems under the control of the Linux kernel (unit is *percent*)
* **ctx_switches**: number of context switches (voluntary + involuntary) per second. A context switch is a procedure that a computer's CPU (central processing unit) follows to change from one task (or process) to another while ensuring that the tasks do not conflict (unit is *number*)
* **interrupts**: number of interrupts per second (unit is *number*)
* **soft_interrupts**: number of software interrupts per second. Always set to 0 on Windows and SunOS (unit is *number*)
* **syscalls**: number of system calls per second. Always 0 on Linux OS (unit is *number*)
* **cpucore**: Total number of CPU core (unit is *number*)
* **time_since_update**: Number of seconds since last update (unit is *seconds*)

Get a specific field::

    # curl http://localhost:61208/api/4/cpu/total
    {"total": 47.3}

GET diskio
----------

Get plugin stats::

    # curl http://localhost:61208/api/4/diskio
    [{"disk_name": "sda",
      "key": "disk_name",
      "read_bytes": 0,
      "read_count": 0,
      "time_since_update": 1,
      "write_bytes": 0,
      "write_count": 0},
     {"alias": "InternalDisk",
      "disk_name": "sda1",
      "key": "disk_name",
      "read_bytes": 0,
      "read_count": 0,
      "time_since_update": 1,
      "write_bytes": 0,
      "write_count": 0}]

Fields descriptions:

* **disk_name**: Disk name (unit is *None*)
* **read_count**: Number of reads since last request (unit is *number*)
* **write_count**: Number of writes since last request (unit is *number*)
* **read_bytes**: Number of bytes read since last request (unit is *byte*)
* **write_bytes**: Number of bytes written since last request (unit is *byte*)
* **time_since_update**: Time since last request (unit is *second*)

Get a specific field::

    # curl http://localhost:61208/api/4/diskio/disk_name
    {"disk_name": ["sda", "sda1", "sda2", "sda5", "dm-0", "dm-1"]}

Get a specific item when field matches the given value::

    # curl http://localhost:61208/api/4/diskio/disk_name/sda
    {"sda": [{"disk_name": "sda",
              "key": "disk_name",
              "read_bytes": 0,
              "read_count": 0,
              "time_since_update": 1,
              "write_bytes": 0,
              "write_count": 0}]}

GET fs
------

Get plugin stats::

    # curl http://localhost:61208/api/4/fs
    [{"alias": "Root",
      "device_name": "/dev/mapper/ubuntu--gnome--vg-root",
      "free": 18082955264,
      "fs_type": "ext4",
      "key": "mnt_point",
      "mnt_point": "/",
      "percent": 92.2,
      "size": 243334156288,
      "used": 212863746048},
     {"device_name": "zsfpool",
      "free": 31195136,
      "fs_type": "zfs",
      "key": "mnt_point",
      "mnt_point": "/zsfpool",
      "percent": 25.4,
      "size": 41811968,
      "used": 10616832}]

Fields descriptions:

* **device_name**: Device name (unit is *None*)
* **fs_type**: File system type (unit is *None*)
* **mnt_point**: Mount point (unit is *None*)
* **size**: Total size (unit is *byte*)
* **used**: Used size (unit is *byte*)
* **free**: Free size (unit is *byte*)
* **percent**: File system usage in percent (unit is *percent*)

Get a specific field::

    # curl http://localhost:61208/api/4/fs/mnt_point
    {"mnt_point": ["/", "/zsfpool", "/var/snap/firefox/common/host-hunspell"]}

Get a specific item when field matches the given value::

    # curl http://localhost:61208/api/4/fs/mnt_point//
    {"/": [{"alias": "Root",
            "device_name": "/dev/mapper/ubuntu--gnome--vg-root",
            "free": 18082955264,
            "fs_type": "ext4",
            "key": "mnt_point",
            "mnt_point": "/",
            "percent": 92.2,
            "size": 243334156288,
            "used": 212863746048}]}

GET ip
------

Get plugin stats::

    # curl http://localhost:61208/api/4/ip
    {"address": "192.168.0.32",
     "gateway": "192.168.0.254",
     "mask": "255.255.255.0",
     "mask_cidr": 24,
     "public_address": "91.166.228.228",
     "public_info_human": ""}

Fields descriptions:

* **address**: Private IP address (unit is *None*)
* **mask**: Private IP mask (unit is *None*)
* **mask_cidr**: Private IP mask in CIDR format (unit is *number*)
* **gateway**: Private IP gateway (unit is *None*)
* **public_address**: Public IP address (unit is *None*)
* **public_info_human**: Public IP information (unit is *None*)

Get a specific field::

    # curl http://localhost:61208/api/4/ip/gateway
    {"gateway": "192.168.0.254"}

GET load
--------

Get plugin stats::

    # curl http://localhost:61208/api/4/load
    {"cpucore": 4,
     "min1": 1.48681640625,
     "min15": 2.0498046875,
     "min5": 2.1923828125}

Fields descriptions:

* **min1**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 1 minute (unit is *float*)
* **min5**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 5 minutes (unit is *float*)
* **min15**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 15 minutes (unit is *float*)
* **cpucore**: Total number of CPU core (unit is *number*)

Get a specific field::

    # curl http://localhost:61208/api/4/load/min1
    {"min1": 1.48681640625}

GET mem
-------

Get plugin stats::

    # curl http://localhost:61208/api/4/mem
    {"active": 3310006272,
     "available": 1515728896,
     "buffers": 43077632,
     "cached": 1603973120,
     "free": 1515728896,
     "inactive": 2717716480,
     "percent": 80.6,
     "shared": 538447872,
     "total": 7823585280,
     "used": 6307856384}

Fields descriptions:

* **total**: Total physical memory available (unit is *bytes*)
* **available**: The actual amount of available memory that can be given instantly to processes that request more memory in bytes; this is calculated by summing different memory values depending on the platform (e.g. free + buffers + cached on Linux) and it is supposed to be used to monitor actual memory usage in a cross platform fashion (unit is *bytes*)
* **percent**: The percentage usage calculated as (total - available) / total * 100 (unit is *percent*)
* **used**: Memory used, calculated differently depending on the platform and designed for informational purposes only (unit is *bytes*)
* **free**: Memory not being used at all (zeroed) that is readily available; note that this doesn't reflect the actual memory available (use 'available' instead) (unit is *bytes*)
* **active**: *(UNIX)*: memory currently in use or very recently used, and so it is in RAM (unit is *bytes*)
* **inactive**: *(UNIX)*: memory that is marked as not used (unit is *bytes*)
* **buffers**: *(Linux, BSD)*: cache for things like file system metadata (unit is *bytes*)
* **cached**: *(Linux, BSD)*: cache for various things (unit is *bytes*)
* **wired**: *(BSD, macOS)*: memory that is marked to always stay in RAM. It is never moved to disk (unit is *bytes*)
* **shared**: *(BSD)*: memory that may be simultaneously accessed by multiple processes (unit is *bytes*)

Get a specific field::

    # curl http://localhost:61208/api/4/mem/total
    {"total": 7823585280}

GET memswap
-----------

Get plugin stats::

    # curl http://localhost:61208/api/4/memswap
    {"free": 3459489792,
     "percent": 57.2,
     "sin": 22417694720,
     "sout": 30997102592,
     "time_since_update": 1,
     "total": 8082419712,
     "used": 4622929920}

Fields descriptions:

* **total**: Total swap memory (unit is *bytes*)
* **used**: Used swap memory (unit is *bytes*)
* **free**: Free swap memory (unit is *bytes*)
* **percent**: Used swap memory in percentage (unit is *percent*)
* **sin**: The number of bytes the system has swapped in from disk (cumulative) (unit is *bytes*)
* **sout**: The number of bytes the system has swapped out from disk (cumulative) (unit is *bytes*)
* **time_since_update**: Number of seconds since last update (unit is *seconds*)

Get a specific field::

    # curl http://localhost:61208/api/4/memswap/total
    {"total": 8082419712}

GET network
-----------

Get plugin stats::

    # curl http://localhost:61208/api/4/network
    [{"alias": None,
      "cumulative_cx": 2778732028,
      "cumulative_rx": 1389366014,
      "cumulative_tx": 1389366014,
      "cx": 0,
      "interface_name": "lo",
      "is_up": True,
      "key": "interface_name",
      "rx": 0,
      "speed": 0,
      "time_since_update": 1,
      "tx": 0},
     {"alias": "WIFI",
      "cumulative_cx": 16672958808,
      "cumulative_rx": 13355083630,
      "cumulative_tx": 3317875178,
      "cx": 126,
      "interface_name": "wlp2s0",
      "is_up": True,
      "key": "interface_name",
      "rx": 0,
      "speed": 0,
      "time_since_update": 1,
      "tx": 126}]

Fields descriptions:

* **interface_name**: Interface name (unit is *string*)
* **alias**: Interface alias name (optional) (unit is *string*)
* **rx**: The received/input rate (unit is *bitpersecond*)
* **tx**: The sent/output rate (unit is *bitpersecond*)
* **cx**: The cumulative received+sent rate (unit is *bitpersecond*)
* **cumulative_rx**: The number of bytes received through the interface (cumulative) (unit is *byte*)
* **cumulative_tx**: The number of bytes sent through the interface (cumulative) (unit is *byte*)
* **cumulative_cx**: The cumulative number of bytes reveived and sent through the interface (cumulative) (unit is *byte*)
* **speed**: Maximum interface speed (in bit per second). Can return 0 on some operating-system (unit is *bitpersecond*)
* **is_up**: Is the interface up ? (unit is *bool*)
* **time_since_update**: Number of seconds since last update (unit is *seconds*)

Get a specific field::

    # curl http://localhost:61208/api/4/network/interface_name
    {"interface_name": ["lo",
                        "wlp2s0",
                        "br-40875d2e2716",
                        "docker0",
                        "br_grafana",
                        "mpqemubr0",
                        "vethbeef843"]}

Get a specific item when field matches the given value::

    # curl http://localhost:61208/api/4/network/interface_name/lo
    {"lo": [{"alias": None,
             "cumulative_cx": 2778732028,
             "cumulative_rx": 1389366014,
             "cumulative_tx": 1389366014,
             "cx": 0,
             "interface_name": "lo",
             "is_up": True,
             "key": "interface_name",
             "rx": 0,
             "speed": 0,
             "time_since_update": 1,
             "tx": 0}]}

GET now
-------

Get plugin stats::

    # curl http://localhost:61208/api/4/now
    "2024-01-28 12:32:07 CET"

GET percpu
----------

Get plugin stats::

    # curl http://localhost:61208/api/4/percpu
    [{"cpu_number": 0,
      "guest": 0.0,
      "guest_nice": 0.0,
      "idle": 16.0,
      "iowait": 0.0,
      "irq": 0.0,
      "key": "cpu_number",
      "nice": 0.0,
      "softirq": 0.0,
      "steal": 0.0,
      "system": 4.0,
      "total": 84.0,
      "user": 32.0},
     {"cpu_number": 1,
      "guest": 0.0,
      "guest_nice": 0.0,
      "idle": 32.0,
      "iowait": 0.0,
      "irq": 0.0,
      "key": "cpu_number",
      "nice": 0.0,
      "softirq": 0.0,
      "steal": 0.0,
      "system": 2.0,
      "total": 68.0,
      "user": 16.0}]

Fields descriptions:

* **cpu_number**: CPU number (unit is *None*)
* **total**: Sum of CPU percentages (except idle) for current CPU number (unit is *percent*)
* **system**: Percent time spent in kernel space. System CPU time is the time spent running code in the Operating System kernel (unit is *percent*)
* **user**: CPU percent time spent in user space. User CPU time is the time spent on the processor running your program's code (or code in libraries) (unit is *percent*)
* **iowait**: *(Linux)*: percent time spent by the CPU waiting for I/O operations to complete (unit is *percent*)
* **idle**: percent of CPU used by any program. Every program or task that runs on a computer system occupies a certain amount of processing time on the CPU. If the CPU has completed all tasks it is idle (unit is *percent*)
* **irq**: *(Linux and BSD)*: percent time spent servicing/handling hardware/software interrupts. Time servicing interrupts (hardware + software) (unit is *percent*)
* **nice**: *(Unix)*: percent time occupied by user level processes with a positive nice value. The time the CPU has spent running users' processes that have been *niced* (unit is *percent*)
* **steal**: *(Linux)*: percentage of time a virtual CPU waits for a real CPU while the hypervisor is servicing another virtual processor (unit is *percent*)
* **guest**: *(Linux)*: percent of time spent running a virtual CPU for guest operating systems under the control of the Linux kernel (unit is *percent*)
* **guest_nice**: *(Linux)*: percent of time spent running a niced guest (virtual CPU) (unit is *percent*)
* **softirq**: *(Linux)*: percent of time spent handling software interrupts (unit is *percent*)

Get a specific field::

    # curl http://localhost:61208/api/4/percpu/cpu_number
    {"cpu_number": [0, 1, 2, 3]}

GET ports
---------

Get plugin stats::

    # curl http://localhost:61208/api/4/ports
    [{"description": "DefaultGateway",
      "host": "192.168.0.254",
      "indice": "port_0",
      "port": 0,
      "refresh": 30,
      "rtt_warning": None,
      "status": 0.026042,
      "timeout": 3}]

Fields descriptions:

* **host**: Measurement is be done on this host (or IP address) (unit is *None*)
* **port**: Measurement is be done on this port (0 for ICMP) (unit is *None*)
* **description**: Human readable description for the host/port (unit is *None*)
* **refresh**: Refresh time (in seconds) for this host/port (unit is *None*)
* **timeout**: Timeout (in seconds) for the measurement (unit is *None*)
* **status**: Measurement result (in seconds) (unit is *second*)
* **rtt_warning**: Warning threshold (in seconds) for the measurement (unit is *second*)
* **indice**: Unique indice for the host/port (unit is *None*)

Get a specific field::

    # curl http://localhost:61208/api/4/ports/host
    {"host": ["192.168.0.254"]}

Get a specific item when field matches the given value::

    # curl http://localhost:61208/api/4/ports/host/192.168.0.254
    {"192.168.0.254": [{"description": "DefaultGateway",
                        "host": "192.168.0.254",
                        "indice": "port_0",
                        "port": 0,
                        "refresh": 30,
                        "rtt_warning": None,
                        "status": 0.026042,
                        "timeout": 3}]}

GET processcount
----------------

Get plugin stats::

    # curl http://localhost:61208/api/4/processcount
    {"pid_max": 0, "running": 1, "sleeping": 336, "thread": 1722, "total": 407}

Fields descriptions:

* **total**: Total number of processes (unit is *number*)
* **running**: Total number of running processes (unit is *number*)
* **sleeping**: Total number of sleeping processes (unit is *number*)
* **thread**: Total number of threads (unit is *number*)
* **pid_max**: Maximum number of processes (unit is *number*)

Get a specific field::

    # curl http://localhost:61208/api/4/processcount/total
    {"total": 407}

GET psutilversion
-----------------

Get plugin stats::

    # curl http://localhost:61208/api/4/psutilversion
    "5.9.7"

GET quicklook
-------------

Get plugin stats::

    # curl http://localhost:61208/api/4/quicklook
    {"cpu": 47.3,
     "cpu_hz": 2025000000.0,
     "cpu_hz_current": 2019334750.0,
     "cpu_name": "Intel(R) Core(TM) i7-4500U CPU @ 1.80GHz",
     "cpucore": 4,
     "load": 51.2,
     "mem": 80.6,
     "percpu": [{"cpu_number": 0,
                 "guest": 0.0,
                 "guest_nice": 0.0,
                 "idle": 16.0,
                 "iowait": 0.0,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 0.0,
                 "steal": 0.0,
                 "system": 4.0,
                 "total": 84.0,
                 "user": 32.0},
                {"cpu_number": 1,
                 "guest": 0.0,
                 "guest_nice": 0.0,
                 "idle": 32.0,
                 "iowait": 0.0,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 0.0,
                 "steal": 0.0,
                 "system": 2.0,
                 "total": 68.0,
                 "user": 16.0},
                {"cpu_number": 2,
                 "guest": 0.0,
                 "guest_nice": 0.0,
                 "idle": 38.0,
                 "iowait": 0.0,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 0.0,
                 "steal": 0.0,
                 "system": 1.0,
                 "total": 62.0,
                 "user": 11.0},
                {"cpu_number": 3,
                 "guest": 0.0,
                 "guest_nice": 0.0,
                 "idle": 21.0,
                 "iowait": 2.0,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 0.0,
                 "steal": 0.0,
                 "system": 5.0,
                 "total": 79.0,
                 "user": 24.0}],
     "swap": 57.2}

Fields descriptions:

* **cpu**: CPU percent usage (unit is *percent*)
* **mem**: MEM percent usage (unit is *percent*)
* **swap**: SWAP percent usage (unit is *percent*)
* **load**: LOAD percent usage (unit is *percent*)
* **cpu_name**: CPU name (unit is *None*)
* **cpu_hz_current**: CPU current frequency (unit is *hertz*)
* **cpu_hz**: CPU max frequency (unit is *hertz*)

Get a specific field::

    # curl http://localhost:61208/api/4/quicklook/cpu_name
    {"cpu_name": "Intel(R) Core(TM) i7-4500U CPU @ 1.80GHz"}

GET sensors
-----------

Get plugin stats::

    # curl http://localhost:61208/api/4/sensors
    [{"critical": 105,
      "key": "label",
      "label": "acpitz 0",
      "type": "temperature_core",
      "unit": "C",
      "value": 27,
      "warning": 105},
     {"critical": 105,
      "key": "label",
      "label": "acpitz 1",
      "type": "temperature_core",
      "unit": "C",
      "value": 29,
      "warning": 105}]

Fields descriptions:

* **label**: Sensor label (unit is *None*)
* **unit**: Sensor unit (unit is *None*)
* **value**: Sensor value (unit is *number*)
* **warning**: Warning threshold (unit is *number*)
* **critical**: Critical threshold (unit is *number*)
* **type**: Sensor type (one of battery, temperature_core, fan_speed) (unit is *None*)

Get a specific field::

    # curl http://localhost:61208/api/4/sensors/label
    {"label": ["acpitz 0",
               "acpitz 1",
               "Package id 0",
               "Core 0",
               "Core 1",
               "CPU",
               "Ambient",
               "SODIMM",
               "BAT BAT0"]}

Get a specific item when field matches the given value::

    # curl http://localhost:61208/api/4/sensors/label/acpitz 0
    {"acpitz 0": [{"critical": 105,
                   "key": "label",
                   "label": "acpitz 0",
                   "type": "temperature_core",
                   "unit": "C",
                   "value": 27,
                   "warning": 105}]}

GET system
----------

Get plugin stats::

    # curl http://localhost:61208/api/4/system
    {"hostname": "XPS13-9333",
     "hr_name": "Ubuntu 22.04 64bit",
     "linux_distro": "Ubuntu 22.04",
     "os_name": "Linux",
     "os_version": "5.15.0-88-generic",
     "platform": "64bit"}

Fields descriptions:

* **os_name**: Operating system name (unit is *None*)
* **hostname**: Hostname (unit is *None*)
* **platform**: Platform (32 or 64 bits) (unit is *None*)
* **linux_distro**: Linux distribution (unit is *None*)
* **os_version**: Operating system version (unit is *None*)
* **hr_name**: Human readable operating sytem name (unit is *None*)

Get a specific field::

    # curl http://localhost:61208/api/4/system/os_name
    {"os_name": "Linux"}

GET uptime
----------

Get plugin stats::

    # curl http://localhost:61208/api/4/uptime
    "64 days, 3:34:07"

GET version
-----------

Get plugin stats::

    # curl http://localhost:61208/api/4/version
    "4.0.0_beta01"

GET all stats
-------------

Get all Glances stats::

    # curl http://localhost:61208/api/4/all
    Return a very big dictionary (avoid using this request, performances will be poor)...

GET top n items of a specific plugin
------------------------------------

Get top 2 processes of the processlist plugin::

    # curl http://localhost:61208/api/4/processlist/top/2
    [{"cmdline": ["/usr/share/code/code",
                  "--ms-enable-electron-run-as-node",
                  "/home/nicolargo/.vscode/extensions/vue.volar-1.8.25/server.js",
                  "--node-ipc",
                  "--clientProcessId=391253"],
      "cpu_percent": 0.0,
      "cpu_times": {"children_system": 0.0,
                    "children_user": 0.0,
                    "iowait": 0.0,
                    "system": 187.73,
                    "user": 3740.06},
      "gids": {"effective": 1000, "real": 1000, "saved": 1000},
      "io_counters": [1703493632, 0, 0, 0, 0],
      "key": "pid",
      "memory_info": {"data": 829427712,
                      "dirty": 0,
                      "lib": 0,
                      "rss": 609075200,
                      "shared": 16568320,
                      "text": 120565760,
                      "vms": 1205534920704},
      "memory_percent": 7.785116135399242,
      "name": "code",
      "nice": 0,
      "num_threads": 8,
      "pid": 391764,
      "status": "S",
      "time_since_update": 1,
      "username": "nicolargo"},
     {"cmdline": ["/usr/share/code/code",
                  "--ms-enable-electron-run-as-node",
                  "/home/nicolargo/.vscode/extensions/ms-python.vscode-pylance-2023.12.1/dist/server.bundle.js",
                  "--cancellationReceive=file:810abd06604ca203178b3fa9390087012fbf550dba",
                  "--node-ipc",
                  "--clientProcessId=391253"],
      "cpu_percent": 0.0,
      "cpu_times": {"children_system": 0.85,
                    "children_user": 6.34,
                    "iowait": 0.0,
                    "system": 471.69,
                    "user": 7941.84},
      "gids": {"effective": 1000, "real": 1000, "saved": 1000},
      "io_counters": [2165837824, 2703360, 0, 0, 0],
      "key": "pid",
      "memory_info": {"data": 956579840,
                      "dirty": 0,
                      "lib": 0,
                      "rss": 499519488,
                      "shared": 16252928,
                      "text": 120565760,
                      "vms": 1207768694784},
      "memory_percent": 6.384789966781061,
      "name": "code",
      "nice": 0,
      "num_threads": 13,
      "pid": 391817,
      "status": "S",
      "time_since_update": 1,
      "username": "nicolargo"}]

Note: Only work for plugin with a list of items

GET item description
--------------------
Get item description (human readable) for a specific plugin/item::

    # curl http://localhost:61208/api/4/diskio/read_bytes/description
    "Number of bytes read since last request."

Note: the description is defined in the fields_description variable of the plugin.

GET item unit
-------------
Get item unit for a specific plugin/item::

    # curl http://localhost:61208/api/4/diskio/read_bytes/unit
    "byte"

Note: the description is defined in the fields_description variable of the plugin.

GET stats history
-----------------

History of a plugin::

    # curl http://localhost:61208/api/4/cpu/history
    {"system": [["2024-01-28T12:32:09.692446", 6.8],
                ["2024-01-28T12:32:10.715124", 1.9],
                ["2024-01-28T12:32:11.935420", 1.9]],
     "user": [["2024-01-28T12:32:09.692430", 40.6],
              ["2024-01-28T12:32:10.715115", 12.8],
              ["2024-01-28T12:32:11.935405", 12.8]]}

Limit history to last 2 values::

    # curl http://localhost:61208/api/4/cpu/history/2
    {"system": [["2024-01-28T12:32:10.715124", 1.9],
                ["2024-01-28T12:32:11.935420", 1.9]],
     "user": [["2024-01-28T12:32:10.715115", 12.8],
              ["2024-01-28T12:32:11.935405", 12.8]]}

History for a specific field::

    # curl http://localhost:61208/api/4/cpu/system/history
    {"system": [["2024-01-28T12:32:07.812827", 6.8],
                ["2024-01-28T12:32:09.692446", 6.8],
                ["2024-01-28T12:32:10.715124", 1.9],
                ["2024-01-28T12:32:11.935420", 1.9]]}

Limit history for a specific field to last 2 values::

    # curl http://localhost:61208/api/4/cpu/system/history
    {"system": [["2024-01-28T12:32:10.715124", 1.9],
                ["2024-01-28T12:32:11.935420", 1.9]]}

GET limits (used for thresholds)
--------------------------------

All limits/thresholds::

    # curl http://localhost:61208/api/4/all/limits
    {"alert": {"alert_disable": ["False"], "history_size": 1200.0},
     "amps": {"amps_disable": ["False"], "history_size": 1200.0},
     "containers": {"containers_all": ["False"],
                    "containers_disable": ["False"],
                    "containers_max_name_size": 20.0,
                    "history_size": 1200.0},
     "core": {"history_size": 1200.0},
     "cpu": {"cpu_ctx_switches_careful": 160000.0,
             "cpu_ctx_switches_critical": 200000.0,
             "cpu_ctx_switches_warning": 180000.0,
             "cpu_disable": ["False"],
             "cpu_iowait_careful": 20.0,
             "cpu_iowait_critical": 25.0,
             "cpu_iowait_warning": 22.5,
             "cpu_steal_careful": 50.0,
             "cpu_steal_critical": 90.0,
             "cpu_steal_warning": 70.0,
             "cpu_system_careful": 50.0,
             "cpu_system_critical": 90.0,
             "cpu_system_log": ["False"],
             "cpu_system_warning": 70.0,
             "cpu_total_careful": 65.0,
             "cpu_total_critical": 85.0,
             "cpu_total_log": ["True"],
             "cpu_total_warning": 75.0,
             "cpu_user_careful": 50.0,
             "cpu_user_critical": 90.0,
             "cpu_user_log": ["False"],
             "cpu_user_warning": 70.0,
             "history_size": 1200.0},
     "diskio": {"diskio_alias": ["sda1:InternalDisk", "sdb1:ExternalDisk"],
                "diskio_disable": ["False"],
                "diskio_hide": ["loop.*", "/dev/loop.*"],
                "history_size": 1200.0},
     "folders": {"folders_disable": ["False"], "history_size": 1200.0},
     "fs": {"fs_alias": ["/:Root"],
            "fs_careful": 50.0,
            "fs_critical": 90.0,
            "fs_disable": ["False"],
            "fs_hide": ["/boot.*", "/snap.*"],
            "fs_warning": 70.0,
            "history_size": 1200.0},
     "gpu": {"gpu_disable": ["False"],
             "gpu_mem_careful": 50.0,
             "gpu_mem_critical": 90.0,
             "gpu_mem_warning": 70.0,
             "gpu_proc_careful": 50.0,
             "gpu_proc_critical": 90.0,
             "gpu_proc_warning": 70.0,
             "history_size": 1200.0},
     "help": {"history_size": 1200.0},
     "ip": {"history_size": 1200.0,
            "ip_censys_fields": ["location:continent",
                                 "location:country",
                                 "autonomous_system:name"],
            "ip_censys_url": ["https://search.censys.io/api"],
            "ip_disable": ["False"],
            "ip_public_ip_disabled": ["False"],
            "ip_public_refresh_interval": 300.0},
     "load": {"history_size": 1200.0,
              "load_careful": 0.7,
              "load_critical": 5.0,
              "load_disable": ["False"],
              "load_warning": 1.0},
     "mem": {"history_size": 1200.0,
             "mem_careful": 50.0,
             "mem_critical": 90.0,
             "mem_disable": ["False"],
             "mem_warning": 70.0},
     "memswap": {"history_size": 1200.0,
                 "memswap_careful": 50.0,
                 "memswap_critical": 90.0,
                 "memswap_disable": ["False"],
                 "memswap_warning": 70.0},
     "network": {"history_size": 1200.0,
                 "network_alias": ["wlp2s0:WIFI"],
                 "network_disable": ["False"],
                 "network_rx_careful": 70.0,
                 "network_rx_critical": 90.0,
                 "network_rx_warning": 80.0,
                 "network_tx_careful": 70.0,
                 "network_tx_critical": 90.0,
                 "network_tx_warning": 80.0},
     "now": {"history_size": 1200.0},
     "percpu": {"history_size": 1200.0,
                "percpu_disable": ["False"],
                "percpu_iowait_careful": 50.0,
                "percpu_iowait_critical": 90.0,
                "percpu_iowait_warning": 70.0,
                "percpu_system_careful": 50.0,
                "percpu_system_critical": 90.0,
                "percpu_system_warning": 70.0,
                "percpu_user_careful": 50.0,
                "percpu_user_critical": 90.0,
                "percpu_user_warning": 70.0},
     "ports": {"history_size": 1200.0,
               "ports_disable": ["False"],
               "ports_port_default_gateway": ["True"],
               "ports_refresh": 30.0,
               "ports_timeout": 3.0},
     "processcount": {"history_size": 1200.0, "processcount_disable": ["False"]},
     "processlist": {"history_size": 1200.0,
                     "processlist_cpu_careful": 50.0,
                     "processlist_cpu_critical": 90.0,
                     "processlist_cpu_warning": 70.0,
                     "processlist_disable": ["False"],
                     "processlist_mem_careful": 50.0,
                     "processlist_mem_critical": 90.0,
                     "processlist_mem_warning": 70.0,
                     "processlist_nice_warning": ["-20",
                                                  "-19",
                                                  "-18",
                                                  "-17",
                                                  "-16",
                                                  "-15",
                                                  "-14",
                                                  "-13",
                                                  "-12",
                                                  "-11",
                                                  "-10",
                                                  "-9",
                                                  "-8",
                                                  "-7",
                                                  "-6",
                                                  "-5",
                                                  "-4",
                                                  "-3",
                                                  "-2",
                                                  "-1",
                                                  "1",
                                                  "2",
                                                  "3",
                                                  "4",
                                                  "5",
                                                  "6",
                                                  "7",
                                                  "8",
                                                  "9",
                                                  "10",
                                                  "11",
                                                  "12",
                                                  "13",
                                                  "14",
                                                  "15",
                                                  "16",
                                                  "17",
                                                  "18",
                                                  "19"]},
     "psutilversion": {"history_size": 1200.0},
     "quicklook": {"history_size": 1200.0,
                   "quicklook_bar_char": ["|"],
                   "quicklook_cpu_careful": 50.0,
                   "quicklook_cpu_critical": 90.0,
                   "quicklook_cpu_warning": 70.0,
                   "quicklook_disable": ["False"],
                   "quicklook_list": ["cpu", "mem", "load"],
                   "quicklook_load_careful": 70.0,
                   "quicklook_load_critical": 500.0,
                   "quicklook_load_warning": 100.0,
                   "quicklook_mem_careful": 50.0,
                   "quicklook_mem_critical": 90.0,
                   "quicklook_mem_warning": 70.0,
                   "quicklook_swap_careful": 50.0,
                   "quicklook_swap_critical": 90.0,
                   "quicklook_swap_warning": 70.0},
     "sensors": {"history_size": 1200.0,
                 "sensors_battery_careful": 80.0,
                 "sensors_battery_critical": 95.0,
                 "sensors_battery_warning": 90.0,
                 "sensors_disable": ["False"],
                 "sensors_refresh": 4.0,
                 "sensors_temperature_core_careful": 60.0,
                 "sensors_temperature_core_critical": 80.0,
                 "sensors_temperature_core_warning": 70.0,
                 "sensors_temperature_hdd_careful": 45.0,
                 "sensors_temperature_hdd_critical": 60.0,
                 "sensors_temperature_hdd_warning": 52.0},
     "system": {"history_size": 1200.0,
                "system_disable": ["False"],
                "system_refresh": 60},
     "uptime": {"history_size": 1200.0},
     "version": {"history_size": 1200.0},
     "wifi": {"history_size": 1200.0,
              "wifi_careful": -65.0,
              "wifi_critical": -85.0,
              "wifi_disable": ["False"],
              "wifi_warning": -75.0}}

Limits/thresholds for the cpu plugin::

    # curl http://localhost:61208/api/4/cpu/limits
    {"cpu_ctx_switches_careful": 160000.0,
     "cpu_ctx_switches_critical": 200000.0,
     "cpu_ctx_switches_warning": 180000.0,
     "cpu_disable": ["False"],
     "cpu_iowait_careful": 20.0,
     "cpu_iowait_critical": 25.0,
     "cpu_iowait_warning": 22.5,
     "cpu_steal_careful": 50.0,
     "cpu_steal_critical": 90.0,
     "cpu_steal_warning": 70.0,
     "cpu_system_careful": 50.0,
     "cpu_system_critical": 90.0,
     "cpu_system_log": ["False"],
     "cpu_system_warning": 70.0,
     "cpu_total_careful": 65.0,
     "cpu_total_critical": 85.0,
     "cpu_total_log": ["True"],
     "cpu_total_warning": 75.0,
     "cpu_user_careful": 50.0,
     "cpu_user_critical": 90.0,
     "cpu_user_log": ["False"],
     "cpu_user_warning": 70.0,
     "history_size": 1200.0}


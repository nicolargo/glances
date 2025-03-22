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

If you want to enable the Glances Central Browser, use:

.. code-block:: bash

    # glances -w --browser --disable-webui

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
``http://localhost:61208/?refresh=5``


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
     "programlist",
     "psutilversion",
     "quicklook",
     "raid",
     "sensors",
     "smart",
     "system",
     "uptime",
     "version",
     "vms",
     "wifi"]

GET alert
---------

Get plugin stats::

    # curl http://localhost:61208/api/4/alert
    []

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
* **global_msg**: Global alert message (unit is *string*)

POST clear events
-----------------

Clear all alarms from the list::

    # curl -H "Content-Type: application/json" -X POST http://localhost:61208/api/4/events/clear/all

Clear warning alarms from the list::

    # curl -H "Content-Type: application/json" -X POST http://localhost:61208/api/4/events/clear/warning

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
      "timer": 0.3096492290496826},
     {"count": 0,
      "countmax": 20.0,
      "countmin": None,
      "key": "name",
      "name": "Python",
      "refresh": 3.0,
      "regex": True,
      "result": None,
      "timer": 0.30959320068359375}]

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

    # curl http://localhost:61208/api/4/amps/name/value/Dropbox
    {"Dropbox": [{"count": 0,
                  "countmax": None,
                  "countmin": 1.0,
                  "key": "name",
                  "name": "Dropbox",
                  "refresh": 3.0,
                  "regex": True,
                  "result": None,
                  "timer": 0.3096492290496826}]}

GET cloud
---------

Get plugin stats::

    # curl http://localhost:61208/api/4/cloud
    {}

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
    [{"command": "bash start.sh",
      "cpu": {"total": 0.0},
      "cpu_percent": 0.0,
      "created": "2025-03-02T18:56:49.050583851Z",
      "engine": "docker",
      "id": "37b79baf008ea602934be8d16d76064f79a032c11e4f6fe6e811b3c46ac20fd0",
      "image": ["ghcr.io/open-webui/open-webui:ollama"],
      "io": {"cumulative_ior": 620675072, "cumulative_iow": 0},
      "io_rx": None,
      "io_wx": None,
      "key": "name",
      "memory": {"inactive_file": 0, "limit": 16422428672, "usage": 488845312},
      "memory_percent": None,
      "memory_usage": 488845312,
      "name": "open-webui",
      "network": {"cumulative_rx": 454153644, "cumulative_tx": 10910712},
      "network_rx": None,
      "network_tx": None,
      "status": "running",
      "uptime": "a week"}]

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
    {"name": ["open-webui"]}

Get a specific item when field matches the given value::

    # curl http://localhost:61208/api/4/containers/name/value/open-webui
    {"open-webui": [{"command": "bash start.sh",
                     "cpu": {"total": 0.0},
                     "cpu_percent": 0.0,
                     "created": "2025-03-02T18:56:49.050583851Z",
                     "engine": "docker",
                     "id": "37b79baf008ea602934be8d16d76064f79a032c11e4f6fe6e811b3c46ac20fd0",
                     "image": ["ghcr.io/open-webui/open-webui:ollama"],
                     "io": {"cumulative_ior": 620675072, "cumulative_iow": 0},
                     "io_rx": None,
                     "io_wx": None,
                     "key": "name",
                     "memory": {"inactive_file": 0,
                                "limit": 16422428672,
                                "usage": 488845312},
                     "memory_percent": None,
                     "memory_usage": 488845312,
                     "name": "open-webui",
                     "network": {"cumulative_rx": 454153644,
                                 "cumulative_tx": 10910712},
                     "network_rx": None,
                     "network_tx": None,
                     "status": "running",
                     "uptime": "a week"}]}

GET core
--------

Get plugin stats::

    # curl http://localhost:61208/api/4/core
    {"log": 16, "phys": 10}

Fields descriptions:

* **phys**: Number of physical cores (hyper thread CPUs are excluded) (unit is *number*)
* **log**: Number of logical CPU cores. A logical CPU is the number of physical cores multiplied by the number of threads that can run on each core (unit is *number*)

Get a specific field::

    # curl http://localhost:61208/api/4/core/phys
    {"phys": 10}

GET cpu
-------

Get plugin stats::

    # curl http://localhost:61208/api/4/cpu
    {"cpucore": 16,
     "ctx_switches": 157096455,
     "guest": 0.0,
     "idle": 92.6,
     "interrupts": 107410302,
     "iowait": 0.1,
     "irq": 0.0,
     "nice": 0.0,
     "soft_interrupts": 47855924,
     "steal": 0.0,
     "syscalls": 0,
     "system": 2.6,
     "total": 7.4,
     "user": 4.7}

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
* **ctx_switches_rate_per_sec**: number of context switches (voluntary + involuntary) per second. A context switch is a procedure that a computer's CPU (central processing unit) follows to change from one task (or process) to another while ensuring that the tasks do not conflict per second (unit is *number* per second)
* **ctx_switches_gauge**: number of context switches (voluntary + involuntary) per second. A context switch is a procedure that a computer's CPU (central processing unit) follows to change from one task (or process) to another while ensuring that the tasks do not conflict (cumulative) (unit is *number*)
* **interrupts**: number of interrupts per second (unit is *number*)
* **interrupts_rate_per_sec**: number of interrupts per second per second (unit is *number* per second)
* **interrupts_gauge**: number of interrupts per second (cumulative) (unit is *number*)
* **soft_interrupts**: number of software interrupts per second. Always set to 0 on Windows and SunOS (unit is *number*)
* **soft_interrupts_rate_per_sec**: number of software interrupts per second. Always set to 0 on Windows and SunOS per second (unit is *number* per second)
* **soft_interrupts_gauge**: number of software interrupts per second. Always set to 0 on Windows and SunOS (cumulative) (unit is *number*)
* **syscalls**: number of system calls per second. Always 0 on Linux OS (unit is *number*)
* **syscalls_rate_per_sec**: number of system calls per second. Always 0 on Linux OS per second (unit is *number* per second)
* **syscalls_gauge**: number of system calls per second. Always 0 on Linux OS (cumulative) (unit is *number*)
* **cpucore**: Total number of CPU core (unit is *number*)
* **time_since_update**: Number of seconds since last update (unit is *seconds*)
* **time_since_update**: Number of seconds since last update (unit is *seconds*)

Get a specific field::

    # curl http://localhost:61208/api/4/cpu/total
    {"total": 7.4}

GET diskio
----------

Get plugin stats::

    # curl http://localhost:61208/api/4/diskio
    [{"disk_name": "nvme0n1",
      "key": "disk_name",
      "read_bytes": 8382154240,
      "read_count": 370011,
      "write_bytes": 71193142272,
      "write_count": 1225588},
     {"disk_name": "nvme0n1p1",
      "key": "disk_name",
      "read_bytes": 18425856,
      "read_count": 1233,
      "write_bytes": 5120,
      "write_count": 3}]

Fields descriptions:

* **disk_name**: Disk name (unit is *None*)
* **read_count**: Number of reads (unit is *number*)
* **read_count_rate_per_sec**: Number of reads per second (unit is *number* per second)
* **read_count_gauge**: Number of reads (cumulative) (unit is *number*)
* **write_count**: Number of writes (unit is *number*)
* **write_count_rate_per_sec**: Number of writes per second (unit is *number* per second)
* **write_count_gauge**: Number of writes (cumulative) (unit is *number*)
* **read_bytes**: Number of bytes read (unit is *byte*)
* **read_bytes_rate_per_sec**: Number of bytes read per second (unit is *byte* per second)
* **read_bytes_gauge**: Number of bytes read (cumulative) (unit is *byte*)
* **write_bytes**: Number of bytes written (unit is *byte*)
* **write_bytes_rate_per_sec**: Number of bytes written per second (unit is *byte* per second)
* **write_bytes_gauge**: Number of bytes written (cumulative) (unit is *byte*)
* **time_since_update**: Number of seconds since last update (unit is *seconds*)

Get a specific field::

    # curl http://localhost:61208/api/4/diskio/disk_name
    {"disk_name": ["nvme0n1",
                   "nvme0n1p1",
                   "nvme0n1p2",
                   "nvme0n1p3",
                   "dm-0",
                   "dm-1"]}

Get a specific item when field matches the given value::

    # curl http://localhost:61208/api/4/diskio/disk_name/value/nvme0n1
    {"nvme0n1": [{"disk_name": "nvme0n1",
                  "key": "disk_name",
                  "read_bytes": 8382154240,
                  "read_count": 370011,
                  "write_bytes": 71193142272,
                  "write_count": 1225588}]}

GET folders
-----------

Get plugin stats::

    # curl http://localhost:61208/api/4/folders
    []

Fields descriptions:

* **path**: Absolute path (unit is *None*)
* **size**: Folder size in bytes (unit is *byte*)
* **refresh**: Refresh interval in seconds (unit is *second*)
* **errno**: Return code when retrieving folder size (0 is no error) (unit is *number*)
* **careful**: Careful threshold in MB (unit is *megabyte*)
* **warning**: Warning threshold in MB (unit is *megabyte*)
* **critical**: Critical threshold in MB (unit is *megabyte*)

GET fs
------

Get plugin stats::

    # curl http://localhost:61208/api/4/fs
    [{"device_name": "/dev/mapper/ubuntu--vg-ubuntu--lv",
      "free": 825913921536,
      "fs_type": "ext4",
      "key": "mnt_point",
      "mnt_point": "/",
      "percent": 13.3,
      "size": 1003736440832,
      "used": 126760013824},
     {"device_name": "zsfpool",
      "free": 41811968,
      "fs_type": "zfs",
      "key": "mnt_point",
      "mnt_point": "/zsfpool",
      "percent": 0.3,
      "size": 41943040,
      "used": 131072}]

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
    {"mnt_point": ["/", "/zsfpool"]}

Get a specific item when field matches the given value::

    # curl http://localhost:61208/api/4/fs/mnt_point/value//
    {"/": [{"device_name": "/dev/mapper/ubuntu--vg-ubuntu--lv",
            "free": 825913921536,
            "fs_type": "ext4",
            "key": "mnt_point",
            "mnt_point": "/",
            "percent": 13.3,
            "size": 1003736440832,
            "used": 126760013824}]}

GET gpu
-------

Get plugin stats::

    # curl http://localhost:61208/api/4/gpu
    []

Fields descriptions:

* **gpu_id**: GPU identification (unit is *None*)
* **name**: GPU name (unit is *None*)
* **mem**: Memory consumption (unit is *percent*)
* **proc**: GPU processor consumption (unit is *percent*)
* **temperature**: GPU temperature (unit is *celsius*)
* **fan_speed**: GPU fan speed (unit is *roundperminute*)

GET help
--------

Get plugin stats::

    # curl http://localhost:61208/api/4/help
    None

GET ip
------

Get plugin stats::

    # curl http://localhost:61208/api/4/ip
    {"address": "192.168.0.28",
     "mask": "255.255.255.0",
     "mask_cidr": 24,
     "public_address": "",
     "public_info_human": ""}

Fields descriptions:

* **address**: Private IP address (unit is *None*)
* **mask**: Private IP mask (unit is *None*)
* **mask_cidr**: Private IP mask in CIDR format (unit is *number*)
* **gateway**: Private IP gateway (unit is *None*)
* **public_address**: Public IP address (unit is *None*)
* **public_info_human**: Public IP information (unit is *None*)

Get a specific field::

    # curl http://localhost:61208/api/4/ip/address
    {"address": "192.168.0.28"}

GET irq
-------

Get plugin stats::

    # curl http://localhost:61208/api/4/irq
    []

Fields descriptions:

* **irq_line**: IRQ line name (unit is *None*)
* **irq_rate**: IRQ rate per second (unit is *numberpersecond*)

GET load
--------

Get plugin stats::

    # curl http://localhost:61208/api/4/load
    {"cpucore": 16,
     "min1": 1.74560546875,
     "min15": 0.80810546875,
     "min5": 1.0078125}

Fields descriptions:

* **min1**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 1 minute (unit is *float*)
* **min5**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 5 minutes (unit is *float*)
* **min15**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 15 minutes (unit is *float*)
* **cpucore**: Total number of CPU core (unit is *number*)

Get a specific field::

    # curl http://localhost:61208/api/4/load/min1
    {"min1": 1.74560546875}

GET mem
-------

Get plugin stats::

    # curl http://localhost:61208/api/4/mem
    {"active": 6679535616,
     "available": 6505562112,
     "buffers": 185286656,
     "cached": 5573652480,
     "free": 6505562112,
     "inactive": 5449142272,
     "percent": 60.4,
     "shared": 764145664,
     "total": 16422428672,
     "used": 9916866560}

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
    {"total": 16422428672}

GET memswap
-----------

Get plugin stats::

    # curl http://localhost:61208/api/4/memswap
    {"free": 3455053824,
     "percent": 19.6,
     "sin": 12197888,
     "sout": 854618112,
     "time_since_update": 1,
     "total": 4294963200,
     "used": 839909376}

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
    {"total": 4294963200}

GET network
-----------

Get plugin stats::

    # curl http://localhost:61208/api/4/network
    [{"alias": None,
      "bytes_all": 0,
      "bytes_all_gauge": 2622508339,
      "bytes_recv": 0,
      "bytes_recv_gauge": 2469455038,
      "bytes_sent": 0,
      "bytes_sent_gauge": 153053301,
      "interface_name": "wlp0s20f3",
      "key": "interface_name",
      "speed": 0,
      "time_since_update": 0.31115031242370605},
     {"alias": None,
      "bytes_all": 0,
      "bytes_all_gauge": 24003803,
      "bytes_recv": 0,
      "bytes_recv_gauge": 441027,
      "bytes_sent": 0,
      "bytes_sent_gauge": 23562776,
      "interface_name": "mpqemubr0",
      "key": "interface_name",
      "speed": 10485760000,
      "time_since_update": 0.31115031242370605}]

Fields descriptions:

* **interface_name**: Interface name (unit is *None*)
* **alias**: Interface alias name (optional) (unit is *None*)
* **bytes_recv**: Number of bytes received (unit is *byte*)
* **bytes_recv_rate_per_sec**: Number of bytes received per second (unit is *byte* per second)
* **bytes_recv_gauge**: Number of bytes received (cumulative) (unit is *byte*)
* **bytes_sent**: Number of bytes sent (unit is *byte*)
* **bytes_sent_rate_per_sec**: Number of bytes sent per second (unit is *byte* per second)
* **bytes_sent_gauge**: Number of bytes sent (cumulative) (unit is *byte*)
* **bytes_all**: Number of bytes received and sent (unit is *byte*)
* **bytes_all_rate_per_sec**: Number of bytes received and sent per second (unit is *byte* per second)
* **bytes_all_gauge**: Number of bytes received and sent (cumulative) (unit is *byte*)
* **speed**: Maximum interface speed (in bit per second). Can return 0 on some operating-system (unit is *bitpersecond*)
* **is_up**: Is the interface up ? (unit is *bool*)
* **time_since_update**: Number of seconds since last update (unit is *seconds*)

Get a specific field::

    # curl http://localhost:61208/api/4/network/interface_name
    {"interface_name": ["wlp0s20f3", "mpqemubr0", "tap-8d309783ee6", "veth7684f4d"]}

Get a specific item when field matches the given value::

    # curl http://localhost:61208/api/4/network/interface_name/value/wlp0s20f3
    {"wlp0s20f3": [{"alias": None,
                    "bytes_all": 0,
                    "bytes_all_gauge": 2622508339,
                    "bytes_recv": 0,
                    "bytes_recv_gauge": 2469455038,
                    "bytes_sent": 0,
                    "bytes_sent_gauge": 153053301,
                    "interface_name": "wlp0s20f3",
                    "key": "interface_name",
                    "speed": 0,
                    "time_since_update": 0.31115031242370605}]}

GET now
-------

Get plugin stats::

    # curl http://localhost:61208/api/4/now
    {"custom": "2025-03-22 17:41:04 CET", "iso": "2025-03-22T17:41:04+01:00"}

Fields descriptions:

* **custom**: Current date in custom format (unit is *None*)
* **iso**: Current date in ISO 8601 format (unit is *None*)

Get a specific field::

    # curl http://localhost:61208/api/4/now/iso
    {"iso": "2025-03-22T17:41:04+01:00"}

GET percpu
----------

Get plugin stats::

    # curl http://localhost:61208/api/4/percpu
    [{"cpu_number": 0,
      "dpc": None,
      "guest": 0.0,
      "guest_nice": 0.0,
      "idle": 30.0,
      "interrupt": None,
      "iowait": 0.0,
      "irq": 0.0,
      "key": "cpu_number",
      "nice": 0.0,
      "softirq": 0.0,
      "steal": 0.0,
      "system": 0.0,
      "total": 70.0,
      "user": 0.0},
     {"cpu_number": 1,
      "dpc": None,
      "guest": 0.0,
      "guest_nice": 0.0,
      "idle": 22.0,
      "interrupt": None,
      "iowait": 0.0,
      "irq": 0.0,
      "key": "cpu_number",
      "nice": 0.0,
      "softirq": 0.0,
      "steal": 0.0,
      "system": 9.0,
      "total": 78.0,
      "user": 0.0}]

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
* **dpc**: *(Windows)*: percent of time spent handling deferred procedure calls (unit is *percent*)
* **interrupt**: *(Windows)*: percent of time spent handling software interrupts (unit is *percent*)

Get a specific field::

    # curl http://localhost:61208/api/4/percpu/cpu_number
    {"cpu_number": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]}

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
      "status": 0.013786,
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

    # curl http://localhost:61208/api/4/ports/host/value/192.168.0.254
    {"192.168.0.254": [{"description": "DefaultGateway",
                        "host": "192.168.0.254",
                        "indice": "port_0",
                        "port": 0,
                        "refresh": 30,
                        "rtt_warning": None,
                        "status": 0.013786,
                        "timeout": 3}]}

GET processcount
----------------

Get plugin stats::

    # curl http://localhost:61208/api/4/processcount
    {"pid_max": 0, "running": 1, "sleeping": 427, "thread": 2030, "total": 567}

Fields descriptions:

* **total**: Total number of processes (unit is *number*)
* **running**: Total number of running processes (unit is *number*)
* **sleeping**: Total number of sleeping processes (unit is *number*)
* **thread**: Total number of threads (unit is *number*)
* **pid_max**: Maximum number of processes (unit is *number*)

Get a specific field::

    # curl http://localhost:61208/api/4/processcount/total
    {"total": 567}

GET processlist
---------------

Get plugin stats::

    # curl http://localhost:61208/api/4/processlist
    [{"cmdline": ["/snap/code/181/usr/share/code/code",
                  "--type=utility",
                  "--utility-sub-type=node.mojom.NodeService",
                  "--lang=en-US",
                  "--service-sandbox-type=none",
                  "--no-sandbox",
                  "--dns-result-order=ipv4first",
                  "--inspect-port=0",
                  "--crashpad-handler-pid=79415",
                  "--enable-crash-reporter=864d4bb7-dd20-4851-830f-29e81dd93517,no_channel",
                  "--user-data-dir=/home/nicolargo/.config/Code",
                  "--standard-schemes=vscode-webview,vscode-file",
                  "--secure-schemes=vscode-webview,vscode-file",
                  "--cors-schemes=vscode-webview,vscode-file",
                  "--fetch-schemes=vscode-webview,vscode-file",
                  "--service-worker-schemes=vscode-webview",
                  "--code-cache-schemes=vscode-webview,vscode-file",
                  "--shared-files=v8_context_snapshot_data:100",
                  "--field-trial-handle=3,i,1279145526343135898,6861814050030728552,262144",
                  "--disable-features=CalculateNativeWinOcclusion,PlzDedicatedWorker,SpareRendererForSitePerProcess",
                  "--variations-seed-version"],
      "cpu_percent": 0.0,
      "cpu_times": {"children_system": 139.72,
                    "children_user": 50.81,
                    "iowait": 0.0,
                    "system": 119.61,
                    "user": 187.77},
      "gids": {"effective": 1000, "real": 1000, "saved": 1000},
      "io_counters": [490232832,
                      272453632,
                      0,
                      0,
                      0,
                      75640832,
                      1458176,
                      0,
                      0,
                      0,
                      70094848,
                      0,
                      0,
                      0,
                      0,
                      21813248,
                      3252224,
                      0,
                      0,
                      0,
                      68483072,
                      35565568,
                      0,
                      0,
                      0,
                      10318848,
                      0,
                      0,
                      0,
                      0,
                      46509056,
                      1436467200,
                      0,
                      0,
                      0,
                      36725760,
                      0,
                      0,
                      0,
                      0,
                      2703360,
                      0,
                      0,
                      0,
                      0,
                      615424,
                      0,
                      0,
                      0,
                      0,
                      5218304,
                      0,
                      0,
                      0,
                      0,
                      140288,
                      0,
                      0,
                      0,
                      0,
                      3473408,
                      2461696,
                      0,
                      0,
                      0,
                      988160,
                      0,
                      0,
                      0,
                      0,
                      1223680,
                      0,
                      0,
                      0,
                      0],
      "key": "pid",
      "memory_info": {"data": 2457976832,
                      "dirty": 0,
                      "lib": 0,
                      "rss": 1292099584,
                      "shared": 124125184,
                      "text": 138166272,
                      "vms": 1272570376192},
      "memory_percent": 7.86789585028316,
      "name": "code",
      "nice": 0,
      "num_threads": 56,
      "pid": 79607,
      "status": "S",
      "time_since_update": 1,
      "username": "nicolargo"},
     {"cmdline": ["/snap/multipass/14300/usr/bin/qemu-system-x86_64",
                  "-bios",
                  "OVMF.fd",
                  "--enable-kvm",
                  "-cpu",
                  "host",
                  "-nic",
                  "tap,ifname=tap-8d309783ee6,script=no,downscript=no,model=virtio-net-pci,mac=52:54:00:c3:48:7b",
                  "-device",
                  "virtio-scsi-pci,id=scsi0",
                  "-drive",
                  "file=/var/snap/multipass/common/data/multipassd/vault/instances/upstanding-sparrow/ubuntu-24.04-server-cloudimg-amd64.img,if=none,format=qcow2,discard=unmap,id=hda",
                  "-device",
                  "scsi-hd,drive=hda,bus=scsi0.0",
                  "-smp",
                  "1",
                  "-m",
                  "1024M",
                  "-qmp",
                  "stdio",
                  "-chardev",
                  "null,id=char0",
                  "-serial",
                  "chardev:char0",
                  "-nographic",
                  "-cdrom",
                  "/var/snap/multipass/common/data/multipassd/vault/instances/upstanding-sparrow/cloud-init-config.iso"],
      "cpu_percent": 0.0,
      "cpu_times": {"children_system": 0.0,
                    "children_user": 0.0,
                    "iowait": 0.0,
                    "system": 46.6,
                    "user": 180.54},
      "gids": {"effective": 0, "real": 0, "saved": 0},
      "io_counters": [0, 0, 0, 0, 0],
      "key": "pid",
      "memory_info": {"data": 1417625600,
                      "dirty": 0,
                      "lib": 0,
                      "rss": 1103982592,
                      "shared": 14286848,
                      "text": 6172672,
                      "vms": 5118357504},
      "memory_percent": 6.722407592990641,
      "name": "qemu-system-x86_64",
      "nice": 0,
      "num_threads": 5,
      "pid": 3297,
      "status": "S",
      "time_since_update": 1,
      "username": "root"}]

Fields descriptions:

* **pid**: Process identifier (ID) (unit is *number*)
* **name**: Process name (unit is *string*)
* **cmdline**: Command line with arguments (unit is *list*)
* **username**: Process owner (unit is *string*)
* **num_threads**: Number of threads (unit is *number*)
* **cpu_percent**: Process CPU consumption (unit is *percent*)
* **memory_percent**: Process memory consumption (unit is *percent*)
* **memory_info**: Process memory information (dict with rss, vms, shared, text, lib, data, dirty keys) (unit is *byte*)
* **status**: Process status (unit is *string*)
* **nice**: Process nice value (unit is *number*)
* **cpu_times**: Process CPU times (dict with user, system, iowait keys) (unit is *second*)
* **gids**: Process group IDs (dict with real, effective, saved keys) (unit is *number*)
* **io_counters**: Process IO counters (list with read_count, write_count, read_bytes, write_bytes, io_tag keys) (unit is *byte*)

GET programlist
---------------

Get plugin stats::

    # curl http://localhost:61208/api/4/programlist
    [{"childrens": [79607,
                    80276,
                    80569,
                    79491,
                    79394,
                    80831,
                    79581,
                    79582,
                    79545,
                    79970,
                    80365,
                    80351,
                    79467,
                    79397,
                    79396],
      "cmdline": ["code"],
      "cpu_percent": 0,
      "cpu_times": {"children_system": 140.97,
                    "children_user": 58.089999999999996,
                    "system": 242.39999999999995,
                    "user": 1004.36},
      "io_counters": [490232832,
                      272453632,
                      0,
                      0,
                      0,
                      75640832,
                      1458176,
                      0,
                      0,
                      0,
                      70094848,
                      0,
                      0,
                      0,
                      0,
                      21813248,
                      3252224,
                      0,
                      0,
                      0,
                      68483072,
                      35565568,
                      0,
                      0,
                      0,
                      10318848,
                      0,
                      0,
                      0,
                      0,
                      46509056,
                      1436467200,
                      0,
                      0,
                      0,
                      36725760,
                      0,
                      0,
                      0,
                      0,
                      2703360,
                      0,
                      0,
                      0,
                      0,
                      615424,
                      0,
                      0,
                      0,
                      0,
                      5218304,
                      0,
                      0,
                      0,
                      0,
                      140288,
                      0,
                      0,
                      0,
                      0,
                      3473408,
                      2461696,
                      0,
                      0,
                      0,
                      988160,
                      0,
                      0,
                      0,
                      0,
                      1223680,
                      0,
                      0,
                      0,
                      0],
      "memory_info": {"data": 11900305408,
                      "rss": 4097130496,
                      "shared": 1183440896,
                      "text": 2072494080,
                      "vms": 13841155485696},
      "memory_percent": 24.948383566345143,
      "name": "code",
      "nice": 0,
      "nprocs": 15,
      "num_threads": 266,
      "pid": "_",
      "status": "S",
      "time_since_update": 1,
      "username": "nicolargo"},
     {"childrens": [3297],
      "cmdline": ["qemu-system-x86_64"],
      "cpu_percent": 0,
      "cpu_times": {"children_system": 0.0,
                    "children_user": 0.0,
                    "iowait": 0.0,
                    "system": 46.6,
                    "user": 180.54},
      "io_counters": [0, 0, 0, 0, 0],
      "memory_info": {"data": 1417625600,
                      "dirty": 0,
                      "lib": 0,
                      "rss": 1103982592,
                      "shared": 14286848,
                      "text": 6172672,
                      "vms": 5118357504},
      "memory_percent": 6.722407592990641,
      "name": "qemu-system-x86_64",
      "nice": 0,
      "nprocs": 1,
      "num_threads": 5,
      "pid": "_",
      "status": "S",
      "time_since_update": 1,
      "username": "root"}]

Fields descriptions:

* **pid**: Process identifier (ID) (unit is *number*)
* **name**: Process name (unit is *string*)
* **cmdline**: Command line with arguments (unit is *list*)
* **username**: Process owner (unit is *string*)
* **num_threads**: Number of threads (unit is *number*)
* **cpu_percent**: Process CPU consumption (unit is *percent*)
* **memory_percent**: Process memory consumption (unit is *percent*)
* **memory_info**: Process memory information (dict with rss, vms, shared, text, lib, data, dirty keys) (unit is *byte*)
* **status**: Process status (unit is *string*)
* **nice**: Process nice value (unit is *number*)
* **cpu_times**: Process CPU times (dict with user, system, iowait keys) (unit is *second*)
* **gids**: Process group IDs (dict with real, effective, saved keys) (unit is *number*)
* **io_counters**: Process IO counters (list with read_count, write_count, read_bytes, write_bytes, io_tag keys) (unit is *byte*)

GET psutilversion
-----------------

Get plugin stats::

    # curl http://localhost:61208/api/4/psutilversion
    "7.0.0"

GET quicklook
-------------

Get plugin stats::

    # curl http://localhost:61208/api/4/quicklook
    {"cpu": 7.4,
     "cpu_hz": 4475000000.0,
     "cpu_hz_current": 1364220562.5,
     "cpu_log_core": 16,
     "cpu_name": "13th Gen Intel(R) Core(TM) i7-13620H",
     "cpu_phys_core": 10,
     "load": 5.1,
     "mem": 60.4,
     "percpu": [{"cpu_number": 0,
                 "dpc": None,
                 "guest": 0.0,
                 "guest_nice": 0.0,
                 "idle": 30.0,
                 "interrupt": None,
                 "iowait": 0.0,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 0.0,
                 "steal": 0.0,
                 "system": 0.0,
                 "total": 70.0,
                 "user": 0.0},
                {"cpu_number": 1,
                 "dpc": None,
                 "guest": 0.0,
                 "guest_nice": 0.0,
                 "idle": 22.0,
                 "interrupt": None,
                 "iowait": 0.0,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 0.0,
                 "steal": 0.0,
                 "system": 9.0,
                 "total": 78.0,
                 "user": 0.0},
                {"cpu_number": 2,
                 "dpc": None,
                 "guest": 0.0,
                 "guest_nice": 0.0,
                 "idle": 30.0,
                 "interrupt": None,
                 "iowait": 0.0,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 0.0,
                 "steal": 0.0,
                 "system": 0.0,
                 "total": 70.0,
                 "user": 0.0},
                {"cpu_number": 3,
                 "dpc": None,
                 "guest": 0.0,
                 "guest_nice": 0.0,
                 "idle": 30.0,
                 "interrupt": None,
                 "iowait": 0.0,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 0.0,
                 "steal": 0.0,
                 "system": 0.0,
                 "total": 70.0,
                 "user": 0.0},
                {"cpu_number": 4,
                 "dpc": None,
                 "guest": 0.0,
                 "guest_nice": 0.0,
                 "idle": 24.0,
                 "interrupt": None,
                 "iowait": 0.0,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 0.0,
                 "steal": 0.0,
                 "system": 3.0,
                 "total": 76.0,
                 "user": 1.0},
                {"cpu_number": 5,
                 "dpc": None,
                 "guest": 0.0,
                 "guest_nice": 0.0,
                 "idle": 26.0,
                 "interrupt": None,
                 "iowait": 0.0,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 0.0,
                 "steal": 0.0,
                 "system": 3.0,
                 "total": 74.0,
                 "user": 1.0},
                {"cpu_number": 6,
                 "dpc": None,
                 "guest": 0.0,
                 "guest_nice": 0.0,
                 "idle": 21.0,
                 "interrupt": None,
                 "iowait": 0.0,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 0.0,
                 "steal": 0.0,
                 "system": 2.0,
                 "total": 79.0,
                 "user": 8.0},
                {"cpu_number": 7,
                 "dpc": None,
                 "guest": 0.0,
                 "guest_nice": 0.0,
                 "idle": 30.0,
                 "interrupt": None,
                 "iowait": 0.0,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 0.0,
                 "steal": 0.0,
                 "system": 0.0,
                 "total": 70.0,
                 "user": 0.0},
                {"cpu_number": 8,
                 "dpc": None,
                 "guest": 0.0,
                 "guest_nice": 0.0,
                 "idle": 28.0,
                 "interrupt": None,
                 "iowait": 0.0,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 0.0,
                 "steal": 0.0,
                 "system": 0.0,
                 "total": 72.0,
                 "user": 3.0},
                {"cpu_number": 9,
                 "dpc": None,
                 "guest": 0.0,
                 "guest_nice": 0.0,
                 "idle": 30.0,
                 "interrupt": None,
                 "iowait": 0.0,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 0.0,
                 "steal": 0.0,
                 "system": 0.0,
                 "total": 70.0,
                 "user": 0.0},
                {"cpu_number": 10,
                 "dpc": None,
                 "guest": 0.0,
                 "guest_nice": 0.0,
                 "idle": 30.0,
                 "interrupt": None,
                 "iowait": 0.0,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 0.0,
                 "steal": 0.0,
                 "system": 0.0,
                 "total": 70.0,
                 "user": 1.0},
                {"cpu_number": 11,
                 "dpc": None,
                 "guest": 0.0,
                 "guest_nice": 0.0,
                 "idle": 30.0,
                 "interrupt": None,
                 "iowait": 0.0,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 0.0,
                 "steal": 0.0,
                 "system": 0.0,
                 "total": 70.0,
                 "user": 0.0},
                {"cpu_number": 12,
                 "dpc": None,
                 "guest": 0.0,
                 "guest_nice": 0.0,
                 "idle": 28.0,
                 "interrupt": None,
                 "iowait": 0.0,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 0.0,
                 "steal": 0.0,
                 "system": 0.0,
                 "total": 72.0,
                 "user": 2.0},
                {"cpu_number": 13,
                 "dpc": None,
                 "guest": 0.0,
                 "guest_nice": 0.0,
                 "idle": 30.0,
                 "interrupt": None,
                 "iowait": 0.0,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 0.0,
                 "steal": 0.0,
                 "system": 0.0,
                 "total": 70.0,
                 "user": 0.0},
                {"cpu_number": 14,
                 "dpc": None,
                 "guest": 0.0,
                 "guest_nice": 0.0,
                 "idle": 30.0,
                 "interrupt": None,
                 "iowait": 0.0,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 0.0,
                 "steal": 0.0,
                 "system": 0.0,
                 "total": 70.0,
                 "user": 1.0},
                {"cpu_number": 15,
                 "dpc": None,
                 "guest": 0.0,
                 "guest_nice": 0.0,
                 "idle": 30.0,
                 "interrupt": None,
                 "iowait": 0.0,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 0.0,
                 "steal": 0.0,
                 "system": 0.0,
                 "total": 70.0,
                 "user": 0.0}],
     "swap": 19.6}

Fields descriptions:

* **cpu**: CPU percent usage (unit is *percent*)
* **mem**: MEM percent usage (unit is *percent*)
* **swap**: SWAP percent usage (unit is *percent*)
* **load**: LOAD percent usage (unit is *percent*)
* **cpu_log_core**: Number of logical CPU core (unit is *number*)
* **cpu_phys_core**: Number of physical CPU core (unit is *number*)
* **cpu_name**: CPU name (unit is *None*)
* **cpu_hz_current**: CPU current frequency (unit is *hertz*)
* **cpu_hz**: CPU max frequency (unit is *hertz*)

Get a specific field::

    # curl http://localhost:61208/api/4/quicklook/cpu_name
    {"cpu_name": "13th Gen Intel(R) Core(TM) i7-13620H"}

GET raid
--------

Get plugin stats::

    # curl http://localhost:61208/api/4/raid
    {}

GET sensors
-----------

Get plugin stats::

    # curl http://localhost:61208/api/4/sensors
    [{"critical": None,
      "key": "label",
      "label": "Ambient",
      "type": "temperature_core",
      "unit": "C",
      "value": 40,
      "warning": 0},
     {"critical": None,
      "key": "label",
      "label": "Ambient 3",
      "type": "temperature_core",
      "unit": "C",
      "value": 30,
      "warning": 0}]

Fields descriptions:

* **label**: Sensor label (unit is *None*)
* **unit**: Sensor unit (unit is *None*)
* **value**: Sensor value (unit is *number*)
* **warning**: Warning threshold (unit is *number*)
* **critical**: Critical threshold (unit is *number*)
* **type**: Sensor type (one of battery, temperature_core, fan_speed) (unit is *None*)

Get a specific field::

    # curl http://localhost:61208/api/4/sensors/label
    {"label": ["Ambient",
               "Ambient 3",
               "Ambient 5",
               "Ambient 6",
               "CPU",
               "Composite",
               "Core 0",
               "Core 12",
               "Core 16",
               "Core 20",
               "Core 28",
               "Core 29",
               "Core 30",
               "Core 31",
               "Core 4",
               "Core 8",
               "HDD",
               "Package id 0",
               "SODIMM",
               "Sensor 1",
               "Sensor 2",
               "dell_smm 0",
               "dell_smm 1",
               "dell_smm 2",
               "dell_smm 3",
               "dell_smm 4",
               "dell_smm 5",
               "dell_smm 6",
               "dell_smm 7",
               "dell_smm 8",
               "dell_smm 9",
               "iwlwifi_1 0",
               "CPU Fan",
               "Video Fan",
               "dell_smm 0",
               "dell_smm 1",
               "BAT BAT0"]}

Get a specific item when field matches the given value::

    # curl http://localhost:61208/api/4/sensors/label/value/Ambient
    {"Ambient": [{"critical": None,
                  "key": "label",
                  "label": "Ambient",
                  "type": "temperature_core",
                  "unit": "C",
                  "value": 40,
                  "warning": 0}]}

GET smart
---------

Get plugin stats::

    # curl http://localhost:61208/api/4/smart
    {}

GET system
----------

Get plugin stats::

    # curl http://localhost:61208/api/4/system
    {"hostname": "nicolargo-xps15",
     "hr_name": "Ubuntu 24.04 64bit / Linux 6.8.0-51-generic",
     "linux_distro": "Ubuntu 24.04",
     "os_name": "Linux",
     "os_version": "6.8.0-51-generic",
     "platform": "64bit"}

Fields descriptions:

* **os_name**: Operating system name (unit is *None*)
* **hostname**: Hostname (unit is *None*)
* **platform**: Platform (32 or 64 bits) (unit is *None*)
* **linux_distro**: Linux distribution (unit is *None*)
* **os_version**: Operating system version (unit is *None*)
* **hr_name**: Human readable operating system name (unit is *None*)

Get a specific field::

    # curl http://localhost:61208/api/4/system/os_name
    {"os_name": "Linux"}

GET uptime
----------

Get plugin stats::

    # curl http://localhost:61208/api/4/uptime
    "7 days, 2:36:15"

GET version
-----------

Get plugin stats::

    # curl http://localhost:61208/api/4/version
    "4.3.1"

GET vms
-------

Get plugin stats::

    # curl http://localhost:61208/api/4/vms
    {}

Fields descriptions:

* **name**: Vm name (unit is *None*)
* **id**: Vm ID (unit is *None*)
* **release**: Vm release (unit is *None*)
* **status**: Vm status (unit is *None*)
* **cpu_count**: Vm CPU count (unit is *None*)
* **memory_usage**: Vm memory usage (unit is *byte*)
* **memory_total**: Vm memory total (unit is *byte*)
* **load_1min**: Vm Load last 1 min (unit is *None*)
* **load_5min**: Vm Load last 5 mins (unit is *None*)
* **load_15min**: Vm Load last 15 mins (unit is *None*)
* **ipv4**: Vm IP v4 address (unit is *None*)
* **engine**: VM engine name (only Mutlipass is currently supported) (unit is *None*)
* **engine_version**: VM engine version (unit is *None*)

GET wifi
--------

Get plugin stats::

    # curl http://localhost:61208/api/4/wifi
    [{"key": "ssid",
      "quality_level": -66.0,
      "quality_link": 44.0,
      "ssid": "wlp0s20f3"}]

Get a specific field::

    # curl http://localhost:61208/api/4/wifi/ssid
    {"ssid": ["wlp0s20f3"]}

Get a specific item when field matches the given value::

    # curl http://localhost:61208/api/4/wifi/ssid/value/wlp0s20f3
    {"wlp0s20f3": [{"key": "ssid",
                    "quality_level": -66.0,
                    "quality_link": 44.0,
                    "ssid": "wlp0s20f3"}]}

GET all stats
-------------

Get all Glances stats::

    # curl http://localhost:61208/api/4/all
    Return a very big dictionary with all stats

Note: Update is done automatically every time /all or /<plugin> is called.

GET stats of a specific process
-------------------------------

Get stats for process with PID == 777::

    # curl http://localhost:61208/api/4/processes/777
    Return stats for process (dict)

Enable extended stats for process with PID == 777 (only one process at a time can be enabled)::

    # curl -X POST http://localhost:61208/api/4/processes/extended/777
    # curl http://localhost:61208/api/4/all
    # curl http://localhost:61208/api/4/processes/777
    Return stats for process (dict)

Note: Update *is not* done automatically when you call /processes/<pid>.

GET top n items of a specific plugin
------------------------------------

Get top 2 processes of the processlist plugin::

    # curl http://localhost:61208/api/4/processlist/top/2
    []

Note: Only work for plugin with a list of items

GET item description
--------------------
Get item description (human readable) for a specific plugin/item::

    # curl http://localhost:61208/api/4/diskio/read_bytes/description
    "Number of bytes read."

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
    {"system": [["2025-03-22T17:41:05.581948", 2.6],
                ["2025-03-22T17:41:06.651293", 0.8],
                ["2025-03-22T17:41:07.669006", 0.8]],
     "user": [["2025-03-22T17:41:05.581940", 4.7],
              ["2025-03-22T17:41:06.651292", 3.7],
              ["2025-03-22T17:41:07.669004", 3.7]]}

Limit history to last 2 values::

    # curl http://localhost:61208/api/4/cpu/history/2
    {"system": [["2025-03-22T17:41:06.651293", 0.8],
                ["2025-03-22T17:41:07.669006", 0.8]],
     "user": [["2025-03-22T17:41:06.651292", 3.7],
              ["2025-03-22T17:41:07.669004", 3.7]]}

History for a specific field::

    # curl http://localhost:61208/api/4/cpu/system/history
    {"system": [["2025-03-22T17:41:04.464503", 2.6],
                ["2025-03-22T17:41:05.581948", 2.6],
                ["2025-03-22T17:41:06.651293", 0.8],
                ["2025-03-22T17:41:07.669006", 0.8]]}

Limit history for a specific field to last 2 values::

    # curl http://localhost:61208/api/4/cpu/system/history
    {"system": [["2025-03-22T17:41:06.651293", 0.8],
                ["2025-03-22T17:41:07.669006", 0.8]]}

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
     "cpu": {"cpu_ctx_switches_careful": 640000.0,
             "cpu_ctx_switches_critical": 800000.0,
             "cpu_ctx_switches_warning": 720000.0,
             "cpu_disable": ["False"],
             "cpu_iowait_careful": 5.0,
             "cpu_iowait_critical": 6.25,
             "cpu_iowait_warning": 5.625,
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
     "diskio": {"diskio_disable": ["False"],
                "diskio_hide": ["loop.*", "/dev/loop.*"],
                "diskio_hide_zero": ["False"],
                "history_size": 1200.0},
     "folders": {"folders_disable": ["False"], "history_size": 1200.0},
     "fs": {"fs_careful": 50.0,
            "fs_critical": 90.0,
            "fs_disable": ["False"],
            "fs_hide": ["/boot.*", ".*/snap.*"],
            "fs_warning": 70.0,
            "history_size": 1200.0},
     "gpu": {"gpu_disable": ["False"],
             "gpu_mem_careful": 50.0,
             "gpu_mem_critical": 90.0,
             "gpu_mem_warning": 70.0,
             "gpu_proc_careful": 50.0,
             "gpu_proc_critical": 90.0,
             "gpu_proc_warning": 70.0,
             "gpu_temperature_careful": 60.0,
             "gpu_temperature_critical": 80.0,
             "gpu_temperature_warning": 70.0,
             "history_size": 1200.0},
     "help": {"history_size": 1200.0},
     "ip": {"history_size": 1200.0,
            "ip_disable": ["False"],
            "ip_public_api": ["https://ipv4.ipleak.net/json/"],
            "ip_public_disabled": ["True"],
            "ip_public_field": ["ip"],
            "ip_public_refresh_interval": 300.0,
            "ip_public_template": ["{continent_name}/{country_name}/{city_name}"]},
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
                 "network_disable": ["False"],
                 "network_hide": ["docker.*", "lo"],
                 "network_hide_no_ip": ["True"],
                 "network_hide_no_up": ["True"],
                 "network_hide_zero": ["False"],
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
                "percpu_max_cpu_display": 4.0,
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
     "programlist": {"history_size": 1200.0},
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
                 "sensors_battery_careful": 70.0,
                 "sensors_battery_critical": 90.0,
                 "sensors_battery_warning": 80.0,
                 "sensors_disable": ["False"],
                 "sensors_hide": ["unknown.*"],
                 "sensors_refresh": 6.0,
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
    {"cpu_ctx_switches_careful": 640000.0,
     "cpu_ctx_switches_critical": 800000.0,
     "cpu_ctx_switches_warning": 720000.0,
     "cpu_disable": ["False"],
     "cpu_iowait_careful": 5.0,
     "cpu_iowait_critical": 6.25,
     "cpu_iowait_warning": 5.625,
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


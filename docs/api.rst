.. _api:

API (Restfull/JSON) documentation
=================================

The Glances Restfull/API server could be ran using the following command line:

.. code-block:: bash

    # glances -w --disable-webui

API URL
-------

The default root API URL is ``http://localhost:61208/api/3``.

The bind address and port could be changed using the ``--bind`` and ``--port`` command line options.

It is also possible to define an URL prefix using the ``url_prefix`` option from the [outputs] section
of the Glances configuration file. The url_prefix should always end with a slash (``/``).

For example:

.. code-block:: ini
    [outputs]
    url_prefix = /glances/

will change the root API URL to ``http://localhost:61208/glances/api/3`` and the Web UI URL to
``http://localhost:61208/glances/``


GET API status
--------------

This entry point should be used to check the API status.
It will return nothing but a 200 return code if everything is OK.

Get the Rest API status::

    # curl -I http://localhost:61208/api/3/status
    "HTTP/1.0 200 OK"

GET plugins list
----------------

Get the plugins list::

    # curl http://localhost:61208/api/3/pluginslist
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
     "wifi"]

GET alert
---------

Get plugin stats::

    # curl http://localhost:61208/api/3/alert
    [[1702229920.0,
      -1,
      "WARNING",
      "MEM",
      77.66056060791016,
      77.66056060791016,
      77.66056060791016,
      77.66056060791016,
      1,
      [],
      "",
      "memory_percent"]]

GET amps
--------

Get plugin stats::

    # curl http://localhost:61208/api/3/amps
    [{"count": 0,
      "countmax": None,
      "countmin": 1.0,
      "key": "name",
      "name": "Dropbox",
      "refresh": 3.0,
      "regex": True,
      "result": None,
      "timer": 0.08340811729431152},
     {"count": 0,
      "countmax": 20.0,
      "countmin": None,
      "key": "name",
      "name": "Python",
      "refresh": 3.0,
      "regex": True,
      "result": None,
      "timer": 0.08331799507141113}]

Get a specific field::

    # curl http://localhost:61208/api/3/amps/name
    {"name": ["Dropbox", "Python", "Conntrack", "Nginx", "Systemd", "SystemV"]}

Get a specific item when field matches the given value::

    # curl http://localhost:61208/api/3/amps/name/Dropbox
    {"Dropbox": [{"count": 0,
                  "countmax": None,
                  "countmin": 1.0,
                  "key": "name",
                  "name": "Dropbox",
                  "refresh": 3.0,
                  "regex": True,
                  "result": None,
                  "timer": 0.08340811729431152}]}

GET connections
---------------

Get plugin stats::

    # curl http://localhost:61208/api/3/connections
    {"net_connections_enabled": True, "nf_conntrack_enabled": True}

Get a specific field::

    # curl http://localhost:61208/api/3/connections/net_connections_enabled
    {"net_connections_enabled": True}

GET core
--------

Get plugin stats::

    # curl http://localhost:61208/api/3/core
    {"log": 8, "phys": 8}

Fields descriptions:

* **phys**: Number of physical cores (hyper thread CPUs are excluded) (unit is *number*)
* **log**: Number of logical CPUs. A logical CPU is the number of physical cores multiplied by the number of threads that can run on each core (unit is *number*)

Get a specific field::

    # curl http://localhost:61208/api/3/core/phys
    {"phys": 8}

GET cpu
-------

Get plugin stats::

    # curl http://localhost:61208/api/3/cpu
    {"cpucore": 8,
     "ctx_switches": 0,
     "idle": 59.9,
     "interrupts": 0,
     "nice": 0.0,
     "soft_interrupts": 0,
     "syscalls": 0,
     "system": 19.0,
     "time_since_update": 1,
     "total": 39.7,
     "user": 21.1}

Fields descriptions:

* **total**: Sum of all CPU percentages (except idle) (unit is *percent*)
* **system**: percent time spent in kernel space. System CPU time is the time spent running code in the Operating System kernel (unit is *percent*)
* **user**: CPU percent time spent in user space. User CPU time is the time spent on the processor running your program's code (or code in libraries) (unit is *percent*)
* **iowait**: *(Linux)*: percent time spent by the CPU waiting for I/O operations to complete (unit is *percent*)
* **dpc**: *(Windows)*: time spent servicing deferred procedure calls (DPCs) (unit is *percent*)
* **idle**: percent of CPU used by any program. Every program or task that runs on a computer system occupies a certain amount of processing time on the CPU. If the CPU has completed all tasks it is idle (unit is *percent*)
* **irq**: *(Linux and BSD)*: percent time spent servicing/handling hardware/software interrupts. Time servicing interrupts (hardware + software) (unit is *percent*)
* **nice**: *(Unix)*: percent time occupied by user level processes with a positive nice value. The time the CPU has spent running users' processes that have been *niced* (unit is *percent*)
* **steal**: *(Linux)*: percentage of time a virtual CPU waits for a real CPU while the hypervisor is servicing another virtual processor (unit is *percent*)
* **ctx_switches**: number of context switches (voluntary + involuntary) per second. A context switch is a procedure that a computer's CPU (central processing unit) follows to change from one task (or process) to another while ensuring that the tasks do not conflict (unit is *number*)
* **interrupts**: number of interrupts per second (unit is *number*)
* **soft_interrupts**: number of software interrupts per second. Always set to 0 on Windows and SunOS (unit is *number*)
* **syscalls**: number of system calls per second. Always 0 on Linux OS (unit is *number*)
* **cpucore**: Total number of CPU core (unit is *number*)
* **time_since_update**: Number of seconds since last update (unit is *seconds*)

Get a specific field::

    # curl http://localhost:61208/api/3/cpu/total
    {"total": 39.7}

GET diskio
----------

Get plugin stats::

    # curl http://localhost:61208/api/3/diskio
    [{"disk_name": "disk0",
      "key": "disk_name",
      "read_bytes": 0,
      "read_count": 0,
      "time_since_update": 1,
      "write_bytes": 0,
      "write_count": 0}]

Get a specific field::

    # curl http://localhost:61208/api/3/diskio/disk_name
    {"disk_name": ["disk0"]}

Get a specific item when field matches the given value::

    # curl http://localhost:61208/api/3/diskio/disk_name/disk0
    {"disk0": [{"disk_name": "disk0",
                "key": "disk_name",
                "read_bytes": 0,
                "read_count": 0,
                "time_since_update": 1,
                "write_bytes": 0,
                "write_count": 0}]}

GET fs
------

Get plugin stats::

    # curl http://localhost:61208/api/3/fs
    [{"device_name": "/dev/disk3s1s1",
      "free": 197418139648,
      "fs_type": "apfs",
      "key": "mnt_point",
      "mnt_point": "/",
      "percent": 4.8,
      "size": 494384795648,
      "used": 9903136768},
     {"device_name": "/dev/disk3s6",
      "free": 197418139648,
      "fs_type": "apfs",
      "key": "mnt_point",
      "mnt_point": "/System/Volumes/VM",
      "percent": 0.0,
      "size": 494384795648,
      "used": 20480}]

Get a specific field::

    # curl http://localhost:61208/api/3/fs/mnt_point
    {"mnt_point": ["/",
                   "/System/Volumes/VM",
                   "/System/Volumes/Preboot",
                   "/System/Volumes/Update",
                   "/System/Volumes/xarts",
                   "/System/Volumes/iSCPreboot",
                   "/System/Volumes/Hardware",
                   "/System/Volumes/Data"]}

Get a specific item when field matches the given value::

    # curl http://localhost:61208/api/3/fs/mnt_point//
    {"/": [{"device_name": "/dev/disk3s1s1",
            "free": 197418139648,
            "fs_type": "apfs",
            "key": "mnt_point",
            "mnt_point": "/",
            "percent": 4.8,
            "size": 494384795648,
            "used": 9903136768}]}

GET load
--------

Get plugin stats::

    # curl http://localhost:61208/api/3/load
    {"cpucore": 8,
     "min1": 6.21044921875,
     "min15": 6.52490234375,
     "min5": 6.1923828125}

Fields descriptions:

* **min1**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 1 minute (unit is *float*)
* **min5**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 5 minutes (unit is *float*)
* **min15**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 15 minutes (unit is *float*)
* **cpucore**: Total number of CPU core (unit is *number*)

Get a specific field::

    # curl http://localhost:61208/api/3/load/min1
    {"min1": 6.21044921875}

GET mem
-------

Get plugin stats::

    # curl http://localhost:61208/api/3/mem
    {"active": 3810230272,
     "available": 3837886464,
     "free": 3837886464,
     "inactive": 3775741952,
     "percent": 77.7,
     "total": 17179869184,
     "used": 13341982720,
     "wired": 2604072960}

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

    # curl http://localhost:61208/api/3/mem/total
    {"total": 17179869184}

GET memswap
-----------

Get plugin stats::

    # curl http://localhost:61208/api/3/memswap
    {"free": 0,
     "percent": 0.0,
     "sin": 113365762048,
     "sout": 7638499328,
     "time_since_update": 1,
     "total": 0,
     "used": 0}

Fields descriptions:

* **total**: Total swap memory (unit is *bytes*)
* **used**: Used swap memory (unit is *bytes*)
* **free**: Free swap memory (unit is *bytes*)
* **percent**: Used swap memory in percentage (unit is *percent*)
* **sin**: The number of bytes the system has swapped in from disk (cumulative) (unit is *bytes*)
* **sout**: The number of bytes the system has swapped out from disk (cumulative) (unit is *bytes*)
* **time_since_update**: Number of seconds since last update (unit is *seconds*)

Get a specific field::

    # curl http://localhost:61208/api/3/memswap/total
    {"total": 0}

GET network
-----------

Get plugin stats::

    # curl http://localhost:61208/api/3/network
    [{"alias": None,
      "cumulative_cx": 720357822,
      "cumulative_rx": 360178911,
      "cumulative_tx": 360178911,
      "cx": 208,
      "interface_name": "lo0",
      "is_up": True,
      "key": "interface_name",
      "rx": 104,
      "speed": 0,
      "time_since_update": 1,
      "tx": 104},
     {"alias": None,
      "cumulative_cx": 0,
      "cumulative_rx": 0,
      "cumulative_tx": 0,
      "cx": 0,
      "interface_name": "gif0",
      "is_up": False,
      "key": "interface_name",
      "rx": 0,
      "speed": 0,
      "time_since_update": 1,
      "tx": 0}]

Fields descriptions:

* **interface_name**: Interface name (unit is *string*)
* **alias**: Interface alias name (optional) (unit is *string*)
* **rx**: The received/input rate (in bit per second) (unit is *bps*)
* **tx**: The sent/output rate (in bit per second) (unit is *bps*)
* **cx**: The cumulative received+sent rate (in bit per second) (unit is *bps*)
* **cumulative_rx**: The number of bytes received through the interface (cumulative) (unit is *bytes*)
* **cumulative_tx**: The number of bytes sent through the interface (cumulative) (unit is *bytes*)
* **cumulative_cx**: The cumulative number of bytes reveived and sent through the interface (cumulative) (unit is *bytes*)
* **speed**: Maximum interface speed (in bit per second). Can return 0 on some operating-system (unit is *bps*)
* **is_up**: Is the interface up ? (unit is *bool*)
* **time_since_update**: Number of seconds since last update (unit is *seconds*)

Get a specific field::

    # curl http://localhost:61208/api/3/network/interface_name
    {"interface_name": ["lo0",
                        "gif0",
                        "stf0",
                        "anpi2",
                        "anpi1",
                        "anpi0",
                        "en4",
                        "en5",
                        "en6",
                        "en1",
                        "en2",
                        "en3",
                        "bridge0",
                        "ap1",
                        "en0",
                        "awdl0",
                        "llw0",
                        "utun0",
                        "utun1",
                        "utun2",
                        "utun3",
                        "utun4",
                        "utun5",
                        "utun6",
                        "utun7"]}

Get a specific item when field matches the given value::

    # curl http://localhost:61208/api/3/network/interface_name/lo0
    {"lo0": [{"alias": None,
              "cumulative_cx": 720357822,
              "cumulative_rx": 360178911,
              "cumulative_tx": 360178911,
              "cx": 208,
              "interface_name": "lo0",
              "is_up": True,
              "key": "interface_name",
              "rx": 104,
              "speed": 0,
              "time_since_update": 1,
              "tx": 104}]}

GET now
-------

Get plugin stats::

    # curl http://localhost:61208/api/3/now
    "2023-12-10 21:38:40 +04"

GET percpu
----------

Get plugin stats::

    # curl http://localhost:61208/api/3/percpu
    [{"cpu_number": 0,
      "idle": 1.0,
      "key": "cpu_number",
      "nice": 0.0,
      "system": 6.0,
      "total": 99.0,
      "user": 10.0},
     {"cpu_number": 1,
      "idle": 1.0,
      "key": "cpu_number",
      "nice": 0.0,
      "system": 6.0,
      "total": 99.0,
      "user": 10.0}]

Get a specific field::

    # curl http://localhost:61208/api/3/percpu/cpu_number
    {"cpu_number": [0, 1, 2, 3, 4, 5, 6, 7]}

GET processcount
----------------

Get plugin stats::

    # curl http://localhost:61208/api/3/processcount
    {"pid_max": 0, "running": 540, "sleeping": 0, "thread": 2309, "total": 540}

Get a specific field::

    # curl http://localhost:61208/api/3/processcount/total
    {"total": 540}

GET psutilversion
-----------------

Get plugin stats::

    # curl http://localhost:61208/api/3/psutilversion
    [5, 9, 6]

GET quicklook
-------------

Get plugin stats::

    # curl http://localhost:61208/api/3/quicklook
    {"cpu": 39.7,
     "cpu_hz": None,
     "cpu_hz_current": None,
     "cpu_name": "CPU",
     "mem": 77.6,
     "percpu": [{"cpu_number": 0,
                 "idle": 1.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "system": 6.0,
                 "total": 99.0,
                 "user": 10.0},
                {"cpu_number": 1,
                 "idle": 1.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "system": 6.0,
                 "total": 99.0,
                 "user": 10.0},
                {"cpu_number": 2,
                 "idle": 12.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "system": 3.0,
                 "total": 88.0,
                 "user": 2.0},
                {"cpu_number": 3,
                 "idle": 8.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "system": 4.0,
                 "total": 92.0,
                 "user": 5.0},
                {"cpu_number": 4,
                 "idle": 14.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "system": 2.0,
                 "total": 86.0,
                 "user": 3.0},
                {"cpu_number": 5,
                 "idle": 15.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "system": 4.0,
                 "total": 85.0,
                 "user": 1.0},
                {"cpu_number": 6,
                 "idle": 17.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "system": 2.0,
                 "total": 83.0,
                 "user": 0.0},
                {"cpu_number": 7,
                 "idle": 19.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "system": 0.0,
                 "total": 81.0,
                 "user": 0.0}],
     "swap": 0.0}

Get a specific field::

    # curl http://localhost:61208/api/3/quicklook/cpu
    {"cpu": 39.7}

GET sensors
-----------

Get plugin stats::

    # curl http://localhost:61208/api/3/sensors
    [{"key": "label",
      "label": "Battery",
      "status": "Charging",
      "type": "battery",
      "unit": "%",
      "value": 80}]

Get a specific field::

    # curl http://localhost:61208/api/3/sensors/label
    {"label": ["Battery"]}

Get a specific item when field matches the given value::

    # curl http://localhost:61208/api/3/sensors/label/Battery
    {"Battery": [{"key": "label",
                  "label": "Battery",
                  "status": "Charging",
                  "type": "battery",
                  "unit": "%",
                  "value": 80}]}

GET system
----------

Get plugin stats::

    # curl http://localhost:61208/api/3/system
    {"hostname": "Georgiis-MacBook-Pro.local",
     "hr_name": "Darwin 14.1.2 64bit",
     "os_name": "Darwin",
     "os_version": "14.1.2",
     "platform": "64bit"}

Get a specific field::

    # curl http://localhost:61208/api/3/system/os_name
    {"os_name": "Darwin"}

GET uptime
----------

Get plugin stats::

    # curl http://localhost:61208/api/3/uptime
    "2 days, 21:58:56"

GET all stats
-------------

Get all Glances stats::

    # curl http://localhost:61208/api/3/all
    Return a very big dictionary (avoid using this request, performances will be poor)...

GET top n items of a specific plugin
------------------------------------

Get top 2 processes of the processlist plugin::

    # curl http://localhost:61208/api/3/processlist/top/2
    [{"cmdline": ["/System/Library/Frameworks/WebKit.framework/Versions/A/XPCServices/com.apple.WebKit.WebContent.xpc/Contents/MacOS/com.apple.WebKit.WebContent"],
      "cpu_percent": 0.0,
      "cpu_times": pcputimes(user=1439.267815424, system=153.321242624, children_user=0.0, children_system=0.0),
      "gids": puids(real=20, effective=20, saved=20),
      "io_counters": [0, 0, 0, 0, 0],
      "key": "pid",
      "memory_info": pmem(rss=671449088, vms=512469778432, pfaults=8159047, pageins=797),
      "memory_percent": 3.9083480834960938,
      "name": "com.apple.WebKit.WebContent",
      "nice": 0,
      "num_threads": 7,
      "pid": 23116,
      "status": "R",
      "time_since_update": 1,
      "username": "georgiy"},
     {"cmdline": ["/System/Volumes/Preboot/Cryptexes/App/System/Applications/Safari.app/Contents/MacOS/Safari"],
      "cpu_percent": 0.0,
      "cpu_times": pcputimes(user=3313.558355968, system=1054.28484096, children_user=0.0, children_system=0.0),
      "gids": puids(real=20, effective=20, saved=20),
      "io_counters": [0, 0, 0, 0, 0],
      "key": "pid",
      "memory_info": pmem(rss=342081536, vms=428145426432, pfaults=9564269, pageins=10950),
      "memory_percent": 1.9911766052246094,
      "name": "Safari",
      "nice": 0,
      "num_threads": 14,
      "pid": 2025,
      "status": "R",
      "time_since_update": 1,
      "username": "georgiy"}]

Note: Only work for plugin with a list of items

GET stats history
-----------------

History of a plugin::

    # curl http://localhost:61208/api/3/cpu/history
    {"system": [["2023-12-10T21:38:41.146559", 19.0],
                ["2023-12-10T21:38:42.182581", 12.1],
                ["2023-12-10T21:38:43.259730", 12.1]],
     "user": [["2023-12-10T21:38:41.146554", 21.1],
              ["2023-12-10T21:38:42.182578", 20.1],
              ["2023-12-10T21:38:43.259727", 20.1]]}

Limit history to last 2 values::

    # curl http://localhost:61208/api/3/cpu/history/2
    {"system": [["2023-12-10T21:38:42.182581", 12.1],
                ["2023-12-10T21:38:43.259730", 12.1]],
     "user": [["2023-12-10T21:38:42.182578", 20.1],
              ["2023-12-10T21:38:43.259727", 20.1]]}

History for a specific field::

    # curl http://localhost:61208/api/3/cpu/system/history
    {"system": [["2023-12-10T21:38:40.083920", 19.0],
                ["2023-12-10T21:38:41.146559", 19.0],
                ["2023-12-10T21:38:42.182581", 12.1],
                ["2023-12-10T21:38:43.259730", 12.1]]}

Limit history for a specific field to last 2 values::

    # curl http://localhost:61208/api/3/cpu/system/history
    {"system": [["2023-12-10T21:38:42.182581", 12.1],
                ["2023-12-10T21:38:43.259730", 12.1]]}

GET limits (used for thresholds)
--------------------------------

All limits/thresholds::

    # curl http://localhost:61208/api/3/all/limits
    {"alert": {"alert_disable": ["False"], "history_size": 1200.0},
     "amps": {"amps_disable": ["False"], "history_size": 1200.0},
     "containers": {"containers_all": ["False"],
                    "containers_disable": ["False"],
                    "containers_max_name_size": 20.0,
                    "history_size": 1200.0},
     "core": {"history_size": 1200.0},
     "cpu": {"cpu_ctx_switches_careful": 320000.0,
             "cpu_ctx_switches_critical": 400000.0,
             "cpu_ctx_switches_warning": 360000.0,
             "cpu_disable": ["False"],
             "cpu_iowait_careful": 10.0,
             "cpu_iowait_critical": 12.5,
             "cpu_iowait_warning": 11.25,
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
                "history_size": 1200.0},
     "folders": {"folders_disable": ["False"], "history_size": 1200.0},
     "fs": {"fs_careful": 50.0,
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
                   "quicklook_cpu_careful": 50.0,
                   "quicklook_cpu_critical": 90.0,
                   "quicklook_cpu_warning": 70.0,
                   "quicklook_disable": ["False"],
                   "quicklook_mem_careful": 50.0,
                   "quicklook_mem_critical": 90.0,
                   "quicklook_mem_warning": 70.0,
                   "quicklook_percentage_char": ["|"],
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
     "wifi": {"history_size": 1200.0,
              "wifi_careful": -65.0,
              "wifi_critical": -85.0,
              "wifi_disable": ["False"],
              "wifi_warning": -75.0}}

Limits/thresholds for the cpu plugin::

    # curl http://localhost:61208/api/3/cpu/limits
    {"cpu_ctx_switches_careful": 320000.0,
     "cpu_ctx_switches_critical": 400000.0,
     "cpu_ctx_switches_warning": 360000.0,
     "cpu_disable": ["False"],
     "cpu_iowait_careful": 10.0,
     "cpu_iowait_critical": 12.5,
     "cpu_iowait_warning": 11.25,
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


.. _api:

API (Restfull/JSON) documentation
=================================

The Glances Restfull/API server could be ran using the following command line:

.. code-block:: bash

    # glances -w --disable-webui

Note: Change request URL api/3 by api/2 if you use Glances 2.x.

GET API status
--------------

This entry point should be used to check the API status.
It will return nothing but a 200 return code if everythin is OK.

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
     "core",
     "cpu",
     "diskio",
     "docker",
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
      "timer": 0.7136623859405518},
     {"count": 0,
      "countmax": 20.0,
      "countmin": None,
      "key": "name",
      "name": "Python",
      "refresh": 3.0,
      "regex": True,
      "result": None,
      "timer": 0.7135648727416992}]

Get a specific field::

    # curl http://localhost:61208/api/3/amps/name
    {"name": ["Dropbox", "Python", "Conntrack", "Nginx", "Systemd", "SystemV"]}

Get a specific item when field matchs the given value::

    # curl http://localhost:61208/api/3/amps/name/Dropbox
    {"Dropbox": [{"count": 0,
                  "countmax": None,
                  "countmin": 1.0,
                  "key": "name",
                  "name": "Dropbox",
                  "refresh": 3.0,
                  "regex": True,
                  "result": None,
                  "timer": 0.7136623859405518}]}

GET core
--------

Get plugin stats::

    # curl http://localhost:61208/api/3/core
    {"log": 4, "phys": 2}

Fields descriptions:

* **phys**: Number of physical cores (hyper thread CPUs are excluded) (unit is *number*)
* **log**: Number of logical CPUs. A logical CPU is the number of physical cores multiplied by the number of threads that can run on each core (unit is *number*)

Get a specific field::

    # curl http://localhost:61208/api/3/core/phys
    {"phys": 2}

GET cpu
-------

Get plugin stats::

    # curl http://localhost:61208/api/3/cpu
    {"cpucore": 4,
     "ctx_switches": 0,
     "guest": 0.0,
     "guest_nice": 0.0,
     "idle": 71.5,
     "interrupts": 0,
     "iowait": 0.3,
     "irq": 0.0,
     "nice": 0.0,
     "soft_interrupts": 0,
     "softirq": 0.0,
     "steal": 0.0,
     "syscalls": 0,
     "system": 3.5,
     "time_since_update": 1,
     "total": 28.9,
     "user": 24.7}

Fields descriptions:

* **total**: Sum of all CPU percentages (except idle) (unit is *percent*)
* **system**: percent time spent in kernel space. System CPU time is the time spent running code in the Operating System kernel (unit is *percent*)
* **user**: CPU percent time spent in user space. User CPU time is the time spent on the processor running your program's code (or code in libraries) (unit is *percent*)
* **iowait**: *(Linux)*: percent time spent by the CPU waiting for I/O operations to complete (unit is *percent*)
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
    {"total": 28.9}

GET diskio
----------

Get plugin stats::

    # curl http://localhost:61208/api/3/diskio
    [{"disk_name": "sda",
      "key": "disk_name",
      "read_bytes": 0,
      "read_count": 0,
      "time_since_update": 1,
      "write_bytes": 0,
      "write_count": 0},
     {"disk_name": "sda1",
      "key": "disk_name",
      "read_bytes": 0,
      "read_count": 0,
      "time_since_update": 1,
      "write_bytes": 0,
      "write_count": 0}]

Get a specific field::

    # curl http://localhost:61208/api/3/diskio/disk_name
    {"disk_name": ["sda", "sda1", "sda2", "sda5", "dm-0", "dm-1"]}

Get a specific item when field matchs the given value::

    # curl http://localhost:61208/api/3/diskio/disk_name/sda
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

    # curl http://localhost:61208/api/3/fs
    [{"device_name": "/dev/mapper/ubuntu--gnome--vg-root",
      "free": 94683729920,
      "fs_type": "ext4",
      "key": "mnt_point",
      "mnt_point": "/",
      "percent": 59.0,
      "size": 243334156288,
      "used": 136262971392}]

Get a specific field::

    # curl http://localhost:61208/api/3/fs/mnt_point
    {"mnt_point": ["/"]}

Get a specific item when field matchs the given value::

    # curl http://localhost:61208/api/3/fs/mnt_point//
    {"/": [{"device_name": "/dev/mapper/ubuntu--gnome--vg-root",
            "free": 94683729920,
            "fs_type": "ext4",
            "key": "mnt_point",
            "mnt_point": "/",
            "percent": 59.0,
            "size": 243334156288,
            "used": 136262971392}]}

GET ip
------

Get plugin stats::

    # curl http://localhost:61208/api/3/ip
    {"address": "192.168.0.32",
     "gateway": "192.168.0.254",
     "mask": "255.255.255.0",
     "mask_cidr": 24,
     "public_address": "91.166.228.228"}

Get a specific field::

    # curl http://localhost:61208/api/3/ip/address
    {"address": "192.168.0.32"}

GET load
--------

Get plugin stats::

    # curl http://localhost:61208/api/3/load
    {"cpucore": 4, "min1": 0.68408203125, "min15": 0.6572265625, "min5": 1.01953125}

Fields descriptions:

* **min1**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 1 minute (unit is *float*)
* **min5**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 5 minutes (unit is *float*)
* **min15**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 15 minutes (unit is *float*)
* **cpucore**: Total number of CPU core (unit is *number*)

Get a specific field::

    # curl http://localhost:61208/api/3/load/min1
    {"min1": 0.68408203125}

GET mem
-------

Get plugin stats::

    # curl http://localhost:61208/api/3/mem
    {"active": 1234366464,
     "available": 4835037184,
     "buffers": 281141248,
     "cached": 3177574400,
     "free": 4835037184,
     "inactive": 3743072256,
     "percent": 38.3,
     "shared": 335007744,
     "total": 7837962240,
     "used": 3002925056}

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
    {"total": 7837962240}

GET memswap
-----------

Get plugin stats::

    # curl http://localhost:61208/api/3/memswap
    {"free": 8082419712,
     "percent": 0.0,
     "sin": 0,
     "sout": 0,
     "time_since_update": 1,
     "total": 8082419712,
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
    {"total": 8082419712}

GET network
-----------

Get plugin stats::

    # curl http://localhost:61208/api/3/network
    [{"alias": None,
      "cumulative_cx": 1935164,
      "cumulative_rx": 967582,
      "cumulative_tx": 967582,
      "cx": 2492,
      "interface_name": "lo",
      "is_up": True,
      "key": "interface_name",
      "rx": 1246,
      "speed": 0,
      "time_since_update": 1,
      "tx": 1246},
     {"alias": None,
      "cumulative_cx": 18024325,
      "cumulative_rx": 15987954,
      "cumulative_tx": 2036371,
      "cx": 12836,
      "interface_name": "wlp2s0",
      "is_up": True,
      "key": "interface_name",
      "rx": 9587,
      "speed": 0,
      "time_since_update": 1,
      "tx": 3249}]

Fields descriptions:

* **interface_name**: Interface name (unit is *string*)
* **alias**: Interface alias name (optional) (unit is *string*)
* **rx**: The received/input rate (in bit per second) (unit is *bps*)
* **tx**: The sent/output rate (in bit per second) (unit is *bps*)
* **cumulative_rx**: The number of bytes received through the interface (cumulative) (unit is *bytes*)
* **cumulative_tx**: The number of bytes sent through the interface (cumulative) (unit is *bytes*)
* **speed**: Maximum interface speed (in bit per second). Can return 0 on some operating-system (unit is *bps*)
* **is_up**: Is the interface up ? (unit is *bool*)
* **time_since_update**: Number of seconds since last update (unit is *seconds*)

Get a specific field::

    # curl http://localhost:61208/api/3/network/interface_name
    {"interface_name": ["lo",
                        "wlp2s0",
                        "br-119e6ee04e05",
                        "br-87386b77b676",
                        "br_grafana",
                        "docker0",
                        "mpqemubr0"]}

Get a specific item when field matchs the given value::

    # curl http://localhost:61208/api/3/network/interface_name/lo
    {"lo": [{"alias": None,
             "cumulative_cx": 1935164,
             "cumulative_rx": 967582,
             "cumulative_tx": 967582,
             "cx": 2492,
             "interface_name": "lo",
             "is_up": True,
             "key": "interface_name",
             "rx": 1246,
             "speed": 0,
             "time_since_update": 1,
             "tx": 1246}]}

GET now
-------

Get plugin stats::

    # curl http://localhost:61208/api/3/now
    "2022-07-27 19:25:01 CEST"

GET percpu
----------

Get plugin stats::

    # curl http://localhost:61208/api/3/percpu
    [{"cpu_number": 0,
      "guest": 0.0,
      "guest_nice": 0.0,
      "idle": 58.0,
      "iowait": 0.0,
      "irq": 0.0,
      "key": "cpu_number",
      "nice": 0.0,
      "softirq": 0.0,
      "steal": 0.0,
      "system": 3.0,
      "total": 42.0,
      "user": 20.0},
     {"cpu_number": 1,
      "guest": 0.0,
      "guest_nice": 0.0,
      "idle": 40.0,
      "iowait": 0.0,
      "irq": 0.0,
      "key": "cpu_number",
      "nice": 0.0,
      "softirq": 0.0,
      "steal": 0.0,
      "system": 2.0,
      "total": 60.0,
      "user": 39.0}]

Get a specific field::

    # curl http://localhost:61208/api/3/percpu/cpu_number
    {"cpu_number": [0, 1, 2, 3]}

GET ports
---------

Get plugin stats::

    # curl http://localhost:61208/api/3/ports
    [{"description": "DefaultGateway",
      "host": "192.168.0.254",
      "indice": "port_0",
      "port": 0,
      "refresh": 30,
      "rtt_warning": None,
      "status": 0.005754,
      "timeout": 3}]

Get a specific field::

    # curl http://localhost:61208/api/3/ports/host
    {"host": ["192.168.0.254"]}

Get a specific item when field matchs the given value::

    # curl http://localhost:61208/api/3/ports/host/192.168.0.254
    {"192.168.0.254": [{"description": "DefaultGateway",
                        "host": "192.168.0.254",
                        "indice": "port_0",
                        "port": 0,
                        "refresh": 30,
                        "rtt_warning": None,
                        "status": 0.005754,
                        "timeout": 3}]}

GET processcount
----------------

Get plugin stats::

    # curl http://localhost:61208/api/3/processcount
    {"pid_max": 0, "running": 1, "sleeping": 211, "thread": 963, "total": 279}

Get a specific field::

    # curl http://localhost:61208/api/3/processcount/total
    {"total": 279}

GET processlist
---------------

Get plugin stats::

    # curl http://localhost:61208/api/3/processlist
    [{"cmdline": ["/snap/firefox/1551/usr/lib/firefox/firefox"],
      "cpu_percent": 0.0,
      "cpu_times": pcputimes(user=79.91, system=24.21, children_user=23.95, children_system=4.95, iowait=0.0),
      "gids": pgids(real=1000, effective=1000, saved=1000),
      "io_counters": [537029632, 195117056, 0, 0, 0],
      "key": "pid",
      "memory_info": pmem(rss=487780352, vms=3243282432, shared=183926784, text=630784, lib=0, data=555700224, dirty=0),
      "memory_percent": 6.2233057147261786,
      "name": "firefox",
      "nice": 0,
      "num_threads": 98,
      "pid": 3866,
      "status": "S",
      "time_since_update": 1,
      "username": "nicolargo"},
     {"cmdline": ["/snap/firefox/1551/usr/lib/firefox/firefox",
                  "-contentproc",
                  "-childID",
                  "1",
                  "-isForBrowser",
                  "-prefsLen",
                  "35771",
                  "-prefMapSize",
                  "226281",
                  "-jsInitLen",
                  "277276",
                  "-parentBuildID",
                  "20220707183149",
                  "-appDir",
                  "/snap/firefox/1551/usr/lib/firefox/browser",
                  "3866",
                  "true",
                  "tab"],
      "cpu_percent": 0.0,
      "cpu_times": pcputimes(user=24.14, system=3.64, children_user=0.0, children_system=0.0, iowait=0.0),
      "gids": pgids(real=1000, effective=1000, saved=1000),
      "io_counters": [3784704, 0, 0, 0, 0],
      "key": "pid",
      "memory_info": pmem(rss=356777984, vms=3025420288, shared=86458368, text=630784, lib=0, data=431472640, dirty=0),
      "memory_percent": 4.551922720158448,
      "name": "WebExtensions",
      "nice": 0,
      "num_threads": 20,
      "pid": 4232,
      "status": "S",
      "time_since_update": 1,
      "username": "nicolargo"}]

Get a specific field::

    # curl http://localhost:61208/api/3/processlist/pid
    {"pid": [3866,
             4232,
             4291,
             3558,
             3173,
             5251,
             4255,
             1952,
             3996,
             2029,
             6101,
             4007,
             3456,
             6902,
             6923,
             7753,
             1377,
             3084,
             2234,
             7854,
             2916,
             3288,
             1273,
             1446,
             3213,
             5463,
             1374,
             343,
             4105,
             3256,
             3319,
             2977,
             3369,
             3523,
             3370,
             4311,
             3364,
             3638,
             5576,
             2160,
             3247,
             2865,
             3378,
             1251,
             3368,
             1772,
             4033,
             1236,
             2195,
             3150,
             3365,
             1284,
             3064,
             3222,
             1955,
             1372,
             2868,
             3605,
             1432,
             3522,
             1077,
             1,
             3383,
             1369,
             3372,
             6775,
             3184,
             3375,
             1951,
             1285,
             2966,
             1257,
             2768,
             1429,
             2190,
             1312,
             1282,
             3422,
             3377,
             3272,
             1280,
             1742,
             1218,
             3309,
             2996,
             3376,
             2191,
             2991,
             389,
             3194,
             3174,
             1235,
             2974,
             3529,
             3366,
             1258,
             2975,
             3519,
             3570,
             3348,
             3615,
             3414,
             3207,
             2988,
             6122,
             1243,
             3227,
             1265,
             1276,
             3363,
             3373,
             1079,
             3374,
             3005,
             3199,
             3061,
             6177,
             1271,
             3265,
             1286,
             3245,
             3181,
             1231,
             2967,
             3139,
             1227,
             1588,
             1076,
             1245,
             3804,
             1234,
             1290,
             3632,
             1089,
             7844,
             1088,
             1974,
             3047,
             1229,
             4224,
             1219,
             7853,
             1976,
             3360,
             1294,
             1978,
             2021,
             1962,
             2,
             3,
             4,
             5,
             7,
             10,
             11,
             12,
             13,
             14,
             15,
             16,
             17,
             18,
             19,
             20,
             21,
             23,
             24,
             25,
             26,
             27,
             29,
             30,
             31,
             32,
             33,
             35,
             36,
             37,
             38,
             39,
             40,
             41,
             42,
             43,
             44,
             49,
             91,
             92,
             93,
             94,
             95,
             96,
             97,
             98,
             99,
             100,
             102,
             104,
             105,
             107,
             109,
             110,
             112,
             113,
             117,
             118,
             119,
             121,
             129,
             132,
             133,
             138,
             187,
             188,
             195,
             196,
             197,
             198,
             199,
             200,
             201,
             202,
             203,
             209,
             210,
             215,
             217,
             234,
             282,
             283,
             363,
             364,
             374,
             390,
             465,
             498,
             534,
             565,
             569,
             576,
             577,
             578,
             723,
             741,
             800,
             801,
             802,
             803,
             808,
             809,
             810,
             811,
             812,
             813,
             814,
             815,
             1006,
             1569,
             2006,
             2048,
             2072,
             2127,
             2128,
             2131,
             2132,
             2133,
             2134,
             2136,
             2138,
             2216,
             2217,
             3244,
             6481,
             6614,
             6629,
             6634,
             6653,
             6715,
             6974]}

Get a specific item when field matchs the given value::

    # curl http://localhost:61208/api/3/processlist/pid/3866
    {"3866": [{"cmdline": ["/snap/firefox/1551/usr/lib/firefox/firefox"],
               "cpu_percent": 0.0,
               "cpu_times": [79.91, 24.21, 23.95, 4.95, 0.0],
               "gids": [1000, 1000, 1000],
               "io_counters": [537029632, 195117056, 0, 0, 0],
               "key": "pid",
               "memory_info": [487780352,
                               3243282432,
                               183926784,
                               630784,
                               0,
                               555700224,
                               0],
               "memory_percent": 6.2233057147261786,
               "name": "firefox",
               "nice": 0,
               "num_threads": 98,
               "pid": 3866,
               "status": "S",
               "time_since_update": 1,
               "username": "nicolargo"}]}

GET psutilversion
-----------------

Get plugin stats::

    # curl http://localhost:61208/api/3/psutilversion
    (5, 9, 1)

GET quicklook
-------------

Get plugin stats::

    # curl http://localhost:61208/api/3/quicklook
    {"cpu": 28.9,
     "cpu_hz": 3000000000.0,
     "cpu_hz_current": 1588220000.0,
     "cpu_name": "Intel(R) Core(TM) i7-4500U CPU @ 1.80GHz",
     "mem": 38.3,
     "percpu": [{"cpu_number": 0,
                 "guest": 0.0,
                 "guest_nice": 0.0,
                 "idle": 58.0,
                 "iowait": 0.0,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 0.0,
                 "steal": 0.0,
                 "system": 3.0,
                 "total": 42.0,
                 "user": 20.0},
                {"cpu_number": 1,
                 "guest": 0.0,
                 "guest_nice": 0.0,
                 "idle": 40.0,
                 "iowait": 0.0,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 0.0,
                 "steal": 0.0,
                 "system": 2.0,
                 "total": 60.0,
                 "user": 39.0},
                {"cpu_number": 2,
                 "guest": 0.0,
                 "guest_nice": 0.0,
                 "idle": 58.0,
                 "iowait": 1.0,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 0.0,
                 "steal": 0.0,
                 "system": 2.0,
                 "total": 42.0,
                 "user": 20.0},
                {"cpu_number": 3,
                 "guest": 0.0,
                 "guest_nice": 0.0,
                 "idle": 73.0,
                 "iowait": 0.0,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 0.0,
                 "steal": 0.0,
                 "system": 2.0,
                 "total": 27.0,
                 "user": 6.0}],
     "swap": 0.0}

Get a specific field::

    # curl http://localhost:61208/api/3/quicklook/cpu
    {"cpu": 28.9}

GET sensors
-----------

Get plugin stats::

    # curl http://localhost:61208/api/3/sensors
    [{"critical": 105,
      "key": "label",
      "label": "acpitz 1",
      "type": "temperature_core",
      "unit": "C",
      "value": 27,
      "warning": 105},
     {"critical": 105,
      "key": "label",
      "label": "acpitz 2",
      "type": "temperature_core",
      "unit": "C",
      "value": 29,
      "warning": 105}]

Get a specific field::

    # curl http://localhost:61208/api/3/sensors/label
    {"label": ["acpitz 1",
               "acpitz 2",
               "Package id 0",
               "Core 0",
               "Core 1",
               "CPU",
               "Ambient",
               "SODIMM",
               "BAT BAT0"]}

Get a specific item when field matchs the given value::

    # curl http://localhost:61208/api/3/sensors/label/acpitz 1
    {"acpitz 1": [{"critical": 105,
                   "key": "label",
                   "label": "acpitz 1",
                   "type": "temperature_core",
                   "unit": "C",
                   "value": 27,
                   "warning": 105}]}

GET system
----------

Get plugin stats::

    # curl http://localhost:61208/api/3/system
    {"hostname": "XPS13-9333",
     "hr_name": "Ubuntu 22.04 64bit",
     "linux_distro": "Ubuntu 22.04",
     "os_name": "Linux",
     "os_version": "5.15.0-41-generic",
     "platform": "64bit"}

Get a specific field::

    # curl http://localhost:61208/api/3/system/os_name
    {"os_name": "Linux"}

GET uptime
----------

Get plugin stats::

    # curl http://localhost:61208/api/3/uptime
    {"seconds": 469}

GET all stats
-------------

Get all Glances stats::

    # curl http://localhost:61208/api/3/all
    Return a very big dictionnary (avoid using this request, performances will be poor)...

GET stats history
-----------------

History of a plugin::

    # curl http://localhost:61208/api/3/cpu/history
    {"system": [["2022-07-27T19:25:01.821257", 3.5],
                ["2022-07-27T19:25:02.853268", 3.5],
                ["2022-07-27T19:25:03.921269", 0.5]],
     "user": [["2022-07-27T19:25:01.821251", 24.7],
              ["2022-07-27T19:25:02.853264", 24.7],
              ["2022-07-27T19:25:03.921265", 1.9]]}

Limit history to last 2 values::

    # curl http://localhost:61208/api/3/cpu/history/2
    {"system": [["2022-07-27T19:25:02.853268", 3.5],
                ["2022-07-27T19:25:03.921269", 0.5]],
     "user": [["2022-07-27T19:25:02.853264", 24.7],
              ["2022-07-27T19:25:03.921265", 1.9]]}

History for a specific field::

    # curl http://localhost:61208/api/3/cpu/system/history
    {"system": [["2022-07-27T19:25:01.821257", 3.5],
                ["2022-07-27T19:25:02.853268", 3.5],
                ["2022-07-27T19:25:03.921269", 0.5]]}

Limit history for a specific field to last 2 values::

    # curl http://localhost:61208/api/3/cpu/system/history
    {"system": [["2022-07-27T19:25:02.853268", 3.5],
                ["2022-07-27T19:25:03.921269", 0.5]]}

GET limits (used for thresholds)
--------------------------------

All limits/thresholds::

    # curl http://localhost:61208/api/3/all/limits
    {"alert": {"history_size": 3600.0},
     "amps": {"amps_disable": ["False"], "history_size": 3600.0},
     "cloud": {"history_size": 3600.0},
     "connections": {"connections_disable": ["True"],
                     "connections_nf_conntrack_percent_careful": 70.0,
                     "connections_nf_conntrack_percent_critical": 90.0,
                     "connections_nf_conntrack_percent_warning": 80.0,
                     "history_size": 3600.0},
     "core": {"history_size": 3600.0},
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
             "history_size": 3600.0},
     "diskio": {"diskio_disable": ["False"],
                "diskio_hide": ["loop.*", "/dev/loop*"],
                "history_size": 3600.0},
     "docker": {"docker_all": ["False"],
                "docker_disable": ["False"],
                "docker_max_name_size": 20.0,
                "history_size": 3600.0},
     "folders": {"folders_disable": ["False"], "history_size": 3600.0},
     "fs": {"fs_careful": 50.0,
            "fs_critical": 90.0,
            "fs_disable": ["False"],
            "fs_hide": ["/boot.*", "/snap.*"],
            "fs_warning": 70.0,
            "history_size": 3600.0},
     "gpu": {"gpu_disable": ["False"],
             "gpu_mem_careful": 50.0,
             "gpu_mem_critical": 90.0,
             "gpu_mem_warning": 70.0,
             "gpu_proc_careful": 50.0,
             "gpu_proc_critical": 90.0,
             "gpu_proc_warning": 70.0,
             "history_size": 3600.0},
     "help": {"history_size": 3600.0},
     "ip": {"history_size": 3600.0, "ip_disable": ["False"]},
     "irq": {"history_size": 3600.0, "irq_disable": ["True"]},
     "load": {"history_size": 3600.0,
              "load_careful": 0.7,
              "load_critical": 5.0,
              "load_disable": ["False"],
              "load_warning": 1.0},
     "mem": {"history_size": 3600.0,
             "mem_careful": 50.0,
             "mem_critical": 90.0,
             "mem_disable": ["False"],
             "mem_warning": 70.0},
     "memswap": {"history_size": 3600.0,
                 "memswap_careful": 50.0,
                 "memswap_critical": 90.0,
                 "memswap_disable": ["False"],
                 "memswap_warning": 70.0},
     "network": {"history_size": 3600.0,
                 "network_disable": ["False"],
                 "network_rx_careful": 70.0,
                 "network_rx_critical": 90.0,
                 "network_rx_warning": 80.0,
                 "network_tx_careful": 70.0,
                 "network_tx_critical": 90.0,
                 "network_tx_warning": 80.0},
     "now": {"history_size": 3600.0},
     "percpu": {"history_size": 3600.0,
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
     "ports": {"history_size": 3600.0,
               "ports_disable": ["False"],
               "ports_port_default_gateway": ["True"],
               "ports_refresh": 30.0,
               "ports_timeout": 3.0},
     "processcount": {"history_size": 3600.0, "processcount_disable": ["False"]},
     "processlist": {"history_size": 3600.0,
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
     "psutilversion": {"history_size": 3600.0},
     "quicklook": {"history_size": 3600.0,
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
     "raid": {"history_size": 3600.0, "raid_disable": ["True"]},
     "sensors": {"history_size": 3600.0,
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
     "smart": {"history_size": 3600.0, "smart_disable": ["True"]},
     "system": {"history_size": 3600.0,
                "system_disable": ["False"],
                "system_refresh": 60},
     "uptime": {"history_size": 3600.0},
     "wifi": {"history_size": 3600.0,
              "wifi_careful": -65.0,
              "wifi_critical": -85.0,
              "wifi_disable": ["True"],
              "wifi_hide": ["lo", "docker.*"],
              "wifi_warning": -75.0}}

Limits/thresholds for the cpu plugin::

    # curl http://localhost:61208/api/3/cpu/limits
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
     "history_size": 3600.0}


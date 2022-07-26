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
      "timer": 0.8538804054260254},
     {"count": 0,
      "countmax": 20.0,
      "countmin": None,
      "key": "name",
      "name": "Python",
      "refresh": 3.0,
      "regex": True,
      "result": None,
      "timer": 0.8537874221801758}]

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
                  "timer": 0.8538804054260254}]}

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
     "idle": 73.3,
     "interrupts": 0,
     "iowait": 0.0,
     "irq": 0.0,
     "nice": 0.0,
     "soft_interrupts": 0,
     "softirq": 0.0,
     "steal": 0.0,
     "syscalls": 0,
     "system": 3.0,
     "time_since_update": 1,
     "total": 27.2,
     "user": 23.7}

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
    {"total": 27.2}

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
      "free": 110062321664,
      "fs_type": "ext4",
      "key": "mnt_point",
      "mnt_point": "/",
      "percent": 52.4,
      "size": 243396149248,
      "used": 120946372608}]

Get a specific field::

    # curl http://localhost:61208/api/3/fs/mnt_point
    {"mnt_point": ["/"]}

Get a specific item when field matchs the given value::

    # curl http://localhost:61208/api/3/fs/mnt_point//
    {"/": [{"device_name": "/dev/mapper/ubuntu--gnome--vg-root",
            "free": 110062321664,
            "fs_type": "ext4",
            "key": "mnt_point",
            "mnt_point": "/",
            "percent": 52.4,
            "size": 243396149248,
            "used": 120946372608}]}

GET ip
------

Get plugin stats::

    # curl http://localhost:61208/api/3/ip
    {"address": "192.168.0.48",
     "gateway": "192.168.0.254",
     "mask": "255.255.255.0",
     "mask_cidr": 24,
     "public_address": "82.66.169.82"}

Get a specific field::

    # curl http://localhost:61208/api/3/ip/address
    {"address": "192.168.0.48"}

GET load
--------

Get plugin stats::

    # curl http://localhost:61208/api/3/load
    {"cpucore": 4, "min1": 1.40771484375, "min15": 1.4169921875, "min5": 1.484375}

Fields descriptions:

* **min1**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 1 minute (unit is *float*)
* **min5**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 5 minutes (unit is *float*)
* **min15**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 15 minutes (unit is *float*)
* **cpucore**: Total number of CPU core (unit is *number*)

Get a specific field::

    # curl http://localhost:61208/api/3/load/min1
    {"min1": 1.40771484375}

GET mem
-------

Get plugin stats::

    # curl http://localhost:61208/api/3/mem
    {"active": 2461896704,
     "available": 3079487488,
     "buffers": 486854656,
     "cached": 3247910912,
     "free": 3079487488,
     "inactive": 4266680320,
     "percent": 60.7,
     "shared": 539095040,
     "total": 7837974528,
     "used": 4758487040}

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
    {"total": 7837974528}

GET memswap
-----------

Get plugin stats::

    # curl http://localhost:61208/api/3/memswap
    {"free": 7600726016,
     "percent": 6.0,
     "sin": 48836608,
     "sout": 519880704,
     "time_since_update": 1,
     "total": 8082419712,
     "used": 481693696}

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
      "cumulative_cx": 47984606,
      "cumulative_rx": 23992303,
      "cumulative_tx": 23992303,
      "cx": 2492,
      "interface_name": "lo",
      "is_up": True,
      "key": "interface_name",
      "rx": 1246,
      "speed": 0,
      "time_since_update": 1,
      "tx": 1246},
     {"alias": None,
      "cumulative_cx": 1734453000,
      "cumulative_rx": 1610954683,
      "cumulative_tx": 123498317,
      "cx": 31305,
      "interface_name": "wlp2s0",
      "is_up": True,
      "key": "interface_name",
      "rx": 25086,
      "speed": 0,
      "time_since_update": 1,
      "tx": 6219}]

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
                        "docker0",
                        "br-87386b77b676",
                        "br_grafana",
                        "mpqemubr0"]}

Get a specific item when field matchs the given value::

    # curl http://localhost:61208/api/3/network/interface_name/lo
    {"lo": [{"alias": None,
             "cumulative_cx": 47984606,
             "cumulative_rx": 23992303,
             "cumulative_tx": 23992303,
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
    "2022-07-24 10:33:51 CEST"

GET percpu
----------

Get plugin stats::

    # curl http://localhost:61208/api/3/percpu
    [{"cpu_number": 0,
      "guest": 0.0,
      "guest_nice": 0.0,
      "idle": 90.0,
      "iowait": 0.0,
      "irq": 0.0,
      "key": "cpu_number",
      "nice": 0.0,
      "softirq": 1.0,
      "steal": 0.0,
      "system": 0.0,
      "total": 10.0,
      "user": 4.0},
     {"cpu_number": 1,
      "guest": 0.0,
      "guest_nice": 0.0,
      "idle": 90.0,
      "iowait": 0.0,
      "irq": 0.0,
      "key": "cpu_number",
      "nice": 0.0,
      "softirq": 1.0,
      "steal": 0.0,
      "system": 3.0,
      "total": 10.0,
      "user": 3.0}]

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
      "status": 0.003645,
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
                        "status": 0.003645,
                        "timeout": 3}]}

GET processcount
----------------

Get plugin stats::

    # curl http://localhost:61208/api/3/processcount
    {"pid_max": 0, "running": 1, "sleeping": 233, "thread": 1256, "total": 299}

Get a specific field::

    # curl http://localhost:61208/api/3/processcount/total
    {"total": 299}

GET processlist
---------------

Get plugin stats::

    # curl http://localhost:61208/api/3/processlist
    [{"cmdline": ["/snap/firefox/1443/usr/lib/firefox/firefox"],
      "cpu_percent": 0.0,
      "cpu_times": pcputimes(user=2687.47, system=1037.45, children_user=2125.3, children_system=344.64, iowait=0.0),
      "gids": pgids(real=1000, effective=1000, saved=1000),
      "io_counters": [982852608, 2811539456, 0, 0, 0],
      "key": "pid",
      "memory_info": pmem(rss=521953280, vms=13237006336, shared=174477312, text=741376, lib=0, data=1154760704, dirty=0),
      "memory_percent": 6.659287780732119,
      "name": "firefox",
      "nice": 0,
      "num_threads": 164,
      "pid": 4236,
      "status": "S",
      "time_since_update": 1,
      "username": "nicolargo"},
     {"cmdline": ["/snap/firefox/1443/usr/lib/firefox/firefox",
                  "-contentproc",
                  "-childID",
                  "3",
                  "-isForBrowser",
                  "-prefsLen",
                  "13098",
                  "-prefMapSize",
                  "255747",
                  "-jsInitLen",
                  "277128",
                  "-parentBuildID",
                  "20220609070438",
                  "-appDir",
                  "/snap/firefox/1443/usr/lib/firefox/browser",
                  "4236",
                  "true",
                  "tab"],
      "cpu_percent": 0.0,
      "cpu_times": pcputimes(user=421.23, system=83.44, children_user=0.0, children_system=0.0, iowait=0.0),
      "gids": pgids(real=1000, effective=1000, saved=1000),
      "io_counters": [11130880, 0, 0, 0, 0],
      "key": "pid",
      "memory_info": pmem(rss=459653120, vms=3240546304, shared=89395200, text=741376, lib=0, data=649822208, dirty=0),
      "memory_percent": 5.864437532400207,
      "name": "WebExtensions",
      "nice": 0,
      "num_threads": 20,
      "pid": 5262,
      "status": "S",
      "time_since_update": 1,
      "username": "nicolargo"}]

Get a specific field::

    # curl http://localhost:61208/api/3/processlist/pid
    {"pid": [4236,
             5262,
             9730,
             9861,
             4450,
             9695,
             3561,
             42242,
             52578,
             75296,
             50530,
             73809,
             76244,
             4417,
             9729,
             9628,
             5492,
             4088,
             76136,
             76002,
             76285,
             9663,
             1980,
             2040,
             76402,
             9796,
             3457,
             2243,
             9761,
             3870,
             9955,
             41978,
             3680,
             73036,
             4095,
             5779,
             1284,
             41980,
             3962,
             1450,
             4391,
             3651,
             3370,
             1433,
             9682,
             3768,
             3844,
             3690,
             3759,
             3766,
             4465,
             347,
             5870,
             58878,
             4126,
             50975,
             1246,
             1264,
             3782,
             58882,
             3765,
             3607,
             1784,
             3643,
             9632,
             3538,
             3033,
             1,
             1293,
             58865,
             51015,
             9633,
             1093,
             1449,
             3761,
             3456,
             3938,
             3767,
             3880,
             1271,
             3359,
             1295,
             1400,
             3774,
             51035,
             3616,
             3586,
             3234,
             3769,
             58880,
             3661,
             36696,
             1290,
             1454,
             3779,
             1754,
             36676,
             3846,
             3028,
             3706,
             3592,
             1289,
             1228,
             3386,
             3382,
             58881,
             3950,
             3559,
             3923,
             3763,
             1272,
             3775,
             3753,
             393,
             3837,
             3853,
             1253,
             1101,
             3843,
             54916,
             3603,
             1245,
             1286,
             3770,
             3658,
             3623,
             3597,
             3771,
             3379,
             3758,
             3451,
             3391,
             1282,
             9827,
             1281,
             1241,
             3526,
             5562,
             3367,
             9854,
             3640,
             3368,
             3568,
             1237,
             1259,
             42042,
             3360,
             1086,
             1244,
             1596,
             76386,
             1139,
             1300,
             73241,
             9648,
             1135,
             1996,
             3959,
             1240,
             4203,
             3433,
             1229,
             2006,
             76401,
             3757,
             1307,
             2049,
             2038,
             2036,
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
             91,
             92,
             93,
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
             110,
             111,
             116,
             117,
             118,
             128,
             131,
             137,
             160,
             187,
             190,
             196,
             197,
             198,
             199,
             200,
             201,
             202,
             203,
             210,
             211,
             216,
             217,
             234,
             287,
             288,
             362,
             363,
             385,
             463,
             499,
             565,
             567,
             568,
             569,
             788,
             789,
             790,
             791,
             792,
             793,
             794,
             795,
             796,
             797,
             798,
             799,
             2051,
             2057,
             2071,
             2150,
             2151,
             2152,
             2153,
             2154,
             2155,
             2156,
             2157,
             3617,
             9635,
             40332,
             43168,
             50836,
             68803,
             69770,
             69963,
             72076,
             72077,
             72167,
             72180,
             74547,
             74770,
             74850,
             75055,
             75272,
             75639,
             75640,
             75991,
             76173,
             76385]}

Get a specific item when field matchs the given value::

    # curl http://localhost:61208/api/3/processlist/pid/4236
    {"4236": [{"cmdline": ["/snap/firefox/1443/usr/lib/firefox/firefox"],
               "cpu_percent": 0.0,
               "cpu_times": [2687.47, 1037.45, 2125.3, 344.64, 0.0],
               "gids": [1000, 1000, 1000],
               "io_counters": [982852608, 2811539456, 0, 0, 0],
               "key": "pid",
               "memory_info": [521953280,
                               13237006336,
                               174477312,
                               741376,
                               0,
                               1154760704,
                               0],
               "memory_percent": 6.659287780732119,
               "name": "firefox",
               "nice": 0,
               "num_threads": 164,
               "pid": 4236,
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
    {"cpu": 27.2,
     "cpu_hz": 3000000000.0,
     "cpu_hz_current": 1605066500.0,
     "cpu_name": "Intel(R) Core(TM) i7-4500U CPU @ 1.80GHz",
     "mem": 60.7,
     "percpu": [{"cpu_number": 0,
                 "guest": 0.0,
                 "guest_nice": 0.0,
                 "idle": 90.0,
                 "iowait": 0.0,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 1.0,
                 "steal": 0.0,
                 "system": 0.0,
                 "total": 10.0,
                 "user": 4.0},
                {"cpu_number": 1,
                 "guest": 0.0,
                 "guest_nice": 0.0,
                 "idle": 90.0,
                 "iowait": 0.0,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 1.0,
                 "steal": 0.0,
                 "system": 3.0,
                 "total": 10.0,
                 "user": 3.0},
                {"cpu_number": 2,
                 "guest": 0.0,
                 "guest_nice": 0.0,
                 "idle": 31.0,
                 "iowait": 0.0,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 0.0,
                 "steal": 0.0,
                 "system": 1.0,
                 "total": 69.0,
                 "user": 63.0},
                {"cpu_number": 3,
                 "guest": 0.0,
                 "guest_nice": 0.0,
                 "idle": 65.0,
                 "iowait": 0.0,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 0.0,
                 "steal": 0.0,
                 "system": 3.0,
                 "total": 35.0,
                 "user": 26.0}],
     "swap": 6.0}

Get a specific field::

    # curl http://localhost:61208/api/3/quicklook/cpu
    {"cpu": 27.2}

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
     "os_version": "5.15.0-40-generic",
     "platform": "64bit"}

Get a specific field::

    # curl http://localhost:61208/api/3/system/os_name
    {"os_name": "Linux"}

GET uptime
----------

Get plugin stats::

    # curl http://localhost:61208/api/3/uptime
    {"seconds": 692162}

GET all stats
-------------

Get all Glances stats::

    # curl http://localhost:61208/api/3/all
    Return a very big dictionnary (avoid using this request, performances will be poor)...

GET stats history
-----------------

History of a plugin::

    # curl http://localhost:61208/api/3/cpu/history
    {"system": [["2022-07-24T10:33:52.103080", 3.0],
                ["2022-07-24T10:33:53.131720", 3.0],
                ["2022-07-24T10:33:54.206957", 0.6]],
     "user": [["2022-07-24T10:33:52.103074", 23.7],
              ["2022-07-24T10:33:53.131716", 23.7],
              ["2022-07-24T10:33:54.206953", 1.8]]}

Limit history to last 2 values::

    # curl http://localhost:61208/api/3/cpu/history/2
    {"system": [["2022-07-24T10:33:53.131720", 3.0],
                ["2022-07-24T10:33:54.206957", 0.6]],
     "user": [["2022-07-24T10:33:53.131716", 23.7],
              ["2022-07-24T10:33:54.206953", 1.8]]}

History for a specific field::

    # curl http://localhost:61208/api/3/cpu/system/history
    {"system": [["2022-07-24T10:33:52.103080", 3.0],
                ["2022-07-24T10:33:53.131720", 3.0],
                ["2022-07-24T10:33:54.206957", 0.6]]}

Limit history for a specific field to last 2 values::

    # curl http://localhost:61208/api/3/cpu/system/history
    {"system": [["2022-07-24T10:33:53.131720", 3.0],
                ["2022-07-24T10:33:54.206957", 0.6]]}

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


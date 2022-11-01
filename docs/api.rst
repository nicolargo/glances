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
      "timer": 0.8049194812774658},
     {"count": 0,
      "countmax": 20.0,
      "countmin": None,
      "key": "name",
      "name": "Python",
      "refresh": 3.0,
      "regex": True,
      "result": None,
      "timer": 0.8047523498535156}]

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
                  "timer": 0.8049194812774658}]}

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
     "iowait": 0.0,
     "irq": 0.0,
     "nice": 0.2,
     "soft_interrupts": 0,
     "softirq": 0.0,
     "steal": 0.0,
     "syscalls": 0,
     "system": 3.6,
     "time_since_update": 1,
     "total": 28.5,
     "user": 24.7}

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
    {"total": 28.5}

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

GET docker
----------

Get plugin stats::

    # curl http://localhost:61208/api/3/docker
    [{"Command": ["/portainer"],
      "Id": "3abd51c615968482d9ccff5afc629f267f6dda113ed68b75b432615fae3b49fb",
      "Image": ["portainer/portainer-ce:2.9.3"],
      "Status": "running",
      "Uptime": "yesterday",
      "cpu_percent": 0.0,
      "io_r": None,
      "io_w": None,
      "key": "name",
      "memory_usage": None,
      "name": "portainer",
      "network_rx": None,
      "network_tx": None}]

GET fs
------

Get plugin stats::

    # curl http://localhost:61208/api/3/fs
    [{"device_name": "/dev/mapper/ubuntu--gnome--vg-root",
      "free": 69936623616,
      "fs_type": "ext4",
      "key": "mnt_point",
      "mnt_point": "/",
      "percent": 69.7,
      "size": 243334156288,
      "used": 161010077696},
     {"device_name": "zsfpool",
      "free": 41811968,
      "fs_type": "zfs",
      "key": "mnt_point",
      "mnt_point": "/zsfpool",
      "percent": 0.3,
      "size": 41943040,
      "used": 131072}]

Get a specific field::

    # curl http://localhost:61208/api/3/fs/mnt_point
    {"mnt_point": ["/", "/zsfpool", "/var/snap/firefox/common/host-hunspell"]}

Get a specific item when field matchs the given value::

    # curl http://localhost:61208/api/3/fs/mnt_point//
    {"/": [{"device_name": "/dev/mapper/ubuntu--gnome--vg-root",
            "free": 69936623616,
            "fs_type": "ext4",
            "key": "mnt_point",
            "mnt_point": "/",
            "percent": 69.7,
            "size": 243334156288,
            "used": 161010077696}]}

GET ip
------

Get plugin stats::

    # curl http://localhost:61208/api/3/ip
    {"address": "192.168.0.48",
     "gateway": "192.168.0.254",
     "mask": "255.255.255.0",
     "mask_cidr": 24,
     "public_address": "82.66.169.82",
     "public_info_human": ""}

Get a specific field::

    # curl http://localhost:61208/api/3/ip/gateway
    {"gateway": "192.168.0.254"}

GET load
--------

Get plugin stats::

    # curl http://localhost:61208/api/3/load
    {"cpucore": 4,
     "min1": 1.66650390625,
     "min15": 1.404296875,
     "min5": 1.32861328125}

Fields descriptions:

* **min1**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 1 minute (unit is *float*)
* **min5**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 5 minutes (unit is *float*)
* **min15**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 15 minutes (unit is *float*)
* **cpucore**: Total number of CPU core (unit is *number*)

Get a specific field::

    # curl http://localhost:61208/api/3/load/min1
    {"min1": 1.66650390625}

GET mem
-------

Get plugin stats::

    # curl http://localhost:61208/api/3/mem
    {"active": 2758340608,
     "available": 2541457408,
     "buffers": 327168000,
     "cached": 2312929280,
     "free": 2541457408,
     "inactive": 3173421056,
     "percent": 67.6,
     "shared": 602021888,
     "total": 7836188672,
     "used": 5294731264}

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
    {"total": 7836188672}

GET memswap
-----------

Get plugin stats::

    # curl http://localhost:61208/api/3/memswap
    {"free": 5597716480,
     "percent": 30.7,
     "sin": 1817985024,
     "sout": 6456958976,
     "time_since_update": 1,
     "total": 8082419712,
     "used": 2484703232}

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
      "cumulative_cx": 388087006,
      "cumulative_rx": 194043503,
      "cumulative_tx": 194043503,
      "cx": 5460,
      "interface_name": "lo",
      "is_up": True,
      "key": "interface_name",
      "rx": 2730,
      "speed": 0,
      "time_since_update": 1,
      "tx": 2730},
     {"alias": None,
      "cumulative_cx": 8754220828,
      "cumulative_rx": 8224522821,
      "cumulative_tx": 529698007,
      "cx": 29194,
      "interface_name": "wlp2s0",
      "is_up": True,
      "key": "interface_name",
      "rx": 22571,
      "speed": 0,
      "time_since_update": 1,
      "tx": 6623}]

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
                        "br-87386b77b676",
                        "br_grafana",
                        "br-119e6ee04e05",
                        "docker0",
                        "mpqemubr0",
                        "vethfb650c2"]}

Get a specific item when field matchs the given value::

    # curl http://localhost:61208/api/3/network/interface_name/lo
    {"lo": [{"alias": None,
             "cumulative_cx": 388087006,
             "cumulative_rx": 194043503,
             "cumulative_tx": 194043503,
             "cx": 5460,
             "interface_name": "lo",
             "is_up": True,
             "key": "interface_name",
             "rx": 2730,
             "speed": 0,
             "time_since_update": 1,
             "tx": 2730}]}

GET now
-------

Get plugin stats::

    # curl http://localhost:61208/api/3/now
    "2022-11-01 10:08:06 CET"

GET percpu
----------

Get plugin stats::

    # curl http://localhost:61208/api/3/percpu
    [{"cpu_number": 0,
      "guest": 0.0,
      "guest_nice": 0.0,
      "idle": 71.0,
      "iowait": 0.0,
      "irq": 0.0,
      "key": "cpu_number",
      "nice": 0.0,
      "softirq": 0.0,
      "steal": 0.0,
      "system": 3.0,
      "total": 29.0,
      "user": 23.0},
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
      "system": 4.0,
      "total": 68.0,
      "user": 61.0}]

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
      "status": 0.005366,
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
                        "status": 0.005366,
                        "timeout": 3}]}

GET processcount
----------------

Get plugin stats::

    # curl http://localhost:61208/api/3/processcount
    {"pid_max": 0, "running": 1, "sleeping": 310, "thread": 1507, "total": 376}

Get a specific field::

    # curl http://localhost:61208/api/3/processcount/total
    {"total": 376}

GET processlist
---------------

Get plugin stats::

    # curl http://localhost:61208/api/3/processlist
    [{"cmdline": ["/snap/firefox/1943/usr/lib/firefox/firefox"],
      "cpu_percent": 0.0,
      "cpu_times": pcputimes(user=6291.33, system=2169.99, children_user=5908.96, children_system=1090.39, iowait=0.0),
      "gids": pgids(real=1000, effective=1000, saved=1000),
      "io_counters": [3058916352, 7061786624, 0, 0, 0],
      "key": "pid",
      "memory_info": pmem(rss=474968064, vms=12959444992, shared=143884288, text=634880, lib=0, data=1040416768, dirty=0),
      "memory_percent": 6.061212712975372,
      "name": "firefox",
      "nice": 0,
      "num_threads": 131,
      "pid": 252940,
      "status": "S",
      "time_since_update": 1,
      "username": "nicolargo"},
     {"cmdline": ["/snap/firefox/1943/usr/lib/firefox/firefox",
                  "-contentproc",
                  "-childID",
                  "1",
                  "-isForBrowser",
                  "-prefsLen",
                  "30965",
                  "-prefMapSize",
                  "235589",
                  "-jsInitLen",
                  "246848",
                  "-parentBuildID",
                  "20221007191409",
                  "-appDir",
                  "/snap/firefox/1943/usr/lib/firefox/browser",
                  "{9845d5f8-7cf9-4af9-9d46-4d914b28196f}",
                  "252940",
                  "true",
                  "tab"],
      "cpu_percent": 0.0,
      "cpu_times": pcputimes(user=979.64, system=187.79, children_user=0.0, children_system=0.0, iowait=0.0),
      "gids": pgids(real=1000, effective=1000, saved=1000),
      "io_counters": [70661120, 0, 0, 0, 0],
      "key": "pid",
      "memory_info": pmem(rss=458870784, vms=3349360640, shared=73793536, text=634880, lib=0, data=762740736, dirty=0),
      "memory_percent": 5.8557904002442065,
      "name": "WebExtensions",
      "nice": 0,
      "num_threads": 20,
      "pid": 253132,
      "status": "S",
      "time_since_update": 1,
      "username": "nicolargo"}]

Get a specific field::

    # curl http://localhost:61208/api/3/processlist/pid
    {"pid": [252940,
             253132,
             479037,
             3549,
             253182,
             479255,
             515816,
             479104,
             521756,
             253186,
             17347,
             521697,
             426999,
             5818,
             482393,
             521757,
             521696,
             478972,
             253147,
             521726,
             479089,
             51440,
             480067,
             495478,
             479007,
             528079,
             527719,
             527880,
             479161,
             4055,
             479296,
             3499,
             2245,
             528204,
             450641,
             479112,
             3958,
             479015,
             253654,
             253071,
             255947,
             510486,
             17308,
             478976,
             3844,
             450239,
             2429,
             17501,
             4977,
             478977,
             3651,
             449090,
             516430,
             17346,
             19717,
             4062,
             3364,
             3743,
             17373,
             3744,
             3737,
             450957,
             107498,
             516464,
             1369,
             3806,
             3760,
             3627,
             1391,
             3742,
             1,
             4087,
             2917,
             492260,
             3929,
             516528,
             107499,
             17755,
             17754,
             1587,
             17566,
             1415,
             109608,
             3663,
             3345,
             3528,
             1945,
             3618,
             1381,
             3736,
             2371,
             3592,
             3557,
             3353,
             1416,
             2412,
             3750,
             2187,
             1593,
             3745,
             3637,
             17292,
             1368,
             3739,
             1352,
             3891,
             1487,
             480091,
             3817,
             523017,
             479311,
             3378,
             15018,
             483374,
             51420,
             1917,
             17237,
             14997,
             3697,
             3588,
             3599,
             16698,
             1408,
             3380,
             3943,
             54676,
             3799,
             1615,
             1392,
             3373,
             3905,
             4518,
             3755,
             3444,
             1375,
             3741,
             3604,
             3569,
             1407,
             1539,
             3583,
             17238,
             3734,
             3747,
             3547,
             3813,
             1412,
             3633,
             3748,
             3804,
             3753,
             3616,
             3729,
             1365,
             1397,
             3437,
             3361,
             3385,
             282637,
             3517,
             2405,
             3362,
             17258,
             1399,
             1360,
             3556,
             54624,
             1743,
             1367,
             1377,
             2406,
             1176,
             2920,
             450933,
             1470,
             17516,
             528177,
             3953,
             478993,
             181215,
             58637,
             58407,
             54523,
             478979,
             1363,
             181218,
             3221,
             181225,
             4187,
             1353,
             528203,
             524145,
             181228,
             450920,
             2208,
             3733,
             3425,
             450913,
             450892,
             450882,
             58639,
             2226,
             3354,
             2252,
             1485,
             181221,
             2,
             3,
             4,
             5,
             7,
             9,
             10,
             11,
             12,
             13,
             14,
             15,
             16,
             18,
             19,
             20,
             21,
             22,
             24,
             25,
             26,
             27,
             28,
             30,
             31,
             32,
             33,
             34,
             36,
             37,
             38,
             39,
             40,
             41,
             42,
             43,
             44,
             45,
             92,
             93,
             94,
             96,
             97,
             98,
             99,
             100,
             101,
             103,
             105,
             106,
             108,
             110,
             112,
             114,
             118,
             119,
             121,
             130,
             133,
             139,
             188,
             195,
             196,
             197,
             198,
             199,
             200,
             201,
             202,
             210,
             211,
             216,
             217,
             234,
             283,
             284,
             359,
             362,
             386,
             485,
             495,
             559,
             560,
             561,
             562,
             778,
             779,
             780,
             781,
             788,
             789,
             790,
             791,
             792,
             793,
             794,
             795,
             848,
             849,
             850,
             851,
             852,
             853,
             854,
             855,
             856,
             857,
             858,
             859,
             860,
             861,
             862,
             863,
             864,
             865,
             866,
             890,
             891,
             898,
             899,
             915,
             916,
             917,
             918,
             919,
             920,
             921,
             1891,
             1897,
             2256,
             2266,
             3584,
             17240,
             17274,
             58642,
             58643,
             58644,
             58645,
             58646,
             58647,
             58648,
             58649,
             58650,
             505755,
             510361,
             510362,
             510364,
             516226,
             516227,
             516229,
             516230,
             516231,
             516279,
             520313,
             521153,
             521398,
             521857,
             522439,
             522908,
             523201,
             525688,
             526517,
             526695,
             526715,
             526939,
             527001,
             527256,
             527678,
             528006,
             528176]}

Get a specific item when field matchs the given value::

    # curl http://localhost:61208/api/3/processlist/pid/252940
    {"252940": [{"cmdline": ["/snap/firefox/1943/usr/lib/firefox/firefox"],
                 "cpu_percent": 0.0,
                 "cpu_times": [6291.33, 2169.99, 5908.96, 1090.39, 0.0],
                 "gids": [1000, 1000, 1000],
                 "io_counters": [3058916352, 7061786624, 0, 0, 0],
                 "key": "pid",
                 "memory_info": [474968064,
                                 12959444992,
                                 143884288,
                                 634880,
                                 0,
                                 1040416768,
                                 0],
                 "memory_percent": 6.061212712975372,
                 "name": "firefox",
                 "nice": 0,
                 "num_threads": 131,
                 "pid": 252940,
                 "status": "S",
                 "time_since_update": 1,
                 "username": "nicolargo"}]}

GET psutilversion
-----------------

Get plugin stats::

    # curl http://localhost:61208/api/3/psutilversion
    (5, 9, 2)

GET quicklook
-------------

Get plugin stats::

    # curl http://localhost:61208/api/3/quicklook
    {"cpu": 28.5,
     "cpu_hz": 1700000000.0,
     "cpu_hz_current": 1249013250.0,
     "cpu_name": "Intel(R) Core(TM) i7-4500U CPU @ 1.80GHz",
     "mem": 67.6,
     "percpu": [{"cpu_number": 0,
                 "guest": 0.0,
                 "guest_nice": 0.0,
                 "idle": 71.0,
                 "iowait": 0.0,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 0.0,
                 "steal": 0.0,
                 "system": 3.0,
                 "total": 29.0,
                 "user": 23.0},
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
                 "system": 4.0,
                 "total": 68.0,
                 "user": 61.0},
                {"cpu_number": 2,
                 "guest": 0.0,
                 "guest_nice": 0.0,
                 "idle": 82.0,
                 "iowait": 0.0,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 0.0,
                 "steal": 0.0,
                 "system": 1.0,
                 "total": 18.0,
                 "user": 15.0},
                {"cpu_number": 3,
                 "guest": 0.0,
                 "guest_nice": 0.0,
                 "idle": 93.0,
                 "iowait": 0.0,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 0.0,
                 "steal": 0.0,
                 "system": 0.0,
                 "total": 7.0,
                 "user": 2.0}],
     "swap": 30.7}

Get a specific field::

    # curl http://localhost:61208/api/3/quicklook/cpu
    {"cpu": 28.5}

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
     "os_version": "5.15.0-48-generic",
     "platform": "64bit"}

Get a specific field::

    # curl http://localhost:61208/api/3/system/os_name
    {"os_name": "Linux"}

GET uptime
----------

Get plugin stats::

    # curl http://localhost:61208/api/3/uptime
    {"seconds": 1470390}

GET all stats
-------------

Get all Glances stats::

    # curl http://localhost:61208/api/3/all
    Return a very big dictionnary (avoid using this request, performances will be poor)...

GET stats history
-----------------

History of a plugin::

    # curl http://localhost:61208/api/3/cpu/history
    {"system": [["2022-11-01T10:08:07.537407", 3.6],
                ["2022-11-01T10:08:08.598269", 3.6],
                ["2022-11-01T10:08:09.808752", 1.1]],
     "user": [["2022-11-01T10:08:07.537399", 24.7],
              ["2022-11-01T10:08:08.598260", 24.7],
              ["2022-11-01T10:08:09.808745", 4.7]]}

Limit history to last 2 values::

    # curl http://localhost:61208/api/3/cpu/history/2
    {"system": [["2022-11-01T10:08:08.598269", 3.6],
                ["2022-11-01T10:08:09.808752", 1.1]],
     "user": [["2022-11-01T10:08:08.598260", 24.7],
              ["2022-11-01T10:08:09.808745", 4.7]]}

History for a specific field::

    # curl http://localhost:61208/api/3/cpu/system/history
    {"system": [["2022-11-01T10:08:07.537407", 3.6],
                ["2022-11-01T10:08:08.598269", 3.6],
                ["2022-11-01T10:08:09.808752", 1.1]]}

Limit history for a specific field to last 2 values::

    # curl http://localhost:61208/api/3/cpu/system/history
    {"system": [["2022-11-01T10:08:08.598269", 3.6],
                ["2022-11-01T10:08:09.808752", 1.1]]}

GET limits (used for thresholds)
--------------------------------

All limits/thresholds::

    # curl http://localhost:61208/api/3/all/limits
    {"alert": {"history_size": 3600.0},
     "amps": {"amps_disable": ["False"], "history_size": 3600.0},
     "cloud": {"history_size": 3600.0},
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
     "ip": {"history_size": 3600.0,
            "ip_censys_fields": ["location:continent",
                                 "location:country",
                                 "autonomous_system:name"],
            "ip_censys_url": ["https://search.censys.io/api"],
            "ip_disable": ["False"],
            "ip_public_ip_disabled": ["False"],
            "ip_public_refresh_interval": 300.0},
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
     "system": {"history_size": 3600.0,
                "system_disable": ["False"],
                "system_refresh": 60},
     "uptime": {"history_size": 3600.0}}

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


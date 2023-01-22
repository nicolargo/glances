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

GET alert
---------

Get plugin stats::

    # curl http://localhost:61208/api/3/alert
    [[1674381772.0,
      -1,
      "WARNING",
      "CPU_TOTAL",
      78.1,
      78.1,
      78.1,
      78.1,
      1,
      [],
      "",
      "cpu_percent"]]

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
      "timer": 1.1751177310943604},
     {"count": 0,
      "countmax": 20.0,
      "countmin": None,
      "key": "name",
      "name": "Python",
      "refresh": 3.0,
      "regex": True,
      "result": None,
      "timer": 1.1748502254486084}]

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
                  "timer": 1.1751177310943604}]}

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
     "idle": 14.7,
     "interrupts": 0,
     "iowait": 7.4,
     "irq": 0.0,
     "nice": 0.0,
     "soft_interrupts": 0,
     "softirq": 0.9,
     "steal": 0.0,
     "syscalls": 0,
     "system": 19.4,
     "time_since_update": 1,
     "total": 78.1,
     "user": 57.6}

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
    {"total": 78.1}

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
    {"containers": [{"Command": ["/portainer"],
                     "Id": "3abd51c615968482d9ccff5afc629f267f6dda113ed68b75b432615fae3b49fb",
                     "Image": ["portainer/portainer-ce:2.9.3"],
                     "Status": "running",
                     "Uptime": "23 hours",
                     "cpu": {"total": 0.0},
                     "cpu_percent": 0.0,
                     "io": {},
                     "io_r": None,
                     "io_w": None,
                     "key": "name",
                     "memory": {},
                     "memory_usage": None,
                     "name": "portainer",
                     "network": {},
                     "network_rx": None,
                     "network_tx": None}],
     "version": {"ApiVersion": "1.41",
                 "Arch": "amd64",
                 "BuildTime": "2023-01-19T17:34:14.000000000+00:00",
                 "Components": [{"Details": {"ApiVersion": "1.41",
                                             "Arch": "amd64",
                                             "BuildTime": "2023-01-19T17:34:14.000000000+00:00",
                                             "Experimental": "false",
                                             "GitCommit": "6051f14",
                                             "GoVersion": "go1.18.10",
                                             "KernelVersion": "5.15.0-58-generic",
                                             "MinAPIVersion": "1.12",
                                             "Os": "linux"},
                                 "Name": "Engine",
                                 "Version": "20.10.23"},
                                {"Details": {"GitCommit": "5b842e528e99d4d4c1686467debf2bd4b88ecd86"},
                                 "Name": "containerd",
                                 "Version": "1.6.15"},
                                {"Details": {"GitCommit": "v1.1.4-0-g5fd4c4d"},
                                 "Name": "runc",
                                 "Version": "1.1.4"},
                                {"Details": {"GitCommit": "de40ad0"},
                                 "Name": "docker-init",
                                 "Version": "0.19.0"}],
                 "GitCommit": "6051f14",
                 "GoVersion": "go1.18.10",
                 "KernelVersion": "5.15.0-58-generic",
                 "MinAPIVersion": "1.12",
                 "Os": "linux",
                 "Platform": {"Name": "Docker Engine - Community"},
                 "Version": "20.10.23"}}

GET fs
------

Get plugin stats::

    # curl http://localhost:61208/api/3/fs
    [{"device_name": "/dev/mapper/ubuntu--gnome--vg-root",
      "free": 63000883200,
      "fs_type": "ext4",
      "key": "mnt_point",
      "mnt_point": "/",
      "percent": 72.7,
      "size": 243334156288,
      "used": 167945818112},
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
            "free": 63000883200,
            "fs_type": "ext4",
            "key": "mnt_point",
            "mnt_point": "/",
            "percent": 72.7,
            "size": 243334156288,
            "used": 167945818112}]}

GET ip
------

Get plugin stats::

    # curl http://localhost:61208/api/3/ip
    {"address": "192.168.0.32",
     "gateway": "192.168.0.254",
     "mask": "255.255.255.0",
     "mask_cidr": 24,
     "public_address": "91.166.228.228",
     "public_info_human": ""}

Get a specific field::

    # curl http://localhost:61208/api/3/ip/gateway
    {"gateway": "192.168.0.254"}

GET load
--------

Get plugin stats::

    # curl http://localhost:61208/api/3/load
    {"cpucore": 4,
     "min1": 2.79248046875,
     "min15": 0.6044921875,
     "min5": 1.24951171875}

Fields descriptions:

* **min1**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 1 minute (unit is *float*)
* **min5**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 5 minutes (unit is *float*)
* **min15**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 15 minutes (unit is *float*)
* **cpucore**: Total number of CPU core (unit is *number*)

Get a specific field::

    # curl http://localhost:61208/api/3/load/min1
    {"min1": 2.79248046875}

GET mem
-------

Get plugin stats::

    # curl http://localhost:61208/api/3/mem
    {"active": 3232829440,
     "available": 2574643200,
     "buffers": 482086912,
     "cached": 2828992512,
     "free": 2574643200,
     "inactive": 3375968256,
     "percent": 67.1,
     "shared": 610131968,
     "total": 7836196864,
     "used": 5261553664}

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
    {"total": 7836196864}

GET memswap
-----------

Get plugin stats::

    # curl http://localhost:61208/api/3/memswap
    {"free": 6393114624,
     "percent": 20.9,
     "sin": 1016889344,
     "sout": 2570014720,
     "time_since_update": 1,
     "total": 8082419712,
     "used": 1689305088}

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
      "cumulative_cx": 104446528,
      "cumulative_rx": 52223264,
      "cumulative_tx": 52223264,
      "cx": 2384,
      "interface_name": "lo",
      "is_up": True,
      "key": "interface_name",
      "rx": 1192,
      "speed": 0,
      "time_since_update": 1,
      "tx": 1192},
     {"alias": None,
      "cumulative_cx": 12191054510,
      "cumulative_rx": 11933885504,
      "cumulative_tx": 257169006,
      "cx": 29422,
      "interface_name": "wlp2s0",
      "is_up": True,
      "key": "interface_name",
      "rx": 22777,
      "speed": 0,
      "time_since_update": 1,
      "tx": 6645}]

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
    {"interface_name": ["lo",
                        "wlp2s0",
                        "br_grafana",
                        "br-119e6ee04e05",
                        "docker0",
                        "br-87386b77b676",
                        "mpqemubr0",
                        "vethf503072",
                        "tap-1e376645a40"]}

Get a specific item when field matchs the given value::

    # curl http://localhost:61208/api/3/network/interface_name/lo
    {"lo": [{"alias": None,
             "cumulative_cx": 104446528,
             "cumulative_rx": 52223264,
             "cumulative_tx": 52223264,
             "cx": 2384,
             "interface_name": "lo",
             "is_up": True,
             "key": "interface_name",
             "rx": 1192,
             "speed": 0,
             "time_since_update": 1,
             "tx": 1192}]}

GET now
-------

Get plugin stats::

    # curl http://localhost:61208/api/3/now
    "2023-01-22 11:02:51 CET"

GET percpu
----------

Get plugin stats::

    # curl http://localhost:61208/api/3/percpu
    [{"cpu_number": 0,
      "guest": 0.0,
      "guest_nice": 0.0,
      "idle": 20.3,
      "iowait": 12.3,
      "irq": 0.0,
      "key": "cpu_number",
      "nice": 0.0,
      "softirq": 0.0,
      "steal": 0.0,
      "system": 24.6,
      "total": 79.7,
      "user": 42.8},
     {"cpu_number": 1,
      "guest": 0.0,
      "guest_nice": 0.0,
      "idle": 16.4,
      "iowait": 6.0,
      "irq": 0.0,
      "key": "cpu_number",
      "nice": 0.0,
      "softirq": 0.0,
      "steal": 0.0,
      "system": 12.7,
      "total": 83.6,
      "user": 64.9}]

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
      "status": 0.01009,
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
                        "status": 0.01009,
                        "timeout": 3}]}

GET processcount
----------------

Get plugin stats::

    # curl http://localhost:61208/api/3/processcount
    {"pid_max": 0, "running": 2, "sleeping": 311, "thread": 1523, "total": 386}

Get a specific field::

    # curl http://localhost:61208/api/3/processcount/total
    {"total": 386}

GET processlist
---------------

Get plugin stats::

    # curl http://localhost:61208/api/3/processlist
    [{"cmdline": ["/snap/firefox/2263/usr/lib/firefox/firefox"],
      "cpu_percent": 0.0,
      "cpu_times": [2122.86, 658.23, 1239.16, 210.94, 0.0],
      "gids": [1000, 1000, 1000],
      "io_counters": [1674662912, 3749654528, 0, 0, 0],
      "key": "pid",
      "memory_info": [584667136, 21991870464, 132120576, 647168, 0, 1149304832, 0],
      "memory_percent": 7.461108317556428,
      "name": "firefox",
      "nice": 0,
      "num_threads": 146,
      "pid": 5040,
      "status": "S",
      "time_since_update": 1,
      "username": "nicolargo"},
     {"cmdline": ["/snap/firefox/2263/usr/lib/firefox/firefox",
                  "-contentproc",
                  "-childID",
                  "1",
                  "-isForBrowser",
                  "-prefsLen",
                  "32129",
                  "-prefMapSize",
                  "236410",
                  "-jsInitLen",
                  "246772",
                  "-parentBuildID",
                  "20230104235612",
                  "-appDir",
                  "/snap/firefox/2263/usr/lib/firefox/browser",
                  "{152fde2c-5751-4719-9edb-ff980730fbac}",
                  "5040",
                  "true",
                  "tab"],
      "cpu_percent": 0.0,
      "cpu_times": [467.87, 83.56, 0.0, 0.0, 0.0],
      "gids": [1000, 1000, 1000],
      "io_counters": [213443584, 0, 0, 0, 0],
      "key": "pid",
      "memory_info": [397238272, 3228049408, 70422528, 647168, 0, 639614976, 0],
      "memory_percent": 5.069273767545818,
      "name": "WebExtensions",
      "nice": 0,
      "num_threads": 20,
      "pid": 5246,
      "status": "S",
      "time_since_update": 1,
      "username": "nicolargo"}]

Get a specific field::

    # curl http://localhost:61208/api/3/processlist/pid
    {"pid": [5040,
             5246,
             5369,
             5752,
             10873,
             5365,
             10653,
             90446,
             4150,
             10724,
             109138,
             4519,
             422,
             109284,
             95798,
             22179,
             11307,
             36722,
             110258,
             5261,
             62850,
             10547,
             110317,
             10709,
             109762,
             110036,
             109882,
             10612,
             6074,
             96478,
             42687,
             4035,
             110285,
             2512,
             11033,
             1672,
             4473,
             5179,
             6020,
             10732,
             6022,
             4585,
             4544,
             10632,
             23231,
             23230,
             11251,
             4248,
             4413,
             11252,
             3955,
             4223,
             2721,
             4932,
             1816,
             90918,
             1635,
             14455,
             10848,
             43005,
             90973,
             4332,
             4263,
             4625,
             2239,
             1806,
             4325,
             14458,
             1,
             96102,
             4331,
             4182,
             102364,
             2701,
             91003,
             1681,
             4214,
             1876,
             1655,
             2640,
             2455,
             10557,
             1885,
             4561,
             1660,
             4445,
             1442,
             4130,
             4261,
             4339,
             4352,
             3944,
             1682,
             3934,
             4485,
             10558,
             4659,
             4328,
             4330,
             4137,
             4327,
             4334,
             4233,
             1777,
             3351,
             1873,
             59511,
             2179,
             1617,
             4050,
             17205,
             4192,
             4348,
             4166,
             4392,
             3700,
             1634,
             3966,
             17189,
             4573,
             4155,
             3968,
             3971,
             1675,
             4347,
             4329,
             1661,
             4377,
             6095,
             4229,
             1666,
             5299,
             2683,
             4314,
             1673,
             1643,
             1676,
             46760,
             10911,
             4452,
             468,
             4335,
             4324,
             4524,
             2684,
             4443,
             4173,
             4337,
             4201,
             4212,
             42986,
             4178,
             1631,
             1670,
             3952,
             4045,
             3976,
             1443,
             3701,
             3953,
             1626,
             4119,
             4162,
             1646,
             2020,
             1441,
             1633,
             3354,
             9703,
             49191,
             110201,
             14505,
             49179,
             10591,
             1449,
             4579,
             1685,
             1450,
             3774,
             10560,
             49194,
             2472,
             42952,
             1804,
             1803,
             42937,
             42964,
             42969,
             49182,
             3945,
             1618,
             110284,
             3707,
             4018,
             4323,
             4820,
             2480,
             104481,
             1695,
             2503,
             2475,
             2485,
             1447,
             1628,
             49185,
             2,
             3,
             4,
             5,
             6,
             8,
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
             104,
             106,
             107,
             109,
             110,
             112,
             117,
             118,
             128,
             131,
             137,
             171,
             175,
             201,
             205,
             217,
             218,
             219,
             220,
             221,
             222,
             223,
             224,
             248,
             249,
             254,
             255,
             312,
             361,
             362,
             442,
             447,
             577,
             601,
             676,
             677,
             678,
             693,
             963,
             964,
             965,
             966,
             967,
             968,
             969,
             970,
             971,
             972,
             973,
             974,
             1026,
             1027,
             1028,
             1029,
             1030,
             1031,
             1032,
             1033,
             1034,
             1035,
             1036,
             1037,
             1038,
             1039,
             1040,
             1041,
             1042,
             1043,
             1044,
             1071,
             1072,
             1080,
             1081,
             1105,
             1106,
             1107,
             1108,
             1109,
             1110,
             1111,
             2504,
             2521,
             2531,
             2597,
             2598,
             2599,
             2600,
             2602,
             2604,
             2609,
             2610,
             4034,
             18603,
             62912,
             62921,
             62922,
             62923,
             62924,
             62925,
             78135,
             78136,
             78138,
             90658,
             90659,
             90662,
             90663,
             90665,
             90718,
             90731,
             107066,
             107228,
             107746,
             107747,
             108008,
             108340,
             108486,
             108619,
             108834,
             108931,
             109106,
             109124,
             109329,
             110081,
             110221,
             110262,
             110263,
             110268,
             110269,
             110311,
             110375,
             110376,
             110377,
             110378,
             110379]}

Get a specific item when field matchs the given value::

    # curl http://localhost:61208/api/3/processlist/pid/5040
    {"5040": [{"cmdline": ["/snap/firefox/2263/usr/lib/firefox/firefox"],
               "cpu_percent": 0.0,
               "cpu_times": [2122.86, 658.23, 1239.16, 210.94, 0.0],
               "gids": [1000, 1000, 1000],
               "io_counters": [1674662912, 3749654528, 0, 0, 0],
               "key": "pid",
               "memory_info": [584667136,
                               21991870464,
                               132120576,
                               647168,
                               0,
                               1149304832,
                               0],
               "memory_percent": 7.461108317556428,
               "name": "firefox",
               "nice": 0,
               "num_threads": 146,
               "pid": 5040,
               "status": "S",
               "time_since_update": 1,
               "username": "nicolargo"}]}

GET psutilversion
-----------------

Get plugin stats::

    # curl http://localhost:61208/api/3/psutilversion
    [5, 9, 4]

GET quicklook
-------------

Get plugin stats::

    # curl http://localhost:61208/api/3/quicklook
    {"cpu": 78.1,
     "cpu_hz": 2025000000.0,
     "cpu_hz_current": 1728936749.9999998,
     "cpu_name": "Intel(R) Core(TM) i7-4500U CPU @ 1.80GHz",
     "mem": 67.1,
     "percpu": [{"cpu_number": 0,
                 "guest": 0.0,
                 "guest_nice": 0.0,
                 "idle": 20.3,
                 "iowait": 12.3,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 0.0,
                 "steal": 0.0,
                 "system": 24.6,
                 "total": 79.7,
                 "user": 42.8},
                {"cpu_number": 1,
                 "guest": 0.0,
                 "guest_nice": 0.0,
                 "idle": 16.4,
                 "iowait": 6.0,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 0.0,
                 "steal": 0.0,
                 "system": 12.7,
                 "total": 83.6,
                 "user": 64.9},
                {"cpu_number": 2,
                 "guest": 0.0,
                 "guest_nice": 0.0,
                 "idle": 9.2,
                 "iowait": 7.7,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 2.1,
                 "steal": 0.0,
                 "system": 18.3,
                 "total": 90.8,
                 "user": 62.7},
                {"cpu_number": 3,
                 "guest": 0.0,
                 "guest_nice": 0.0,
                 "idle": 12.1,
                 "iowait": 2.9,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 0.7,
                 "steal": 0.0,
                 "system": 13.6,
                 "total": 87.9,
                 "user": 70.7}],
     "swap": 20.9}

Get a specific field::

    # curl http://localhost:61208/api/3/quicklook/cpu
    {"cpu": 78.1}

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
     "os_version": "5.15.0-58-generic",
     "platform": "64bit"}

Get a specific field::

    # curl http://localhost:61208/api/3/system/os_name
    {"os_name": "Linux"}

GET uptime
----------

Get plugin stats::

    # curl http://localhost:61208/api/3/uptime
    "7 days, 17:52:03"

GET all stats
-------------

Get all Glances stats::

    # curl http://localhost:61208/api/3/all
    Return a very big dictionnary (avoid using this request, performances will be poor)...

GET stats history
-----------------

History of a plugin::

    # curl http://localhost:61208/api/3/cpu/history
    {"system": [["2023-01-22T11:02:52.355003", 19.4],
                ["2023-01-22T11:02:53.467824", 19.4],
                ["2023-01-22T11:02:54.710232", 13.2]],
     "user": [["2023-01-22T11:02:52.354990", 57.6],
              ["2023-01-22T11:02:53.467809", 57.6],
              ["2023-01-22T11:02:54.710224", 28.5]]}

Limit history to last 2 values::

    # curl http://localhost:61208/api/3/cpu/history/2
    {"system": [["2023-01-22T11:02:53.467824", 19.4],
                ["2023-01-22T11:02:54.710232", 13.2]],
     "user": [["2023-01-22T11:02:53.467809", 57.6],
              ["2023-01-22T11:02:54.710224", 28.5]]}

History for a specific field::

    # curl http://localhost:61208/api/3/cpu/system/history
    {"system": [["2023-01-22T11:02:52.355003", 19.4],
                ["2023-01-22T11:02:53.467824", 19.4],
                ["2023-01-22T11:02:54.710232", 13.2]]}

Limit history for a specific field to last 2 values::

    # curl http://localhost:61208/api/3/cpu/system/history
    {"system": [["2023-01-22T11:02:53.467824", 19.4],
                ["2023-01-22T11:02:54.710232", 13.2]]}

GET limits (used for thresholds)
--------------------------------

All limits/thresholds::

    # curl http://localhost:61208/api/3/all/limits
    {"alert": {"history_size": 1200.0},
     "amps": {"amps_disable": ["False"], "history_size": 1200.0},
     "cloud": {"history_size": 1200.0},
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
     "diskio": {"diskio_disable": ["False"],
                "diskio_hide": ["loop.*", "/dev/loop.*"],
                "history_size": 1200.0},
     "docker": {"docker_all": ["False"],
                "docker_disable": ["False"],
                "docker_max_name_size": 20.0,
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
     "uptime": {"history_size": 1200.0}}

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
     "history_size": 1200.0}


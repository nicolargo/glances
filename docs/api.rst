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
      "timer": 0.8425271511077881},
     {"count": 0,
      "countmax": 20.0,
      "countmin": None,
      "key": "name",
      "name": "Python",
      "refresh": 3.0,
      "regex": True,
      "result": None,
      "timer": 0.8423657417297363}]

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
                  "timer": 0.8425271511077881}]}

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
     "idle": 58.6,
     "interrupts": 0,
     "iowait": 0.0,
     "irq": 0.0,
     "nice": 0.0,
     "soft_interrupts": 0,
     "softirq": 0.0,
     "steal": 0.0,
     "syscalls": 0,
     "system": 6.7,
     "time_since_update": 1,
     "total": 38.2,
     "user": 34.7}

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
    {"total": 38.2}

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
                     "Uptime": "36 mins",
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
                 "BuildTime": "2022-12-15T22:25:58.000000000+00:00",
                 "Components": [{"Details": {"ApiVersion": "1.41",
                                             "Arch": "amd64",
                                             "BuildTime": "2022-12-15T22:25:58.000000000+00:00",
                                             "Experimental": "false",
                                             "GitCommit": "42c8b31",
                                             "GoVersion": "go1.18.9",
                                             "KernelVersion": "5.15.0-56-generic",
                                             "MinAPIVersion": "1.12",
                                             "Os": "linux"},
                                 "Name": "Engine",
                                 "Version": "20.10.22"},
                                {"Details": {"GitCommit": "5b842e528e99d4d4c1686467debf2bd4b88ecd86"},
                                 "Name": "containerd",
                                 "Version": "1.6.15"},
                                {"Details": {"GitCommit": "v1.1.4-0-g5fd4c4d"},
                                 "Name": "runc",
                                 "Version": "1.1.4"},
                                {"Details": {"GitCommit": "de40ad0"},
                                 "Name": "docker-init",
                                 "Version": "0.19.0"}],
                 "GitCommit": "42c8b31",
                 "GoVersion": "go1.18.9",
                 "KernelVersion": "5.15.0-56-generic",
                 "MinAPIVersion": "1.12",
                 "Os": "linux",
                 "Platform": {"Name": "Docker Engine - Community"},
                 "Version": "20.10.22"}}

GET fs
------

Get plugin stats::

    # curl http://localhost:61208/api/3/fs
    [{"device_name": "/dev/mapper/ubuntu--gnome--vg-root",
      "free": 50442330112,
      "fs_type": "ext4",
      "key": "mnt_point",
      "mnt_point": "/",
      "percent": 78.2,
      "size": 243334156288,
      "used": 180504371200},
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
            "free": 50442330112,
            "fs_type": "ext4",
            "key": "mnt_point",
            "mnt_point": "/",
            "percent": 78.2,
            "size": 243334156288,
            "used": 180504371200}]}

GET ip
------

Get plugin stats::

    # curl http://localhost:61208/api/3/ip
    {"address": "192.168.1.14",
     "gateway": "192.168.1.1",
     "mask": "255.255.255.0",
     "mask_cidr": 24,
     "public_address": "109.210.93.150",
     "public_info_human": ""}

Get a specific field::

    # curl http://localhost:61208/api/3/ip/gateway
    {"gateway": "192.168.1.1"}

GET load
--------

Get plugin stats::

    # curl http://localhost:61208/api/3/load
    {"cpucore": 4, "min1": 1.31591796875, "min15": 1.9091796875, "min5": 1.6796875}

Fields descriptions:

* **min1**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 1 minute (unit is *float*)
* **min5**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 5 minutes (unit is *float*)
* **min15**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 15 minutes (unit is *float*)
* **cpucore**: Total number of CPU core (unit is *number*)

Get a specific field::

    # curl http://localhost:61208/api/3/load/min1
    {"min1": 1.31591796875}

GET mem
-------

Get plugin stats::

    # curl http://localhost:61208/api/3/mem
    {"active": 2804523008,
     "available": 2706178048,
     "buffers": 264335360,
     "cached": 3114909696,
     "free": 2706178048,
     "inactive": 3516907520,
     "percent": 65.5,
     "shared": 591532032,
     "total": 7836188672,
     "used": 5130010624}

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
    {"free": 2626473984,
     "percent": 67.5,
     "sin": 4755005440,
     "sout": 11063549952,
     "time_since_update": 1,
     "total": 8082419712,
     "used": 5455945728}

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
      "cumulative_cx": 398215554,
      "cumulative_rx": 199107777,
      "cumulative_tx": 199107777,
      "cx": 3314,
      "interface_name": "lo",
      "is_up": True,
      "key": "interface_name",
      "rx": 1657,
      "speed": 0,
      "time_since_update": 1,
      "tx": 1657},
     {"alias": None,
      "cumulative_cx": 39497892918,
      "cumulative_rx": 38949809930,
      "cumulative_tx": 548082988,
      "cx": 27720,
      "interface_name": "wlp2s0",
      "is_up": True,
      "key": "interface_name",
      "rx": 21708,
      "speed": 0,
      "time_since_update": 1,
      "tx": 6012}]

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
                        "docker0",
                        "br-119e6ee04e05",
                        "br-87386b77b676",
                        "br_grafana",
                        "mpqemubr0",
                        "tap-1e376645a40",
                        "veth57bdacb"]}

Get a specific item when field matchs the given value::

    # curl http://localhost:61208/api/3/network/interface_name/lo
    {"lo": [{"alias": None,
             "cumulative_cx": 398215554,
             "cumulative_rx": 199107777,
             "cumulative_tx": 199107777,
             "cx": 3314,
             "interface_name": "lo",
             "is_up": True,
             "key": "interface_name",
             "rx": 1657,
             "speed": 0,
             "time_since_update": 1,
             "tx": 1657}]}

GET now
-------

Get plugin stats::

    # curl http://localhost:61208/api/3/now
    "2023-01-14 09:45:44 CET"

GET percpu
----------

Get plugin stats::

    # curl http://localhost:61208/api/3/percpu
    [{"cpu_number": 0,
      "guest": 0.0,
      "guest_nice": 0.0,
      "idle": 56.1,
      "iowait": 0.0,
      "irq": 0.0,
      "key": "cpu_number",
      "nice": 0.0,
      "softirq": 0.0,
      "steal": 0.0,
      "system": 4.7,
      "total": 43.9,
      "user": 39.3},
     {"cpu_number": 1,
      "guest": 0.0,
      "guest_nice": 0.0,
      "idle": 28.2,
      "iowait": 0.0,
      "irq": 0.0,
      "key": "cpu_number",
      "nice": 0.0,
      "softirq": 0.0,
      "steal": 0.0,
      "system": 3.9,
      "total": 71.8,
      "user": 68.0}]

Get a specific field::

    # curl http://localhost:61208/api/3/percpu/cpu_number
    {"cpu_number": [0, 1, 2, 3]}

GET ports
---------

Get plugin stats::

    # curl http://localhost:61208/api/3/ports
    [{"description": "DefaultGateway",
      "host": "192.168.1.1",
      "indice": "port_0",
      "port": 0,
      "refresh": 30,
      "rtt_warning": None,
      "status": 0.007094,
      "timeout": 3}]

Get a specific field::

    # curl http://localhost:61208/api/3/ports/host
    {"host": ["192.168.1.1"]}

Get a specific item when field matchs the given value::

    # curl http://localhost:61208/api/3/ports/host/192.168.1.1
    {"192.168.1.1": [{"description": "DefaultGateway",
                      "host": "192.168.1.1",
                      "indice": "port_0",
                      "port": 0,
                      "refresh": 30,
                      "rtt_warning": None,
                      "status": 0.007094,
                      "timeout": 3}]}

GET processcount
----------------

Get plugin stats::

    # curl http://localhost:61208/api/3/processcount
    {"pid_max": 0, "running": 2, "sleeping": 334, "thread": 1765, "total": 403}

Get a specific field::

    # curl http://localhost:61208/api/3/processcount/total
    {"total": 403}

GET processlist
---------------

Get plugin stats::

    # curl http://localhost:61208/api/3/processlist
    [{"cmdline": ["/snap/firefox/2154/usr/lib/firefox/firefox"],
      "cpu_percent": 0.0,
      "cpu_times": [8504.75, 2803.93, 8401.36, 1489.57, 0.0],
      "gids": [1000, 1000, 1000],
      "io_counters": [6360911872, 11858505728, 0, 0, 0],
      "key": "pid",
      "memory_info": [484036608, 22242152448, 100323328, 659456, 0, 1409527808, 0],
      "memory_percent": 6.176939176178121,
      "name": "firefox",
      "nice": 0,
      "num_threads": 187,
      "pid": 4674,
      "status": "S",
      "time_since_update": 1,
      "username": "nicolargo"},
     {"cmdline": ["/snap/firefox/2154/usr/lib/firefox/firefox",
                  "-contentproc",
                  "-childID",
                  "1",
                  "-isForBrowser",
                  "-prefsLen",
                  "31799",
                  "-prefMapSize",
                  "234979",
                  "-jsInitLen",
                  "246704",
                  "-parentBuildID",
                  "20221128185858",
                  "-appDir",
                  "/snap/firefox/2154/usr/lib/firefox/browser",
                  "{8ed7e0e9-5dcf-4c35-9523-65d5178968f5}",
                  "4674",
                  "true",
                  "tab"],
      "cpu_percent": 0.0,
      "cpu_times": [1878.88, 294.96, 0.0, 0.0, 0.0],
      "gids": [1000, 1000, 1000],
      "io_counters": [446676992, 0, 0, 0, 0],
      "key": "pid",
      "memory_info": [379330560, 3766951936, 44253184, 659456, 0, 1161146368, 0],
      "memory_percent": 4.840753277871052,
      "name": "WebExtensions",
      "nice": 0,
      "num_threads": 20,
      "pid": 4980,
      "status": "S",
      "time_since_update": 1,
      "username": "nicolargo"}]

Get a specific field::

    # curl http://localhost:61208/api/3/processlist/pid
    {"pid": [4674,
             4980,
             5110,
             527830,
             173709,
             3699,
             5464,
             431554,
             495017,
             5113,
             173765,
             174093,
             87518,
             10140,
             93773,
             5000,
             173645,
             534445,
             511174,
             173751,
             534543,
             9953,
             534732,
             535113,
             284680,
             128927,
             173679,
             535159,
             4050,
             3586,
             4426,
             173949,
             493657,
             511164,
             2510,
             3351,
             173688,
             173781,
             496818,
             496817,
             408152,
             493678,
             4206,
             511549,
             427,
             173973,
             3820,
             5730,
             17316,
             174051,
             1616,
             3512,
             493683,
             1,
             5690,
             3903,
             4008,
             165775,
             3792,
             174314,
             493699,
             94498,
             2702,
             1662,
             1641,
             87895,
             87994,
             4158,
             87995,
             174313,
             4433,
             87753,
             3897,
             5691,
             4458,
             87853,
             94497,
             4903,
             3902,
             17315,
             3829,
             173649,
             87454,
             3273,
             1838,
             3676,
             3783,
             3695,
             10499,
             87474,
             3907,
             2209,
             3730,
             3486,
             3915,
             3901,
             3910,
             10649,
             533610,
             10551,
             511526,
             10082,
             87412,
             1615,
             173650,
             4005,
             3904,
             10318,
             165937,
             1663,
             1777,
             2417,
             2626,
             10319,
             3805,
             10094,
             3956,
             1837,
             17467,
             1636,
             2688,
             4049,
             4089,
             3521,
             87413,
             87779,
             3861,
             1416,
             102131,
             10032,
             1782,
             1598,
             115869,
             17484,
             3970,
             1659,
             3524,
             465,
             2159,
             3898,
             3527,
             3802,
             5024,
             3743,
             1626,
             10033,
             3908,
             4036,
             3697,
             4170,
             10048,
             1642,
             3906,
             1654,
             3717,
             173849,
             3591,
             3896,
             3726,
             3909,
             3722,
             3900,
             3781,
             3994,
             10381,
             3748,
             87429,
             3584,
             3905,
             1868,
             1612,
             3891,
             112675,
             1607,
             1660,
             3533,
             3510,
             98474,
             10372,
             3508,
             1648,
             1652,
             3706,
             3664,
             1629,
             1999,
             1614,
             1415,
             535105,
             1419,
             1666,
             4187,
             2680,
             173665,
             1432,
             17364,
             2681,
             1430,
             2428,
             3354,
             142951,
             1609,
             98475,
             1599,
             535158,
             5769,
             10035,
             173652,
             87415,
             3895,
             2483,
             511483,
             3572,
             511504,
             191811,
             98353,
             98484,
             511512,
             532452,
             98346,
             511490,
             4546,
             3487,
             2430,
             2492,
             2465,
             1431,
             1669,
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
             104,
             105,
             108,
             110,
             112,
             113,
             118,
             119,
             120,
             121,
             131,
             135,
             141,
             204,
             218,
             219,
             220,
             221,
             222,
             223,
             224,
             225,
             249,
             250,
             255,
             256,
             313,
             366,
             367,
             447,
             448,
             545,
             614,
             685,
             686,
             687,
             694,
             950,
             951,
             952,
             953,
             956,
             957,
             958,
             959,
             960,
             961,
             966,
             967,
             1021,
             1022,
             1023,
             1024,
             1025,
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
             1056,
             1057,
             1065,
             1066,
             1083,
             1084,
             1085,
             1086,
             1087,
             1088,
             1089,
             2491,
             2527,
             2539,
             2586,
             2587,
             2589,
             2590,
             2592,
             2598,
             2599,
             2606,
             3780,
             4620,
             10063,
             87445,
             282372,
             284747,
             284755,
             284756,
             284759,
             284760,
             445439,
             445440,
             445441,
             491085,
             493353,
             493435,
             493436,
             493437,
             493438,
             493440,
             493488,
             525438,
             526723,
             527334,
             529501,
             532606,
             532692,
             532694,
             532700,
             532986,
             533409,
             533601,
             533685,
             533744,
             533796,
             533986,
             534098,
             534679]}

Get a specific item when field matchs the given value::

    # curl http://localhost:61208/api/3/processlist/pid/4674
    {"4674": [{"cmdline": ["/snap/firefox/2154/usr/lib/firefox/firefox"],
               "cpu_percent": 0.0,
               "cpu_times": [8504.75, 2803.93, 8401.36, 1489.57, 0.0],
               "gids": [1000, 1000, 1000],
               "io_counters": [6360911872, 11858505728, 0, 0, 0],
               "key": "pid",
               "memory_info": [484036608,
                               22242152448,
                               100323328,
                               659456,
                               0,
                               1409527808,
                               0],
               "memory_percent": 6.176939176178121,
               "name": "firefox",
               "nice": 0,
               "num_threads": 187,
               "pid": 4674,
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
    {"cpu": 38.2,
     "cpu_hz": 2025000000.0,
     "cpu_hz_current": 1247640750.0,
     "cpu_name": "Intel(R) Core(TM) i7-4500U CPU @ 1.80GHz",
     "mem": 65.5,
     "percpu": [{"cpu_number": 0,
                 "guest": 0.0,
                 "guest_nice": 0.0,
                 "idle": 56.1,
                 "iowait": 0.0,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 0.0,
                 "steal": 0.0,
                 "system": 4.7,
                 "total": 43.9,
                 "user": 39.3},
                {"cpu_number": 1,
                 "guest": 0.0,
                 "guest_nice": 0.0,
                 "idle": 28.2,
                 "iowait": 0.0,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 0.0,
                 "steal": 0.0,
                 "system": 3.9,
                 "total": 71.8,
                 "user": 68.0},
                {"cpu_number": 2,
                 "guest": 0.0,
                 "guest_nice": 0.0,
                 "idle": 82.4,
                 "iowait": 0.0,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 0.0,
                 "steal": 0.0,
                 "system": 2.9,
                 "total": 17.6,
                 "user": 14.7},
                {"cpu_number": 3,
                 "guest": 0.0,
                 "guest_nice": 0.0,
                 "idle": 80.4,
                 "iowait": 0.0,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 0.0,
                 "steal": 0.0,
                 "system": 4.9,
                 "total": 19.6,
                 "user": 14.7}],
     "swap": 67.5}

Get a specific field::

    # curl http://localhost:61208/api/3/quicklook/cpu
    {"cpu": 38.2}

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
               "CPU",
               "Ambient",
               "SODIMM",
               "Package id 0",
               "Core 0",
               "Core 1",
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
     "os_version": "5.15.0-56-generic",
     "platform": "64bit"}

Get a specific field::

    # curl http://localhost:61208/api/3/system/os_name
    {"os_name": "Linux"}

GET uptime
----------

Get plugin stats::

    # curl http://localhost:61208/api/3/uptime
    "32 days, 23:30:09"

GET all stats
-------------

Get all Glances stats::

    # curl http://localhost:61208/api/3/all
    Return a very big dictionnary (avoid using this request, performances will be poor)...

GET stats history
-----------------

History of a plugin::

    # curl http://localhost:61208/api/3/cpu/history
    {"system": [["2023-01-14T09:45:45.821873", 6.7],
                ["2023-01-14T09:45:46.919905", 6.7],
                ["2023-01-14T09:45:48.110702", 4.8]],
     "user": [["2023-01-14T09:45:45.821864", 34.7],
              ["2023-01-14T09:45:46.919895", 34.7],
              ["2023-01-14T09:45:48.110694", 12.4]]}

Limit history to last 2 values::

    # curl http://localhost:61208/api/3/cpu/history/2
    {"system": [["2023-01-14T09:45:46.919905", 6.7],
                ["2023-01-14T09:45:48.110702", 4.8]],
     "user": [["2023-01-14T09:45:46.919895", 34.7],
              ["2023-01-14T09:45:48.110694", 12.4]]}

History for a specific field::

    # curl http://localhost:61208/api/3/cpu/system/history
    {"system": [["2023-01-14T09:45:45.821873", 6.7],
                ["2023-01-14T09:45:46.919905", 6.7],
                ["2023-01-14T09:45:48.110702", 4.8]]}

Limit history for a specific field to last 2 values::

    # curl http://localhost:61208/api/3/cpu/system/history
    {"system": [["2023-01-14T09:45:46.919905", 6.7],
                ["2023-01-14T09:45:48.110702", 4.8]]}

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


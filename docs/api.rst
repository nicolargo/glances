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
      "timer": 0.8387062549591064},
     {"count": 0,
      "countmax": 20.0,
      "countmin": None,
      "key": "name",
      "name": "Python",
      "refresh": 3.0,
      "regex": True,
      "result": None,
      "timer": 0.8385326862335205}]

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
                  "timer": 0.8387062549591064}]}

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
     "idle": 52.4,
     "interrupts": 0,
     "iowait": 2.5,
     "irq": 0.0,
     "nice": 0.0,
     "soft_interrupts": 0,
     "softirq": 0.2,
     "steal": 0.0,
     "syscalls": 0,
     "system": 9.1,
     "time_since_update": 1,
     "total": 37.6,
     "user": 35.8}

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
    {"total": 37.6}

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
    [{"Command": ["/entrypoint.sh", "telegraf"],
      "Id": "9230f84acadbb7bc8c087d0827389c9a87bb7c7022a1a299dcf4a5f3a441f1d3",
      "Image": ["telegraf:latest"],
      "Names": ["telegraf"],
      "Status": "running",
      "Uptime": "1 weeks",
      "cpu_percent": 0.0,
      "io_r": None,
      "io_w": None,
      "key": "name",
      "memory_usage": 33148928,
      "name": "telegraf",
      "network_rx": None,
      "network_tx": None},
     {"Command": ["/run.sh"],
      "Id": "09d96704c3e6b6cb21657d990e3c8ae1e44bac779ded141efb8fed899563dd66",
      "Image": ["grafana/grafana:latest"],
      "Names": ["grafana"],
      "Status": "running",
      "Uptime": "1 weeks",
      "cpu_percent": 0.0,
      "io_r": None,
      "io_w": None,
      "key": "name",
      "memory_usage": None,
      "name": "grafana",
      "network_rx": None,
      "network_tx": None}]

GET fs
------

Get plugin stats::

    # curl http://localhost:61208/api/3/fs
    [{"device_name": "/dev/mapper/ubuntu--gnome--vg-root",
      "free": 78089314304,
      "fs_type": "ext4",
      "key": "mnt_point",
      "mnt_point": "/",
      "percent": 66.2,
      "size": 243334156288,
      "used": 152857387008},
     {"device_name": "/dev/mapper/ubuntu--gnome--vg-root",
      "free": 78089314304,
      "fs_type": "ext4",
      "key": "mnt_point",
      "mnt_point": "/var/snap/firefox/common/host-hunspell",
      "percent": 66.2,
      "size": 243334156288,
      "used": 152857387008}]

Get a specific field::

    # curl http://localhost:61208/api/3/fs/mnt_point
    {"mnt_point": ["/", "/var/snap/firefox/common/host-hunspell"]}

Get a specific item when field matchs the given value::

    # curl http://localhost:61208/api/3/fs/mnt_point//
    {"/": [{"device_name": "/dev/mapper/ubuntu--gnome--vg-root",
            "free": 78089314304,
            "fs_type": "ext4",
            "key": "mnt_point",
            "mnt_point": "/",
            "percent": 66.2,
            "size": 243334156288,
            "used": 152857387008}]}

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
     "min1": 1.12890625,
     "min15": 1.07568359375,
     "min5": 1.20458984375}

Fields descriptions:

* **min1**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 1 minute (unit is *float*)
* **min5**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 5 minutes (unit is *float*)
* **min15**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 15 minutes (unit is *float*)
* **cpucore**: Total number of CPU core (unit is *number*)

Get a specific field::

    # curl http://localhost:61208/api/3/load/min1
    {"min1": 1.12890625}

GET mem
-------

Get plugin stats::

    # curl http://localhost:61208/api/3/mem
    {"active": 2355691520,
     "available": 2727350272,
     "buffers": 249974784,
     "cached": 2882801664,
     "free": 2727350272,
     "inactive": 3822198784,
     "percent": 65.2,
     "shared": 569184256,
     "total": 7836200960,
     "used": 5108850688}

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
    {"total": 7836200960}

GET memswap
-----------

Get plugin stats::

    # curl http://localhost:61208/api/3/memswap
    {"free": 3790909440,
     "percent": 53.1,
     "sin": 10184392704,
     "sout": 16056197120,
     "time_since_update": 1,
     "total": 8082419712,
     "used": 4291510272}

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
      "cumulative_cx": 547141210,
      "cumulative_rx": 273570605,
      "cumulative_tx": 273570605,
      "cx": 2492,
      "interface_name": "lo",
      "is_up": True,
      "key": "interface_name",
      "rx": 1246,
      "speed": 0,
      "time_since_update": 1,
      "tx": 1246},
     {"alias": None,
      "cumulative_cx": 9679745577,
      "cumulative_rx": 9073526296,
      "cumulative_tx": 606219281,
      "cx": 21718,
      "interface_name": "wlp2s0",
      "is_up": True,
      "key": "interface_name",
      "rx": 15792,
      "speed": 0,
      "time_since_update": 1,
      "tx": 5926}]

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
                        "veth909d06e",
                        "veth9b67642",
                        "vethd7de7ad",
                        "vboxnet0",
                        "mpqemubr0"]}

Get a specific item when field matchs the given value::

    # curl http://localhost:61208/api/3/network/interface_name/lo
    {"lo": [{"alias": None,
             "cumulative_cx": 547141210,
             "cumulative_rx": 273570605,
             "cumulative_tx": 273570605,
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
    "2022-09-24 19:01:55 CEST"

GET percpu
----------

Get plugin stats::

    # curl http://localhost:61208/api/3/percpu
    [{"cpu_number": 0,
      "guest": 0.0,
      "guest_nice": 0.0,
      "idle": 31.0,
      "iowait": 8.0,
      "irq": 0.0,
      "key": "cpu_number",
      "nice": 0.0,
      "softirq": 0.0,
      "steal": 0.0,
      "system": 8.0,
      "total": 69.0,
      "user": 50.0},
     {"cpu_number": 1,
      "guest": 0.0,
      "guest_nice": 0.0,
      "idle": 51.0,
      "iowait": 1.0,
      "irq": 0.0,
      "key": "cpu_number",
      "nice": 0.0,
      "softirq": 0.0,
      "steal": 0.0,
      "system": 8.0,
      "total": 49.0,
      "user": 37.0}]

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
      "status": 0.005664,
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
                        "status": 0.005664,
                        "timeout": 3}]}

GET processcount
----------------

Get plugin stats::

    # curl http://localhost:61208/api/3/processcount
    {"pid_max": 0, "running": 3, "sleeping": 292, "thread": 1722, "total": 361}

Get a specific field::

    # curl http://localhost:61208/api/3/processcount/total
    {"total": 361}

GET processlist
---------------

Get plugin stats::

    # curl http://localhost:61208/api/3/processlist
    [{"cmdline": ["/snap/firefox/1877/usr/lib/firefox/firefox"],
      "cpu_percent": 0.0,
      "cpu_times": pcputimes(user=451.28, system=141.31, children_user=205.71, children_system=31.59, iowait=0.0),
      "gids": pgids(real=1000, effective=1000, saved=1000),
      "io_counters": [526351360, 531091456, 0, 0, 0],
      "key": "pid",
      "memory_info": pmem(rss=450482176, vms=12297506816, shared=152215552, text=634880, lib=0, data=729407488, dirty=0),
      "memory_percent": 5.748731793626692,
      "name": "firefox",
      "nice": 0,
      "num_threads": 121,
      "pid": 477633,
      "status": "S",
      "time_since_update": 1,
      "username": "nicolargo"},
     {"cmdline": ["/snap/firefox/1877/usr/lib/firefox/firefox",
                  "-contentproc",
                  "-childID",
                  "1",
                  "-isForBrowser",
                  "-prefsLen",
                  "30507",
                  "-prefMapSize",
                  "235589",
                  "-jsInitLen",
                  "246848",
                  "-parentBuildID",
                  "20220922230616",
                  "-appDir",
                  "/snap/firefox/1877/usr/lib/firefox/browser",
                  "{6ceebb90-379f-4229-b8e3-37e0494c36c4}",
                  "477633",
                  "true",
                  "tab"],
      "cpu_percent": 0.0,
      "cpu_times": pcputimes(user=77.7, system=13.75, children_user=0.0, children_system=0.0, iowait=0.0),
      "gids": pgids(real=1000, effective=1000, saved=1000),
      "io_counters": [4724736, 0, 0, 0, 0],
      "key": "pid",
      "memory_info": pmem(rss=407302144, vms=3239350272, shared=82366464, text=634880, lib=0, data=641540096, dirty=0),
      "memory_percent": 5.197699064624295,
      "name": "WebExtensions",
      "nice": 0,
      "num_threads": 22,
      "pid": 477906,
      "status": "S",
      "time_since_update": 1,
      "username": "nicolargo"}]

Get a specific field::

    # curl http://localhost:61208/api/3/processlist/pid
    {"pid": [477633,
             477906,
             478013,
             4784,
             478017,
             371539,
             371076,
             371144,
             318967,
             8690,
             486802,
             484335,
             488179,
             378577,
             477924,
             174274,
             488541,
             371161,
             371008,
             488573,
             488854,
             488677,
             7012,
             27079,
             371044,
             138155,
             385575,
             488841,
             5288,
             2173,
             451763,
             231559,
             371369,
             477843,
             478972,
             396952,
             86902,
             488833,
             4677,
             479017,
             378578,
             231684,
             294867,
             488868,
             231727,
             343,
             454839,
             451764,
             385601,
             371175,
             2410,
             306104,
             57024,
             364779,
             143873,
             371055,
             385574,
             4882,
             371492,
             27101,
             487714,
             8716,
             445656,
             4980,
             1234,
             174164,
             1,
             4592,
             9030,
             6654,
             4955,
             4950,
             4850,
             5060,
             8974,
             8689,
             174166,
             8896,
             4859,
             1283,
             1282,
             4581,
             5295,
             1255,
             4954,
             371013,
             4608,
             5151,
             8633,
             4868,
             21750,
             5075,
             4600,
             5774,
             4562,
             27046,
             21749,
             9249,
             294892,
             4762,
             4963,
             12787,
             371014,
             2894,
             9250,
             1430,
             4894,
             459894,
             4770,
             231540,
             1387,
             13199,
             7033,
             290593,
             5320,
             4953,
             13659,
             5031,
             1233,
             4985,
             231642,
             5132,
             231697,
             1883,
             4956,
             13217,
             4814,
             1080,
             8648,
             1431,
             4958,
             5078,
             290540,
             4901,
             1278,
             1216,
             1893,
             371324,
             4864,
             1229,
             5044,
             2107,
             4833,
             1242,
             4949,
             4952,
             2334,
             2370,
             27078,
             4809,
             1251,
             4822,
             8584,
             4610,
             4678,
             5054,
             4787,
             8583,
             4951,
             1277,
             5085,
             5160,
             1256,
             4972,
             4615,
             4938,
             388,
             7265,
             4683,
             294886,
             8600,
             4796,
             4848,
             4970,
             1225,
             488805,
             60479,
             4803,
             1244,
             4957,
             4795,
             8936,
             1260,
             1264,
             174259,
             4749,
             1445,
             371029,
             98466,
             1232,
             8860,
             1613,
             4589,
             1077,
             1285,
             5176,
             2897,
             1081,
             2112,
             2154,
             71513,
             4590,
             2131,
             1088,
             2367,
             1090,
             1228,
             2368,
             371016,
             1217,
             488840,
             1949,
             8586,
             4948,
             2125,
             231626,
             231453,
             231471,
             231611,
             4654,
             227172,
             231459,
             231492,
             231514,
             231500,
             231478,
             4582,
             231522,
             5403,
             2124,
             1289,
             445844,
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
             105,
             106,
             108,
             109,
             111,
             116,
             117,
             118,
             128,
             131,
             137,
             171,
             173,
             189,
             196,
             197,
             198,
             201,
             202,
             203,
             204,
             205,
             209,
             210,
             215,
             216,
             233,
             281,
             282,
             370,
             371,
             389,
             507,
             549,
             570,
             571,
             572,
             573,
             803,
             804,
             805,
             806,
             807,
             808,
             809,
             810,
             811,
             812,
             813,
             814,
             2146,
             2205,
             2225,
             2286,
             2289,
             2290,
             2291,
             2293,
             2295,
             2296,
             2297,
             4847,
             8614,
             295453,
             463540,
             486333,
             486502,
             486568,
             487115,
             487502,
             487592,
             487598,
             487600,
             487601,
             487605,
             487606,
             487631,
             487632,
             487635,
             487655,
             487659,
             488819]}

Get a specific item when field matchs the given value::

    # curl http://localhost:61208/api/3/processlist/pid/477633
    {"477633": [{"cmdline": ["/snap/firefox/1877/usr/lib/firefox/firefox"],
                 "cpu_percent": 0.0,
                 "cpu_times": [451.28, 141.31, 205.71, 31.59, 0.0],
                 "gids": [1000, 1000, 1000],
                 "io_counters": [526351360, 531091456, 0, 0, 0],
                 "key": "pid",
                 "memory_info": [450482176,
                                 12297506816,
                                 152215552,
                                 634880,
                                 0,
                                 729407488,
                                 0],
                 "memory_percent": 5.748731793626692,
                 "name": "firefox",
                 "nice": 0,
                 "num_threads": 121,
                 "pid": 477633,
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
    {"cpu": 37.6,
     "cpu_hz": 3000000000.0,
     "cpu_hz_current": 2549363750.0,
     "cpu_name": "Intel(R) Core(TM) i7-4500U CPU @ 1.80GHz",
     "mem": 65.2,
     "percpu": [{"cpu_number": 0,
                 "guest": 0.0,
                 "guest_nice": 0.0,
                 "idle": 31.0,
                 "iowait": 8.0,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 0.0,
                 "steal": 0.0,
                 "system": 8.0,
                 "total": 69.0,
                 "user": 50.0},
                {"cpu_number": 1,
                 "guest": 0.0,
                 "guest_nice": 0.0,
                 "idle": 51.0,
                 "iowait": 1.0,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 0.0,
                 "steal": 0.0,
                 "system": 8.0,
                 "total": 49.0,
                 "user": 37.0},
                {"cpu_number": 2,
                 "guest": 0.0,
                 "guest_nice": 0.0,
                 "idle": 80.0,
                 "iowait": 0.0,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 0.0,
                 "steal": 0.0,
                 "system": 5.0,
                 "total": 20.0,
                 "user": 9.0},
                {"cpu_number": 3,
                 "guest": 0.0,
                 "guest_nice": 0.0,
                 "idle": 69.0,
                 "iowait": 1.0,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 0.0,
                 "steal": 0.0,
                 "system": 8.0,
                 "total": 31.0,
                 "user": 20.0}],
     "swap": 53.1}

Get a specific field::

    # curl http://localhost:61208/api/3/quicklook/cpu
    {"cpu": 37.6}

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
     "os_version": "5.15.0-46-generic",
     "platform": "64bit"}

Get a specific field::

    # curl http://localhost:61208/api/3/system/os_name
    {"os_name": "Linux"}

GET uptime
----------

Get plugin stats::

    # curl http://localhost:61208/api/3/uptime
    {"seconds": 1849550}

GET all stats
-------------

Get all Glances stats::

    # curl http://localhost:61208/api/3/all
    Return a very big dictionnary (avoid using this request, performances will be poor)...

GET stats history
-----------------

History of a plugin::

    # curl http://localhost:61208/api/3/cpu/history
    {"system": [["2022-09-24T19:01:56.588010", 9.1],
                ["2022-09-24T19:01:57.677626", 9.1],
                ["2022-09-24T19:01:58.852745", 6.0]],
     "user": [["2022-09-24T19:01:56.588000", 35.8],
              ["2022-09-24T19:01:57.677620", 35.8],
              ["2022-09-24T19:01:58.852740", 42.2]]}

Limit history to last 2 values::

    # curl http://localhost:61208/api/3/cpu/history/2
    {"system": [["2022-09-24T19:01:57.677626", 9.1],
                ["2022-09-24T19:01:58.852745", 6.0]],
     "user": [["2022-09-24T19:01:57.677620", 35.8],
              ["2022-09-24T19:01:58.852740", 42.2]]}

History for a specific field::

    # curl http://localhost:61208/api/3/cpu/system/history
    {"system": [["2022-09-24T19:01:56.588010", 9.1],
                ["2022-09-24T19:01:57.677626", 9.1],
                ["2022-09-24T19:01:58.852745", 6.0]]}

Limit history for a specific field to last 2 values::

    # curl http://localhost:61208/api/3/cpu/system/history
    {"system": [["2022-09-24T19:01:57.677626", 9.1],
                ["2022-09-24T19:01:58.852745", 6.0]]}

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


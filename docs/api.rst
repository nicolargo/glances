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
    [[1680939943.0,
      -1,
      "WARNING",
      "MEM",
      77.81948363261539,
      77.81948363261539,
      77.81948363261539,
      77.81948363261539,
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
      "timer": 0.6206016540527344},
     {"count": 0,
      "countmax": 20.0,
      "countmin": None,
      "key": "name",
      "name": "Python",
      "refresh": 3.0,
      "regex": True,
      "result": None,
      "timer": 0.6204922199249268}]

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
                  "timer": 0.6206016540527344}]}

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
     "idle": 70.4,
     "interrupts": 0,
     "iowait": 0.3,
     "irq": 0.0,
     "nice": 0.0,
     "soft_interrupts": 0,
     "softirq": 0.3,
     "steal": 0.0,
     "syscalls": 0,
     "system": 3.7,
     "time_since_update": 1,
     "total": 29.7,
     "user": 25.3}

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
    {"total": 29.7}

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
    {"containers": [{"Command": ["docker-entrypoint.sh", "mongod"],
                     "Id": "c3a1bb27858df965e1c524c6ef33c0fd26d765cae5bcd90fbe9e662b703a52aa",
                     "Image": ["mongo:latest"],
                     "Status": "running",
                     "Uptime": "3 weeks",
                     "cpu": {"total": 0.0},
                     "cpu_percent": 0.0,
                     "io": {"cumulative_ior": 294912,
                            "cumulative_iow": 52502528,
                            "time_since_update": 1},
                     "io_r": None,
                     "io_w": None,
                     "key": "name",
                     "memory": {"cache": None,
                                "limit": 7836196864,
                                "max_usage": None,
                                "rss": None,
                                "usage": 22757376},
                     "memory_usage": 22757376,
                     "name": "docker-mongo_mongo_1",
                     "network": {"cumulative_rx": 9491455,
                                 "cumulative_tx": 7065249,
                                 "time_since_update": 1},
                     "network_rx": None,
                     "network_tx": None},
                    {"Command": ["tini",
                                 "--",
                                 "/docker-entrypoint.sh",
                                 "mongo-express"],
                     "Id": "5aa8f03d6027d00244cf5ce5f4ffe616fd8a31e95ff7091ca02b8d99c00b276c",
                     "Image": ["mongo-express:latest"],
                     "Status": "running",
                     "Uptime": "3 weeks",
                     "cpu": {"total": 0.0},
                     "cpu_percent": 0.0,
                     "io": {},
                     "io_r": None,
                     "io_w": None,
                     "key": "name",
                     "memory": {},
                     "memory_usage": None,
                     "name": "docker-mongo_mongo-express_1",
                     "network": {},
                     "network_rx": None,
                     "network_tx": None},
                    {"Command": ["/portainer"],
                     "Id": "3abd51c615968482d9ccff5afc629f267f6dda113ed68b75b432615fae3b49fb",
                     "Image": ["portainer/portainer-ce:2.9.3"],
                     "Status": "running",
                     "Uptime": "3 weeks",
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
     "version": {"ApiVersion": "1.42",
                 "Arch": "amd64",
                 "BuildTime": "2023-02-09T19:46:56.000000000+00:00",
                 "Components": [{"Details": {"ApiVersion": "1.42",
                                             "Arch": "amd64",
                                             "BuildTime": "2023-02-09T19:46:56.000000000+00:00",
                                             "Experimental": "false",
                                             "GitCommit": "bc3805a",
                                             "GoVersion": "go1.19.5",
                                             "KernelVersion": "5.15.0-58-generic",
                                             "MinAPIVersion": "1.12",
                                             "Os": "linux"},
                                 "Name": "Engine",
                                 "Version": "23.0.1"},
                                {"Details": {"GitCommit": "1e1ea6e986c6c86565bc33d52e34b81b3e2bc71f"},
                                 "Name": "containerd",
                                 "Version": "1.6.19"},
                                {"Details": {"GitCommit": "v1.1.4-0-g5fd4c4d"},
                                 "Name": "runc",
                                 "Version": "1.1.4"},
                                {"Details": {"GitCommit": "de40ad0"},
                                 "Name": "docker-init",
                                 "Version": "0.19.0"}],
                 "GitCommit": "bc3805a",
                 "GoVersion": "go1.19.5",
                 "KernelVersion": "5.15.0-58-generic",
                 "MinAPIVersion": "1.12",
                 "Os": "linux",
                 "Platform": {"Name": "Docker Engine - Community"},
                 "Version": "23.0.1"}}

GET fs
------

Get plugin stats::

    # curl http://localhost:61208/api/3/fs
    [{"device_name": "/dev/mapper/ubuntu--gnome--vg-root",
      "free": 47726575616,
      "fs_type": "ext4",
      "key": "mnt_point",
      "mnt_point": "/",
      "percent": 79.3,
      "size": 243334156288,
      "used": 183220125696},
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
            "free": 47726575616,
            "fs_type": "ext4",
            "key": "mnt_point",
            "mnt_point": "/",
            "percent": 79.3,
            "size": 243334156288,
            "used": 183220125696}]}

GET ip
------

Get plugin stats::

    # curl http://localhost:61208/api/3/ip
    {"address": "192.168.1.14",
     "gateway": "192.168.1.1",
     "mask": "255.255.255.0",
     "mask_cidr": 24,
     "public_address": "92.151.148.66",
     "public_info_human": ""}

Get a specific field::

    # curl http://localhost:61208/api/3/ip/gateway
    {"gateway": "192.168.1.1"}

GET load
--------

Get plugin stats::

    # curl http://localhost:61208/api/3/load
    {"cpucore": 4,
     "min1": 2.0029296875,
     "min15": 1.28759765625,
     "min5": 1.45166015625}

Fields descriptions:

* **min1**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 1 minute (unit is *float*)
* **min5**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 5 minutes (unit is *float*)
* **min15**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 15 minutes (unit is *float*)
* **cpucore**: Total number of CPU core (unit is *number*)

Get a specific field::

    # curl http://localhost:61208/api/3/load/min1
    {"min1": 2.0029296875}

GET mem
-------

Get plugin stats::

    # curl http://localhost:61208/api/3/mem
    {"active": 2645381120,
     "available": 1738108928,
     "buffers": 318296064,
     "cached": 2023813120,
     "free": 1738108928,
     "inactive": 3751419904,
     "percent": 77.8,
     "shared": 562442240,
     "total": 7836196864,
     "used": 6098087936}

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
    {"free": 5987336192,
     "percent": 25.9,
     "sin": 12361428992,
     "sout": 19754192896,
     "time_since_update": 1,
     "total": 8082419712,
     "used": 2095083520}

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
      "cumulative_cx": 1606186076,
      "cumulative_rx": 803093038,
      "cumulative_tx": 803093038,
      "cx": 3024,
      "interface_name": "lo",
      "is_up": True,
      "key": "interface_name",
      "rx": 1512,
      "speed": 0,
      "time_since_update": 1,
      "tx": 1512},
     {"alias": None,
      "cumulative_cx": 43116202825,
      "cumulative_rx": 41603851987,
      "cumulative_tx": 1512350838,
      "cx": 29024,
      "interface_name": "wlp2s0",
      "is_up": True,
      "key": "interface_name",
      "rx": 22262,
      "speed": 0,
      "time_since_update": 1,
      "tx": 6762}]

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
                        "tap-1e376645a40",
                        "br-ef0a06c4e10f",
                        "vethb3a7bab",
                        "vethf490fc8",
                        "veth335689d"]}

Get a specific item when field matchs the given value::

    # curl http://localhost:61208/api/3/network/interface_name/lo
    {"lo": [{"alias": None,
             "cumulative_cx": 1606186076,
             "cumulative_rx": 803093038,
             "cumulative_tx": 803093038,
             "cx": 3024,
             "interface_name": "lo",
             "is_up": True,
             "key": "interface_name",
             "rx": 1512,
             "speed": 0,
             "time_since_update": 1,
             "tx": 1512}]}

GET now
-------

Get plugin stats::

    # curl http://localhost:61208/api/3/now
    "2023-04-08 09:45:42 CEST"

GET percpu
----------

Get plugin stats::

    # curl http://localhost:61208/api/3/percpu
    [{"cpu_number": 0,
      "guest": 0.0,
      "guest_nice": 0.0,
      "idle": 64.0,
      "iowait": 0.0,
      "irq": 0.0,
      "key": "cpu_number",
      "nice": 0.0,
      "softirq": 0.0,
      "steal": 0.0,
      "system": 1.0,
      "total": 36.0,
      "user": 5.0},
     {"cpu_number": 1,
      "guest": 0.0,
      "guest_nice": 0.0,
      "idle": 5.0,
      "iowait": 0.0,
      "irq": 0.0,
      "key": "cpu_number",
      "nice": 0.0,
      "softirq": 0.0,
      "steal": 0.0,
      "system": 2.0,
      "total": 95.0,
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
      "status": 0.006088,
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
                      "status": 0.006088,
                      "timeout": 3}]}

GET processcount
----------------

Get plugin stats::

    # curl http://localhost:61208/api/3/processcount
    {"pid_max": 0, "running": 1, "sleeping": 330, "thread": 1714, "total": 394}

Get a specific field::

    # curl http://localhost:61208/api/3/processcount/total
    {"total": 394}

GET processlist
---------------

Get plugin stats::

    # curl http://localhost:61208/api/3/processlist
    [{"cmdline": ["/snap/firefox/2391/usr/lib/firefox/firefox",
                  "-contentproc",
                  "-childID",
                  "6",
                  "-isForBrowser",
                  "-prefsLen",
                  "37134",
                  "-prefMapSize",
                  "238694",
                  "-jsInitLen",
                  "246560",
                  "-parentBuildID",
                  "20230228074855",
                  "-appDir",
                  "/snap/firefox/2391/usr/lib/firefox/browser",
                  "{c1ca9a6d-573a-4f47-ae48-01d6063a6f70}",
                  "971363",
                  "true",
                  "tab"],
      "cpu_percent": 0.0,
      "cpu_times": [1150.92, 205.51, 0.0, 0.0, 0.0],
      "gids": [1000, 1000, 1000],
      "io_counters": [200408064, 0, 0, 0, 0],
      "key": "pid",
      "memory_info": [502607872, 3444826112, 39489536, 626688, 0, 847261696, 0],
      "memory_percent": 6.413926050135537,
      "name": "WebExtensions",
      "nice": 0,
      "num_threads": 20,
      "pid": 971772,
      "status": "S",
      "time_since_update": 1,
      "username": "nicolargo"},
     {"cmdline": ["/snap/firefox/2391/usr/lib/firefox/firefox"],
      "cpu_percent": 0.0,
      "cpu_times": [6001.81, 1837.81, 4047.83, 726.16, 0.0],
      "gids": [1000, 1000, 1000],
      "io_counters": [3540272128, 7502446592, 0, 0, 0],
      "key": "pid",
      "memory_info": [419807232, 22266421248, 106196992, 626688, 0, 1420001280, 0],
      "memory_percent": 5.357282866751623,
      "name": "firefox",
      "nice": 0,
      "num_threads": 181,
      "pid": 971363,
      "status": "S",
      "time_since_update": 1,
      "username": "nicolargo"}]

Get a specific field::

    # curl http://localhost:61208/api/3/processlist/pid
    {"pid": [971772,
             971363,
             1142094,
             4150,
             971555,
             1152927,
             1004923,
             971564,
             971559,
             1141786,
             1150071,
             1151591,
             4473,
             1003910,
             1004590,
             1141895,
             1004867,
             904358,
             1004969,
             1004902,
             1070813,
             1108336,
             6074,
             1159121,
             1158993,
             1159255,
             971522,
             1142299,
             883393,
             1112467,
             2512,
             1141869,
             1141872,
             1159353,
             3351,
             4035,
             1141798,
             4413,
             1004911,
             4544,
             1141957,
             1141939,
             1005000,
             95798,
             1021669,
             1145400,
             1152205,
             1085807,
             2721,
             1119851,
             904833,
             4248,
             4585,
             972136,
             4932,
             904838,
             1152226,
             971505,
             3955,
             1,
             1635,
             4332,
             1145411,
             4325,
             1660,
             14455,
             1152242,
             4561,
             4214,
             4331,
             4223,
             904977,
             4625,
             1681,
             1004872,
             4445,
             1145919,
             3934,
             4659,
             14458,
             1876,
             3944,
             4352,
             972138,
             4327,
             4263,
             1145412,
             905822,
             4130,
             1145413,
             4330,
             1004873,
             1634,
             4137,
             4233,
             3968,
             129087,
             4339,
             1141912,
             1085898,
             993612,
             1145410,
             1145536,
             4261,
             4377,
             59511,
             883381,
             3966,
             2239,
             4182,
             4452,
             17189,
             1682,
             2179,
             129101,
             904778,
             129097,
             1643,
             4524,
             5299,
             904722,
             219792,
             4229,
             96102,
             17205,
             903463,
             4192,
             706956,
             1666,
             3976,
             1631,
             1673,
             4201,
             1655,
             1873,
             4335,
             3971,
             4329,
             4443,
             4392,
             904801,
             1617,
             4155,
             1675,
             4050,
             1661,
             4337,
             4328,
             4573,
             903414,
             4324,
             4045,
             1885,
             4166,
             4178,
             1626,
             4334,
             4173,
             4348,
             4212,
             1646,
             1670,
             4347,
             4119,
             4485,
             9703,
             1159314,
             1004889,
             4314,
             49191,
             3952,
             1633,
             49179,
             14505,
             2020,
             4162,
             1441,
             129100,
             3953,
             3700,
             4579,
             1685,
             1449,
             129099,
             1145294,
             2485,
             3354,
             1450,
             2472,
             49182,
             1618,
             1159352,
             1154223,
             1145290,
             1004875,
             49194,
             4323,
             904754,
             2480,
             904748,
             904639,
             4018,
             904665,
             3707,
             904706,
             1156987,
             904719,
             3701,
             904643,
             219931,
             1803,
             904652,
             1804,
             4820,
             2475,
             3945,
             2503,
             1447,
             1695,
             1628,
             706960,
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
             220739,
             220749,
             220750,
             220751,
             220752,
             220756,
             904821,
             1148559,
             1148560,
             1148562,
             1151236,
             1151955,
             1151966,
             1151970,
             1151971,
             1151973,
             1151974,
             1151975,
             1152026,
             1154944,
             1155108,
             1155798,
             1156380,
             1156410,
             1156605,
             1157612,
             1157817,
             1157841,
             1158554,
             1158745,
             1159075,
             1159119]}

Get a specific item when field matchs the given value::

    # curl http://localhost:61208/api/3/processlist/pid/971772
    {"971772": [{"cmdline": ["/snap/firefox/2391/usr/lib/firefox/firefox",
                             "-contentproc",
                             "-childID",
                             "6",
                             "-isForBrowser",
                             "-prefsLen",
                             "37134",
                             "-prefMapSize",
                             "238694",
                             "-jsInitLen",
                             "246560",
                             "-parentBuildID",
                             "20230228074855",
                             "-appDir",
                             "/snap/firefox/2391/usr/lib/firefox/browser",
                             "{c1ca9a6d-573a-4f47-ae48-01d6063a6f70}",
                             "971363",
                             "true",
                             "tab"],
                 "cpu_percent": 0.0,
                 "cpu_times": [1150.92, 205.51, 0.0, 0.0, 0.0],
                 "gids": [1000, 1000, 1000],
                 "io_counters": [200408064, 0, 0, 0, 0],
                 "key": "pid",
                 "memory_info": [502607872,
                                 3444826112,
                                 39489536,
                                 626688,
                                 0,
                                 847261696,
                                 0],
                 "memory_percent": 6.413926050135537,
                 "name": "WebExtensions",
                 "nice": 0,
                 "num_threads": 20,
                 "pid": 971772,
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
    {"cpu": 29.7,
     "cpu_hz": 3000000000.0,
     "cpu_hz_current": 1872249249.9999998,
     "cpu_name": "Intel(R) Core(TM) i7-4500U CPU @ 1.80GHz",
     "mem": 77.8,
     "percpu": [{"cpu_number": 0,
                 "guest": 0.0,
                 "guest_nice": 0.0,
                 "idle": 64.0,
                 "iowait": 0.0,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 0.0,
                 "steal": 0.0,
                 "system": 1.0,
                 "total": 36.0,
                 "user": 5.0},
                {"cpu_number": 1,
                 "guest": 0.0,
                 "guest_nice": 0.0,
                 "idle": 5.0,
                 "iowait": 0.0,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 0.0,
                 "steal": 0.0,
                 "system": 2.0,
                 "total": 95.0,
                 "user": 68.0},
                {"cpu_number": 2,
                 "guest": 0.0,
                 "guest_nice": 0.0,
                 "idle": 67.0,
                 "iowait": 0.0,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 0.0,
                 "steal": 0.0,
                 "system": 2.0,
                 "total": 33.0,
                 "user": 2.0},
                {"cpu_number": 3,
                 "guest": 0.0,
                 "guest_nice": 0.0,
                 "idle": 67.0,
                 "iowait": 0.0,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 0.0,
                 "steal": 0.0,
                 "system": 3.0,
                 "total": 33.0,
                 "user": 4.0}],
     "swap": 25.9}

Get a specific field::

    # curl http://localhost:61208/api/3/quicklook/cpu
    {"cpu": 29.7}

GET sensors
-----------

Get plugin stats::

    # curl http://localhost:61208/api/3/sensors
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

Get a specific field::

    # curl http://localhost:61208/api/3/sensors/label
    {"label": ["acpitz 0",
               "acpitz 1",
               "Package id 0",
               "Core 0",
               "Core 1",
               "CPU",
               "Ambient",
               "SODIMM",
               "BAT BAT0"]}

Get a specific item when field matchs the given value::

    # curl http://localhost:61208/api/3/sensors/label/acpitz 0
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
    "83 days, 16:34:33"

GET all stats
-------------

Get all Glances stats::

    # curl http://localhost:61208/api/3/all
    Return a very big dictionnary (avoid using this request, performances will be poor)...

GET stats history
-----------------

History of a plugin::

    # curl http://localhost:61208/api/3/cpu/history
    {"system": [["2023-04-08T09:45:43.167852", 3.7],
                ["2023-04-08T09:45:44.242850", 3.7],
                ["2023-04-08T09:45:45.342786", 3.3]],
     "user": [["2023-04-08T09:45:43.167846", 25.3],
              ["2023-04-08T09:45:44.242844", 25.3],
              ["2023-04-08T09:45:45.342782", 5.5]]}

Limit history to last 2 values::

    # curl http://localhost:61208/api/3/cpu/history/2
    {"system": [["2023-04-08T09:45:44.242850", 3.7],
                ["2023-04-08T09:45:45.342786", 3.3]],
     "user": [["2023-04-08T09:45:44.242844", 25.3],
              ["2023-04-08T09:45:45.342782", 5.5]]}

History for a specific field::

    # curl http://localhost:61208/api/3/cpu/system/history
    {"system": [["2023-04-08T09:45:43.167852", 3.7],
                ["2023-04-08T09:45:44.242850", 3.7],
                ["2023-04-08T09:45:45.342786", 3.3]]}

Limit history for a specific field to last 2 values::

    # curl http://localhost:61208/api/3/cpu/system/history
    {"system": [["2023-04-08T09:45:44.242850", 3.7],
                ["2023-04-08T09:45:45.342786", 3.3]]}

GET limits (used for thresholds)
--------------------------------

All limits/thresholds::

    # curl http://localhost:61208/api/3/all/limits
    {"alert": {"history_size": 1200.0},
     "amps": {"amps_disable": ["False"], "history_size": 1200.0},
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


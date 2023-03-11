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
      "timer": 0.8183016777038574},
     {"count": 0,
      "countmax": 20.0,
      "countmin": None,
      "key": "name",
      "name": "Python",
      "refresh": 3.0,
      "regex": True,
      "result": None,
      "timer": 0.8182027339935303}]

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
                  "timer": 0.8183016777038574}]}

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
     "idle": 70.9,
     "interrupts": 0,
     "iowait": 0.0,
     "irq": 0.0,
     "nice": 0.0,
     "soft_interrupts": 0,
     "softirq": 0.0,
     "steal": 0.0,
     "syscalls": 0,
     "system": 4.0,
     "time_since_update": 1,
     "total": 29.8,
     "user": 25.2}

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
    {"total": 29.8}

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
                     "Uptime": "1 months",
                     "cpu": {"total": 0.0},
                     "cpu_percent": 0.0,
                     "io": {"cumulative_ior": 847872,
                            "cumulative_iow": 53813248,
                            "time_since_update": 1},
                     "io_r": None,
                     "io_w": None,
                     "key": "name",
                     "memory": {"cache": None,
                                "limit": 7836196864,
                                "max_usage": None,
                                "rss": None,
                                "usage": 23642112},
                     "memory_usage": 23642112,
                     "name": "docker-mongo_mongo_1",
                     "network": {"cumulative_rx": 37744307,
                                 "cumulative_tx": 28244833,
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
                     "Uptime": "1 months",
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
                     "Uptime": "1 months",
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
                 "BuildTime": "2023-02-01T17:49:08.000000000+00:00",
                 "Components": [{"Details": {"ApiVersion": "1.42",
                                             "Arch": "amd64",
                                             "BuildTime": "2023-02-01T17:49:08.000000000+00:00",
                                             "Experimental": "false",
                                             "GitCommit": "d7573ab",
                                             "GoVersion": "go1.19.5",
                                             "KernelVersion": "5.15.0-58-generic",
                                             "MinAPIVersion": "1.12",
                                             "Os": "linux"},
                                 "Name": "Engine",
                                 "Version": "23.0.0"},
                                {"Details": {"GitCommit": "31aa4358a36870b21a992d3ad2bef29e1d693bec"},
                                 "Name": "containerd",
                                 "Version": "1.6.16"},
                                {"Details": {"GitCommit": "v1.1.4-0-g5fd4c4d"},
                                 "Name": "runc",
                                 "Version": "1.1.4"},
                                {"Details": {"GitCommit": "de40ad0"},
                                 "Name": "docker-init",
                                 "Version": "0.19.0"}],
                 "GitCommit": "d7573ab",
                 "GoVersion": "go1.19.5",
                 "KernelVersion": "5.15.0-58-generic",
                 "MinAPIVersion": "1.12",
                 "Os": "linux",
                 "Platform": {"Name": "Docker Engine - Community"},
                 "Version": "23.0.0"}}

GET fs
------

Get plugin stats::

    # curl http://localhost:61208/api/3/fs
    [{"device_name": "/dev/mapper/ubuntu--gnome--vg-root",
      "free": 53470863360,
      "fs_type": "ext4",
      "key": "mnt_point",
      "mnt_point": "/",
      "percent": 76.8,
      "size": 243334156288,
      "used": 177475837952},
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
            "free": 53470863360,
            "fs_type": "ext4",
            "key": "mnt_point",
            "mnt_point": "/",
            "percent": 76.8,
            "size": 243334156288,
            "used": 177475837952}]}

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
     "min1": 0.79833984375,
     "min15": 0.7431640625,
     "min5": 0.8056640625}

Fields descriptions:

* **min1**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 1 minute (unit is *float*)
* **min5**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 5 minutes (unit is *float*)
* **min15**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 15 minutes (unit is *float*)
* **cpucore**: Total number of CPU core (unit is *number*)

Get a specific field::

    # curl http://localhost:61208/api/3/load/min1
    {"min1": 0.79833984375}

GET mem
-------

Get plugin stats::

    # curl http://localhost:61208/api/3/mem
    {"active": 2350882816,
     "available": 2422988800,
     "buffers": 131072000,
     "cached": 2795134976,
     "free": 2422988800,
     "inactive": 3522777088,
     "percent": 69.1,
     "shared": 685944832,
     "total": 7836196864,
     "used": 5413208064}

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
    {"free": 5875109888,
     "percent": 27.3,
     "sin": 8760786944,
     "sout": 14506393600,
     "time_since_update": 1,
     "total": 8082419712,
     "used": 2207309824}

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
      "cumulative_cx": 1140515614,
      "cumulative_rx": 570257807,
      "cumulative_tx": 570257807,
      "cx": 5342,
      "interface_name": "lo",
      "is_up": True,
      "key": "interface_name",
      "rx": 2671,
      "speed": 0,
      "time_since_update": 1,
      "tx": 2671},
     {"alias": None,
      "cumulative_cx": 36011739106,
      "cumulative_rx": 34790353651,
      "cumulative_tx": 1221385455,
      "cx": 24457,
      "interface_name": "wlp2s0",
      "is_up": True,
      "key": "interface_name",
      "rx": 18960,
      "speed": 0,
      "time_since_update": 1,
      "tx": 5497}]

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
                        "veth9910148",
                        "veth5e7315e",
                        "veth24ae93e"]}

Get a specific item when field matchs the given value::

    # curl http://localhost:61208/api/3/network/interface_name/lo
    {"lo": [{"alias": None,
             "cumulative_cx": 1140515614,
             "cumulative_rx": 570257807,
             "cumulative_tx": 570257807,
             "cx": 5342,
             "interface_name": "lo",
             "is_up": True,
             "key": "interface_name",
             "rx": 2671,
             "speed": 0,
             "time_since_update": 1,
             "tx": 2671}]}

GET now
-------

Get plugin stats::

    # curl http://localhost:61208/api/3/now
    "2023-03-11 17:30:43 CET"

GET percpu
----------

Get plugin stats::

    # curl http://localhost:61208/api/3/percpu
    [{"cpu_number": 0,
      "guest": 0.0,
      "guest_nice": 0.0,
      "idle": 22.0,
      "iowait": 0.0,
      "irq": 0.0,
      "key": "cpu_number",
      "nice": 0.0,
      "softirq": 0.0,
      "steal": 0.0,
      "system": 1.0,
      "total": 78.0,
      "user": 67.0},
     {"cpu_number": 1,
      "guest": 0.0,
      "guest_nice": 0.0,
      "idle": 81.0,
      "iowait": 0.0,
      "irq": 0.0,
      "key": "cpu_number",
      "nice": 0.0,
      "softirq": 0.0,
      "steal": 0.0,
      "system": 2.0,
      "total": 19.0,
      "user": 7.0}]

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
      "status": 0.003449,
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
                        "status": 0.003449,
                        "timeout": 3}]}

GET processcount
----------------

Get plugin stats::

    # curl http://localhost:61208/api/3/processcount
    {"pid_max": 0, "running": 1, "sleeping": 319, "thread": 1542, "total": 387}

Get a specific field::

    # curl http://localhost:61208/api/3/processcount/total
    {"total": 387}

GET processlist
---------------

Get plugin stats::

    # curl http://localhost:61208/api/3/processlist
    [{"cmdline": ["/snap/firefox/2391/usr/lib/firefox/firefox"],
      "cpu_percent": 0.0,
      "cpu_times": [1287.11, 419.09, 1097.08, 148.64, 0.0],
      "gids": [1000, 1000, 1000],
      "io_counters": [502609920, 1333940224, 0, 0, 0],
      "key": "pid",
      "memory_info": [509206528, 21605502976, 176431104, 626688, 0, 833679360, 0],
      "memory_percent": 6.498133429231825,
      "name": "firefox",
      "nice": 0,
      "num_threads": 117,
      "pid": 846720,
      "status": "S",
      "time_since_update": 1,
      "username": "nicolargo"},
     {"cmdline": ["/snap/firefox/2391/usr/lib/firefox/firefox",
                  "-contentproc",
                  "-childID",
                  "1",
                  "-isForBrowser",
                  "-prefsLen",
                  "31514",
                  "-prefMapSize",
                  "238439",
                  "-jsInitLen",
                  "246560",
                  "-parentBuildID",
                  "20230228074855",
                  "-appDir",
                  "/snap/firefox/2391/usr/lib/firefox/browser",
                  "{0f8147f2-5422-4d6d-9491-68894fb5c106}",
                  "846720",
                  "true",
                  "tab"],
      "cpu_percent": 0.0,
      "cpu_times": [185.15, 34.08, 0.0, 0.0, 0.0],
      "gids": [1000, 1000, 1000],
      "io_counters": [9207808, 0, 0, 0, 0],
      "key": "pid",
      "memory_info": [435576832, 3219697664, 100659200, 626688, 0, 613511168, 0],
      "memory_percent": 5.558523344418112,
      "name": "WebExtensions",
      "nice": 0,
      "num_threads": 20,
      "pid": 846991,
      "status": "S",
      "time_since_update": 1,
      "username": "nicolargo"}]

Get a specific field::

    # curl http://localhost:61208/api/3/processlist/pid
    {"pid": [846720,
             846991,
             847043,
             4150,
             847035,
             255919,
             255685,
             847039,
             859882,
             836010,
             255737,
             847051,
             4473,
             847007,
             285410,
             422,
             875536,
             255627,
             258480,
             6074,
             255751,
             876641,
             876390,
             847507,
             876962,
             255664,
             62850,
             877142,
             2512,
             4544,
             4035,
             846970,
             847508,
             256270,
             258481,
             255769,
             596789,
             285072,
             95798,
             2721,
             4585,
             255672,
             4413,
             789543,
             860282,
             285950,
             4248,
             789544,
             3955,
             286011,
             255906,
             255976,
             4932,
             1635,
             829380,
             829424,
             14455,
             1,
             4325,
             4331,
             4223,
             4332,
             4561,
             4214,
             3351,
             4625,
             1660,
             1681,
             219792,
             14458,
             1876,
             4327,
             3934,
             3944,
             5299,
             4182,
             4130,
             4659,
             4263,
             4445,
             286108,
             4339,
             4233,
             4137,
             2239,
             1682,
             129087,
             4352,
             129101,
             4261,
             255632,
             830552,
             823483,
             17189,
             4377,
             129097,
             3968,
             1634,
             1442,
             255633,
             1777,
             2179,
             117714,
             59511,
             4330,
             4452,
             1643,
             706956,
             17205,
             1655,
             4524,
             3700,
             706252,
             3966,
             4229,
             3971,
             1873,
             96102,
             4201,
             4192,
             1673,
             4334,
             4392,
             4155,
             4329,
             4443,
             1617,
             4328,
             1675,
             4573,
             4485,
             1661,
             4337,
             4050,
             285853,
             1631,
             4178,
             4166,
             1666,
             4348,
             4324,
             4335,
             4045,
             4347,
             285970,
             285913,
             4173,
             468,
             4212,
             3976,
             1885,
             1626,
             1676,
             4314,
             1670,
             9703,
             1646,
             4119,
             1443,
             877118,
             3952,
             129099,
             49191,
             2020,
             255649,
             1633,
             4162,
             1441,
             14505,
             49179,
             3953,
             3701,
             3354,
             129100,
             1449,
             1685,
             4579,
             1450,
             2472,
             219931,
             49182,
             1618,
             843176,
             877141,
             1804,
             49194,
             1803,
             4323,
             2480,
             3707,
             4018,
             255635,
             285883,
             285777,
             285877,
             872737,
             285835,
             285843,
             285784,
             285905,
             3945,
             4820,
             285898,
             2475,
             1447,
             2503,
             2485,
             706960,
             1628,
             1695,
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
             285941,
             829051,
             829052,
             829054,
             859825,
             860163,
             860164,
             860166,
             860167,
             860169,
             860220,
             868345,
             871910,
             872852,
             873104,
             873258,
             873643,
             874420,
             874573,
             874834,
             874866,
             875114,
             875396,
             875564,
             876077,
             876089,
             876121,
             876528,
             876924,
             877134]}

Get a specific item when field matchs the given value::

    # curl http://localhost:61208/api/3/processlist/pid/846720
    {"846720": [{"cmdline": ["/snap/firefox/2391/usr/lib/firefox/firefox"],
                 "cpu_percent": 0.0,
                 "cpu_times": [1287.11, 419.09, 1097.08, 148.64, 0.0],
                 "gids": [1000, 1000, 1000],
                 "io_counters": [502609920, 1333940224, 0, 0, 0],
                 "key": "pid",
                 "memory_info": [509206528,
                                 21605502976,
                                 176431104,
                                 626688,
                                 0,
                                 833679360,
                                 0],
                 "memory_percent": 6.498133429231825,
                 "name": "firefox",
                 "nice": 0,
                 "num_threads": 117,
                 "pid": 846720,
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
    {"cpu": 29.8,
     "cpu_hz": 3000000000.0,
     "cpu_hz_current": 1604295750.0,
     "cpu_name": "Intel(R) Core(TM) i7-4500U CPU @ 1.80GHz",
     "mem": 69.1,
     "percpu": [{"cpu_number": 0,
                 "guest": 0.0,
                 "guest_nice": 0.0,
                 "idle": 22.0,
                 "iowait": 0.0,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 0.0,
                 "steal": 0.0,
                 "system": 1.0,
                 "total": 78.0,
                 "user": 67.0},
                {"cpu_number": 1,
                 "guest": 0.0,
                 "guest_nice": 0.0,
                 "idle": 81.0,
                 "iowait": 0.0,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 0.0,
                 "steal": 0.0,
                 "system": 2.0,
                 "total": 19.0,
                 "user": 7.0},
                {"cpu_number": 2,
                 "guest": 0.0,
                 "guest_nice": 0.0,
                 "idle": 70.0,
                 "iowait": 0.0,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 0.0,
                 "steal": 0.0,
                 "system": 2.0,
                 "total": 30.0,
                 "user": 20.0},
                {"cpu_number": 3,
                 "guest": 0.0,
                 "guest_nice": 0.0,
                 "idle": 83.0,
                 "iowait": 0.0,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 0.0,
                 "steal": 0.0,
                 "system": 5.0,
                 "total": 17.0,
                 "user": 6.0}],
     "swap": 27.3}

Get a specific field::

    # curl http://localhost:61208/api/3/quicklook/cpu
    {"cpu": 29.8}

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
    "56 days, 0:19:45"

GET all stats
-------------

Get all Glances stats::

    # curl http://localhost:61208/api/3/all
    Return a very big dictionnary (avoid using this request, performances will be poor)...

GET stats history
-----------------

History of a plugin::

    # curl http://localhost:61208/api/3/cpu/history
    {"system": [["2023-03-11T17:30:44.653473", 4.0],
                ["2023-03-11T17:30:45.724303", 4.0],
                ["2023-03-11T17:30:46.822979", 0.9]],
     "user": [["2023-03-11T17:30:44.653466", 25.2],
              ["2023-03-11T17:30:45.724298", 25.2],
              ["2023-03-11T17:30:46.822974", 5.1]]}

Limit history to last 2 values::

    # curl http://localhost:61208/api/3/cpu/history/2
    {"system": [["2023-03-11T17:30:45.724303", 4.0],
                ["2023-03-11T17:30:46.822979", 0.9]],
     "user": [["2023-03-11T17:30:45.724298", 25.2],
              ["2023-03-11T17:30:46.822974", 5.1]]}

History for a specific field::

    # curl http://localhost:61208/api/3/cpu/system/history
    {"system": [["2023-03-11T17:30:44.653473", 4.0],
                ["2023-03-11T17:30:45.724303", 4.0],
                ["2023-03-11T17:30:46.822979", 0.9]]}

Limit history for a specific field to last 2 values::

    # curl http://localhost:61208/api/3/cpu/system/history
    {"system": [["2023-03-11T17:30:45.724303", 4.0],
                ["2023-03-11T17:30:46.822979", 0.9]]}

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


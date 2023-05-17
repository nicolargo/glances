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
      "timer": 1.0500612258911133},
     {"count": 0,
      "countmax": 20.0,
      "countmin": None,
      "key": "name",
      "name": "Python",
      "refresh": 3.0,
      "regex": True,
      "result": None,
      "timer": 1.0497639179229736}]

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
                  "timer": 1.0500612258911133}]}

GET connections
---------------

Get plugin stats::

    # curl http://localhost:61208/api/3/connections
    {"net_connections_enabled": True, "nf_conntrack_enabled": True}

Get a specific field::

    # curl http://localhost:61208/api/3/connections/net_connections_enabled
    {"net_connections_enabled": True}

GET containers
--------------

Get plugin stats::

    # curl http://localhost:61208/api/3/containers
    {"containers": [{"Command": ["top"],
                     "Created": "2023-05-08T15:29:34.918692365+02:00",
                     "Id": "4b7f732d43e4bc5d92fe5298cba025b550e6a608754c1c38f9a90aaecd46b8f9",
                     "Image": "["docker.io/library/ubuntu:latest"]",
                     "Status": "running",
                     "Uptime": "1 weeks",
                     "cpu": {"total": 9.174878746049114e-07},
                     "cpu_percent": 9.174878746049114e-07,
                     "engine": "podman",
                     "io": {"ior": 0.0, "iow": 0.0, "time_since_update": 1},
                     "io_r": 0.0,
                     "io_w": 0.0,
                     "key": "name",
                     "memory": {"limit": 7836184576.0, "usage": 1548288.0},
                     "memory_usage": 1548288.0,
                     "name": "frosty_bouman",
                     "network": {"rx": 0.0, "time_since_update": 1, "tx": 0.0},
                     "network_rx": 0.0,
                     "network_tx": 0.0,
                     "pod_id": "8d0f1c783def",
                     "pod_name": "frosty_bouman"},
                    {"Command": [],
                     "Created": "2022-10-22T14:23:03.120912374+02:00",
                     "Id": "9491515251edcd5bb5dc17205d7ee573c0be96fe0b08b0a12a7e2cea874565ea",
                     "Image": "["k8s.gcr.io/pause:3.5"]",
                     "Status": "running",
                     "Uptime": "1 weeks",
                     "cpu": {"total": 2.644991475256057e-10},
                     "cpu_percent": 2.644991475256057e-10,
                     "engine": "podman",
                     "io": {"ior": 0.0, "iow": 0.0, "time_since_update": 1},
                     "io_r": 0.0,
                     "io_w": 0.0,
                     "key": "name",
                     "memory": {"limit": 7836184576.0, "usage": 434176.0},
                     "memory_usage": 434176.0,
                     "name": "8d0f1c783def-infra",
                     "network": {"rx": 0.0, "time_since_update": 1, "tx": 0.0},
                     "network_rx": 0.0,
                     "network_tx": 0.0,
                     "pod_id": "8d0f1c783def",
                     "pod_name": "8d0f1c783def-infra"},
                    {"Command": ["/portainer"],
                     "Created": "2022-10-29T14:59:10.266701439Z",
                     "Id": "3abd51c615968482d9ccff5afc629f267f6dda113ed68b75b432615fae3b49fb",
                     "Image": ["portainer/portainer-ce:2.9.3"],
                     "Status": "running",
                     "Uptime": "4 days",
                     "cpu": {"total": 0.0},
                     "cpu_percent": 0.0,
                     "engine": "docker",
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
     "version": {},
     "version_podman": {}}

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
     "idle": 66.1,
     "interrupts": 0,
     "iowait": 0.2,
     "irq": 0.0,
     "nice": 0.0,
     "soft_interrupts": 0,
     "softirq": 0.0,
     "steal": 0.0,
     "syscalls": 0,
     "system": 6.6,
     "time_since_update": 1,
     "total": 35.5,
     "user": 27.2}

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
    {"total": 35.5}

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
      "free": 8354877440,
      "fs_type": "ext4",
      "key": "mnt_point",
      "mnt_point": "/",
      "percent": 96.4,
      "size": 243334156288,
      "used": 222591823872},
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
            "free": 8354877440,
            "fs_type": "ext4",
            "key": "mnt_point",
            "mnt_point": "/",
            "percent": 96.4,
            "size": 243334156288,
            "used": 222591823872}]}

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
     "min1": 2.630859375,
     "min15": 1.4560546875,
     "min5": 1.42822265625}

Fields descriptions:

* **min1**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 1 minute (unit is *float*)
* **min5**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 5 minutes (unit is *float*)
* **min15**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 15 minutes (unit is *float*)
* **cpucore**: Total number of CPU core (unit is *number*)

Get a specific field::

    # curl http://localhost:61208/api/3/load/min1
    {"min1": 2.630859375}

GET mem
-------

Get plugin stats::

    # curl http://localhost:61208/api/3/mem
    {"active": 3263430656,
     "available": 2511720448,
     "buffers": 743632896,
     "cached": 2523037696,
     "free": 2511720448,
     "inactive": 3192811520,
     "percent": 67.9,
     "shared": 627544064,
     "total": 7836184576,
     "used": 5324464128}

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
    {"total": 7836184576}

GET memswap
-----------

Get plugin stats::

    # curl http://localhost:61208/api/3/memswap
    {"free": 5526786048,
     "percent": 31.6,
     "sin": 2906378240,
     "sout": 5210710016,
     "time_since_update": 1,
     "total": 8082419712,
     "used": 2555633664}

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
      "cumulative_cx": 151835804,
      "cumulative_rx": 75917902,
      "cumulative_tx": 75917902,
      "cx": 6340,
      "interface_name": "lo",
      "is_up": True,
      "key": "interface_name",
      "rx": 3170,
      "speed": 0,
      "time_since_update": 1,
      "tx": 3170},
     {"alias": None,
      "cumulative_cx": 8971420885,
      "cumulative_rx": 8692531338,
      "cumulative_tx": 278889547,
      "cx": 32318,
      "interface_name": "wlp2s0",
      "is_up": True,
      "key": "interface_name",
      "rx": 20465,
      "speed": 0,
      "time_since_update": 1,
      "tx": 11853}]

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
                        "br_grafana",
                        "mpqemubr0",
                        "vethcddb0e6"]}

Get a specific item when field matchs the given value::

    # curl http://localhost:61208/api/3/network/interface_name/lo
    {"lo": [{"alias": None,
             "cumulative_cx": 151835804,
             "cumulative_rx": 75917902,
             "cumulative_tx": 75917902,
             "cx": 6340,
             "interface_name": "lo",
             "is_up": True,
             "key": "interface_name",
             "rx": 3170,
             "speed": 0,
             "time_since_update": 1,
             "tx": 3170}]}

GET now
-------

Get plugin stats::

    # curl http://localhost:61208/api/3/now
    "2023-05-17 11:24:06 CEST"

GET percpu
----------

Get plugin stats::

    # curl http://localhost:61208/api/3/percpu
    [{"cpu_number": 0,
      "guest": 0.0,
      "guest_nice": 0.0,
      "idle": 20.2,
      "iowait": 0.0,
      "irq": 0.0,
      "key": "cpu_number",
      "nice": 0.0,
      "softirq": 0.0,
      "steal": 0.0,
      "system": 6.7,
      "total": 79.8,
      "user": 73.1},
     {"cpu_number": 1,
      "guest": 0.0,
      "guest_nice": 0.0,
      "idle": 70.6,
      "iowait": 0.0,
      "irq": 0.0,
      "key": "cpu_number",
      "nice": 0.0,
      "softirq": 0.0,
      "steal": 0.0,
      "system": 6.7,
      "total": 29.4,
      "user": 22.7}]

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
      "status": 0.005277,
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
                      "status": 0.005277,
                      "timeout": 3}]}

GET processcount
----------------

Get plugin stats::

    # curl http://localhost:61208/api/3/processcount
    {"pid_max": 0, "running": 1, "sleeping": 316, "thread": 1601, "total": 384}

Get a specific field::

    # curl http://localhost:61208/api/3/processcount/total
    {"total": 384}

GET processlist
---------------

Get plugin stats::

    # curl http://localhost:61208/api/3/processlist
    [{"cmdline": ["/snap/firefox/2605/usr/lib/firefox/firefox"],
      "cpu_percent": 0.0,
      "cpu_times": [6652.64, 2012.85, 5052.81, 704.23, 0.0],
      "gids": [1000, 1000, 1000],
      "io_counters": [4205573120, 6936297472, 0, 0, 0],
      "key": "pid",
      "memory_info": [507658240, 22263525376, 129363968, 618496, 0, 1405198336, 0],
      "memory_percent": 6.478385432048301,
      "name": "firefox",
      "nice": 0,
      "num_threads": 168,
      "pid": 10541,
      "status": "S",
      "time_since_update": 1,
      "username": "nicolargo"},
     {"cmdline": ["/snap/firefox/2605/usr/lib/firefox/firefox",
                  "-contentproc",
                  "-childID",
                  "6",
                  "-isForBrowser",
                  "-prefsLen",
                  "38436",
                  "-prefMapSize",
                  "241898",
                  "-jsInitLen",
                  "240056",
                  "-parentBuildID",
                  "20230424185118",
                  "-appDir",
                  "/snap/firefox/2605/usr/lib/firefox/browser",
                  "{c94b5dea-52c6-4c75-a314-5de48bda9cdc}",
                  "10541",
                  "true",
                  "tab"],
      "cpu_percent": 0.0,
      "cpu_times": [1100.17, 125.28, 0.0, 0.0, 0.0],
      "gids": [1000, 1000, 1000],
      "io_counters": [209806336, 0, 0, 0, 0],
      "key": "pid",
      "memory_info": [406437888, 3516469248, 78082048, 618496, 0, 918466560, 0],
      "memory_percent": 5.186680891167411,
      "name": "WebExtensions",
      "nice": 0,
      "num_threads": 20,
      "pid": 11043,
      "status": "S",
      "time_since_update": 1,
      "username": "nicolargo"}]

Get a specific field::

    # curl http://localhost:61208/api/3/processlist/pid
    {"pid": [10541,
             11043,
             59195,
             10770,
             10778,
             60503,
             55857,
             3927,
             10774,
             59454,
             250191,
             181461,
             10790,
             195248,
             4288,
             10733,
             60104,
             11646,
             421,
             165661,
             59069,
             257253,
             257768,
             257484,
             257543,
             59161,
             59523,
             60232,
             2398,
             11380,
             257817,
             4339,
             257829,
             4385,
             3810,
             4243,
             11381,
             59525,
             59663,
             10710,
             195141,
             250777,
             60106,
             143262,
             257721,
             60489,
             143263,
             60134,
             1618,
             1771,
             59182,
             2636,
             250733,
             4023,
             60191,
             3730,
             250835,
             60192,
             4666,
             1584,
             56140,
             1,
             17997,
             227509,
             4179,
             4091,
             4000,
             250871,
             4090,
             4403,
             4075,
             3991,
             3901,
             4308,
             1605,
             3115,
             2554,
             1794,
             2168,
             1630,
             1727,
             36919,
             4046,
             1631,
             3719,
             59126,
             20173,
             3710,
             2607,
             4009,
             1598,
             2341,
             3956,
             4105,
             74953,
             59127,
             3908,
             1764,
             1379,
             256714,
             4086,
             4244,
             1818,
             1583,
             4169,
             3745,
             4127,
             14243,
             4442,
             4126,
             14266,
             1627,
             2116,
             4097,
             4078,
             3989,
             1628,
             1566,
             4316,
             4145,
             4080,
             3498,
             4119,
             3925,
             3748,
             2604,
             3970,
             3939,
             1591,
             4033,
             4005,
             4099,
             4062,
             3952,
             1612,
             1624,
             4196,
             3825,
             3947,
             1606,
             4107,
             3975,
             4098,
             4302,
             1579,
             2605,
             4074,
             3743,
             10848,
             3819,
             4157,
             4079,
             3753,
             1380,
             1825,
             3499,
             1616,
             3727,
             1575,
             3728,
             461,
             3888,
             3934,
             1593,
             56119,
             1377,
             1964,
             257754,
             1582,
             12480,
             12489,
             59145,
             18045,
             4332,
             3118,
             1634,
             1390,
             1391,
             2361,
             3573,
             16182,
             20400,
             1725,
             1726,
             12483,
             1567,
             20396,
             20180,
             12492,
             59130,
             257816,
             4593,
             56100,
             56106,
             56087,
             3720,
             3503,
             56081,
             4072,
             3794,
             2358,
             247115,
             2382,
             2345,
             1637,
             2360,
             1392,
             1577,
             20185,
             12486,
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
             103,
             106,
             107,
             109,
             110,
             112,
             117,
             118,
             119,
             129,
             132,
             138,
             181,
             183,
             206,
             219,
             223,
             226,
             228,
             231,
             232,
             233,
             234,
             249,
             250,
             255,
             256,
             313,
             361,
             362,
             439,
             440,
             530,
             544,
             655,
             700,
             702,
             703,
             898,
             899,
             900,
             901,
             908,
             909,
             910,
             911,
             912,
             913,
             914,
             915,
             962,
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
             975,
             976,
             977,
             978,
             979,
             980,
             1001,
             1002,
             1009,
             1010,
             1031,
             1032,
             1033,
             1034,
             1035,
             1036,
             1037,
             2138,
             2140,
             2141,
             2142,
             2143,
             2394,
             2410,
             2422,
             2491,
             2492,
             2493,
             2506,
             2508,
             2510,
             2515,
             2525,
             3988,
             193069,
             193070,
             193072,
             249139,
             249929,
             250365,
             250457,
             250459,
             250462,
             250467,
             250473,
             250474,
             250475,
             250476,
             250477,
             250479,
             250529,
             255880,
             256024,
             256316,
             256366,
             256541,
             256899,
             256900,
             256944,
             256946,
             257104,
             257206,
             257329,
             257419]}

Get a specific item when field matchs the given value::

    # curl http://localhost:61208/api/3/processlist/pid/10541
    {"10541": [{"cmdline": ["/snap/firefox/2605/usr/lib/firefox/firefox"],
                "cpu_percent": 0.0,
                "cpu_times": [6652.64, 2012.85, 5052.81, 704.23, 0.0],
                "gids": [1000, 1000, 1000],
                "io_counters": [4205573120, 6936297472, 0, 0, 0],
                "key": "pid",
                "memory_info": [507658240,
                                22263525376,
                                129363968,
                                618496,
                                0,
                                1405198336,
                                0],
                "memory_percent": 6.478385432048301,
                "name": "firefox",
                "nice": 0,
                "num_threads": 168,
                "pid": 10541,
                "status": "S",
                "time_since_update": 1,
                "username": "nicolargo"}]}

GET psutilversion
-----------------

Get plugin stats::

    # curl http://localhost:61208/api/3/psutilversion
    [5, 9, 5]

GET quicklook
-------------

Get plugin stats::

    # curl http://localhost:61208/api/3/quicklook
    {"cpu": 35.5,
     "cpu_hz": 2025000000.0,
     "cpu_hz_current": 1498956999.9999998,
     "cpu_name": "Intel(R) Core(TM) i7-4500U CPU @ 1.80GHz",
     "mem": 67.9,
     "percpu": [{"cpu_number": 0,
                 "guest": 0.0,
                 "guest_nice": 0.0,
                 "idle": 20.2,
                 "iowait": 0.0,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 0.0,
                 "steal": 0.0,
                 "system": 6.7,
                 "total": 79.8,
                 "user": 73.1},
                {"cpu_number": 1,
                 "guest": 0.0,
                 "guest_nice": 0.0,
                 "idle": 70.6,
                 "iowait": 0.0,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 0.0,
                 "steal": 0.0,
                 "system": 6.7,
                 "total": 29.4,
                 "user": 22.7},
                {"cpu_number": 2,
                 "guest": 0.0,
                 "guest_nice": 0.0,
                 "idle": 85.7,
                 "iowait": 0.0,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 0.0,
                 "steal": 0.0,
                 "system": 3.4,
                 "total": 14.3,
                 "user": 10.9},
                {"cpu_number": 3,
                 "guest": 0.0,
                 "guest_nice": 0.0,
                 "idle": 82.0,
                 "iowait": 0.0,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 0.0,
                 "steal": 0.0,
                 "system": 6.6,
                 "total": 18.0,
                 "user": 11.5}],
     "swap": 31.6}

Get a specific field::

    # curl http://localhost:61208/api/3/quicklook/cpu
    {"cpu": 35.5}

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
     "os_version": "5.15.0-71-generic",
     "platform": "64bit"}

Get a specific field::

    # curl http://localhost:61208/api/3/system/os_name
    {"os_name": "Linux"}

GET uptime
----------

Get plugin stats::

    # curl http://localhost:61208/api/3/uptime
    "8 days, 22:22:23"

GET all stats
-------------

Get all Glances stats::

    # curl http://localhost:61208/api/3/all
    Return a very big dictionnary (avoid using this request, performances will be poor)...

GET stats history
-----------------

History of a plugin::

    # curl http://localhost:61208/api/3/cpu/history
    {"system": [["2023-05-17T11:24:07.350522", 6.6],
                ["2023-05-17T11:24:08.472521", 6.6],
                ["2023-05-17T11:24:09.656447", 2.5]],
     "user": [["2023-05-17T11:24:07.350513", 27.2],
              ["2023-05-17T11:24:08.472515", 27.2],
              ["2023-05-17T11:24:09.656439", 10.8]]}

Limit history to last 2 values::

    # curl http://localhost:61208/api/3/cpu/history/2
    {"system": [["2023-05-17T11:24:08.472521", 6.6],
                ["2023-05-17T11:24:09.656447", 2.5]],
     "user": [["2023-05-17T11:24:08.472515", 27.2],
              ["2023-05-17T11:24:09.656439", 10.8]]}

History for a specific field::

    # curl http://localhost:61208/api/3/cpu/system/history
    {"system": [["2023-05-17T11:24:07.350522", 6.6],
                ["2023-05-17T11:24:08.472521", 6.6],
                ["2023-05-17T11:24:09.656447", 2.5]]}

Limit history for a specific field to last 2 values::

    # curl http://localhost:61208/api/3/cpu/system/history
    {"system": [["2023-05-17T11:24:08.472521", 6.6],
                ["2023-05-17T11:24:09.656447", 2.5]]}

GET limits (used for thresholds)
--------------------------------

All limits/thresholds::

    # curl http://localhost:61208/api/3/all/limits
    {"alert": {"history_size": 1200.0},
     "amps": {"amps_disable": ["False"], "history_size": 1200.0},
     "containers": {"containers_all": ["False"],
                    "containers_disable": ["False"],
                    "containers_max_name_size": 20.0,
                    "history_size": 1200.0},
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


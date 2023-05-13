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

GET alert
---------

Get plugin stats::

    # curl http://localhost:61208/api/3/alert
    [[1683984558.0,
      -1,
      "WARNING",
      "MEM",
      73.17533404664918,
      73.17533404664918,
      73.17533404664918,
      73.17533404664918,
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
      "timer": 0.8803508281707764},
     {"count": 0,
      "countmax": 20.0,
      "countmin": None,
      "key": "name",
      "name": "Python",
      "refresh": 3.0,
      "regex": True,
      "result": None,
      "timer": 0.8801853656768799}]

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
                  "timer": 0.8803508281707764}]}

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
    {"containers": [{"Command": ["/portainer"],
                     "Created": "2022-10-29T14:59:10.266701439Z",
                     "Id": "3abd51c615968482d9ccff5afc629f267f6dda113ed68b75b432615fae3b49fb",
                     "Image": ["portainer/portainer-ce:2.9.3"],
                     "Status": "running",
                     "Uptime": "6 hours",
                     "cpu": {"total": 0.0},
                     "cpu_percent": 0.0,
                     "engine": "docker",
                     "io": {"cumulative_ior": 0, "cumulative_iow": 184320},
                     "io_r": None,
                     "io_w": None,
                     "key": "name",
                     "memory": {"cache": None,
                                "limit": 7836184576,
                                "max_usage": None,
                                "rss": None,
                                "usage": 19238912},
                     "memory_usage": 19238912,
                     "name": "portainer",
                     "network": {"cumulative_rx": 516952, "cumulative_tx": 0},
                     "network_rx": None,
                     "network_tx": None},
                    {"Command": ["top"],
                     "Created": "2023-05-08T15:29:34.918692365+02:00",
                     "Id": "4b7f732d43e4bc5d92fe5298cba025b550e6a608754c1c38f9a90aaecd46b8f9",
                     "Image": "["docker.io/library/ubuntu:latest"]",
                     "Status": "running",
                     "Uptime": "4 days",
                     "cpu": {"total": 3.4516486319009634e-07},
                     "cpu_percent": 3.4516486319009634e-07,
                     "engine": "podman",
                     "io": {"ior": 0.0, "iow": 0.0, "time_since_update": 1},
                     "io_r": 0.0,
                     "io_w": 0.0,
                     "key": "name",
                     "memory": {"limit": 7836184576.0, "usage": 2195456.0},
                     "memory_usage": 2195456.0,
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
                     "Uptime": "4 days",
                     "cpu": {"total": 2.5083365383979135e-10},
                     "cpu_percent": 2.5083365383979135e-10,
                     "engine": "podman",
                     "io": {"ior": 0.0, "iow": 0.0, "time_since_update": 1},
                     "io_r": 0.0,
                     "io_w": 0.0,
                     "key": "name",
                     "memory": {"limit": 7836184576.0, "usage": 647168.0},
                     "memory_usage": 647168.0,
                     "name": "8d0f1c783def-infra",
                     "network": {"rx": 0.0, "time_since_update": 1, "tx": 0.0},
                     "network_rx": 0.0,
                     "network_tx": 0.0,
                     "pod_id": "8d0f1c783def",
                     "pod_name": "8d0f1c783def-infra"}],
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
     "idle": 70.8,
     "interrupts": 0,
     "iowait": 0.2,
     "irq": 0.0,
     "nice": 0.0,
     "soft_interrupts": 0,
     "softirq": 0.0,
     "steal": 0.0,
     "syscalls": 0,
     "system": 3.7,
     "time_since_update": 1,
     "total": 29.0,
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
    {"total": 29.0}

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
      "free": 9096110080,
      "fs_type": "ext4",
      "key": "mnt_point",
      "mnt_point": "/",
      "percent": 96.1,
      "size": 243334156288,
      "used": 221850591232},
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
            "free": 9096110080,
            "fs_type": "ext4",
            "key": "mnt_point",
            "mnt_point": "/",
            "percent": 96.1,
            "size": 243334156288,
            "used": 221850591232}]}

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
     "min1": 0.8857421875,
     "min15": 0.74365234375,
     "min5": 0.77685546875}

Fields descriptions:

* **min1**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 1 minute (unit is *float*)
* **min5**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 5 minutes (unit is *float*)
* **min15**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 15 minutes (unit is *float*)
* **cpucore**: Total number of CPU core (unit is *number*)

Get a specific field::

    # curl http://localhost:61208/api/3/load/min1
    {"min1": 0.8857421875}

GET mem
-------

Get plugin stats::

    # curl http://localhost:61208/api/3/mem
    {"active": 2534027264,
     "available": 2102030336,
     "buffers": 218550272,
     "cached": 2393772032,
     "free": 2102030336,
     "inactive": 3635040256,
     "percent": 73.2,
     "shared": 637190144,
     "total": 7836184576,
     "used": 5734154240}

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
    {"free": 7234039808,
     "percent": 10.5,
     "sin": 499916800,
     "sout": 1525796864,
     "time_since_update": 1,
     "total": 8082419712,
     "used": 848379904}

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
      "cumulative_cx": 56960572,
      "cumulative_rx": 28480286,
      "cumulative_tx": 28480286,
      "cx": 6512,
      "interface_name": "lo",
      "is_up": True,
      "key": "interface_name",
      "rx": 3256,
      "speed": 0,
      "time_since_update": 1,
      "tx": 3256},
     {"alias": None,
      "cumulative_cx": 3229266842,
      "cumulative_rx": 3098498206,
      "cumulative_tx": 130768636,
      "cx": 22545,
      "interface_name": "wlp2s0",
      "is_up": True,
      "key": "interface_name",
      "rx": 14112,
      "speed": 0,
      "time_since_update": 1,
      "tx": 8433}]

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
             "cumulative_cx": 56960572,
             "cumulative_rx": 28480286,
             "cumulative_tx": 28480286,
             "cx": 6512,
             "interface_name": "lo",
             "is_up": True,
             "key": "interface_name",
             "rx": 3256,
             "speed": 0,
             "time_since_update": 1,
             "tx": 3256}]}

GET now
-------

Get plugin stats::

    # curl http://localhost:61208/api/3/now
    "2023-05-13 15:29:18 CEST"

GET percpu
----------

Get plugin stats::

    # curl http://localhost:61208/api/3/percpu
    [{"cpu_number": 0,
      "guest": 0.0,
      "guest_nice": 0.0,
      "idle": 2.9,
      "iowait": 0.0,
      "irq": 0.0,
      "key": "cpu_number",
      "nice": 0.0,
      "softirq": 0.0,
      "steal": 0.0,
      "system": 4.9,
      "total": 97.1,
      "user": 92.2},
     {"cpu_number": 1,
      "guest": 0.0,
      "guest_nice": 0.0,
      "idle": 96.0,
      "iowait": 0.0,
      "irq": 0.0,
      "key": "cpu_number",
      "nice": 0.0,
      "softirq": 0.0,
      "steal": 0.0,
      "system": 1.0,
      "total": 4.0,
      "user": 3.0}]

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
      "status": 0.008301,
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
                      "status": 0.008301,
                      "timeout": 3}]}

GET processcount
----------------

Get plugin stats::

    # curl http://localhost:61208/api/3/processcount
    {"pid_max": 0, "running": 1, "sleeping": 310, "thread": 1568, "total": 439}

Get a specific field::

    # curl http://localhost:61208/api/3/processcount/total
    {"total": 439}

GET processlist
---------------

Get plugin stats::

    # curl http://localhost:61208/api/3/processlist
    [{"cmdline": ["/snap/firefox/2605/usr/lib/firefox/firefox"],
      "cpu_percent": 0.0,
      "cpu_times": [2184.25, 667.78, 1237.1, 178.98, 0.0],
      "gids": [1000, 1000, 1000],
      "io_counters": [1531420672, 2813288448, 0, 0, 0],
      "key": "pid",
      "memory_info": [487464960, 21833334784, 137736192, 618496, 0, 1029808128, 0],
      "memory_percent": 6.220692676037344,
      "name": "firefox",
      "nice": 0,
      "num_threads": 140,
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
      "cpu_times": [435.82, 49.35, 0.0, 0.0, 0.0],
      "gids": [1000, 1000, 1000],
      "io_counters": [30860288, 0, 0, 0, 0],
      "key": "pid",
      "memory_info": [473804800, 3518271488, 87040000, 618496, 0, 924098560, 0],
      "memory_percent": 6.046371105794638,
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
             60503,
             10770,
             10778,
             67269,
             59454,
             3927,
             59195,
             4288,
             10774,
             82905,
             55857,
             50925,
             10790,
             71741,
             59069,
             10733,
             60104,
             421,
             11646,
             71710,
             59523,
             60134,
             60106,
             84415,
             59161,
             60489,
             85078,
             85144,
             59525,
             59663,
             60232,
             2398,
             3810,
             85317,
             60191,
             11380,
             59182,
             60192,
             10710,
             11381,
             4179,
             4385,
             4243,
             4023,
             1771,
             3730,
             20173,
             17997,
             2636,
             59126,
             59127,
             4000,
             4666,
             4091,
             1618,
             4403,
             1727,
             1584,
             2168,
             4046,
             56140,
             4090,
             36919,
             4075,
             1598,
             3956,
             1825,
             4169,
             2554,
             3991,
             1,
             2607,
             4442,
             4339,
             84438,
             1630,
             1794,
             51324,
             4308,
             1605,
             4086,
             4126,
             1379,
             4244,
             2341,
             4080,
             3901,
             4078,
             3719,
             4105,
             3710,
             3908,
             3115,
             51357,
             4097,
             3825,
             4009,
             1764,
             1631,
             1818,
             1628,
             2116,
             74953,
             1627,
             1566,
             14243,
             14266,
             3970,
             3939,
             4119,
             4145,
             56119,
             78856,
             3743,
             4033,
             3498,
             60199,
             1583,
             3748,
             4316,
             3952,
             4107,
             3925,
             4062,
             1591,
             4302,
             1606,
             2604,
             1624,
             4127,
             4079,
             4196,
             4005,
             3975,
             10848,
             1616,
             3947,
             4098,
             1380,
             4074,
             4099,
             3745,
             1612,
             16182,
             4157,
             461,
             3989,
             3819,
             3727,
             3753,
             1579,
             2605,
             3728,
             3888,
             3499,
             3934,
             1575,
             1593,
             1377,
             1964,
             1582,
             18045,
             12489,
             12480,
             1634,
             4332,
             85272,
             1390,
             1391,
             59145,
             3118,
             3573,
             20400,
             2361,
             12492,
             12483,
             3720,
             59130,
             1725,
             1726,
             4593,
             20396,
             20180,
             1567,
             56106,
             56087,
             56100,
             85316,
             56081,
             3794,
             4072,
             2358,
             3503,
             78769,
             1637,
             2382,
             2345,
             2360,
             20185,
             1392,
             1577,
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
             51078,
             51079,
             51081,
             69313,
             69647,
             70461,
             75183,
             80333,
             81339,
             81683,
             81911,
             82593,
             82688,
             82773,
             82994,
             83112,
             83723,
             83900,
             83920,
             84008,
             84129,
             84204,
             84205,
             84302,
             84303,
             84304,
             84305,
             84306,
             84307,
             84308,
             84309,
             84310,
             84311,
             84312,
             84313,
             84314,
             84315,
             84316,
             84317,
             84318,
             84319,
             84320,
             84321,
             84322,
             84323,
             84324,
             84325,
             84326,
             84327,
             84328,
             84329,
             84330,
             84331,
             84332,
             84333,
             84334,
             84335,
             84336,
             84337,
             84338,
             84339,
             84340,
             84341,
             84342,
             84343,
             84344,
             84345,
             84346,
             84347,
             84348,
             84349,
             84350,
             84351,
             84352,
             84353,
             84354,
             84355,
             84356,
             84357,
             84358,
             84359,
             84360,
             84361,
             84362,
             84363,
             84364,
             84365,
             84366,
             84403,
             84463,
             84575]}

Get a specific item when field matchs the given value::

    # curl http://localhost:61208/api/3/processlist/pid/10541
    {"10541": [{"cmdline": ["/snap/firefox/2605/usr/lib/firefox/firefox"],
                "cpu_percent": 0.0,
                "cpu_times": [2184.25, 667.78, 1237.1, 178.98, 0.0],
                "gids": [1000, 1000, 1000],
                "io_counters": [1531420672, 2813288448, 0, 0, 0],
                "key": "pid",
                "memory_info": [487464960,
                                21833334784,
                                137736192,
                                618496,
                                0,
                                1029808128,
                                0],
                "memory_percent": 6.220692676037344,
                "name": "firefox",
                "nice": 0,
                "num_threads": 140,
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
    {"cpu": 29.0,
     "cpu_hz": 2025000000.0,
     "cpu_hz_current": 1634067000.0,
     "cpu_name": "Intel(R) Core(TM) i7-4500U CPU @ 1.80GHz",
     "mem": 73.2,
     "percpu": [{"cpu_number": 0,
                 "guest": 0.0,
                 "guest_nice": 0.0,
                 "idle": 2.9,
                 "iowait": 0.0,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 0.0,
                 "steal": 0.0,
                 "system": 4.9,
                 "total": 97.1,
                 "user": 92.2},
                {"cpu_number": 1,
                 "guest": 0.0,
                 "guest_nice": 0.0,
                 "idle": 96.0,
                 "iowait": 0.0,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 0.0,
                 "steal": 0.0,
                 "system": 1.0,
                 "total": 4.0,
                 "user": 3.0},
                {"cpu_number": 2,
                 "guest": 0.0,
                 "guest_nice": 0.0,
                 "idle": 92.2,
                 "iowait": 0.0,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 0.0,
                 "steal": 0.0,
                 "system": 3.9,
                 "total": 7.8,
                 "user": 3.9},
                {"cpu_number": 3,
                 "guest": 0.0,
                 "guest_nice": 0.0,
                 "idle": 94.1,
                 "iowait": 0.0,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 0.0,
                 "steal": 0.0,
                 "system": 2.0,
                 "total": 5.9,
                 "user": 4.0}],
     "swap": 10.5}

Get a specific field::

    # curl http://localhost:61208/api/3/quicklook/cpu
    {"cpu": 29.0}

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
    "5 days, 2:27:37"

GET all stats
-------------

Get all Glances stats::

    # curl http://localhost:61208/api/3/all
    Return a very big dictionnary (avoid using this request, performances will be poor)...

GET stats history
-----------------

History of a plugin::

    # curl http://localhost:61208/api/3/cpu/history
    {"system": [["2023-05-13T15:29:19.051714", 3.7],
                ["2023-05-13T15:29:20.309432", 3.7],
                ["2023-05-13T15:29:21.521897", 3.5]],
     "user": [["2023-05-13T15:29:19.051705", 25.2],
              ["2023-05-13T15:29:20.309418", 25.2],
              ["2023-05-13T15:29:21.521889", 10.4]]}

Limit history to last 2 values::

    # curl http://localhost:61208/api/3/cpu/history/2
    {"system": [["2023-05-13T15:29:20.309432", 3.7],
                ["2023-05-13T15:29:21.521897", 3.5]],
     "user": [["2023-05-13T15:29:20.309418", 25.2],
              ["2023-05-13T15:29:21.521889", 10.4]]}

History for a specific field::

    # curl http://localhost:61208/api/3/cpu/system/history
    {"system": [["2023-05-13T15:29:19.051714", 3.7],
                ["2023-05-13T15:29:20.309432", 3.7],
                ["2023-05-13T15:29:21.521897", 3.5]]}

Limit history for a specific field to last 2 values::

    # curl http://localhost:61208/api/3/cpu/system/history
    {"system": [["2023-05-13T15:29:20.309432", 3.7],
                ["2023-05-13T15:29:21.521897", 3.5]]}

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


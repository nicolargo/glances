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
    [[1711185029.0,
      -1,
      "WARNING",
      "MEM",
      77.19987581483426,
      77.19987581483426,
      77.19987581483426,
      77.19987581483426,
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
      "timer": 0.9669091701507568},
     {"count": 0,
      "countmax": 20.0,
      "countmin": None,
      "key": "name",
      "name": "Python",
      "refresh": 3.0,
      "regex": True,
      "result": None,
      "timer": 0.9667403697967529}]

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
                  "timer": 0.9669091701507568}]}

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
                     "Uptime": "1 weeks",
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
     "idle": 68.7,
     "interrupts": 0,
     "iowait": 4.0,
     "irq": 0.0,
     "nice": 0.0,
     "soft_interrupts": 0,
     "softirq": 0.3,
     "steal": 0.0,
     "syscalls": 0,
     "system": 4.3,
     "time_since_update": 1,
     "total": 25.0,
     "user": 22.6}

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
    {"total": 25.0}

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
      "free": 36856778752,
      "fs_type": "ext4",
      "key": "mnt_point",
      "mnt_point": "/",
      "percent": 84.0,
      "size": 243334156288,
      "used": 194089922560},
     {"device_name": "zsfpool",
      "free": 31195136,
      "fs_type": "zfs",
      "key": "mnt_point",
      "mnt_point": "/zsfpool",
      "percent": 25.4,
      "size": 41811968,
      "used": 10616832}]

Get a specific field::

    # curl http://localhost:61208/api/3/fs/mnt_point
    {"mnt_point": ["/", "/zsfpool", "/var/snap/firefox/common/host-hunspell"]}

Get a specific item when field matchs the given value::

    # curl http://localhost:61208/api/3/fs/mnt_point//
    {"/": [{"device_name": "/dev/mapper/ubuntu--gnome--vg-root",
            "free": 36856778752,
            "fs_type": "ext4",
            "key": "mnt_point",
            "mnt_point": "/",
            "percent": 84.0,
            "size": 243334156288,
            "used": 194089922560}]}

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
     "min1": 1.87353515625,
     "min15": 1.30029296875,
     "min5": 1.5517578125}

Fields descriptions:

* **min1**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 1 minute (unit is *float*)
* **min5**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 5 minutes (unit is *float*)
* **min15**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 15 minutes (unit is *float*)
* **cpucore**: Total number of CPU core (unit is *number*)

Get a specific field::

    # curl http://localhost:61208/api/3/load/min1
    {"min1": 1.87353515625}

GET mem
-------

Get plugin stats::

    # curl http://localhost:61208/api/3/mem
    {"active": 3217502208,
     "available": 1783783424,
     "buffers": 242143232,
     "cached": 2323054592,
     "free": 1783783424,
     "inactive": 3508854784,
     "percent": 77.2,
     "shared": 658030592,
     "total": 7823568896,
     "used": 6039785472}

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
    {"total": 7823568896}

GET memswap
-----------

Get plugin stats::

    # curl http://localhost:61208/api/3/memswap
    {"free": 3968638976,
     "percent": 50.9,
     "sin": 4544499712,
     "sout": 9235214336,
     "time_since_update": 1,
     "total": 8082419712,
     "used": 4113780736}

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
      "cumulative_cx": 5405761891,
      "cumulative_rx": 5075958831,
      "cumulative_tx": 329803060,
      "cx": 27520,
      "interface_name": "wlp2s0",
      "is_up": True,
      "key": "interface_name",
      "rx": 19247,
      "speed": 0,
      "time_since_update": 1,
      "tx": 8273},
     {"alias": None,
      "cumulative_cx": 0,
      "cumulative_rx": 0,
      "cumulative_tx": 0,
      "cx": 0,
      "interface_name": "br-40875d2e2716",
      "is_up": False,
      "key": "interface_name",
      "rx": 0,
      "speed": 0,
      "time_since_update": 1,
      "tx": 0}]

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
    {"interface_name": ["wlp2s0",
                        "br-40875d2e2716",
                        "br_grafana",
                        "lxdbr0",
                        "veth05608da0",
                        "mpqemubr0",
                        "veth3c5f47a"]}

Get a specific item when field matchs the given value::

    # curl http://localhost:61208/api/3/network/interface_name/wlp2s0
    {"wlp2s0": [{"alias": None,
                 "cumulative_cx": 5405761891,
                 "cumulative_rx": 5075958831,
                 "cumulative_tx": 329803060,
                 "cx": 27520,
                 "interface_name": "wlp2s0",
                 "is_up": True,
                 "key": "interface_name",
                 "rx": 19247,
                 "speed": 0,
                 "time_since_update": 1,
                 "tx": 8273}]}

GET now
-------

Get plugin stats::

    # curl http://localhost:61208/api/3/now
    "2024-03-23 10:10:28 CET"

GET percpu
----------

Get plugin stats::

    # curl http://localhost:61208/api/3/percpu
    [{"cpu_number": 0,
      "guest": 0.0,
      "guest_nice": 0.0,
      "idle": 84.3,
      "iowait": 2.6,
      "irq": 0.0,
      "key": "cpu_number",
      "nice": 0.0,
      "softirq": 1.7,
      "steal": 0.0,
      "system": 1.7,
      "total": 15.7,
      "user": 9.6},
     {"cpu_number": 1,
      "guest": 0.0,
      "guest_nice": 0.0,
      "idle": 94.8,
      "iowait": 0.9,
      "irq": 0.0,
      "key": "cpu_number",
      "nice": 0.0,
      "softirq": 0.0,
      "steal": 0.0,
      "system": 0.9,
      "total": 5.2,
      "user": 3.4}]

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
      "status": 0.005803,
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
                        "status": 0.005803,
                        "timeout": 3}]}

GET processcount
----------------

Get plugin stats::

    # curl http://localhost:61208/api/3/processcount
    {"pid_max": 0, "running": 1, "sleeping": 335, "thread": 1678, "total": 403}

Get a specific field::

    # curl http://localhost:61208/api/3/processcount/total
    {"total": 403}

GET processlist
---------------

Get plugin stats::

    # curl http://localhost:61208/api/3/processlist
    [{"cmdline": ["/usr/share/code/code",
                  "--type=renderer",
                  "--crashpad-handler-pid=35523",
                  "--enable-crash-reporter=721e05a9-6035-4dcb-bd58-68097aa48dd0,no_channel",
                  "--user-data-dir=/home/nicolargo/.config/Code",
                  "--standard-schemes=vscode-webview,vscode-file",
                  "--enable-sandbox",
                  "--secure-schemes=vscode-webview,vscode-file",
                  "--cors-schemes=vscode-webview,vscode-file",
                  "--fetch-schemes=vscode-webview,vscode-file",
                  "--service-worker-schemes=vscode-webview",
                  "--code-cache-schemes=vscode-webview,vscode-file",
                  "--app-path=/usr/share/code/resources/app",
                  "--enable-sandbox",
                  "--enable-blink-features=HighlightAPI",
                  "--first-renderer-process",
                  "--lang=en-US",
                  "--num-raster-threads=2",
                  "--enable-main-frame-before-activation",
                  "--renderer-client-id=4",
                  "--time-ticks-at-unix-epoch=-1709539275787032",
                  "--launch-time-ticks=3773104105",
                  "--shared-files=v8_context_snapshot_data:100",
                  "--field-trial-handle=0,i,2992833077465328896,17440056338018087593,262144",
                  "--disable-features=CalculateNativeWinOcclusion,SpareRendererForSitePerProcess",
                  "--vscode-window-config=vscode:0a3f42ef-a12c-453d-8061-6c7b57ac6b4f"],
      "cpu_percent": 0.0,
      "cpu_times": [8788.45, 733.23, 0.0, 0.0, 0.0],
      "gids": [1000, 1000, 1000],
      "io_counters": [608010240, 3362816, 0, 0, 0],
      "key": "pid",
      "memory_info": [590098432,
                      1221794549760,
                      72073216,
                      126423040,
                      0,
                      1257771008,
                      0],
      "memory_percent": 7.54257347055131,
      "name": "code",
      "nice": 0,
      "num_threads": 15,
      "pid": 35570,
      "status": "S",
      "time_since_update": 1,
      "username": "nicolargo"},
     {"cmdline": ["/usr/share/code/code",
                  "/home/nicolargo/.vscode/extensions/ms-python.vscode-pylance-2024.2.2/dist/server.bundle.js",
                  "--cancellationReceive=file:a926d4bb77e62306671377ffa0d7cb38591c07e817",
                  "--node-ipc",
                  "--clientProcessId=35618"],
      "cpu_percent": 0.0,
      "cpu_times": [4611.97, 204.93, 4.37, 0.34, 0.0],
      "gids": [1000, 1000, 1000],
      "io_counters": [672653312, 1871872, 0, 0, 0],
      "key": "pid",
      "memory_info": [487878656,
                      1208849584128,
                      22482944,
                      126423040,
                      0,
                      867049472,
                      0],
      "memory_percent": 6.236011499169393,
      "name": "code",
      "nice": 0,
      "num_threads": 13,
      "pid": 36130,
      "status": "S",
      "time_since_update": 1,
      "username": "nicolargo"}]

Get a specific field::

    # curl http://localhost:61208/api/3/processlist/pid
    {"pid": [35570,
             36130,
             7992,
             8257,
             35618,
             645109,
             8407,
             5554,
             654062,
             665779,
             385672,
             662277,
             654683,
             14040,
             35835,
             35502,
             644502,
             666300,
             8217,
             666454,
             666819,
             35537,
             35790,
             5406,
             35631,
             35957,
             667098,
             6163,
             36217,
             293224,
             32821,
             35632,
             667109,
             6332,
             2423,
             35857,
             8749,
             35996,
             3248,
             55881,
             265662,
             55878,
             4024,
             517283,
             640398,
             35546,
             420,
             35955,
             629519,
             5849,
             2621,
             640457,
             8604,
             104932,
             1645,
             293597,
             6341,
             6122,
             8189,
             640503,
             243963,
             36155,
             8156,
             1497,
             5306,
             35958,
             185654,
             185653,
             185679,
             35956,
             5998,
             5809,
             4301,
             1,
             5795,
             5988,
             1518,
             35369,
             5996,
             6640,
             1544,
             6291,
             1728,
             2129,
             6009,
             5840,
             5893,
             5611,
             4703,
             5649,
             5257,
             5522,
             6085,
             6028,
             35507,
             35506,
             640813,
             2543,
             1496,
             5994,
             32846,
             1729,
             31214,
             5325,
             1648,
             6022,
             1512,
             2363,
             1277,
             6001,
             6713,
             2586,
             6063,
             31232,
             5319,
             6080,
             5914,
             1479,
             182445,
             5989,
             2079,
             5329,
             5832,
             1532,
             1503,
             1545,
             6089,
             6305,
             48508,
             5558,
             6010,
             6107,
             6251,
             1520,
             4210,
             5643,
             1538,
             104945,
             5636,
             5993,
             8273,
             5793,
             5987,
             5631,
             5667,
             6017,
             6084,
             6002,
             5407,
             5676,
             6004,
             5412,
             3556,
             111079,
             5955,
             35523,
             1540,
             3557,
             4251,
             455,
             35387,
             1731,
             111058,
             5334,
             1487,
             5303,
             35509,
             111116,
             1526,
             5507,
             1492,
             5304,
             1527,
             5568,
             293566,
             1274,
             1504,
             1900,
             1495,
             1279,
             6317,
             36208,
             666856,
             2564,
             1607,
             4286,
             34330,
             1289,
             1288,
             4294,
             2375,
             3251,
             2565,
             1490,
             4136,
             3787,
             653392,
             293551,
             1480,
             1635,
             667097,
             4302,
             293512,
             3947,
             4269,
             4200,
             293544,
             2384,
             5986,
             293491,
             5390,
             4272,
             4299,
             7895,
             1631,
             2398,
             2381,
             5258,
             1287,
             2407,
             3560,
             4304,
             1617,
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
             105,
             106,
             108,
             110,
             112,
             115,
             116,
             117,
             128,
             131,
             137,
             184,
             202,
             224,
             225,
             226,
             227,
             228,
             231,
             232,
             233,
             239,
             247,
             248,
             253,
             254,
             311,
             360,
             361,
             437,
             438,
             524,
             550,
             659,
             660,
             661,
             673,
             920,
             921,
             922,
             923,
             930,
             931,
             932,
             933,
             934,
             935,
             936,
             937,
             989,
             990,
             991,
             992,
             993,
             994,
             995,
             996,
             997,
             998,
             999,
             1000,
             1001,
             1002,
             1003,
             1004,
             1005,
             1006,
             1007,
             1028,
             1029,
             1036,
             1037,
             1058,
             1059,
             1060,
             1061,
             1062,
             1063,
             1064,
             2100,
             2101,
             2102,
             2103,
             2104,
             2107,
             2109,
             2110,
             2111,
             2112,
             2425,
             2529,
             2530,
             2531,
             2532,
             2533,
             2534,
             2535,
             2536,
             4058,
             5656,
             15197,
             19449,
             19450,
             72733,
             111072,
             629230,
             629231,
             629234,
             640161,
             640162,
             640165,
             640166,
             640169,
             640216,
             652755,
             654117,
             656184,
             658124,
             660421,
             660669,
             661136,
             662149,
             663088,
             663825,
             664298,
             664546,
             664862,
             664982,
             665624,
             666288,
             666401,
             667053]}

Get a specific item when field matchs the given value::

    # curl http://localhost:61208/api/3/processlist/pid/35570
    {"35570": [{"cmdline": ["/usr/share/code/code",
                            "--type=renderer",
                            "--crashpad-handler-pid=35523",
                            "--enable-crash-reporter=721e05a9-6035-4dcb-bd58-68097aa48dd0,no_channel",
                            "--user-data-dir=/home/nicolargo/.config/Code",
                            "--standard-schemes=vscode-webview,vscode-file",
                            "--enable-sandbox",
                            "--secure-schemes=vscode-webview,vscode-file",
                            "--cors-schemes=vscode-webview,vscode-file",
                            "--fetch-schemes=vscode-webview,vscode-file",
                            "--service-worker-schemes=vscode-webview",
                            "--code-cache-schemes=vscode-webview,vscode-file",
                            "--app-path=/usr/share/code/resources/app",
                            "--enable-sandbox",
                            "--enable-blink-features=HighlightAPI",
                            "--first-renderer-process",
                            "--lang=en-US",
                            "--num-raster-threads=2",
                            "--enable-main-frame-before-activation",
                            "--renderer-client-id=4",
                            "--time-ticks-at-unix-epoch=-1709539275787032",
                            "--launch-time-ticks=3773104105",
                            "--shared-files=v8_context_snapshot_data:100",
                            "--field-trial-handle=0,i,2992833077465328896,17440056338018087593,262144",
                            "--disable-features=CalculateNativeWinOcclusion,SpareRendererForSitePerProcess",
                            "--vscode-window-config=vscode:0a3f42ef-a12c-453d-8061-6c7b57ac6b4f"],
                "cpu_percent": 0.0,
                "cpu_times": [8788.45, 733.23, 0.0, 0.0, 0.0],
                "gids": [1000, 1000, 1000],
                "io_counters": [608010240, 3362816, 0, 0, 0],
                "key": "pid",
                "memory_info": [590098432,
                                1221794549760,
                                72073216,
                                126423040,
                                0,
                                1257771008,
                                0],
                "memory_percent": 7.54257347055131,
                "name": "code",
                "nice": 0,
                "num_threads": 15,
                "pid": 35570,
                "status": "S",
                "time_since_update": 1,
                "username": "nicolargo"}]}

GET psutilversion
-----------------

Get plugin stats::

    # curl http://localhost:61208/api/3/psutilversion
    [5, 9, 8]

GET quicklook
-------------

Get plugin stats::

    # curl http://localhost:61208/api/3/quicklook
    {"cpu": 25.0,
     "cpu_hz": 2025000000.0,
     "cpu_hz_current": 1818595250.0,
     "cpu_name": "Intel(R) Core(TM) i7-4500U CPU @ 1.80GHz",
     "mem": 77.2,
     "percpu": [{"cpu_number": 0,
                 "guest": 0.0,
                 "guest_nice": 0.0,
                 "idle": 84.3,
                 "iowait": 2.6,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 1.7,
                 "steal": 0.0,
                 "system": 1.7,
                 "total": 15.7,
                 "user": 9.6},
                {"cpu_number": 1,
                 "guest": 0.0,
                 "guest_nice": 0.0,
                 "idle": 94.8,
                 "iowait": 0.9,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 0.0,
                 "steal": 0.0,
                 "system": 0.9,
                 "total": 5.2,
                 "user": 3.4},
                {"cpu_number": 2,
                 "guest": 0.0,
                 "guest_nice": 0.0,
                 "idle": 47.5,
                 "iowait": 5.8,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 0.0,
                 "steal": 0.0,
                 "system": 4.2,
                 "total": 52.5,
                 "user": 42.5},
                {"cpu_number": 3,
                 "guest": 0.0,
                 "guest_nice": 0.0,
                 "idle": 54.7,
                 "iowait": 9.4,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 0.0,
                 "steal": 0.0,
                 "system": 6.0,
                 "total": 45.3,
                 "user": 29.9}],
     "swap": 50.9}

Get a specific field::

    # curl http://localhost:61208/api/3/quicklook/cpu
    {"cpu": 25.0}

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
     "os_version": "5.15.0-94-generic",
     "platform": "64bit"}

Get a specific field::

    # curl http://localhost:61208/api/3/system/os_name
    {"os_name": "Linux"}

GET uptime
----------

Get plugin stats::

    # curl http://localhost:61208/api/3/uptime
    "19 days, 1:09:46"

GET all stats
-------------

Get all Glances stats::

    # curl http://localhost:61208/api/3/all
    Return a very big dictionnary (avoid using this request, performances will be poor)...

GET stats history
-----------------

History of a plugin::

    # curl http://localhost:61208/api/3/cpu/history
    {"system": [["2024-03-23T10:10:29.601235", 4.3],
                ["2024-03-23T10:10:30.667810", 4.3],
                ["2024-03-23T10:10:31.828837", 2.9]],
     "user": [["2024-03-23T10:10:29.601227", 22.6],
              ["2024-03-23T10:10:30.667804", 22.6],
              ["2024-03-23T10:10:31.828831", 5.3]]}

Limit history to last 2 values::

    # curl http://localhost:61208/api/3/cpu/history/2
    {"system": [["2024-03-23T10:10:30.667810", 4.3],
                ["2024-03-23T10:10:31.828837", 2.9]],
     "user": [["2024-03-23T10:10:30.667804", 22.6],
              ["2024-03-23T10:10:31.828831", 5.3]]}

History for a specific field::

    # curl http://localhost:61208/api/3/cpu/system/history
    {"system": [["2024-03-23T10:10:29.601235", 4.3],
                ["2024-03-23T10:10:30.667810", 4.3],
                ["2024-03-23T10:10:31.828837", 2.9]]}

Limit history for a specific field to last 2 values::

    # curl http://localhost:61208/api/3/cpu/system/history
    {"system": [["2024-03-23T10:10:30.667810", 4.3],
                ["2024-03-23T10:10:31.828837", 2.9]]}

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
                 "network_hide": ["docker.*", "lo"],
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


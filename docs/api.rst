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
    [[1675093869.0,
      -1,
      "WARNING",
      "MEM",
      82.83225325565277,
      82.83225325565277,
      82.83225325565277,
      82.83225325565277,
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
      "timer": 0.6673910617828369},
     {"count": 0,
      "countmax": 20.0,
      "countmin": None,
      "key": "name",
      "name": "Python",
      "refresh": 3.0,
      "regex": True,
      "result": None,
      "timer": 0.667231559753418}]

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
                  "timer": 0.6673910617828369}]}

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
     "idle": 67.7,
     "interrupts": 0,
     "iowait": 0.2,
     "irq": 0.0,
     "nice": 0.0,
     "soft_interrupts": 0,
     "softirq": 0.0,
     "steal": 0.0,
     "syscalls": 0,
     "system": 6.3,
     "time_since_update": 1,
     "total": 31.2,
     "user": 25.7}

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
    {"total": 31.2}

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
                     "Uptime": "6 hours",
                     "cpu": {"total": 0.0},
                     "cpu_percent": 0.0,
                     "io": {"cumulative_ior": 0,
                            "cumulative_iow": 548864,
                            "time_since_update": 1},
                     "io_r": None,
                     "io_w": None,
                     "key": "name",
                     "memory": {"cache": None,
                                "limit": 7836196864,
                                "max_usage": None,
                                "rss": None,
                                "usage": 121462784},
                     "memory_usage": 121462784,
                     "name": "docker-mongo_mongo_1",
                     "network": {"cumulative_rx": 1546897,
                                 "cumulative_tx": 943210,
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
                     "Uptime": "6 hours",
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
                     "Uptime": "1 weeks",
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
      "free": 61967261696,
      "fs_type": "ext4",
      "key": "mnt_point",
      "mnt_point": "/",
      "percent": 73.2,
      "size": 243334156288,
      "used": 168979439616},
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
            "free": 61967261696,
            "fs_type": "ext4",
            "key": "mnt_point",
            "mnt_point": "/",
            "percent": 73.2,
            "size": 243334156288,
            "used": 168979439616}]}

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
    {"cpucore": 4, "min1": 1.9677734375, "min15": 1.2421875, "min5": 1.4140625}

Fields descriptions:

* **min1**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 1 minute (unit is *float*)
* **min5**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 5 minutes (unit is *float*)
* **min15**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 15 minutes (unit is *float*)
* **cpucore**: Total number of CPU core (unit is *number*)

Get a specific field::

    # curl http://localhost:61208/api/3/load/min1
    {"min1": 1.9677734375}

GET mem
-------

Get plugin stats::

    # curl http://localhost:61208/api/3/mem
    {"active": 2301452288,
     "available": 1345298432,
     "buffers": 91602944,
     "cached": 1984524288,
     "free": 1345298432,
     "inactive": 4274671616,
     "percent": 82.8,
     "shared": 603455488,
     "total": 7836196864,
     "used": 6490898432}

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
    {"free": 5992534016,
     "percent": 25.9,
     "sin": 2847645696,
     "sout": 5540925440,
     "time_since_update": 1,
     "total": 8082419712,
     "used": 2089885696}

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
      "cumulative_cx": 184715152,
      "cumulative_rx": 92357576,
      "cumulative_tx": 92357576,
      "cx": 8458,
      "interface_name": "lo",
      "is_up": True,
      "key": "interface_name",
      "rx": 4229,
      "speed": 0,
      "time_since_update": 1,
      "tx": 4229},
     {"alias": None,
      "cumulative_cx": 13554125250,
      "cumulative_rx": 13227076404,
      "cumulative_tx": 327048846,
      "cx": 25901,
      "interface_name": "wlp2s0",
      "is_up": True,
      "key": "interface_name",
      "rx": 20009,
      "speed": 0,
      "time_since_update": 1,
      "tx": 5892}]

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
                        "vethf503072",
                        "mpqemubr0",
                        "tap-1e376645a40",
                        "br-ef0a06c4e10f",
                        "veth9a140b2",
                        "veth9ed6876"]}

Get a specific item when field matchs the given value::

    # curl http://localhost:61208/api/3/network/interface_name/lo
    {"lo": [{"alias": None,
             "cumulative_cx": 184715152,
             "cumulative_rx": 92357576,
             "cumulative_tx": 92357576,
             "cx": 8458,
             "interface_name": "lo",
             "is_up": True,
             "key": "interface_name",
             "rx": 4229,
             "speed": 0,
             "time_since_update": 1,
             "tx": 4229}]}

GET now
-------

Get plugin stats::

    # curl http://localhost:61208/api/3/now
    "2023-01-30 16:51:08 CET"

GET percpu
----------

Get plugin stats::

    # curl http://localhost:61208/api/3/percpu
    [{"cpu_number": 0,
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
      "user": 11.0},
     {"cpu_number": 1,
      "guest": 0.0,
      "guest_nice": 0.0,
      "idle": 41.0,
      "iowait": 0.0,
      "irq": 0.0,
      "key": "cpu_number",
      "nice": 0.0,
      "softirq": 0.0,
      "steal": 0.0,
      "system": 0.0,
      "total": 59.0,
      "user": 41.0}]

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
      "status": 0.006011,
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
                      "status": 0.006011,
                      "timeout": 3}]}

GET processcount
----------------

Get plugin stats::

    # curl http://localhost:61208/api/3/processcount
    {"pid_max": 0, "running": 1, "sleeping": 332, "thread": 1844, "total": 463}

Get a specific field::

    # curl http://localhost:61208/api/3/processcount/total
    {"total": 463}

GET processlist
---------------

Get plugin stats::

    # curl http://localhost:61208/api/3/processlist
    [{"cmdline": ["/snap/multipass/8140/usr/bin/qemu-system-x86_64",
                  "--enable-kvm",
                  "-cpu",
                  "host",
                  "-nic",
                  "tap,ifname=tap-1e376645a40,script=no,downscript=no,model=virtio-net-pci,mac=52:54:00:05:05:17",
                  "-device",
                  "virtio-scsi-pci,id=scsi0",
                  "-drive",
                  "file=/var/snap/multipass/common/data/multipassd/vault/instances/primary/ubuntu-22.04-server-cloudimg-amd64.img,if=none,format=qcow2,discard=unmap,id=hda",
                  "-device",
                  "scsi-hd,drive=hda,bus=scsi0.0",
                  "-smp",
                  "1",
                  "-m",
                  "1024M",
                  "-qmp",
                  "stdio",
                  "-chardev",
                  "null,id=char0",
                  "-serial",
                  "chardev:char0",
                  "-nographic",
                  "-cdrom",
                  "/var/snap/multipass/common/data/multipassd/vault/instances/primary/cloud-init-config.iso",
                  "-loadvm",
                  "suspend",
                  "-machine",
                  "pc-i440fx-focal"],
      "cpu_percent": 0.0,
      "cpu_times": [15.8, 8.88, 0.0, 0.0, 0.0],
      "gids": [0, 0, 0],
      "io_counters": [0, 0, 0, 0, 0],
      "key": "pid",
      "memory_info": [508997632, 2645762048, 4816896, 5414912, 0, 1256706048, 0],
      "memory_percent": 6.49546764628092,
      "name": "qemu-system-x86_64",
      "nice": 0,
      "num_threads": 6,
      "pid": 165054,
      "status": "S",
      "time_since_update": 1,
      "username": "root"},
     {"cmdline": ["/usr/share/code/code",
                  "--ms-enable-electron-run-as-node",
                  "/home/nicolargo/.vscode/extensions/ms-python.vscode-pylance-2023.1.40/dist/server.bundle.js",
                  "--cancellationReceive=file:9e8ad4331c82252be52c9e10943b0d98e4704856e6",
                  "--node-ipc",
                  "--clientProcessId=152377"],
      "cpu_percent": 0.0,
      "cpu_times": [292.89, 21.42, 1.52, 0.16, 0.0],
      "gids": [1000, 1000, 1000],
      "io_counters": [103936000, 573440, 0, 0, 0],
      "key": "pid",
      "memory_info": [444641280, 49868906496, 31858688, 112656384, 0, 718778368, 0],
      "memory_percent": 5.674197416385889,
      "name": "code",
      "nice": 0,
      "num_threads": 13,
      "pid": 152522,
      "status": "S",
      "time_since_update": 1,
      "username": "nicolargo"}]

Get a specific field::

    # curl http://localhost:61208/api/3/processlist/pid
    {"pid": [165054,
             152522,
             5040,
             5246,
             5752,
             5369,
             4150,
             10653,
             173071,
             5365,
             173932,
             171502,
             166223,
             180530,
             152377,
             137271,
             176436,
             182287,
             173116,
             184024,
             177108,
             151269,
             178661,
             173149,
             10547,
             168824,
             422,
             5261,
             185474,
             10709,
             186130,
             185886,
             185571,
             6074,
             10612,
             171875,
             178970,
             168735,
             178475,
             42687,
             168734,
             187074,
             4035,
             62850,
             2512,
             95798,
             10732,
             4473,
             4544,
             2721,
             4585,
             1816,
             152506,
             10632,
             4932,
             4413,
             4248,
             1672,
             14455,
             3955,
             14458,
             6020,
             5179,
             164782,
             4325,
             4332,
             4625,
             1635,
             4331,
             43005,
             6022,
             4445,
             160043,
             186352,
             4223,
             4352,
             4659,
             4330,
             156821,
             1,
             129101,
             129097,
             2239,
             4263,
             1681,
             1660,
             4561,
             156833,
             178639,
             129087,
             178867,
             4214,
             4182,
             1682,
             1876,
             3944,
             3968,
             4339,
             10557,
             4130,
             1442,
             3934,
             4327,
             4233,
             96102,
             1655,
             4137,
             1777,
             4261,
             4334,
             1634,
             17189,
             4485,
             4328,
             10558,
             1873,
             3351,
             17205,
             1617,
             59511,
             2179,
             4392,
             3971,
             4166,
             3966,
             4155,
             4348,
             4573,
             4178,
             4050,
             4452,
             4192,
             117714,
             4524,
             1675,
             4229,
             6095,
             1661,
             4347,
             4377,
             1673,
             5299,
             152553,
             1643,
             4329,
             42986,
             4335,
             160053,
             4324,
             4314,
             468,
             4173,
             4212,
             4337,
             4443,
             4201,
             3976,
             129099,
             1676,
             4045,
             1666,
             1885,
             1631,
             1670,
             3952,
             1443,
             4119,
             9703,
             1626,
             129100,
             1646,
             3953,
             3700,
             2020,
             4162,
             178850,
             1441,
             3701,
             178609,
             1633,
             178617,
             178843,
             49191,
             165074,
             186999,
             49179,
             14505,
             4579,
             1685,
             1449,
             1450,
             3354,
             10591,
             2472,
             164891,
             49182,
             160052,
             1618,
             1803,
             1804,
             10560,
             49194,
             42952,
             184504,
             187073,
             42969,
             42937,
             42964,
             4018,
             4323,
             2480,
             3707,
             4820,
             3945,
             2503,
             2475,
             181945,
             1695,
             1447,
             2485,
             1628,
             49185,
             178889,
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
             156446,
             156447,
             156448,
             165059,
             165063,
             171811,
             174709,
             181685,
             182152,
             182465,
             183251,
             183453,
             184060,
             184494,
             184765,
             185058,
             185059,
             185233,
             185234,
             185575,
             185576,
             185577,
             185578,
             185753,
             185754,
             185793,
             186114,
             186175,
             186214,
             186242,
             186243,
             186244,
             186245,
             186246,
             186247,
             186248,
             186249,
             186250,
             186251,
             186252,
             186253,
             186254,
             186255,
             186256,
             186257,
             186258,
             186259,
             186260,
             186261,
             186262,
             186263,
             186264,
             186265,
             186266,
             186267,
             186268,
             186269,
             186270,
             186271,
             186272,
             186273,
             186274,
             186275,
             186276,
             186277,
             186278,
             186279,
             186280,
             186281,
             186282,
             186283,
             186284,
             186285,
             186286,
             186287,
             186288,
             186289,
             186290,
             186291,
             186292,
             186293,
             186294,
             186295,
             186296,
             186297,
             186298,
             186299,
             186300,
             186301,
             186302,
             186303,
             186304,
             186305,
             186306]}

Get a specific item when field matchs the given value::

    # curl http://localhost:61208/api/3/processlist/pid/165054
    {"165054": [{"cmdline": ["/snap/multipass/8140/usr/bin/qemu-system-x86_64",
                             "--enable-kvm",
                             "-cpu",
                             "host",
                             "-nic",
                             "tap,ifname=tap-1e376645a40,script=no,downscript=no,model=virtio-net-pci,mac=52:54:00:05:05:17",
                             "-device",
                             "virtio-scsi-pci,id=scsi0",
                             "-drive",
                             "file=/var/snap/multipass/common/data/multipassd/vault/instances/primary/ubuntu-22.04-server-cloudimg-amd64.img,if=none,format=qcow2,discard=unmap,id=hda",
                             "-device",
                             "scsi-hd,drive=hda,bus=scsi0.0",
                             "-smp",
                             "1",
                             "-m",
                             "1024M",
                             "-qmp",
                             "stdio",
                             "-chardev",
                             "null,id=char0",
                             "-serial",
                             "chardev:char0",
                             "-nographic",
                             "-cdrom",
                             "/var/snap/multipass/common/data/multipassd/vault/instances/primary/cloud-init-config.iso",
                             "-loadvm",
                             "suspend",
                             "-machine",
                             "pc-i440fx-focal"],
                 "cpu_percent": 0.0,
                 "cpu_times": [15.8, 8.88, 0.0, 0.0, 0.0],
                 "gids": [0, 0, 0],
                 "io_counters": [0, 0, 0, 0, 0],
                 "key": "pid",
                 "memory_info": [508997632,
                                 2645762048,
                                 4816896,
                                 5414912,
                                 0,
                                 1256706048,
                                 0],
                 "memory_percent": 6.49546764628092,
                 "name": "qemu-system-x86_64",
                 "nice": 0,
                 "num_threads": 6,
                 "pid": 165054,
                 "status": "S",
                 "time_since_update": 1,
                 "username": "root"}]}

GET psutilversion
-----------------

Get plugin stats::

    # curl http://localhost:61208/api/3/psutilversion
    [5, 9, 4]

GET quicklook
-------------

Get plugin stats::

    # curl http://localhost:61208/api/3/quicklook
    {"cpu": 31.2,
     "cpu_hz": 2025000000.0,
     "cpu_hz_current": 1498985500.0,
     "cpu_name": "Intel(R) Core(TM) i7-4500U CPU @ 1.80GHz",
     "mem": 82.8,
     "percpu": [{"cpu_number": 0,
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
                 "user": 11.0},
                {"cpu_number": 1,
                 "guest": 0.0,
                 "guest_nice": 0.0,
                 "idle": 41.0,
                 "iowait": 0.0,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 0.0,
                 "steal": 0.0,
                 "system": 0.0,
                 "total": 59.0,
                 "user": 41.0},
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
                 "user": 12.0},
                {"cpu_number": 3,
                 "guest": 0.0,
                 "guest_nice": 0.0,
                 "idle": 47.0,
                 "iowait": 1.0,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 0.0,
                 "steal": 0.0,
                 "system": 6.0,
                 "total": 53.0,
                 "user": 28.0}],
     "swap": 25.9}

Get a specific field::

    # curl http://localhost:61208/api/3/quicklook/cpu
    {"cpu": 31.2}

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
    "15 days, 23:40:18"

GET all stats
-------------

Get all Glances stats::

    # curl http://localhost:61208/api/3/all
    Return a very big dictionnary (avoid using this request, performances will be poor)...

GET stats history
-----------------

History of a plugin::

    # curl http://localhost:61208/api/3/cpu/history
    {"system": [["2023-01-30T16:51:09.475449", 6.3],
                ["2023-01-30T16:51:10.596399", 6.3],
                ["2023-01-30T16:51:11.787449", 2.1]],
     "user": [["2023-01-30T16:51:09.475441", 25.7],
              ["2023-01-30T16:51:10.596393", 25.7],
              ["2023-01-30T16:51:11.787442", 5.0]]}

Limit history to last 2 values::

    # curl http://localhost:61208/api/3/cpu/history/2
    {"system": [["2023-01-30T16:51:10.596399", 6.3],
                ["2023-01-30T16:51:11.787449", 2.1]],
     "user": [["2023-01-30T16:51:10.596393", 25.7],
              ["2023-01-30T16:51:11.787442", 5.0]]}

History for a specific field::

    # curl http://localhost:61208/api/3/cpu/system/history
    {"system": [["2023-01-30T16:51:09.475449", 6.3],
                ["2023-01-30T16:51:10.596399", 6.3],
                ["2023-01-30T16:51:11.787449", 2.1]]}

Limit history for a specific field to last 2 values::

    # curl http://localhost:61208/api/3/cpu/system/history
    {"system": [["2023-01-30T16:51:10.596399", 6.3],
                ["2023-01-30T16:51:11.787449", 2.1]]}

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


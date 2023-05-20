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
    [[1684593857.0,
      -1,
      "WARNING",
      "MEM",
      74.95383222581204,
      74.95383222581204,
      74.95383222581204,
      74.95383222581204,
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
      "timer": 1.7997314929962158},
     {"count": 0,
      "countmax": 20.0,
      "countmin": None,
      "key": "name",
      "name": "Python",
      "refresh": 3.0,
      "regex": True,
      "result": None,
      "timer": 1.7995269298553467}]

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
                  "timer": 1.7997314929962158}]}

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
                     "cpu": {"total": 2.2993346332214973e-06},
                     "cpu_percent": 2.2993346332214973e-06,
                     "engine": "podman",
                     "io": {"ior": 0.0, "iow": 0.0, "time_since_update": 1},
                     "io_r": 0.0,
                     "io_w": 0.0,
                     "key": "name",
                     "memory": {"limit": 7836184576.0, "usage": 1142784.0},
                     "memory_usage": 1142784.0,
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
                     "cpu": {"total": 2.754373096346692e-10},
                     "cpu_percent": 2.754373096346692e-10,
                     "engine": "podman",
                     "io": {"ior": 0.0, "iow": 0.0, "time_since_update": 1},
                     "io_r": 0.0,
                     "io_w": 0.0,
                     "key": "name",
                     "memory": {"limit": 7836184576.0, "usage": 208896.0},
                     "memory_usage": 208896.0,
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
                     "Uptime": "7 hours",
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
     "guest": 1.1,
     "guest_nice": 0.0,
     "idle": 38.7,
     "interrupts": 0,
     "iowait": 3.2,
     "irq": 0.0,
     "nice": 0.0,
     "soft_interrupts": 0,
     "softirq": 0.4,
     "steal": 0.0,
     "syscalls": 0,
     "system": 7.7,
     "time_since_update": 1,
     "total": 62.2,
     "user": 50.0}

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
    {"total": 62.2}

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
      "free": 4763168768,
      "fs_type": "ext4",
      "key": "mnt_point",
      "mnt_point": "/",
      "percent": 97.9,
      "size": 243334156288,
      "used": 226183532544},
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
            "free": 4763168768,
            "fs_type": "ext4",
            "key": "mnt_point",
            "mnt_point": "/",
            "percent": 97.9,
            "size": 243334156288,
            "used": 226183532544}]}

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
     "min1": 3.00634765625,
     "min15": 1.19775390625,
     "min5": 1.4345703125}

Fields descriptions:

* **min1**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 1 minute (unit is *float*)
* **min5**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 5 minutes (unit is *float*)
* **min15**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 15 minutes (unit is *float*)
* **cpucore**: Total number of CPU core (unit is *number*)

Get a specific field::

    # curl http://localhost:61208/api/3/load/min1
    {"min1": 3.00634765625}

GET mem
-------

Get plugin stats::

    # curl http://localhost:61208/api/3/mem
    {"active": 3130548224,
     "available": 1962663936,
     "buffers": 142680064,
     "cached": 2079936512,
     "free": 1962663936,
     "inactive": 3094474752,
     "percent": 75.0,
     "shared": 498302976,
     "total": 7836184576,
     "used": 5873520640}

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
    {"free": 3018182656,
     "percent": 62.7,
     "sin": 10520571904,
     "sout": 16592646144,
     "time_since_update": 1,
     "total": 8082419712,
     "used": 5064237056}

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
      "cumulative_cx": 344481682,
      "cumulative_rx": 172240841,
      "cumulative_tx": 172240841,
      "cx": 7770,
      "interface_name": "lo",
      "is_up": True,
      "key": "interface_name",
      "rx": 3885,
      "speed": 0,
      "time_since_update": 1,
      "tx": 3885},
     {"alias": None,
      "cumulative_cx": 22624441944,
      "cumulative_rx": 21888194655,
      "cumulative_tx": 736247289,
      "cx": 146685,
      "interface_name": "wlp2s0",
      "is_up": True,
      "key": "interface_name",
      "rx": 135811,
      "speed": 0,
      "time_since_update": 1,
      "tx": 10874}]

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
                        "vboxnet0",
                        "tap-1e376645a40",
                        "veth54fd604"]}

Get a specific item when field matchs the given value::

    # curl http://localhost:61208/api/3/network/interface_name/lo
    {"lo": [{"alias": None,
             "cumulative_cx": 344481682,
             "cumulative_rx": 172240841,
             "cumulative_tx": 172240841,
             "cx": 7770,
             "interface_name": "lo",
             "is_up": True,
             "key": "interface_name",
             "rx": 3885,
             "speed": 0,
             "time_since_update": 1,
             "tx": 3885}]}

GET now
-------

Get plugin stats::

    # curl http://localhost:61208/api/3/now
    "2023-05-20 16:44:16 CEST"

GET percpu
----------

Get plugin stats::

    # curl http://localhost:61208/api/3/percpu
    [{"cpu_number": 0,
      "guest": 1.5,
      "guest_nice": 0.0,
      "idle": 26.2,
      "iowait": 1.5,
      "irq": 0.0,
      "key": "cpu_number",
      "nice": 0.0,
      "softirq": 0.0,
      "steal": 0.0,
      "system": 4.4,
      "total": 73.8,
      "user": 68.0},
     {"cpu_number": 1,
      "guest": 0.0,
      "guest_nice": 0.0,
      "idle": 39.4,
      "iowait": 1.0,
      "irq": 0.0,
      "key": "cpu_number",
      "nice": 0.0,
      "softirq": 0.0,
      "steal": 0.0,
      "system": 4.8,
      "total": 60.6,
      "user": 54.8}]

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
      "status": 0.00792,
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
                        "status": 0.00792,
                        "timeout": 3}]}

GET processcount
----------------

Get plugin stats::

    # curl http://localhost:61208/api/3/processcount
    {"pid_max": 0, "running": 1, "sleeping": 347, "thread": 1761, "total": 415}

Get a specific field::

    # curl http://localhost:61208/api/3/processcount/total
    {"total": 415}

GET processlist
---------------

Get plugin stats::

    # curl http://localhost:61208/api/3/processlist
    [{"cmdline": ["/snap/firefox/2605/usr/lib/firefox/firefox"],
      "cpu_percent": 0.0,
      "cpu_times": [16463.82, 5059.85, 11961.09, 1725.84, 0.0],
      "gids": [1000, 1000, 1000],
      "io_counters": [9699624960, 15455608832, 0, 0, 0],
      "key": "pid",
      "memory_info": [524517376, 22345007104, 90595328, 618496, 0, 1481629696, 0],
      "memory_percent": 6.693530134632704,
      "name": "firefox",
      "nice": 0,
      "num_threads": 171,
      "pid": 10541,
      "status": "S",
      "time_since_update": 1,
      "username": "nicolargo"},
     {"cmdline": ["/snap/multipass/8465/usr/bin/qemu-system-x86_64",
                  "-bios",
                  "OVMF.fd",
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
                  "/var/snap/multipass/common/data/multipassd/vault/instances/primary/cloud-init-config.iso"],
      "cpu_percent": 0.0,
      "cpu_times": [846.85, 90.96, 0.0, 0.0, 0.0],
      "gids": [0, 0, 0],
      "io_counters": [0, 0, 0, 0, 0],
      "key": "pid",
      "memory_info": [510238720, 3458437120, 2822144, 5304320, 0, 1366933504, 0],
      "memory_percent": 6.511315743668364,
      "name": "qemu-system-x86_64",
      "nice": 0,
      "num_threads": 4,
      "pid": 354319,
      "status": "S",
      "time_since_update": 1,
      "username": "root"}]

Get a specific field::

    # curl http://localhost:61208/api/3/processlist/pid
    {"pid": [10541,
             354319,
             10770,
             11043,
             374779,
             374071,
             3927,
             469948,
             374587,
             317865,
             10778,
             10774,
             429788,
             59195,
             469241,
             399766,
             430971,
             372037,
             11646,
             59069,
             374904,
             10733,
             480322,
             480143,
             480228,
             374842,
             435889,
             10790,
             59161,
             480580,
             59523,
             4243,
             421,
             480591,
             466459,
             374575,
             374705,
             3810,
             457618,
             466460,
             374905,
             372303,
             4385,
             165661,
             417207,
             463383,
             1618,
             1771,
             372048,
             372151,
             2398,
             372186,
             372172,
             59182,
             4339,
             374703,
             313257,
             2636,
             431242,
             374702,
             4023,
             4666,
             1,
             3730,
             4179,
             59663,
             1584,
             427863,
             4075,
             10710,
             17997,
             430855,
             4308,
             4091,
             1630,
             1605,
             4403,
             4000,
             4009,
             4090,
             3991,
             3719,
             11381,
             11380,
             1794,
             372168,
             431219,
             479905,
             372170,
             354726,
             4169,
             372169,
             4086,
             1727,
             4033,
             3745,
             4105,
             3901,
             3710,
             4442,
             3908,
             4046,
             4127,
             36919,
             1631,
             3743,
             14243,
             1583,
             4302,
             3956,
             1379,
             418247,
             74953,
             4126,
             3748,
             3115,
             20173,
             14266,
             1591,
             4196,
             59126,
             2116,
             4005,
             1764,
             4316,
             4145,
             4097,
             4080,
             1627,
             2168,
             2607,
             1818,
             3989,
             1579,
             1628,
             3925,
             4079,
             4244,
             4157,
             3970,
             59127,
             2554,
             4099,
             1612,
             3819,
             1380,
             4078,
             10848,
             2341,
             1566,
             227509,
             1598,
             1624,
             4119,
             4074,
             3825,
             3947,
             4098,
             4062,
             3939,
             4107,
             3975,
             3753,
             3952,
             1575,
             1606,
             313277,
             461,
             354741,
             1593,
             480538,
             3934,
             3728,
             12480,
             3888,
             1616,
             59145,
             12489,
             1377,
             1582,
             18045,
             4332,
             1964,
             1825,
             3727,
             59130,
             1634,
             16182,
             1391,
             2361,
             2605,
             1577,
             3118,
             2604,
             1390,
             12483,
             1567,
             431184,
             20396,
             354739,
             431178,
             431203,
             20180,
             480579,
             431197,
             4072,
             2358,
             469137,
             3503,
             12492,
             1726,
             1725,
             3794,
             3498,
             3499,
             3720,
             20400,
             313283,
             2345,
             2382,
             4593,
             2360,
             1392,
             1637,
             3573,
             20185,
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
             12486,
             313404,
             354325,
             354329,
             417249,
             417250,
             417251,
             417252,
             417254,
             417255,
             417257,
             417258,
             417259,
             417260,
             417261,
             417262,
             417263,
             417264,
             417265,
             417266,
             417267,
             427608,
             427609,
             427611,
             454059,
             459092,
             463267,
             463268,
             463271,
             463272,
             463274,
             463320,
             467345,
             467496,
             468536,
             468902,
             469637,
             469929,
             470092,
             471704,
             476042,
             477638,
             478302,
             479060,
             479698,
             479767,
             480036,
             480278,
             480424,
             480454]}

Get a specific item when field matchs the given value::

    # curl http://localhost:61208/api/3/processlist/pid/10541
    {"10541": [{"cmdline": ["/snap/firefox/2605/usr/lib/firefox/firefox"],
                "cpu_percent": 0.0,
                "cpu_times": [16463.82, 5059.85, 11961.09, 1725.84, 0.0],
                "gids": [1000, 1000, 1000],
                "io_counters": [9699624960, 15455608832, 0, 0, 0],
                "key": "pid",
                "memory_info": [524517376,
                                22345007104,
                                90595328,
                                618496,
                                0,
                                1481629696,
                                0],
                "memory_percent": 6.693530134632704,
                "name": "firefox",
                "nice": 0,
                "num_threads": 171,
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
    {"cpu": 62.2,
     "cpu_hz": 2025000000.0,
     "cpu_hz_current": 1273980750.0,
     "cpu_name": "Intel(R) Core(TM) i7-4500U CPU @ 1.80GHz",
     "mem": 75.0,
     "percpu": [{"cpu_number": 0,
                 "guest": 1.5,
                 "guest_nice": 0.0,
                 "idle": 26.2,
                 "iowait": 1.5,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 0.0,
                 "steal": 0.0,
                 "system": 4.4,
                 "total": 73.8,
                 "user": 68.0},
                {"cpu_number": 1,
                 "guest": 0.0,
                 "guest_nice": 0.0,
                 "idle": 39.4,
                 "iowait": 1.0,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 0.0,
                 "steal": 0.0,
                 "system": 4.8,
                 "total": 60.6,
                 "user": 54.8},
                {"cpu_number": 2,
                 "guest": 0.5,
                 "guest_nice": 0.0,
                 "idle": 36.0,
                 "iowait": 4.3,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 0.9,
                 "steal": 0.0,
                 "system": 9.5,
                 "total": 64.0,
                 "user": 49.3},
                {"cpu_number": 3,
                 "guest": 2.8,
                 "guest_nice": 0.0,
                 "idle": 36.6,
                 "iowait": 6.5,
                 "irq": 0.0,
                 "key": "cpu_number",
                 "nice": 0.0,
                 "softirq": 0.0,
                 "steal": 0.0,
                 "system": 12.5,
                 "total": 63.4,
                 "user": 44.4}],
     "swap": 62.7}

Get a specific field::

    # curl http://localhost:61208/api/3/quicklook/cpu
    {"cpu": 62.2}

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
    "12 days, 3:42:29"

GET all stats
-------------

Get all Glances stats::

    # curl http://localhost:61208/api/3/all
    Return a very big dictionnary (avoid using this request, performances will be poor)...

GET stats history
-----------------

History of a plugin::

    # curl http://localhost:61208/api/3/cpu/history
    {"system": [["2023-05-20T16:44:17.685943", 7.7],
                ["2023-05-20T16:44:18.817737", 7.7],
                ["2023-05-20T16:44:19.996995", 1.1]],
     "user": [["2023-05-20T16:44:17.685935", 50.0],
              ["2023-05-20T16:44:18.817731", 50.0],
              ["2023-05-20T16:44:19.996988", 4.3]]}

Limit history to last 2 values::

    # curl http://localhost:61208/api/3/cpu/history/2
    {"system": [["2023-05-20T16:44:18.817737", 7.7],
                ["2023-05-20T16:44:19.996995", 1.1]],
     "user": [["2023-05-20T16:44:18.817731", 50.0],
              ["2023-05-20T16:44:19.996988", 4.3]]}

History for a specific field::

    # curl http://localhost:61208/api/3/cpu/system/history
    {"system": [["2023-05-20T16:44:17.685943", 7.7],
                ["2023-05-20T16:44:18.817737", 7.7],
                ["2023-05-20T16:44:19.996995", 1.1]]}

Limit history for a specific field to last 2 values::

    # curl http://localhost:61208/api/3/cpu/system/history
    {"system": [["2023-05-20T16:44:18.817737", 7.7],
                ["2023-05-20T16:44:19.996995", 1.1]]}

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


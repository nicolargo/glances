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
    'HTTP/1.0 200 OK'

GET plugins list
----------------

Get the plugins list::

    # curl http://localhost:61208/api/3/pluginslist
    ['alert',
     'amps',
     'cloud',
     'connections',
     'core',
     'cpu',
     'diskio',
     'docker',
     'folders',
     'fs',
     'gpu',
     'help',
     'ip',
     'irq',
     'load',
     'mem',
     'memswap',
     'network',
     'now',
     'percpu',
     'ports',
     'processcount',
     'processlist',
     'psutilversion',
     'quicklook',
     'raid',
     'sensors',
     'smart',
     'system',
     'uptime',
     'wifi']

GET alert
---------

Get plugin stats::

    # curl http://localhost:61208/api/3/alert
    [[1649600032.0,
      -1,
      'WARNING',
      'MEM',
      87.2703077870435,
      87.2703077870435,
      87.2703077870435,
      87.2703077870435,
      1,
      [],
      '',
      'memory_percent']]

GET amps
--------

Get plugin stats::

    # curl http://localhost:61208/api/3/amps
    [{'count': 0,
      'countmax': None,
      'countmin': 1.0,
      'key': 'name',
      'name': 'Dropbox',
      'refresh': 3.0,
      'regex': True,
      'result': None,
      'timer': 0.14095854759216309},
     {'count': 0,
      'countmax': 20.0,
      'countmin': None,
      'key': 'name',
      'name': 'Python',
      'refresh': 3.0,
      'regex': True,
      'result': None,
      'timer': 0.14076852798461914}]

Get a specific field::

    # curl http://localhost:61208/api/3/amps/name
    {'name': ['Dropbox', 'Python', 'Conntrack', 'Nginx', 'Systemd', 'SystemV']}

Get a specific item when field matchs the given value::

    # curl http://localhost:61208/api/3/amps/name/Dropbox
    {'Dropbox': [{'count': 0,
                  'countmax': None,
                  'countmin': 1.0,
                  'key': 'name',
                  'name': 'Dropbox',
                  'refresh': 3.0,
                  'regex': True,
                  'result': None,
                  'timer': 0.14095854759216309}]}

GET core
--------

Get plugin stats::

    # curl http://localhost:61208/api/3/core
    {'log': 4, 'phys': 2}

Fields descriptions:

* **phys**: Number of physical cores (hyper thread CPUs are excluded) (unit is *number*)
* **log**: Number of logical CPUs. A logical CPU is the number of physical cores multiplied by the number of threads that can run on each core (unit is *number*)

Get a specific field::

    # curl http://localhost:61208/api/3/core/phys
    {'phys': 2}

GET cpu
-------

Get plugin stats::

    # curl http://localhost:61208/api/3/cpu
    {'cpucore': 4,
     'ctx_switches': 0,
     'guest': 0.0,
     'guest_nice': 0.0,
     'idle': 59.6,
     'interrupts': 0,
     'iowait': 0.2,
     'irq': 0.0,
     'nice': 0.7,
     'soft_interrupts': 0,
     'softirq': 0.9,
     'steal': 0.0,
     'syscalls': 0,
     'system': 10.1,
     'time_since_update': 1,
     'total': 38.8,
     'user': 28.5}

Fields descriptions:

* **total**: Sum of all CPU percentages (except idle) (unit is *percent*)
* **system**: percent time spent in kernel space. System CPU time is the time spent running code in the Operating System kernel (unit is *percent*)
* **user**: CPU percent time spent in user space. User CPU time is the time spent on the processor running your program's code (or code in libraries) (unit is *percent*)
* **iowait**: *(Linux)*: percent time spent by the CPU waiting for I/O operations to complete (unit is *percent*)
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
    {'total': 38.8}

GET diskio
----------

Get plugin stats::

    # curl http://localhost:61208/api/3/diskio
    [{'disk_name': 'sda',
      'key': 'disk_name',
      'read_bytes': 0,
      'read_count': 0,
      'time_since_update': 1,
      'write_bytes': 0,
      'write_count': 0},
     {'disk_name': 'sda1',
      'key': 'disk_name',
      'read_bytes': 0,
      'read_count': 0,
      'time_since_update': 1,
      'write_bytes': 0,
      'write_count': 0}]

Get a specific field::

    # curl http://localhost:61208/api/3/diskio/disk_name
    {'disk_name': ['sda', 'sda1', 'sda2', 'sda5', 'dm-0', 'dm-1']}

Get a specific item when field matchs the given value::

    # curl http://localhost:61208/api/3/diskio/disk_name/sda
    {'sda': [{'disk_name': 'sda',
              'key': 'disk_name',
              'read_bytes': 0,
              'read_count': 0,
              'time_since_update': 1,
              'write_bytes': 0,
              'write_count': 0}]}

GET fs
------

Get plugin stats::

    # curl http://localhost:61208/api/3/fs
    [{'device_name': '/dev/mapper/ubuntu--gnome--vg-root',
      'free': 79632797696,
      'fs_type': 'ext4',
      'key': 'mnt_point',
      'mnt_point': '/',
      'percent': 65.5,
      'size': 243396149248,
      'used': 151375896576}]

Get a specific field::

    # curl http://localhost:61208/api/3/fs/mnt_point
    {'mnt_point': ['/']}

Get a specific item when field matchs the given value::

    # curl http://localhost:61208/api/3/fs/mnt_point//
    {'/': [{'device_name': '/dev/mapper/ubuntu--gnome--vg-root',
            'free': 79632797696,
            'fs_type': 'ext4',
            'key': 'mnt_point',
            'mnt_point': '/',
            'percent': 65.5,
            'size': 243396149248,
            'used': 151375896576}]}

GET ip
------

Get plugin stats::

    # curl http://localhost:61208/api/3/ip
    {'address': '192.168.0.49',
     'gateway': '192.168.0.254',
     'mask': '255.255.255.0',
     'mask_cidr': 24,
     'public_address': '88.165.169.242'}

Get a specific field::

    # curl http://localhost:61208/api/3/ip/address
    {'address': '192.168.0.49'}

GET load
--------

Get plugin stats::

    # curl http://localhost:61208/api/3/load
    {'cpucore': 4, 'min1': 1.76, 'min15': 1.61, 'min5': 1.69}

Fields descriptions:

* **min1**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 1 minute (unit is *float*)
* **min5**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 5 minutes (unit is *float*)
* **min15**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 15 minutes (unit is *float*)
* **cpucore**: Total number of CPU core (unit is *number*)

Get a specific field::

    # curl http://localhost:61208/api/3/load/min1
    {'min1': 1.76}

GET mem
-------

Get plugin stats::

    # curl http://localhost:61208/api/3/mem
    {'active': 3452456960,
     'available': 999153664,
     'buffers': 112189440,
     'cached': 1540894720,
     'free': 999153664,
     'inactive': 1303179264,
     'percent': 87.3,
     'shared': 497025024,
     'total': 7849000960,
     'used': 6849847296}

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
    {'total': 7849000960}

GET memswap
-----------

Get plugin stats::

    # curl http://localhost:61208/api/3/memswap
    {'free': 7769960448,
     'percent': 3.9,
     'sin': 21983232,
     'sout': 333402112,
     'time_since_update': 1,
     'total': 8082419712,
     'used': 312459264}

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
    {'total': 8082419712}

GET network
-----------

Get plugin stats::

    # curl http://localhost:61208/api/3/network
    [{'alias': None,
      'cumulative_cx': 243100,
      'cumulative_rx': 6357,
      'cumulative_tx': 236743,
      'cx': 0,
      'interface_name': 'docker0',
      'is_up': False,
      'key': 'interface_name',
      'rx': 0,
      'speed': 0,
      'time_since_update': 1,
      'tx': 0},
     {'alias': None,
      'cumulative_cx': 183333,
      'cumulative_rx': 0,
      'cumulative_tx': 183333,
      'cx': 0,
      'interface_name': 'vboxnet0',
      'is_up': True,
      'key': 'interface_name',
      'rx': 0,
      'speed': 10485760,
      'time_since_update': 1,
      'tx': 0}]

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
    {'interface_name': ['docker0',
                        'vboxnet0',
                        'br-87386b77b676',
                        'lo',
                        'br-119e6ee04e05',
                        'br_grafana',
                        'mpqemubr0',
                        'wlp2s0']}

Get a specific item when field matchs the given value::

    # curl http://localhost:61208/api/3/network/interface_name/docker0
    {'docker0': [{'alias': None,
                  'cumulative_cx': 243100,
                  'cumulative_rx': 6357,
                  'cumulative_tx': 236743,
                  'cx': 0,
                  'interface_name': 'docker0',
                  'is_up': False,
                  'key': 'interface_name',
                  'rx': 0,
                  'speed': 0,
                  'time_since_update': 1,
                  'tx': 0}]}

GET now
-------

Get plugin stats::

    # curl http://localhost:61208/api/3/now
    '2022-04-10 16:13:52 CEST'

GET percpu
----------

Get plugin stats::

    # curl http://localhost:61208/api/3/percpu
    [{'cpu_number': 0,
      'guest': 0.0,
      'guest_nice': 0.0,
      'idle': 78.0,
      'iowait': 0.0,
      'irq': 0.0,
      'key': 'cpu_number',
      'nice': 1.0,
      'softirq': 0.0,
      'steal': 0.0,
      'system': 9.0,
      'total': 22.0,
      'user': 9.0},
     {'cpu_number': 1,
      'guest': 0.0,
      'guest_nice': 0.0,
      'idle': 55.0,
      'iowait': 0.0,
      'irq': 0.0,
      'key': 'cpu_number',
      'nice': 1.0,
      'softirq': 2.0,
      'steal': 0.0,
      'system': 7.0,
      'total': 45.0,
      'user': 32.0}]

Get a specific field::

    # curl http://localhost:61208/api/3/percpu/cpu_number
    {'cpu_number': [0, 1, 2, 3]}

GET ports
---------

Get plugin stats::

    # curl http://localhost:61208/api/3/ports
    [{'description': 'DefaultGateway',
      'host': '192.168.0.254',
      'indice': 'port_0',
      'port': 0,
      'refresh': 30,
      'rtt_warning': None,
      'status': 0.007151,
      'timeout': 3}]

Get a specific field::

    # curl http://localhost:61208/api/3/ports/host
    {'host': ['192.168.0.254']}

Get a specific item when field matchs the given value::

    # curl http://localhost:61208/api/3/ports/host/192.168.0.254
    {'192.168.0.254': [{'description': 'DefaultGateway',
                        'host': '192.168.0.254',
                        'indice': 'port_0',
                        'port': 0,
                        'refresh': 30,
                        'rtt_warning': None,
                        'status': 0.007151,
                        'timeout': 3}]}

GET processcount
----------------

Get plugin stats::

    # curl http://localhost:61208/api/3/processcount
    {'pid_max': 0, 'running': 1, 'sleeping': 261, 'thread': 1317, 'total': 319}

Get a specific field::

    # curl http://localhost:61208/api/3/processcount/total
    {'total': 319}

GET processlist
---------------

Get plugin stats::

    # curl http://localhost:61208/api/3/processlist
    [{'cmdline': ['/usr/lib/virtualbox/VBoxHeadless',
                  '--comment',
                  'minikube',
                  '--startvm',
                  '74869efd-ada3-41eb-98e3-b7d2901c8e39',
                  '--vrde',
                  'config'],
      'cpu_percent': 0.0,
      'cpu_times': pcputimes(user=128.45, system=1415.02, children_user=0.0, children_system=0.0, iowait=0.0),
      'gids': pgids(real=1000, effective=1000, saved=1000),
      'io_counters': [0, 0, 0, 0, 0],
      'key': 'pid',
      'memory_info': pmem(rss=963088384, vms=4204658688, shared=924651520, text=53248, lib=0, data=98004992, dirty=0),
      'memory_percent': 12.270203417072839,
      'name': 'VBoxHeadless',
      'nice': 0,
      'num_threads': 28,
      'pid': 9872,
      'ppid': 9690,
      'status': 'S',
      'time_since_update': 1,
      'username': 'nicolargo'},
     {'cmdline': ['/usr/lib/firefox/firefox',
                  '-contentproc',
                  '-childID',
                  '4',
                  '-isForBrowser',
                  '-prefsLen',
                  '4855',
                  '-prefMapSize',
                  '253021',
                  '-jsInitLen',
                  '278884',
                  '-parentBuildID',
                  '20211215221728',
                  '-appDir',
                  '/usr/lib/firefox/browser',
                  '4964',
                  'true',
                  'tab'],
      'cpu_percent': 0.0,
      'cpu_times': pcputimes(user=157.91, system=26.98, children_user=0.0, children_system=0.0, iowait=0.03),
      'gids': pgids(real=1000, effective=1000, saved=1000),
      'io_counters': [9154560, 0, 0, 0, 0],
      'key': 'pid',
      'memory_info': pmem(rss=413597696, vms=3211755520, shared=44220416, text=643072, lib=0, data=648302592, dirty=0),
      'memory_percent': 5.269431079289866,
      'name': 'WebExtensions',
      'nice': 0,
      'num_threads': 21,
      'pid': 5235,
      'ppid': 4964,
      'status': 'S',
      'time_since_update': 1,
      'username': 'nicolargo'}]

Get a specific field::

    # curl http://localhost:61208/api/3/processlist/pid
    {'pid': [9872,
             5235,
             4964,
             16062,
             5294,
             5305,
             16229,
             15998,
             5894,
             4033,
             15053,
             20039,
             20161,
             15933,
             16038,
             15966,
             5060,
             20727,
             20793,
             20685,
             5648,
             8850,
             16111,
             16075,
             2185,
             22482,
             3875,
             2233,
             15983,
             22458,
             3789,
             16242,
             3846,
             2410,
             7066,
             5563,
             15938,
             1332,
             15937,
             5595,
             4119,
             14247,
             14256,
             9690,
             349,
             1160,
             3787,
             4305,
             4193,
             4094,
             2380,
             4187,
             1315,
             2197,
             1320,
             4192,
             1,
             4088,
             1173,
             1175,
             4627,
             1199,
             5024,
             3531,
             9684,
             4062,
             2189,
             4130,
             2386,
             10484,
             4191,
             14266,
             4232,
             3777,
             4019,
             4194,
             4213,
             4589,
             4167,
             14265,
             15940,
             1039,
             4308,
             1584,
             4188,
             4105,
             4198,
             4064,
             3762,
             1326,
             3824,
             1196,
             1365,
             4057,
             3831,
             1142,
             3900,
             1158,
             3813,
             4276,
             4203,
             9177,
             16135,
             8860,
             1201,
             1195,
             2384,
             3797,
             4190,
             4209,
             1166,
             3855,
             3872,
             2385,
             1192,
             4068,
             4079,
             4102,
             4229,
             4179,
             3988,
             4186,
             4061,
             3791,
             4600,
             3536,
             1186,
             3861,
             3998,
             4301,
             4197,
             3817,
             3836,
             4269,
             4195,
             3842,
             1040,
             383,
             4200,
             1182,
             1168,
             1202,
             1150,
             4013,
             4003,
             4083,
             1151,
             1038,
             1155,
             1446,
             22470,
             16161,
             1230,
             1380,
             4546,
             1143,
             3778,
             22481,
             2062,
             2112,
             2218,
             2201,
             1235,
             2203,
             1015,
             377,
             1153,
             3970,
             2,
             3,
             4,
             6,
             9,
             10,
             11,
             12,
             13,
             14,
             15,
             16,
             17,
             18,
             21,
             22,
             23,
             24,
             26,
             27,
             28,
             29,
             30,
             32,
             33,
             34,
             35,
             36,
             37,
             38,
             39,
             40,
             41,
             42,
             90,
             91,
             92,
             93,
             94,
             95,
             96,
             97,
             98,
             102,
             103,
             105,
             106,
             108,
             110,
             119,
             122,
             137,
             188,
             189,
             191,
             192,
             193,
             194,
             195,
             196,
             197,
             202,
             203,
             204,
             207,
             208,
             238,
             280,
             286,
             289,
             291,
             307,
             363,
             368,
             388,
             396,
             398,
             399,
             400,
             401,
             469,
             495,
             520,
             636,
             766,
             767,
             768,
             769,
             771,
             772,
             773,
             774,
             775,
             776,
             785,
             786,
             881,
             910,
             912,
             913,
             915,
             917,
             922,
             929,
             933,
             935,
             938,
             942,
             945,
             951,
             954,
             956,
             957,
             965,
             969,
             973,
             976,
             978,
             1384,
             1458,
             1459,
             1461,
             1462,
             1464,
             1465,
             1466,
             1467,
             2257,
             2279,
             3847,
             6489,
             6712,
             7008,
             7325,
             7549,
             7739,
             7999,
             9904,
             13281,
             13643,
             13855,
             14128,
             16158,
             16256,
             16973,
             19932,
             20344,
             20572,
             20724,
             21047,
             22267]}

Get a specific item when field matchs the given value::

    # curl http://localhost:61208/api/3/processlist/pid/9872
    {'9872': [{'cmdline': ['/usr/lib/virtualbox/VBoxHeadless',
                           '--comment',
                           'minikube',
                           '--startvm',
                           '74869efd-ada3-41eb-98e3-b7d2901c8e39',
                           '--vrde',
                           'config'],
               'cpu_percent': 0.0,
               'cpu_times': [128.45, 1415.02, 0.0, 0.0, 0.0],
               'gids': [1000, 1000, 1000],
               'io_counters': [0, 0, 0, 0, 0],
               'key': 'pid',
               'memory_info': [963088384,
                               4204658688,
                               924651520,
                               53248,
                               0,
                               98004992,
                               0],
               'memory_percent': 12.270203417072839,
               'name': 'VBoxHeadless',
               'nice': 0,
               'num_threads': 28,
               'pid': 9872,
               'ppid': 9690,
               'status': 'S',
               'time_since_update': 1,
               'username': 'nicolargo'}]}

GET psutilversion
-----------------

Get plugin stats::

    # curl http://localhost:61208/api/3/psutilversion
    (5, 9, 0)

GET quicklook
-------------

Get plugin stats::

    # curl http://localhost:61208/api/3/quicklook
    {'cpu': 38.8,
     'cpu_hz': 3000000000.0,
     'cpu_hz_current': 2543000.0,
     'cpu_name': 'Intel(R) Core(TM) i7-4500U CPU @ 1.80GHz',
     'mem': 87.3,
     'percpu': [{'cpu_number': 0,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 78.0,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 1.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 9.0,
                 'total': 22.0,
                 'user': 9.0},
                {'cpu_number': 1,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 55.0,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 1.0,
                 'softirq': 2.0,
                 'steal': 0.0,
                 'system': 7.0,
                 'total': 45.0,
                 'user': 32.0},
                {'cpu_number': 2,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 78.0,
                 'iowait': 1.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 9.0,
                 'total': 22.0,
                 'user': 10.0},
                {'cpu_number': 3,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 27.0,
                 'iowait': 1.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 1.0,
                 'steal': 0.0,
                 'system': 3.0,
                 'total': 73.0,
                 'user': 66.0}],
     'swap': 3.9}

Get a specific field::

    # curl http://localhost:61208/api/3/quicklook/cpu
    {'cpu': 38.8}

GET sensors
-----------

Get plugin stats::

    # curl http://localhost:61208/api/3/sensors
    [{'critical': 105,
      'key': 'label',
      'label': 'acpitz 1',
      'type': 'temperature_core',
      'unit': 'C',
      'value': 27,
      'warning': 105},
     {'critical': 105,
      'key': 'label',
      'label': 'acpitz 2',
      'type': 'temperature_core',
      'unit': 'C',
      'value': 29,
      'warning': 105}]

Get a specific field::

    # curl http://localhost:61208/api/3/sensors/label
    {'label': ['acpitz 1',
               'acpitz 2',
               'CPU',
               'Ambient',
               'SODIMM',
               'Package id 0',
               'Core 0',
               'Core 1',
               'BAT BAT0']}

Get a specific item when field matchs the given value::

    # curl http://localhost:61208/api/3/sensors/label/acpitz 1
    {'acpitz 1': [{'critical': 105,
                   'key': 'label',
                   'label': 'acpitz 1',
                   'type': 'temperature_core',
                   'unit': 'C',
                   'value': 27,
                   'warning': 105}]}

GET system
----------

Get plugin stats::

    # curl http://localhost:61208/api/3/system
    {'hostname': 'XPS13-9333',
     'hr_name': 'Ubuntu 20.04 64bit',
     'linux_distro': 'Ubuntu 20.04',
     'os_name': 'Linux',
     'os_version': '5.4.0-91-generic',
     'platform': '64bit'}

Get a specific field::

    # curl http://localhost:61208/api/3/system/os_name
    {'os_name': 'Linux'}

GET uptime
----------

Get plugin stats::

    # curl http://localhost:61208/api/3/uptime
    {'seconds': 199257}

GET all stats
-------------

Get all Glances stats::

    # curl http://localhost:61208/api/3/all
    Return a very big dictionnary (avoid using this request, performances will be poor)...

GET stats history
-----------------

History of a plugin::

    # curl http://localhost:61208/api/3/cpu/history
    {'system': [['2022-04-10T16:13:53.155669', 10.1],
                ['2022-04-10T16:13:54.194594', 10.1],
                ['2022-04-10T16:13:55.280474', 10.9]],
     'user': [['2022-04-10T16:13:53.155662', 28.5],
              ['2022-04-10T16:13:54.194590', 28.5],
              ['2022-04-10T16:13:55.280470', 4.2]]}

Limit history to last 2 values::

    # curl http://localhost:61208/api/3/cpu/history/2
    {'system': [['2022-04-10T16:13:54.194594', 10.1],
                ['2022-04-10T16:13:55.280474', 10.9]],
     'user': [['2022-04-10T16:13:54.194590', 28.5],
              ['2022-04-10T16:13:55.280470', 4.2]]}

History for a specific field::

    # curl http://localhost:61208/api/3/cpu/system/history
    {'system': [['2022-04-10T16:13:53.155669', 10.1],
                ['2022-04-10T16:13:54.194594', 10.1],
                ['2022-04-10T16:13:55.280474', 10.9]]}

Limit history for a specific field to last 2 values::

    # curl http://localhost:61208/api/3/cpu/system/history
    {'system': [['2022-04-10T16:13:54.194594', 10.1],
                ['2022-04-10T16:13:55.280474', 10.9]]}

GET limits (used for thresholds)
--------------------------------

All limits/thresholds::

    # curl http://localhost:61208/api/3/all/limits
    {'alert': {'history_size': 3600.0},
     'amps': {'amps_disable': ['False'], 'history_size': 3600.0},
     'cloud': {'history_size': 3600.0},
     'connections': {'connections_disable': ['True'],
                     'connections_nf_conntrack_percent_careful': 70.0,
                     'connections_nf_conntrack_percent_critical': 90.0,
                     'connections_nf_conntrack_percent_warning': 80.0,
                     'history_size': 3600.0},
     'core': {'history_size': 3600.0},
     'cpu': {'cpu_ctx_switches_careful': 160000.0,
             'cpu_ctx_switches_critical': 200000.0,
             'cpu_ctx_switches_warning': 180000.0,
             'cpu_disable': ['False'],
             'cpu_iowait_careful': 20.0,
             'cpu_iowait_critical': 25.0,
             'cpu_iowait_warning': 22.5,
             'cpu_steal_careful': 50.0,
             'cpu_steal_critical': 90.0,
             'cpu_steal_warning': 70.0,
             'cpu_system_careful': 50.0,
             'cpu_system_critical': 90.0,
             'cpu_system_log': ['False'],
             'cpu_system_warning': 70.0,
             'cpu_total_careful': 65.0,
             'cpu_total_critical': 85.0,
             'cpu_total_log': ['True'],
             'cpu_total_warning': 75.0,
             'cpu_user_careful': 50.0,
             'cpu_user_critical': 90.0,
             'cpu_user_log': ['False'],
             'cpu_user_warning': 70.0,
             'history_size': 3600.0},
     'diskio': {'diskio_disable': ['False'],
                'diskio_hide': ['loop.*', '/dev/loop*'],
                'history_size': 3600.0},
     'docker': {'docker_all': ['False'],
                'docker_disable': ['False'],
                'docker_max_name_size': 20.0,
                'history_size': 3600.0},
     'folders': {'folders_disable': ['False'], 'history_size': 3600.0},
     'fs': {'fs_careful': 50.0,
            'fs_critical': 90.0,
            'fs_disable': ['False'],
            'fs_hide': ['/boot.*', '/snap.*'],
            'fs_warning': 70.0,
            'history_size': 3600.0},
     'gpu': {'gpu_disable': ['False'],
             'gpu_mem_careful': 50.0,
             'gpu_mem_critical': 90.0,
             'gpu_mem_warning': 70.0,
             'gpu_proc_careful': 50.0,
             'gpu_proc_critical': 90.0,
             'gpu_proc_warning': 70.0,
             'history_size': 3600.0},
     'help': {'history_size': 3600.0},
     'ip': {'history_size': 3600.0, 'ip_disable': ['False']},
     'irq': {'history_size': 3600.0, 'irq_disable': ['True']},
     'load': {'history_size': 3600.0,
              'load_careful': 0.7,
              'load_critical': 5.0,
              'load_disable': ['False'],
              'load_warning': 1.0},
     'mem': {'history_size': 3600.0,
             'mem_careful': 50.0,
             'mem_critical': 90.0,
             'mem_disable': ['False'],
             'mem_warning': 70.0},
     'memswap': {'history_size': 3600.0,
                 'memswap_careful': 50.0,
                 'memswap_critical': 90.0,
                 'memswap_disable': ['False'],
                 'memswap_warning': 70.0},
     'network': {'history_size': 3600.0,
                 'network_disable': ['False'],
                 'network_rx_careful': 70.0,
                 'network_rx_critical': 90.0,
                 'network_rx_warning': 80.0,
                 'network_tx_careful': 70.0,
                 'network_tx_critical': 90.0,
                 'network_tx_warning': 80.0},
     'now': {'history_size': 3600.0},
     'percpu': {'history_size': 3600.0,
                'percpu_disable': ['False'],
                'percpu_iowait_careful': 50.0,
                'percpu_iowait_critical': 90.0,
                'percpu_iowait_warning': 70.0,
                'percpu_system_careful': 50.0,
                'percpu_system_critical': 90.0,
                'percpu_system_warning': 70.0,
                'percpu_user_careful': 50.0,
                'percpu_user_critical': 90.0,
                'percpu_user_warning': 70.0},
     'ports': {'history_size': 3600.0,
               'ports_disable': ['False'],
               'ports_port_default_gateway': ['True'],
               'ports_refresh': 30.0,
               'ports_timeout': 3.0},
     'processcount': {'history_size': 3600.0, 'processcount_disable': ['False']},
     'processlist': {'history_size': 3600.0,
                     'processlist_cpu_careful': 50.0,
                     'processlist_cpu_critical': 90.0,
                     'processlist_cpu_warning': 70.0,
                     'processlist_disable': ['False'],
                     'processlist_mem_careful': 50.0,
                     'processlist_mem_critical': 90.0,
                     'processlist_mem_warning': 70.0,
                     'processlist_nice_warning': ['-20',
                                                  '-19',
                                                  '-18',
                                                  '-17',
                                                  '-16',
                                                  '-15',
                                                  '-14',
                                                  '-13',
                                                  '-12',
                                                  '-11',
                                                  '-10',
                                                  '-9',
                                                  '-8',
                                                  '-7',
                                                  '-6',
                                                  '-5',
                                                  '-4',
                                                  '-3',
                                                  '-2',
                                                  '-1',
                                                  '1',
                                                  '2',
                                                  '3',
                                                  '4',
                                                  '5',
                                                  '6',
                                                  '7',
                                                  '8',
                                                  '9',
                                                  '10',
                                                  '11',
                                                  '12',
                                                  '13',
                                                  '14',
                                                  '15',
                                                  '16',
                                                  '17',
                                                  '18',
                                                  '19']},
     'psutilversion': {'history_size': 3600.0},
     'quicklook': {'history_size': 3600.0,
                   'quicklook_cpu_careful': 50.0,
                   'quicklook_cpu_critical': 90.0,
                   'quicklook_cpu_warning': 70.0,
                   'quicklook_disable': ['False'],
                   'quicklook_mem_careful': 50.0,
                   'quicklook_mem_critical': 90.0,
                   'quicklook_mem_warning': 70.0,
                   'quicklook_percentage_char': ['|'],
                   'quicklook_swap_careful': 50.0,
                   'quicklook_swap_critical': 90.0,
                   'quicklook_swap_warning': 70.0},
     'raid': {'history_size': 3600.0, 'raid_disable': ['True']},
     'sensors': {'history_size': 3600.0,
                 'sensors_battery_careful': 80.0,
                 'sensors_battery_critical': 95.0,
                 'sensors_battery_warning': 90.0,
                 'sensors_disable': ['False'],
                 'sensors_refresh': 4.0,
                 'sensors_temperature_core_careful': 60.0,
                 'sensors_temperature_core_critical': 80.0,
                 'sensors_temperature_core_warning': 70.0,
                 'sensors_temperature_hdd_careful': 45.0,
                 'sensors_temperature_hdd_critical': 60.0,
                 'sensors_temperature_hdd_warning': 52.0},
     'smart': {'history_size': 3600.0, 'smart_disable': ['True']},
     'system': {'history_size': 3600.0,
                'system_disable': ['False'],
                'system_refresh': 60},
     'uptime': {'history_size': 3600.0},
     'wifi': {'history_size': 3600.0,
              'wifi_careful': -65.0,
              'wifi_critical': -85.0,
              'wifi_disable': ['True'],
              'wifi_hide': ['lo', 'docker.*'],
              'wifi_warning': -75.0}}

Limits/thresholds for the cpu plugin::

    # curl http://localhost:61208/api/3/cpu/limits
    {'cpu_ctx_switches_careful': 160000.0,
     'cpu_ctx_switches_critical': 200000.0,
     'cpu_ctx_switches_warning': 180000.0,
     'cpu_disable': ['False'],
     'cpu_iowait_careful': 20.0,
     'cpu_iowait_critical': 25.0,
     'cpu_iowait_warning': 22.5,
     'cpu_steal_careful': 50.0,
     'cpu_steal_critical': 90.0,
     'cpu_steal_warning': 70.0,
     'cpu_system_careful': 50.0,
     'cpu_system_critical': 90.0,
     'cpu_system_log': ['False'],
     'cpu_system_warning': 70.0,
     'cpu_total_careful': 65.0,
     'cpu_total_critical': 85.0,
     'cpu_total_log': ['True'],
     'cpu_total_warning': 75.0,
     'cpu_user_careful': 50.0,
     'cpu_user_critical': 90.0,
     'cpu_user_log': ['False'],
     'cpu_user_warning': 70.0,
     'history_size': 3600.0}


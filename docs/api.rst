.. _api:

API (Restfull/JSON) documentation
=================================

The Glances Restfull/API server could be ran using the following command line:

.. code-block:: bash

    # glances -w --disable-webui

Note: Change request URL api/3 by api/2 if you use Glances 2.x.

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
    [[1629527675.0,
      -1,
      'WARNING',
      'MEM',
      87.45747587103037,
      87.45747587103037,
      87.45747587103037,
      87.45747587103037,
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
      'timer': 0.2592196464538574},
     {'count': 0,
      'countmax': 20.0,
      'countmin': None,
      'key': 'name',
      'name': 'Python',
      'refresh': 3.0,
      'regex': True,
      'result': None,
      'timer': 0.25902843475341797}]

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
                  'timer': 0.2592196464538574}]}

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
     'idle': 70.5,
     'interrupts': 0,
     'iowait': 1.0,
     'irq': 0.0,
     'nice': 0.0,
     'soft_interrupts': 0,
     'softirq': 5.7,
     'steal': 0.0,
     'syscalls': 0,
     'system': 2.7,
     'time_since_update': 1,
     'total': 28.3,
     'user': 20.1}

Fields descriptions:

* **total**: Sum of all CPU percentages (except idle) (unit is *percent*)
* **system**: percent time spent in kernel space. System CPU time is the time spent running code in the Operating System kernel (unit is *percent*)
* **user**: CPU percent time spent in user space. User CPU time is the time spent on the processor running your program's code (or code in libraries) (unit is *percent*)
* **iowait**: *(Linux)*: percent time spent by the CPU waiting for I/O operations to complete (unit is *percent*)
* **idle**: percent of CPU used by any program. Every program or task that runs on a computer system occupies a certain amount of processing time on the CPU. If the CPU has completed all tasks it is idle (unit is *percent*)
* **irq**: *(Linux and BSD)*: percent time spent servicing/handling hardware/software interrupts. Time servicing interrupts (hardware + software) (unit is *percent*)
* **nice**: *(Unix)*: percent time occupied by user level processes with a positive nice value. The time the CPU has spent running users' processes that have been *niced* (unit is *percent*)
* **steal**: *(Linux)*: percentage of time a virtual CPU waits for a real CPU while the hypervisor is servicing another virtual processor (unit is *percent*)
* **ctx_switches**: number of context switches (voluntary + involuntary) per second. A context switch is a procedure that a computer's CPU (central processing unit) follows to change from one task (or process) to another while ensuring that the tasks do not conflict (unit is *percent*)
* **interrupts**: number of interrupts per second (unit is *percent*)
* **soft_interrupts**: number of software interrupts per second. Always set to 0 on Windows and SunOS (unit is *percent*)
* **cpucore**: Total number of CPU core (unit is *number*)
* **time_since_update**: Number of seconds since last update (unit is *seconds*)

Get a specific field::

    # curl http://localhost:61208/api/3/cpu/total
    {'total': 28.3}

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

GET docker
----------

Get plugin stats::

    # curl http://localhost:61208/api/3/docker
    [{'Command': ['/run.sh'],
      'Id': '65edb2094923e8732c04ba287c7cc2ef0c6178b4d93cd2bc328d9cd60f292b29',
      'Image': ['grafana/grafana:latest'],
      'Names': ['grafana'],
      'Status': 'running',
      'cpu_percent': 0.0,
      'io_r': None,
      'io_w': None,
      'key': 'name',
      'memory_usage': None,
      'name': 'grafana',
      'network_rx': None,
      'network_tx': None},
     {'Command': ['/entrypoint.sh', 'telegraf'],
      'Id': '84db65dbbbfead7851695dbff97f7751b5b3b93f7a50c24d66d4caab45b5f159',
      'Image': [],
      'Names': ['telegraf'],
      'Status': 'running',
      'cpu_percent': 0.0,
      'io_r': None,
      'io_w': None,
      'key': 'name',
      'memory_usage': None,
      'name': 'telegraf',
      'network_rx': None,
      'network_tx': None}]

GET fs
------

Get plugin stats::

    # curl http://localhost:61208/api/3/fs
    [{'device_name': '/dev/mapper/ubuntu--gnome--vg-root',
      'free': 34209202176,
      'fs_type': 'ext4',
      'key': 'mnt_point',
      'mnt_point': '/',
      'percent': 85.2,
      'size': 243396149248,
      'used': 196799492096}]

Get a specific field::

    # curl http://localhost:61208/api/3/fs/mnt_point
    {'mnt_point': ['/']}

Get a specific item when field matchs the given value::

    # curl http://localhost:61208/api/3/fs/mnt_point//
    {'/': [{'device_name': '/dev/mapper/ubuntu--gnome--vg-root',
            'free': 34209202176,
            'fs_type': 'ext4',
            'key': 'mnt_point',
            'mnt_point': '/',
            'percent': 85.2,
            'size': 243396149248,
            'used': 196799492096}]}

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
    {'cpucore': 4, 'min1': 0.87, 'min15': 1.18, 'min5': 0.91}

Fields descriptions:

* **min1**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 1 minute (unit is *number*)
* **min5**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 5 minutes (unit is *number*)
* **min15**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 15 minutes (unit is *number*)
* **cpucore**: Total number of CPU core (unit is *number*)

Get a specific field::

    # curl http://localhost:61208/api/3/load/min1
    {'min1': 0.87}

GET mem
-------

Get plugin stats::

    # curl http://localhost:61208/api/3/mem
    {'active': 5509173248,
     'available': 984465408,
     'buffers': 69275648,
     'cached': 1757458432,
     'free': 984465408,
     'inactive': 1291149312,
     'percent': 87.5,
     'shared': 954650624,
     'total': 7849021440,
     'used': 6864556032}

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
    {'total': 7849021440}

GET memswap
-----------

Get plugin stats::

    # curl http://localhost:61208/api/3/memswap
    {'free': 7486050304,
     'percent': 7.4,
     'sin': 90058752,
     'sout': 668807168,
     'time_since_update': 1,
     'total': 8082419712,
     'used': 596369408}

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
      'cumulative_cx': 116226779,
      'cumulative_rx': 26881826,
      'cumulative_tx': 89344953,
      'cx': 0,
      'interface_name': 'veth20bf375',
      'is_up': True,
      'key': 'interface_name',
      'rx': 0,
      'speed': 10485760000,
      'time_since_update': 1,
      'tx': 0},
     {'alias': None,
      'cumulative_cx': 0,
      'cumulative_rx': 0,
      'cumulative_tx': 0,
      'cx': 0,
      'interface_name': 'mpqemubr0',
      'is_up': False,
      'key': 'interface_name',
      'rx': 0,
      'speed': 0,
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
    {'interface_name': ['veth20bf375',
                        'mpqemubr0',
                        'veth35385e9',
                        'br-119e6ee04e05',
                        'lo',
                        'docker0',
                        'br-87386b77b676',
                        'tap-838a195875f',
                        'veth4279222',
                        'wlp2s0',
                        'veth041bfdd']}

Get a specific item when field matchs the given value::

    # curl http://localhost:61208/api/3/network/interface_name/veth20bf375
    {'veth20bf375': [{'alias': None,
                      'cumulative_cx': 116226779,
                      'cumulative_rx': 26881826,
                      'cumulative_tx': 89344953,
                      'cx': 0,
                      'interface_name': 'veth20bf375',
                      'is_up': True,
                      'key': 'interface_name',
                      'rx': 0,
                      'speed': 10485760000,
                      'time_since_update': 1,
                      'tx': 0}]}

GET now
-------

Get plugin stats::

    # curl http://localhost:61208/api/3/now
    '2021-08-21 08:34:35 CEST'

GET percpu
----------

Get plugin stats::

    # curl http://localhost:61208/api/3/percpu
    [{'cpu_number': 0,
      'guest': 0.0,
      'guest_nice': 0.0,
      'idle': 28.3,
      'iowait': 0.0,
      'irq': 0.0,
      'key': 'cpu_number',
      'nice': 0.0,
      'softirq': 0.9,
      'steal': 0.0,
      'system': 2.8,
      'total': 71.7,
      'user': 67.9},
     {'cpu_number': 1,
      'guest': 0.0,
      'guest_nice': 0.0,
      'idle': 93.7,
      'iowait': 0.0,
      'irq': 0.0,
      'key': 'cpu_number',
      'nice': 0.0,
      'softirq': 2.7,
      'steal': 0.0,
      'system': 1.8,
      'total': 6.3,
      'user': 1.8}]

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
      'status': 0.007762,
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
                        'status': 0.007762,
                        'timeout': 3}]}

GET processcount
----------------

Get plugin stats::

    # curl http://localhost:61208/api/3/processcount
    {'pid_max': 0, 'running': 1, 'sleeping': 281, 'thread': 1532, 'total': 339}

Get a specific field::

    # curl http://localhost:61208/api/3/processcount/total
    {'total': 339}

GET processlist
---------------

Get plugin stats::

    # curl http://localhost:61208/api/3/processlist
    [{'cmdline': ['/usr/lib/firefox/firefox', '-new-window'],
      'cpu_percent': 0.0,
      'cpu_times': pcputimes(user=5585.01, system=1722.47, children_user=3282.2, children_system=675.02, iowait=1.8),
      'gids': pgids(real=1000, effective=1000, saved=1000),
      'io_counters': [1098960896, 5357330432, 0, 0, 0],
      'key': 'pid',
      'memory_info': pmem(rss=1037713408, vms=5342564352, shared=156327936, text=622592, lib=0, data=1466003456, dirty=0),
      'memory_percent': 13.220927168215251,
      'name': 'firefox',
      'nice': 0,
      'num_threads': 132,
      'pid': 4142,
      'ppid': 3391,
      'status': 'S',
      'time_since_update': 1,
      'username': 'nicolargo'},
     {'cmdline': ['/usr/lib/firefox/firefox',
                  '-contentproc',
                  '-childID',
                  '5',
                  '-isForBrowser',
                  '-prefsLen',
                  '4953',
                  '-prefMapSize',
                  '250397',
                  '-parentBuildID',
                  '20210527174632',
                  '-appdir',
                  '/usr/lib/firefox/browser',
                  '4142',
                  'true',
                  'tab'],
      'cpu_percent': 0.0,
      'cpu_times': pcputimes(user=590.19, system=97.22, children_user=0.0, children_system=0.0, iowait=0.04),
      'gids': pgids(real=1000, effective=1000, saved=1000),
      'io_counters': [8634368, 0, 0, 0, 0],
      'key': 'pid',
      'memory_info': pmem(rss=731287552, vms=3396091904, shared=39550976, text=622592, lib=0, data=911761408, dirty=0),
      'memory_percent': 9.316926416753423,
      'name': 'WebExtensions',
      'nice': 0,
      'num_threads': 25,
      'pid': 4378,
      'ppid': 4142,
      'status': 'S',
      'time_since_update': 1,
      'username': 'nicolargo'}]

Get a specific field::

    # curl http://localhost:61208/api/3/processlist/pid
    {'pid': [4142,
             4378,
             4258,
             9692,
             4690,
             9388,
             3638,
             18293,
             31464,
             99335,
             11502,
             64775,
             9359,
             9426,
             38222,
             92962,
             92898,
             9330,
             9453,
             9441,
             27823,
             4280,
             7272,
             18645,
             102620,
             30528,
             9474,
             108015,
             2217,
             9542,
             68876,
             9378,
             3460,
             9711,
             2297,
             3485,
             3402,
             3735,
             1162,
             9231,
             105514,
             9233,
             5343,
             9333,
             9334,
             11685,
             351,
             4726,
             101319,
             3400,
             81429,
             1319,
             3704,
             1140,
             3905,
             3697,
             3768,
             3764,
             1,
             2251,
             2439,
             3789,
             3795,
             3159,
             1175,
             1308,
             3799,
             1150,
             3845,
             1154,
             101343,
             3668,
             7777,
             3793,
             3791,
             3623,
             101342,
             3829,
             3721,
             3391,
             2236,
             1022,
             3439,
             2449,
             3802,
             3673,
             1306,
             3211,
             1551,
             3819,
             3948,
             1174,
             3676,
             30686,
             3371,
             3414,
             30672,
             1176,
             53315,
             1138,
             36769,
             3510,
             3824,
             1118,
             1359,
             1145,
             3792,
             3679,
             3456,
             106400,
             107588,
             3447,
             3470,
             81481,
             36746,
             1172,
             3426,
             3718,
             3826,
             3862,
             3405,
             3672,
             3476,
             2446,
             3790,
             3949,
             3432,
             2468,
             1169,
             3601,
             3689,
             3853,
             1159,
             3788,
             53321,
             3812,
             38268,
             3843,
             3483,
             53324,
             11661,
             1157,
             3807,
             3821,
             3452,
             1132,
             383,
             1131,
             1146,
             1023,
             1021,
             2447,
             3214,
             11480,
             68853,
             3606,
             1177,
             1430,
             3092,
             3693,
             107999,
             1135,
             9294,
             3616,
             9536,
             1209,
             53327,
             1350,
             68839,
             11452,
             105810,
             3063,
             1119,
             11427,
             11465,
             108014,
             2097,
             3077,
             2275,
             11440,
             2271,
             4551,
             3395,
             1215,
             2269,
             997,
             373,
             1134,
             3580,
             2,
             3,
             4,
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
             20,
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
             91,
             92,
             93,
             94,
             95,
             96,
             97,
             98,
             99,
             103,
             104,
             106,
             107,
             108,
             113,
             122,
             138,
             181,
             191,
             192,
             193,
             194,
             195,
             196,
             197,
             198,
             204,
             205,
             206,
             209,
             210,
             240,
             282,
             283,
             291,
             292,
             294,
             363,
             368,
             392,
             401,
             404,
             405,
             406,
             407,
             430,
             434,
             441,
             493,
             499,
             535,
             779,
             780,
             781,
             782,
             783,
             784,
             785,
             786,
             787,
             788,
             789,
             790,
             908,
             909,
             910,
             911,
             912,
             913,
             915,
             916,
             930,
             936,
             941,
             945,
             947,
             951,
             954,
             957,
             1360,
             1495,
             1496,
             1497,
             1498,
             1499,
             1500,
             1502,
             1504,
             2329,
             2357,
             3115,
             3463,
             51408,
             51705,
             53671,
             54440,
             81351,
             84910,
             98874,
             98921,
             101187,
             101201,
             103005,
             103071,
             103136,
             103416,
             103834,
             104097,
             105012,
             105142,
             105193,
             105304,
             105912,
             107210,
             107765,
             107770]}

Get a specific item when field matchs the given value::

    # curl http://localhost:61208/api/3/processlist/pid/4142
    {'4142': [{'cmdline': ['/usr/lib/firefox/firefox', '-new-window'],
               'cpu_percent': 0.0,
               'cpu_times': [5585.01, 1722.47, 3282.2, 675.02, 1.8],
               'gids': [1000, 1000, 1000],
               'io_counters': [1098960896, 5357330432, 0, 0, 0],
               'key': 'pid',
               'memory_info': [1037713408,
                               5342564352,
                               156327936,
                               622592,
                               0,
                               1466003456,
                               0],
               'memory_percent': 13.220927168215251,
               'name': 'firefox',
               'nice': 0,
               'num_threads': 132,
               'pid': 4142,
               'ppid': 3391,
               'status': 'S',
               'time_since_update': 1,
               'username': 'nicolargo'}]}

GET psutilversion
-----------------

Get plugin stats::

    # curl http://localhost:61208/api/3/psutilversion
    (5, 8, 0)

GET quicklook
-------------

Get plugin stats::

    # curl http://localhost:61208/api/3/quicklook
    {'cpu': 28.3,
     'cpu_hz': 3000000000.0,
     'cpu_hz_current': 2128037500.0,
     'cpu_name': 'Intel(R) Core(TM) i7-4500U CPU @ 1.80GHz',
     'mem': 87.5,
     'percpu': [{'cpu_number': 0,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 28.3,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.9,
                 'steal': 0.0,
                 'system': 2.8,
                 'total': 71.7,
                 'user': 67.9},
                {'cpu_number': 1,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 93.7,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 2.7,
                 'steal': 0.0,
                 'system': 1.8,
                 'total': 6.3,
                 'user': 1.8},
                {'cpu_number': 2,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 71.3,
                 'iowait': 2.3,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 17.1,
                 'steal': 0.0,
                 'system': 1.6,
                 'total': 28.7,
                 'user': 7.8},
                {'cpu_number': 3,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 88.8,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.9,
                 'steal': 0.0,
                 'system': 2.8,
                 'total': 11.2,
                 'user': 7.5}],
     'swap': 7.4}

Get a specific field::

    # curl http://localhost:61208/api/3/quicklook/cpu
    {'cpu': 28.3}

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
               'Battery']}

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
     'os_version': '5.4.0-74-generic',
     'platform': '64bit'}

Get a specific field::

    # curl http://localhost:61208/api/3/system/os_name
    {'os_name': 'Linux'}

GET uptime
----------

Get plugin stats::

    # curl http://localhost:61208/api/3/uptime
    {'seconds': 1178914}

GET all stats
-------------

Get all Glances stats::

    # curl http://localhost:61208/api/3/all
    Return a very big dictionnary (avoid using this request, performances will be poor)...

GET stats history
-----------------

History of a plugin::

    # curl http://localhost:61208/api/3/cpu/history
    {'system': [['2021-08-21T08:34:35.429123', 2.7],
                ['2021-08-21T08:34:36.506330', 2.7],
                ['2021-08-21T08:34:37.594678', 1.5]],
     'user': [['2021-08-21T08:34:35.429113', 20.1],
              ['2021-08-21T08:34:36.506327', 20.1],
              ['2021-08-21T08:34:37.594673', 4.4]]}

Limit history to last 2 values::

    # curl http://localhost:61208/api/3/cpu/history/2
    {'system': [['2021-08-21T08:34:36.506330', 2.7],
                ['2021-08-21T08:34:37.594678', 1.5]],
     'user': [['2021-08-21T08:34:36.506327', 20.1],
              ['2021-08-21T08:34:37.594673', 4.4]]}

History for a specific field::

    # curl http://localhost:61208/api/3/cpu/system/history
    {'system': [['2021-08-21T08:34:35.429123', 2.7],
                ['2021-08-21T08:34:36.506330', 2.7],
                ['2021-08-21T08:34:37.594678', 1.5]]}

Limit history for a specific field to last 2 values::

    # curl http://localhost:61208/api/3/cpu/system/history
    {'system': [['2021-08-21T08:34:36.506330', 2.7],
                ['2021-08-21T08:34:37.594678', 1.5]]}

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


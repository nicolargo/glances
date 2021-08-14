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
      'timer': 0.19156432151794434},
     {'count': 0,
      'countmax': 20.0,
      'countmin': None,
      'key': 'name',
      'name': 'Python',
      'refresh': 3.0,
      'regex': True,
      'result': None,
      'timer': 0.19138813018798828}]

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
                  'timer': 0.19156432151794434}]}

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
     'idle': 65.9,
     'interrupts': 0,
     'iowait': 0.6,
     'irq': 0.0,
     'nice': 0.0,
     'soft_interrupts': 0,
     'softirq': 3.3,
     'steal': 0.0,
     'syscalls': 0,
     'system': 3.5,
     'time_since_update': 1,
     'total': 34.2,
     'user': 26.8}

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
    {'total': 34.2}

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
      'Id': '5f8abfeafe0a176954ca2a2062afcd07eb74988ddfbf6323fccd8e5f882b4e4b',
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
      'Image': ['telegraf:latest'],
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
      'free': 36151685120,
      'fs_type': 'ext4',
      'key': 'mnt_point',
      'mnt_point': '/',
      'percent': 84.4,
      'size': 243396149248,
      'used': 194857009152}]

Get a specific field::

    # curl http://localhost:61208/api/3/fs/mnt_point
    {'mnt_point': ['/']}

Get a specific item when field matchs the given value::

    # curl http://localhost:61208/api/3/fs/mnt_point//
    {'/': [{'device_name': '/dev/mapper/ubuntu--gnome--vg-root',
            'free': 36151685120,
            'fs_type': 'ext4',
            'key': 'mnt_point',
            'mnt_point': '/',
            'percent': 84.4,
            'size': 243396149248,
            'used': 194857009152}]}

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
    {'cpucore': 4, 'min1': 1.56, 'min15': 0.79, 'min5': 1.33}

Fields descriptions:

* **min1**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 1 minute (unit is *number*)
* **min5**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 5 minutes (unit is *number*)
* **min15**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 15 minutes (unit is *number*)
* **cpucore**: Total number of CPU core (unit is *number*)

Get a specific field::

    # curl http://localhost:61208/api/3/load/min1
    {'min1': 1.56}

GET mem
-------

Get plugin stats::

    # curl http://localhost:61208/api/3/mem
    {'active': 4615663616,
     'available': 2695766016,
     'buffers': 443973632,
     'cached': 2841604096,
     'free': 2695766016,
     'inactive': 2135314432,
     'percent': 65.7,
     'shared': 709017600,
     'total': 7849021440,
     'used': 5153255424}

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
    {'free': 7994896384,
     'percent': 1.1,
     'sin': 3284992,
     'sout': 88502272,
     'time_since_update': 1,
     'total': 8082419712,
     'used': 87523328}

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
      'cumulative_cx': 10370393,
      'cumulative_rx': 1511916,
      'cumulative_tx': 8858477,
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
      'interface_name': 'mpqemubr0-dummy',
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
                        'mpqemubr0-dummy',
                        'mpqemubr0',
                        'veth35385e9',
                        'br-119e6ee04e05',
                        'lo',
                        'docker0',
                        'br-87386b77b676',
                        'tap-838a195875f',
                        'wlp2s0',
                        'veth8f84d90',
                        'veth041bfdd']}

Get a specific item when field matchs the given value::

    # curl http://localhost:61208/api/3/network/interface_name/veth20bf375
    {'veth20bf375': [{'alias': None,
                      'cumulative_cx': 10370393,
                      'cumulative_rx': 1511916,
                      'cumulative_tx': 8858477,
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
    '2021-08-14 16:57:33 CEST'

GET percpu
----------

Get plugin stats::

    # curl http://localhost:61208/api/3/percpu
    [{'cpu_number': 0,
      'guest': 0.0,
      'guest_nice': 0.0,
      'idle': 37.3,
      'iowait': 0.7,
      'irq': 0.0,
      'key': 'cpu_number',
      'nice': 0.0,
      'softirq': 0.0,
      'steal': 0.0,
      'system': 2.6,
      'total': 62.7,
      'user': 59.5},
     {'cpu_number': 1,
      'guest': 0.0,
      'guest_nice': 0.0,
      'idle': 54.6,
      'iowait': 2.0,
      'irq': 0.0,
      'key': 'cpu_number',
      'nice': 0.0,
      'softirq': 0.0,
      'steal': 0.0,
      'system': 2.6,
      'total': 45.4,
      'user': 40.8}]

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
      'status': 0.011298,
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
                        'status': 0.011298,
                        'timeout': 3}]}

GET processcount
----------------

Get plugin stats::

    # curl http://localhost:61208/api/3/processcount
    {'pid_max': 0, 'running': 1, 'sleeping': 274, 'thread': 1407, 'total': 337}

Get a specific field::

    # curl http://localhost:61208/api/3/processcount/total
    {'total': 337}

GET processlist
---------------

Get plugin stats::

    # curl http://localhost:61208/api/3/processlist
    [{'cmdline': ['/usr/lib/firefox/firefox', '-new-window'],
      'cpu_percent': 0.0,
      'cpu_times': pcputimes(user=1895.06, system=548.01, children_user=1331.84, children_system=203.91, iowait=1.48),
      'gids': pgids(real=1000, effective=1000, saved=1000),
      'io_counters': [555024384, 1994608640, 0, 0, 0],
      'key': 'pid',
      'memory_info': pmem(rss=559951872, vms=4650143744, shared=200867840, text=622592, lib=0, data=973697024, dirty=0),
      'memory_percent': 7.134034175857723,
      'name': 'firefox',
      'nice': 0,
      'num_threads': 120,
      'pid': 4142,
      'ppid': 3391,
      'status': 'S',
      'time_since_update': 1,
      'username': 'nicolargo'},
     {'cmdline': ['/usr/lib/firefox/firefox',
                  '-contentproc',
                  '-childID',
                  '2',
                  '-isForBrowser',
                  '-prefsLen',
                  '96',
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
      'cpu_times': pcputimes(user=317.95, system=66.8, children_user=0.0, children_system=0.0, iowait=0.09),
      'gids': pgids(real=1000, effective=1000, saved=1000),
      'io_counters': [16916480, 0, 0, 0, 0],
      'key': 'pid',
      'memory_info': pmem(rss=454049792, vms=3319758848, shared=145993728, text=622592, lib=0, data=582402048, dirty=0),
      'memory_percent': 5.784794900496538,
      'name': 'Web Content',
      'nice': 0,
      'num_threads': 30,
      'pid': 4258,
      'ppid': 4142,
      'status': 'S',
      'time_since_update': 1,
      'username': 'nicolargo'}]

Get a specific field::

    # curl http://localhost:61208/api/3/processlist/pid
    {'pid': [4142,
             4258,
             4378,
             9692,
             4690,
             3638,
             18293,
             9388,
             11502,
             31464,
             9426,
             38222,
             27823,
             9330,
             9441,
             4280,
             9453,
             9359,
             18645,
             7272,
             30528,
             53256,
             2217,
             9474,
             9542,
             9378,
             2297,
             3485,
             2468,
             3460,
             9334,
             9333,
             11646,
             5343,
             3159,
             1162,
             3211,
             3905,
             54247,
             11685,
             3735,
             9233,
             9711,
             9231,
             1319,
             3402,
             1316,
             4726,
             3704,
             3673,
             3799,
             3795,
             3789,
             3845,
             3764,
             3768,
             351,
             2439,
             3793,
             3697,
             1140,
             3676,
             3829,
             1150,
             3400,
             2251,
             1308,
             3791,
             3623,
             2236,
             1022,
             1,
             1175,
             3948,
             51755,
             23730,
             3510,
             2449,
             1154,
             1350,
             3214,
             3802,
             3819,
             3668,
             3391,
             23729,
             3371,
             1551,
             1306,
             1174,
             3824,
             3439,
             3721,
             30672,
             1176,
             1359,
             30686,
             53315,
             36769,
             3447,
             7777,
             1172,
             3862,
             3792,
             11661,
             3790,
             3092,
             3414,
             3843,
             3949,
             1118,
             3470,
             2446,
             3689,
             3679,
             383,
             3426,
             3672,
             3826,
             3821,
             11621,
             11480,
             3476,
             1145,
             1138,
             3788,
             38268,
             3456,
             3718,
             1169,
             3601,
             1023,
             53321,
             3812,
             3483,
             3807,
             3853,
             3432,
             53324,
             2447,
             1159,
             36746,
             7281,
             3405,
             3452,
             1157,
             1132,
             3693,
             1146,
             1131,
             1021,
             3616,
             1177,
             3606,
             3395,
             9536,
             9294,
             1430,
             2059,
             1135,
             54233,
             11452,
             11440,
             1209,
             53327,
             3063,
             11427,
             11465,
             11595,
             3077,
             4551,
             1119,
             54246,
             36394,
             2097,
             2271,
             3580,
             2275,
             2269,
             1215,
             3115,
             997,
             373,
             1134,
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
             442,
             493,
             499,
             535,
             651,
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
             900,
             906,
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
             939,
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
             3463,
             45464,
             49536,
             51408,
             51413,
             51424,
             51624,
             51645,
             51651,
             51699,
             51700,
             51705,
             52508,
             52509,
             52671,
             52784,
             53358,
             53530,
             53531,
             53532,
             53671,
             53718,
             53730]}

Get a specific item when field matchs the given value::

    # curl http://localhost:61208/api/3/processlist/pid/4142
    {'4142': [{'cmdline': ['/usr/lib/firefox/firefox', '-new-window'],
               'cpu_percent': 0.0,
               'cpu_times': [1895.06, 548.01, 1331.84, 203.91, 1.48],
               'gids': [1000, 1000, 1000],
               'io_counters': [555024384, 1994608640, 0, 0, 0],
               'key': 'pid',
               'memory_info': [559951872,
                               4650143744,
                               200867840,
                               622592,
                               0,
                               973697024,
                               0],
               'memory_percent': 7.134034175857723,
               'name': 'firefox',
               'nice': 0,
               'num_threads': 120,
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
    {'cpu': 34.2,
     'cpu_hz': 2025000000.0,
     'cpu_hz_current': 1676300749.9999998,
     'cpu_name': 'Intel(R) Core(TM) i7-4500U CPU @ 1.80GHz',
     'mem': 65.7,
     'percpu': [{'cpu_number': 0,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 37.3,
                 'iowait': 0.7,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 2.6,
                 'total': 62.7,
                 'user': 59.5},
                {'cpu_number': 1,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 54.6,
                 'iowait': 2.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 2.6,
                 'total': 45.4,
                 'user': 40.8},
                {'cpu_number': 2,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 81.9,
                 'iowait': 0.6,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 9.0,
                 'steal': 0.0,
                 'system': 0.6,
                 'total': 18.1,
                 'user': 7.8},
                {'cpu_number': 3,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 84.5,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 5.0,
                 'steal': 0.0,
                 'system': 5.0,
                 'total': 15.5,
                 'user': 5.6}],
     'swap': 1.1}

Get a specific field::

    # curl http://localhost:61208/api/3/quicklook/cpu
    {'cpu': 34.2}

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
    {'seconds': 604292}

GET all stats
-------------

Get all Glances stats::

    # curl http://localhost:61208/api/3/all
    Return a very big dictionnary (avoid using this request, performances will be poor)...

GET stats history
-----------------

History of a plugin::

    # curl http://localhost:61208/api/3/cpu/history
    {'system': [['2021-08-14T16:57:33.339311', 3.5],
                ['2021-08-14T16:57:34.452028', 3.5],
                ['2021-08-14T16:57:35.592317', 3.5]],
     'user': [['2021-08-14T16:57:33.339295', 26.8],
              ['2021-08-14T16:57:34.452022', 26.8],
              ['2021-08-14T16:57:35.592311', 6.9]]}

Limit history to last 2 values::

    # curl http://localhost:61208/api/3/cpu/history/2
    {'system': [['2021-08-14T16:57:34.452028', 3.5],
                ['2021-08-14T16:57:35.592317', 3.5]],
     'user': [['2021-08-14T16:57:34.452022', 26.8],
              ['2021-08-14T16:57:35.592311', 6.9]]}

History for a specific field::

    # curl http://localhost:61208/api/3/cpu/system/history
    {'system': [['2021-08-14T16:57:33.339311', 3.5],
                ['2021-08-14T16:57:34.452028', 3.5],
                ['2021-08-14T16:57:35.592317', 3.5]]}

Limit history for a specific field to last 2 values::

    # curl http://localhost:61208/api/3/cpu/system/history
    {'system': [['2021-08-14T16:57:34.452028', 3.5],
                ['2021-08-14T16:57:35.592317', 3.5]]}

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


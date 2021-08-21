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
    [[1629538146.0,
      -1,
      'WARNING',
      'MEM',
      81.55474321140343,
      81.55474321140343,
      81.55474321140343,
      81.55474321140343,
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
      'timer': 0.5234799385070801},
     {'count': 0,
      'countmax': 20.0,
      'countmin': None,
      'key': 'name',
      'name': 'Python',
      'refresh': 3.0,
      'regex': True,
      'result': None,
      'timer': 0.5233094692230225}]

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
                  'timer': 0.5234799385070801}]}

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
     'idle': 75.1,
     'interrupts': 0,
     'iowait': 0.3,
     'irq': 0.0,
     'nice': 0.0,
     'soft_interrupts': 0,
     'softirq': 4.9,
     'steal': 0.0,
     'syscalls': 0,
     'system': 3.0,
     'time_since_update': 1,
     'total': 26.7,
     'user': 16.8}

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
    {'total': 26.7}

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
      'free': 34175746048,
      'fs_type': 'ext4',
      'key': 'mnt_point',
      'mnt_point': '/',
      'percent': 85.2,
      'size': 243396149248,
      'used': 196832948224}]

Get a specific field::

    # curl http://localhost:61208/api/3/fs/mnt_point
    {'mnt_point': ['/']}

Get a specific item when field matchs the given value::

    # curl http://localhost:61208/api/3/fs/mnt_point//
    {'/': [{'device_name': '/dev/mapper/ubuntu--gnome--vg-root',
            'free': 34175746048,
            'fs_type': 'ext4',
            'key': 'mnt_point',
            'mnt_point': '/',
            'percent': 85.2,
            'size': 243396149248,
            'used': 196832948224}]}

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
    {'cpucore': 4, 'min1': 1.79, 'min15': 1.16, 'min5': 1.35}

Fields descriptions:

* **min1**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 1 minute (unit is *number*)
* **min5**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 5 minutes (unit is *number*)
* **min15**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 15 minutes (unit is *number*)
* **cpucore**: Total number of CPU core (unit is *number*)

Get a specific field::

    # curl http://localhost:61208/api/3/load/min1
    {'min1': 1.79}

GET mem
-------

Get plugin stats::

    # curl http://localhost:61208/api/3/mem
    {'active': 5300064256,
     'available': 1447772160,
     'buffers': 177422336,
     'cached': 2273996800,
     'free': 1447772160,
     'inactive': 1538215936,
     'percent': 81.6,
     'shared': 1025073152,
     'total': 7849021440,
     'used': 6401249280}

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
    {'free': 7481946112,
     'percent': 7.4,
     'sin': 120209408,
     'sout': 699346944,
     'time_since_update': 1,
     'total': 8082419712,
     'used': 600473600}

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
      'cumulative_cx': 118689595,
      'cumulative_rx': 27228964,
      'cumulative_tx': 91460631,
      'cx': 63,
      'interface_name': 'veth20bf375',
      'is_up': True,
      'key': 'interface_name',
      'rx': 0,
      'speed': 10485760000,
      'time_since_update': 1,
      'tx': 63},
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
                      'cumulative_cx': 118689595,
                      'cumulative_rx': 27228964,
                      'cumulative_tx': 91460631,
                      'cx': 63,
                      'interface_name': 'veth20bf375',
                      'is_up': True,
                      'key': 'interface_name',
                      'rx': 0,
                      'speed': 10485760000,
                      'time_since_update': 1,
                      'tx': 63}]}

GET now
-------

Get plugin stats::

    # curl http://localhost:61208/api/3/now
    '2021-08-21 11:29:06 CEST'

GET percpu
----------

Get plugin stats::

    # curl http://localhost:61208/api/3/percpu
    [{'cpu_number': 0,
      'guest': 0.0,
      'guest_nice': 0.0,
      'idle': 26.7,
      'iowait': 0.0,
      'irq': 0.0,
      'key': 'cpu_number',
      'nice': 0.0,
      'softirq': 0.7,
      'steal': 0.0,
      'system': 4.4,
      'total': 73.3,
      'user': 68.1},
     {'cpu_number': 1,
      'guest': 0.0,
      'guest_nice': 0.0,
      'idle': 95.5,
      'iowait': 0.0,
      'irq': 0.0,
      'key': 'cpu_number',
      'nice': 0.0,
      'softirq': 1.5,
      'steal': 0.0,
      'system': 1.5,
      'total': 4.5,
      'user': 1.5}]

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
      'status': 0.006823,
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
                        'status': 0.006823,
                        'timeout': 3}]}

GET processcount
----------------

Get plugin stats::

    # curl http://localhost:61208/api/3/processcount
    {'pid_max': 0, 'running': 1, 'sleeping': 282, 'thread': 1568, 'total': 340}

Get a specific field::

    # curl http://localhost:61208/api/3/processcount/total
    {'total': 340}

GET processlist
---------------

Get plugin stats::

    # curl http://localhost:61208/api/3/processlist
    [{'cmdline': ['/usr/lib/firefox/firefox', '-new-window'],
      'cpu_percent': 0.0,
      'cpu_times': pcputimes(user=6122.49, system=1864.21, children_user=3434.01, children_system=699.19, iowait=1.83),
      'gids': pgids(real=1000, effective=1000, saved=1000),
      'io_counters': [1270943744, 5694791680, 0, 0, 0],
      'key': 'pid',
      'memory_info': pmem(rss=737452032, vms=5285826560, shared=218091520, text=622592, lib=0, data=1192505344, dirty=0),
      'memory_percent': 9.395464614758398,
      'name': 'firefox',
      'nice': 0,
      'num_threads': 140,
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
      'cpu_times': pcputimes(user=1221.57, system=231.7, children_user=0.0, children_system=0.0, iowait=0.26),
      'gids': pgids(real=1000, effective=1000, saved=1000),
      'io_counters': [40177664, 200081408, 0, 0, 0],
      'key': 'pid',
      'memory_info': pmem(rss=508583936, vms=3566657536, shared=84766720, text=622592, lib=0, data=722067456, dirty=0),
      'memory_percent': 6.479583982382395,
      'name': 'Web Content',
      'nice': 0,
      'num_threads': 35,
      'pid': 4258,
      'ppid': 4142,
      'status': 'S',
      'time_since_update': 1,
      'username': 'nicolargo'}]

Get a specific field::

    # curl http://localhost:61208/api/3/processlist/pid
    {'pid': [4142,
             4258,
             4690,
             4378,
             9692,
             110403,
             9388,
             3638,
             31464,
             11502,
             64775,
             110952,
             113064,
             92898,
             9426,
             92962,
             38222,
             9359,
             27823,
             9330,
             9441,
             9453,
             4280,
             7272,
             112685,
             18645,
             30528,
             9474,
             115744,
             2297,
             9378,
             68876,
             9542,
             2217,
             3460,
             9711,
             3485,
             3402,
             3735,
             351,
             9231,
             9233,
             1162,
             3211,
             5343,
             11685,
             9333,
             9334,
             105514,
             4726,
             3400,
             3768,
             111911,
             1319,
             81429,
             1140,
             3697,
             3704,
             3905,
             3764,
             3795,
             1,
             3799,
             3789,
             2251,
             3845,
             2439,
             3793,
             3673,
             1175,
             1308,
             1150,
             101343,
             1154,
             3668,
             7777,
             3676,
             3159,
             101342,
             3623,
             3791,
             3819,
             3721,
             3371,
             3391,
             3829,
             3802,
             1176,
             2236,
             3439,
             1022,
             1306,
             107588,
             1551,
             2449,
             3948,
             2468,
             1174,
             30686,
             30672,
             1138,
             53315,
             36769,
             3821,
             3510,
             3949,
             3414,
             3824,
             1118,
             3792,
             1359,
             3679,
             1145,
             3456,
             106400,
             3826,
             3447,
             3470,
             81481,
             3718,
             36746,
             3426,
             1172,
             3862,
             3405,
             3672,
             3476,
             3790,
             2446,
             3807,
             3432,
             3092,
             3601,
             3689,
             1169,
             11661,
             3853,
             3788,
             1159,
             53321,
             3812,
             3483,
             38268,
             3843,
             1132,
             68853,
             53324,
             1157,
             3452,
             11480,
             383,
             1146,
             1131,
             1023,
             1021,
             2447,
             3214,
             3606,
             1177,
             1430,
             3693,
             115728,
             1135,
             9294,
             3616,
             9536,
             1209,
             53327,
             11452,
             68839,
             1350,
             3063,
             1119,
             11427,
             115743,
             11465,
             105810,
             2097,
             3077,
             2275,
             2271,
             4551,
             3395,
             11440,
             1215,
             997,
             2269,
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
             103136,
             103416,
             104097,
             105142,
             105193,
             105304,
             111862,
             111863,
             112865,
             113376,
             113389,
             113516,
             113762,
             113881,
             114992,
             115433,
             115558]}

Get a specific item when field matchs the given value::

    # curl http://localhost:61208/api/3/processlist/pid/4142
    {'4142': [{'cmdline': ['/usr/lib/firefox/firefox', '-new-window'],
               'cpu_percent': 0.0,
               'cpu_times': [6122.49, 1864.21, 3434.01, 699.19, 1.83],
               'gids': [1000, 1000, 1000],
               'io_counters': [1270943744, 5694791680, 0, 0, 0],
               'key': 'pid',
               'memory_info': [737452032,
                               5285826560,
                               218091520,
                               622592,
                               0,
                               1192505344,
                               0],
               'memory_percent': 9.395464614758398,
               'name': 'firefox',
               'nice': 0,
               'num_threads': 140,
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
    {'cpu': 26.7,
     'cpu_hz': 3000000000.0,
     'cpu_hz_current': 1541328000.0,
     'cpu_name': 'Intel(R) Core(TM) i7-4500U CPU @ 1.80GHz',
     'mem': 81.6,
     'percpu': [{'cpu_number': 0,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 26.7,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.7,
                 'steal': 0.0,
                 'system': 4.4,
                 'total': 73.3,
                 'user': 68.1},
                {'cpu_number': 1,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 95.5,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 1.5,
                 'steal': 0.0,
                 'system': 1.5,
                 'total': 4.5,
                 'user': 1.5},
                {'cpu_number': 2,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 82.6,
                 'iowait': 1.3,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 12.1,
                 'steal': 0.0,
                 'system': 0.7,
                 'total': 17.4,
                 'user': 3.4},
                {'cpu_number': 3,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 86.5,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 6.4,
                 'steal': 0.0,
                 'system': 2.8,
                 'total': 13.5,
                 'user': 4.3}],
     'swap': 7.4}

Get a specific field::

    # curl http://localhost:61208/api/3/quicklook/cpu
    {'cpu': 26.7}

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
     'os_version': '5.4.0-74-generic',
     'platform': '64bit'}

Get a specific field::

    # curl http://localhost:61208/api/3/system/os_name
    {'os_name': 'Linux'}

GET uptime
----------

Get plugin stats::

    # curl http://localhost:61208/api/3/uptime
    {'seconds': 1189384}

GET all stats
-------------

Get all Glances stats::

    # curl http://localhost:61208/api/3/all
    Return a very big dictionnary (avoid using this request, performances will be poor)...

GET stats history
-----------------

History of a plugin::

    # curl http://localhost:61208/api/3/cpu/history
    {'system': [['2021-08-21T11:29:07.039633', 3.0],
                ['2021-08-21T11:29:08.147174', 3.0],
                ['2021-08-21T11:29:09.287220', 2.5]],
     'user': [['2021-08-21T11:29:07.039622', 16.8],
              ['2021-08-21T11:29:08.147168', 16.8],
              ['2021-08-21T11:29:09.287213', 4.2]]}

Limit history to last 2 values::

    # curl http://localhost:61208/api/3/cpu/history/2
    {'system': [['2021-08-21T11:29:08.147174', 3.0],
                ['2021-08-21T11:29:09.287220', 2.5]],
     'user': [['2021-08-21T11:29:08.147168', 16.8],
              ['2021-08-21T11:29:09.287213', 4.2]]}

History for a specific field::

    # curl http://localhost:61208/api/3/cpu/system/history
    {'system': [['2021-08-21T11:29:07.039633', 3.0],
                ['2021-08-21T11:29:08.147174', 3.0],
                ['2021-08-21T11:29:09.287220', 2.5]]}

Limit history for a specific field to last 2 values::

    # curl http://localhost:61208/api/3/cpu/system/history
    {'system': [['2021-08-21T11:29:08.147174', 3.0],
                ['2021-08-21T11:29:09.287220', 2.5]]}

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


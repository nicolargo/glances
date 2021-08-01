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
    [[1627804818.0,
      -1,
      'WARNING',
      'MEM',
      75.49093945284471,
      75.49093945284471,
      75.49093945284471,
      75.49093945284471,
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
      'timer': 0.2887728214263916},
     {'count': 0,
      'countmax': 20.0,
      'countmin': None,
      'key': 'name',
      'name': 'Python',
      'refresh': 3.0,
      'regex': True,
      'result': None,
      'timer': 0.28859639167785645}]

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
                  'timer': 0.2887728214263916}]}

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
     'idle': 74.8,
     'interrupts': 0,
     'iowait': 0.0,
     'irq': 0.0,
     'nice': 0.0,
     'soft_interrupts': 0,
     'softirq': 3.2,
     'steal': 0.0,
     'syscalls': 0,
     'system': 3.2,
     'time_since_update': 1,
     'total': 28.0,
     'user': 18.7}

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
    {'total': 28.0}

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
      'free': 36343627776,
      'fs_type': 'ext4',
      'key': 'mnt_point',
      'mnt_point': '/',
      'percent': 84.3,
      'size': 243396149248,
      'used': 194665066496}]

Get a specific field::

    # curl http://localhost:61208/api/3/fs/mnt_point
    {'mnt_point': ['/']}

Get a specific item when field matchs the given value::

    # curl http://localhost:61208/api/3/fs/mnt_point//
    {'/': [{'device_name': '/dev/mapper/ubuntu--gnome--vg-root',
            'free': 36343627776,
            'fs_type': 'ext4',
            'key': 'mnt_point',
            'mnt_point': '/',
            'percent': 84.3,
            'size': 243396149248,
            'used': 194665066496}]}

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
    {'cpucore': 4, 'min1': 1.61, 'min15': 1.41, 'min5': 1.51}

Fields descriptions:

* **min1**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 1 minute (unit is *number*)
* **min5**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 5 minutes (unit is *number*)
* **min15**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 15 minutes (unit is *number*)
* **cpucore**: Total number of CPU core (unit is *number*)

Get a specific field::

    # curl http://localhost:61208/api/3/load/min1
    {'min1': 1.61}

GET mem
-------

Get plugin stats::

    # curl http://localhost:61208/api/3/mem
    {'active': 4883918848,
     'available': 1923731456,
     'buffers': 253976576,
     'cached': 2159919104,
     'free': 1923731456,
     'inactive': 1493590016,
     'percent': 75.5,
     'shared': 837779456,
     'total': 7849062400,
     'used': 5925330944}

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
    {'total': 7849062400}

GET memswap
-----------

Get plugin stats::

    # curl http://localhost:61208/api/3/memswap
    {'free': 6198513664,
     'percent': 23.3,
     'sin': 8927154176,
     'sout': 13442445312,
     'time_since_update': 1,
     'total': 8082419712,
     'used': 1883906048}

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
      'tx': 0},
     {'alias': None,
      'cumulative_cx': 3815603736,
      'cumulative_rx': 1907801868,
      'cumulative_tx': 1907801868,
      'cx': 1680,
      'interface_name': 'lo',
      'is_up': True,
      'key': 'interface_name',
      'rx': 840,
      'speed': 0,
      'time_since_update': 1,
      'tx': 840}]

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
    {'interface_name': ['mpqemubr0-dummy',
                        'lo',
                        'mpqemubr0',
                        'tap-838a195875f',
                        'docker0',
                        'wlp2s0',
                        'br-119e6ee04e05',
                        'vboxnet0',
                        'br-87386b77b676']}

Get a specific item when field matchs the given value::

    # curl http://localhost:61208/api/3/network/interface_name/mpqemubr0-dummy
    {'mpqemubr0-dummy': [{'alias': None,
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
                          'tx': 0}]}

GET now
-------

Get plugin stats::

    # curl http://localhost:61208/api/3/now
    '2021-08-01 10:00:18 CEST'

GET percpu
----------

Get plugin stats::

    # curl http://localhost:61208/api/3/percpu
    [{'cpu_number': 0,
      'guest': 0.0,
      'guest_nice': 0.0,
      'idle': 58.3,
      'iowait': 0.0,
      'irq': 0.0,
      'key': 'cpu_number',
      'nice': 0.0,
      'softirq': 0.0,
      'steal': 0.0,
      'system': 2.8,
      'total': 41.7,
      'user': 38.9},
     {'cpu_number': 1,
      'guest': 0.0,
      'guest_nice': 0.0,
      'idle': 85.2,
      'iowait': 0.0,
      'irq': 0.0,
      'key': 'cpu_number',
      'nice': 0.0,
      'softirq': 11.5,
      'steal': 0.0,
      'system': 0.8,
      'total': 14.8,
      'user': 2.5}]

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
      'status': 0.008997,
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
                        'status': 0.008997,
                        'timeout': 3}]}

GET processcount
----------------

Get plugin stats::

    # curl http://localhost:61208/api/3/processcount
    {'pid_max': 0, 'running': 1, 'sleeping': 286, 'thread': 1418, 'total': 347}

Get a specific field::

    # curl http://localhost:61208/api/3/processcount/total
    {'total': 347}

GET processlist
---------------

Get plugin stats::

    # curl http://localhost:61208/api/3/processlist
    [{'cmdline': ['/home/nicolargo/dev/glances/venv/bin/python3.8',
                  '/home/nicolargo/.vscode/extensions/ms-python.python-2021.5.926500501/pythonFiles/run-jedi-language-server.py'],
      'cpu_percent': 0.0,
      'cpu_times': pcputimes(user=7133.85, system=375.42, children_user=0.0, children_system=0.0, iowait=16.66),
      'gids': pgids(real=1000, effective=1000, saved=1000),
      'io_counters': [766472192, 117370880, 0, 0, 0],
      'key': 'pid',
      'memory_info': pmem(rss=703184896, vms=946077696, shared=4890624, text=2846720, lib=0, data=725467136, dirty=0),
      'memory_percent': 8.958839415010894,
      'name': 'python3.8',
      'nice': 0,
      'num_threads': 4,
      'pid': 2702806,
      'ppid': 2702621,
      'status': 'S',
      'time_since_update': 1,
      'username': 'nicolargo'},
     {'cmdline': ['/usr/lib/firefox/firefox', '-new-window'],
      'cpu_percent': 0.0,
      'cpu_times': pcputimes(user=5160.1, system=1765.91, children_user=5308.13, children_system=907.19, iowait=3.06),
      'gids': pgids(real=1000, effective=1000, saved=1000),
      'io_counters': [2364518400, 5913870336, 0, 0, 0],
      'key': 'pid',
      'memory_info': pmem(rss=498114560, vms=4753195008, shared=156286976, text=622592, lib=0, data=1138978816, dirty=0),
      'memory_percent': 6.346166390523281,
      'name': 'firefox',
      'nice': 0,
      'num_threads': 125,
      'pid': 2993020,
      'ppid': 8496,
      'status': 'S',
      'time_since_update': 1,
      'username': 'nicolargo'}]

Get a specific field::

    # curl http://localhost:61208/api/3/processlist/pid
    {'pid': [2702806,
             2993020,
             2702582,
             2993144,
             9122,
             2993283,
             2993375,
             3146884,
             42230,
             3176234,
             2702621,
             3179000,
             3075417,
             3131841,
             2702553,
             2702525,
             744165,
             3183387,
             2993158,
             2702636,
             2702653,
             3244,
             4497,
             3168367,
             2791638,
             2702815,
             3184843,
             2741015,
             8639,
             8654,
             3169962,
             2791637,
             2702565,
             2791665,
             8540,
             3167609,
             3419,
             2625397,
             2702789,
             9696,
             2598927,
             2994159,
             3154355,
             3178606,
             28036,
             8538,
             1,
             2739211,
             9412,
             1101,
             2791760,
             9880,
             9791,
             3166295,
             9918,
             2702662,
             3166294,
             9915,
             9520,
             10076,
             1140,
             9421,
             9539,
             9975,
             8496,
             2625601,
             42244,
             7479,
             218114,
             1264,
             3141573,
             3201,
             3138286,
             3153688,
             1675998,
             3131599,
             2614935,
             8553,
             9911,
             9608,
             3074778,
             2702529,
             3074791,
             9427,
             3074785,
             9962,
             2702528,
             9936,
             2625324,
             1099,
             8546,
             8594,
             2625388,
             3103956,
             9910,
             1636,
             9073,
             9432,
             2625339,
             3131609,
             9820,
             3131612,
             2078532,
             10009,
             1316,
             9957,
             1137,
             1141,
             223473,
             2625334,
             9934,
             9762,
             3075380,
             9596,
             2625605,
             1085,
             9903,
             8633,
             10001,
             44159,
             2622728,
             9929,
             10045,
             9453,
             43602,
             223504,
             9925,
             8575,
             1093,
             8623,
             10017,
             9953,
             1115,
             9877,
             2625489,
             8822,
             8650,
             169607,
             9420,
             2548721,
             2525291,
             1905447,
             8672,
             8614,
             627089,
             713820,
             9010,
             9941,
             8995,
             298444,
             1122,
             1110,
             9016,
             43938,
             9969,
             8664,
             3184831,
             1096,
             1134,
             8586,
             2879345,
             2625337,
             1168,
             1001,
             3131615,
             2879435,
             4504,
             3170267,
             1097,
             1125,
             9066,
             2625021,
             2625338,
             3217,
             1462,
             8953,
             2620923,
             1086,
             9512,
             3184842,
             3953,
             3168425,
             3229,
             3225,
             1310,
             978,
             1171,
             370,
             13314,
             8498,
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
             21,
             22,
             23,
             24,
             27,
             28,
             29,
             30,
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
             102,
             103,
             105,
             107,
             108,
             112,
             121,
             139,
             181,
             191,
             192,
             193,
             194,
             195,
             196,
             197,
             198,
             200,
             201,
             206,
             207,
             238,
             288,
             289,
             309,
             360,
             364,
             390,
             439,
             450,
             451,
             452,
             453,
             513,
             514,
             531,
             842,
             843,
             844,
             845,
             846,
             847,
             848,
             849,
             850,
             851,
             852,
             853,
             1323,
             1527,
             1529,
             1531,
             1533,
             1534,
             1537,
             1538,
             1540,
             8648,
             11754,
             14346,
             45609,
             45610,
             45621,
             45622,
             45623,
             45624,
             45625,
             45626,
             217392,
             574771,
             1893153,
             2058173,
             2318240,
             2624916,
             2624918,
             2702007,
             2717801,
             2780261,
             2816759,
             2816957,
             2817447,
             2817525,
             2817644,
             2848355,
             2848483,
             2848744,
             2891750,
             2892014,
             2926441,
             2938027,
             2939167,
             2981539,
             3043867,
             3076088,
             3076171,
             3076588,
             3143304,
             3154246,
             3166323,
             3167277,
             3167547,
             3168934,
             3169582,
             3175884,
             3178339,
             3178406,
             3178495,
             3178496,
             3178517,
             3178523,
             3182284,
             3182857,
             3183063,
             3184028,
             3184214,
             3184248,
             3184379]}

Get a specific item when field matchs the given value::

    # curl http://localhost:61208/api/3/processlist/pid/2702806
    {'2702806': [{'cmdline': ['/home/nicolargo/dev/glances/venv/bin/python3.8',
                              '/home/nicolargo/.vscode/extensions/ms-python.python-2021.5.926500501/pythonFiles/run-jedi-language-server.py'],
                  'cpu_percent': 0.0,
                  'cpu_times': [7133.85, 375.42, 0.0, 0.0, 16.66],
                  'gids': [1000, 1000, 1000],
                  'io_counters': [766472192, 117370880, 0, 0, 0],
                  'key': 'pid',
                  'memory_info': [703184896,
                                  946077696,
                                  4890624,
                                  2846720,
                                  0,
                                  725467136,
                                  0],
                  'memory_percent': 8.958839415010894,
                  'name': 'python3.8',
                  'nice': 0,
                  'num_threads': 4,
                  'pid': 2702806,
                  'ppid': 2702621,
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
    {'cpu': 28.0,
     'cpu_hz': 2025000000.0,
     'cpu_hz_current': 1485273250.0,
     'cpu_name': 'Intel(R) Core(TM) i7-4500U CPU @ 1.80GH',
     'mem': 75.5,
     'percpu': [{'cpu_number': 0,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 58.3,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 2.8,
                 'total': 41.7,
                 'user': 38.9},
                {'cpu_number': 1,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 85.2,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 11.5,
                 'steal': 0.0,
                 'system': 0.8,
                 'total': 14.8,
                 'user': 2.5},
                {'cpu_number': 2,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 73.5,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 3.5,
                 'steal': 0.0,
                 'system': 4.4,
                 'total': 26.5,
                 'user': 18.6},
                {'cpu_number': 3,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 68.5,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 0.9,
                 'total': 31.5,
                 'user': 30.6}],
     'swap': 23.3}

Get a specific field::

    # curl http://localhost:61208/api/3/quicklook/cpu
    {'cpu': 28.0}

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
     'os_version': '5.4.0-66-generic',
     'platform': '64bit'}

Get a specific field::

    # curl http://localhost:61208/api/3/system/os_name
    {'os_name': 'Linux'}

GET uptime
----------

Get plugin stats::

    # curl http://localhost:61208/api/3/uptime
    {'seconds': 9157701}

GET all stats
-------------

Get all Glances stats::

    # curl http://localhost:61208/api/3/all
    Return a very big dictionnary (avoid using this request, performances will be poor)...

GET stats history
-----------------

History of a plugin::

    # curl http://localhost:61208/api/3/cpu/history
    {'system': [['2021-08-01T10:00:18.628670', 3.2],
                ['2021-08-01T10:00:19.690589', 3.2],
                ['2021-08-01T10:00:20.834888', 1.5]],
     'user': [['2021-08-01T10:00:18.628661', 18.7],
              ['2021-08-01T10:00:19.690583', 18.7],
              ['2021-08-01T10:00:20.834881', 4.1]]}

Limit history to last 2 values::

    # curl http://localhost:61208/api/3/cpu/history/2
    {'system': [['2021-08-01T10:00:19.690589', 3.2],
                ['2021-08-01T10:00:20.834888', 1.5]],
     'user': [['2021-08-01T10:00:19.690583', 18.7],
              ['2021-08-01T10:00:20.834881', 4.1]]}

History for a specific field::

    # curl http://localhost:61208/api/3/cpu/system/history
    {'system': [['2021-08-01T10:00:18.628670', 3.2],
                ['2021-08-01T10:00:19.690589', 3.2],
                ['2021-08-01T10:00:20.834888', 1.5]]}

Limit history for a specific field to last 2 values::

    # curl http://localhost:61208/api/3/cpu/system/history
    {'system': [['2021-08-01T10:00:19.690589', 3.2],
                ['2021-08-01T10:00:20.834888', 1.5]]}

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


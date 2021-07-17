.. _api:

API (Restfull/JSON) documentation
=================================

The Glances Restfull/API server could be ran using the following command line:

.. code-block:: bash

    # glances -w --disable-webui

Note: Change request URL api/3 by api/2 if you use Glances 2.x.

GET Plugins list
----------------

Example::

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

.. code-block:: json

    # curl http://localhost:61208/api/3/alert
    [[1626506953.0,
      -1,
      'WARNING',
      'MEM',
      73.75089692241458,
      73.75089692241458,
      73.75089692241458,
      73.75089692241458,
      1,
      [],
      '',
      'memory_percent']]

GET amps
--------

.. code-block:: json

    # curl http://localhost:61208/api/3/amps
    [{'count': 0,
      'countmax': None,
      'countmin': 1.0,
      'key': 'name',
      'name': 'Dropbox',
      'refresh': 3.0,
      'regex': True,
      'result': None,
      'timer': 0.11381411552429199},
     {'count': 0,
      'countmax': 20.0,
      'countmin': None,
      'key': 'name',
      'name': 'Python',
      'refresh': 3.0,
      'regex': True,
      'result': None,
      'timer': 0.11371397972106934}]

Get a specific field:

.. code-block:: json

    # curl http://localhost:61208/api/3/amps/name
    {'name': ['Dropbox', 'Python', 'Conntrack', 'Nginx', 'Systemd', 'SystemV']}

Get a specific item when field matchs the given value:

.. code-block:: json

    # curl http://localhost:61208/api/3/amps/name/Dropbox
    {'Dropbox': [{'count': 0,
                  'countmax': None,
                  'countmin': 1.0,
                  'key': 'name',
                  'name': 'Dropbox',
                  'refresh': 3.0,
                  'regex': True,
                  'result': None,
                  'timer': 0.11381411552429199}]}

GET core
--------

.. code-block:: json

    # curl http://localhost:61208/api/3/core
    {'log': 4, 'phys': 2}

Fields descriptions:

* **phys**: Number of physical cores (hyper thread CPUs are excluded) (unit is *number*)
* **log**: Number of logical CPUs. A logical CPU is the number of physical cores multiplied by the number of threads that can run on each core (unit is *number*)

Get a specific field:

.. code-block:: json

    # curl http://localhost:61208/api/3/core/phys
    {'phys': 2}

GET cpu
-------

.. code-block:: json

    # curl http://localhost:61208/api/3/cpu
    {'cpucore': 4,
     'ctx_switches': 0,
     'guest': 0.0,
     'guest_nice': 0.0,
     'idle': 67.7,
     'interrupts': 0,
     'iowait': 0.0,
     'irq': 0.0,
     'nice': 0.0,
     'soft_interrupts': 0,
     'softirq': 8.9,
     'steal': 0.0,
     'syscalls': 0,
     'system': 7.0,
     'time_since_update': 1,
     'total': 32.7,
     'user': 16.5}

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

Get a specific field:

.. code-block:: json

    # curl http://localhost:61208/api/3/cpu/total
    {'total': 32.7}

GET diskio
----------

.. code-block:: json

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

Get a specific field:

.. code-block:: json

    # curl http://localhost:61208/api/3/diskio/disk_name
    {'disk_name': ['sda', 'sda1', 'sda2', 'sda5', 'dm-0', 'dm-1', 'sdc', 'sdc1']}

Get a specific item when field matchs the given value:

.. code-block:: json

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

.. code-block:: json

    # curl http://localhost:61208/api/3/fs
    [{'device_name': '/dev/mapper/ubuntu--gnome--vg-root',
      'free': 36254167040,
      'fs_type': 'ext4',
      'key': 'mnt_point',
      'mnt_point': '/',
      'percent': 84.3,
      'size': 243396149248,
      'used': 194754527232},
     {'device_name': '/dev/sdc1',
      'free': 3814915088384,
      'fs_type': 'fuseblk',
      'key': 'mnt_point',
      'mnt_point': '/media/nicolargo/Elements',
      'percent': 4.6,
      'size': 4000750497792,
      'used': 185835409408}]

Get a specific field:

.. code-block:: json

    # curl http://localhost:61208/api/3/fs/mnt_point
    {'mnt_point': ['/', '/media/nicolargo/Elements']}

Get a specific item when field matchs the given value:

.. code-block:: json

    # curl http://localhost:61208/api/3/fs/mnt_point//
    {'/': [{'device_name': '/dev/mapper/ubuntu--gnome--vg-root',
            'free': 36254167040,
            'fs_type': 'ext4',
            'key': 'mnt_point',
            'mnt_point': '/',
            'percent': 84.3,
            'size': 243396149248,
            'used': 194754527232}]}

GET ip
------

.. code-block:: json

    # curl http://localhost:61208/api/3/ip
    {'address': '192.168.43.139',
     'gateway': '192.168.43.136',
     'mask': '255.255.255.0',
     'mask_cidr': 24}

Get a specific field:

.. code-block:: json

    # curl http://localhost:61208/api/3/ip/address
    {'address': '192.168.43.139'}

GET load
--------

.. code-block:: json

    # curl http://localhost:61208/api/3/load
    {'cpucore': 4, 'min1': 0.44, 'min15': 1.1, 'min5': 0.83}

Fields descriptions:

* **min1**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 1 minute (unit is *number*)
* **min5**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 5 minutes (unit is *number*)
* **min15**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 15 minutes (unit is *number*)
* **cpucore**: Total number of CPU core (unit is *number*)

Get a specific field:

.. code-block:: json

    # curl http://localhost:61208/api/3/load/min1
    {'min1': 0.44}

GET mem
-------

.. code-block:: json

    # curl http://localhost:61208/api/3/mem
    {'active': 4698603520,
     'available': 2060308480,
     'buffers': 686833664,
     'cached': 1725063168,
     'free': 2060308480,
     'inactive': 1597227008,
     'percent': 73.8,
     'shared': 700612608,
     'total': 7849062400,
     'used': 5788753920}

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

Get a specific field:

.. code-block:: json

    # curl http://localhost:61208/api/3/mem/total
    {'total': 7849062400}

GET memswap
-----------

.. code-block:: json

    # curl http://localhost:61208/api/3/memswap
    {'free': 6102118400,
     'percent': 24.5,
     'sin': 8697491456,
     'sout': 13157560320,
     'time_since_update': 1,
     'total': 8082419712,
     'used': 1980301312}

Fields descriptions:

* **total**: Total swap memory (unit is *bytes*)
* **used**: Used swap memory (unit is *bytes*)
* **free**: Free swap memory (unit is *bytes*)
* **percent**: Used swap memory in percentage (unit is *percent*)
* **sin**: The number of bytes the system has swapped in from disk (cumulative) (unit is *bytes*)
* **sout**: The number of bytes the system has swapped out from disk (cumulative) (unit is *bytes*)
* **time_since_update**: Number of seconds since last update (unit is *seconds*)

Get a specific field:

.. code-block:: json

    # curl http://localhost:61208/api/3/memswap/total
    {'total': 8082419712}

GET network
-----------

.. code-block:: json

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
      'cumulative_cx': 3715365760,
      'cumulative_rx': 1857682880,
      'cumulative_tx': 1857682880,
      'cx': 200,
      'interface_name': 'lo',
      'is_up': True,
      'key': 'interface_name',
      'rx': 100,
      'speed': 0,
      'time_since_update': 1,
      'tx': 100}]

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

Get a specific field:

.. code-block:: json

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

Get a specific item when field matchs the given value:

.. code-block:: json

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

.. code-block:: json

    # curl http://localhost:61208/api/3/now
    '2021-07-17 09:29:13 CEST'

GET percpu
----------

.. code-block:: json

    # curl http://localhost:61208/api/3/percpu
    [{'cpu_number': 0,
      'guest': 0.0,
      'guest_nice': 0.0,
      'idle': 21.0,
      'iowait': 0.0,
      'irq': 0.0,
      'key': 'cpu_number',
      'nice': 0.0,
      'softirq': 10.0,
      'steal': 0.0,
      'system': 0.0,
      'total': 79.0,
      'user': 0.0},
     {'cpu_number': 1,
      'guest': 0.0,
      'guest_nice': 0.0,
      'idle': 22.0,
      'iowait': 0.0,
      'irq': 0.0,
      'key': 'cpu_number',
      'nice': 0.0,
      'softirq': 1.0,
      'steal': 0.0,
      'system': 1.0,
      'total': 78.0,
      'user': 1.0}]

Get a specific field:

.. code-block:: json

    # curl http://localhost:61208/api/3/percpu/cpu_number
    {'cpu_number': [0, 1, 2, 3]}

GET ports
---------

.. code-block:: json

    # curl http://localhost:61208/api/3/ports
    [{'description': 'DefaultGateway',
      'host': '192.168.43.136',
      'indice': 'port_0',
      'port': 0,
      'refresh': 30,
      'rtt_warning': None,
      'status': 0.006171,
      'timeout': 3}]

Get a specific field:

.. code-block:: json

    # curl http://localhost:61208/api/3/ports/host
    {'host': ['192.168.43.136']}

Get a specific item when field matchs the given value:

.. code-block:: json

    # curl http://localhost:61208/api/3/ports/host/192.168.43.136
    {'192.168.43.136': [{'description': 'DefaultGateway',
                         'host': '192.168.43.136',
                         'indice': 'port_0',
                         'port': 0,
                         'refresh': 30,
                         'rtt_warning': None,
                         'status': 0.006171,
                         'timeout': 3}]}

GET processcount
----------------

.. code-block:: json

    # curl http://localhost:61208/api/3/processcount
    {'pid_max': 0, 'running': 1, 'sleeping': 285, 'thread': 1427, 'total': 347}

Get a specific field:

.. code-block:: json

    # curl http://localhost:61208/api/3/processcount/total
    {'total': 347}

GET processlist
---------------

.. code-block:: json

    # curl http://localhost:61208/api/3/processlist
    [{'cmdline': ['/home/nicolargo/dev/glances/venv/bin/python3.8',
                  '/home/nicolargo/.vscode/extensions/ms-python.python-2021.5.926500501/pythonFiles/run-jedi-language-server.py'],
      'cpu_percent': 0.0,
      'cpu_times': pcputimes(user=5793.51, system=343.17, children_user=0.0, children_system=0.0, iowait=15.24),
      'gids': pgids(real=1000, effective=1000, saved=1000),
      'io_counters': [678944768, 109338624, 0, 0, 0],
      'key': 'pid',
      'memory_info': pmem(rss=668692480, vms=912785408, shared=3633152, text=2846720, lib=0, data=692174848, dirty=0),
      'memory_percent': 8.519393093371255,
      'name': 'python3.8',
      'nice': 0,
      'num_threads': 4,
      'pid': 2702806,
      'ppid': 2702621,
      'status': 'S',
      'time_since_update': 1,
      'username': 'nicolargo'},
     {'cmdline': ['/usr/share/code/code',
                  '--type=renderer',
                  '--disable-color-correct-rendering',
                  '--no-sandbox',
                  '--field-trial-handle=12394583116449707336,2893691487865030553,131072',
                  '--enable-features=WebComponentsV0Enabled',
                  '--disable-features=CertVerifierService,CookiesWithoutSameSiteMustBeSecure,SameSiteByDefaultCookies,SpareRendererForSitePerProcess',
                  '--lang=en-US',
                  '--enable-crash-reporter=7c06f526-63e8-47aa-8c08-b95f6ad2ec2d,no_channel',
                  '--global-crash-keys=7c06f526-63e8-47aa-8c08-b95f6ad2ec2d,no_channel,_companyName=Microsoft,_productName=VSCode,_version=1.56.2',
                  '--standard-schemes=vscode-webview,vscode-file',
                  '--secure-schemes=vscode-webview,vscode-file',
                  '--bypasscsp-schemes',
                  '--cors-schemes=vscode-webview,vscode-file',
                  '--fetch-schemes=vscode-webview,vscode-file',
                  '--service-worker-schemes=vscode-webview',
                  '--streaming-schemes',
                  '--app-path=/usr/share/code/resources/app',
                  '--no-sandbox',
                  '--no-zygote',
                  '--num-raster-threads=2',
                  '--enable-main-frame-before-activation',
                  '--renderer-client-id=5',
                  '--no-v8-untrusted-code-mitigations',
                  '--shared-files=v8_context_snapshot_data:100',
                  '--vscode-window-config=vscode:9f2589e5-1786-4a6a-98fc-d85b382d2411'],
      'cpu_percent': 0.0,
      'cpu_times': pcputimes(user=6616.73, system=540.33, children_user=17.21, children_system=3.63, iowait=6.73),
      'gids': pgids(real=1000, effective=1000, saved=1000),
      'io_counters': [1004748800, 48324608, 0, 0, 0],
      'key': 'pid',
      'memory_info': pmem(rss=437821440, vms=54421401600, shared=50536448, text=123428864, lib=0, data=862879744, dirty=0),
      'memory_percent': 5.578009419316121,
      'name': 'code',
      'nice': 0,
      'num_threads': 20,
      'pid': 2702582,
      'ppid': 2702525,
      'status': 'S',
      'time_since_update': 1,
      'username': 'nicolargo'}]

Get a specific field:

.. code-block:: json

    # curl http://localhost:61208/api/3/processlist/pid
    {'pid': [2702806,
             2702582,
             2993144,
             2993020,
             2993283,
             9122,
             3079121,
             42230,
             2993375,
             2702621,
             3078543,
             3075417,
             2993148,
             3090242,
             2938292,
             2702525,
             744165,
             2702553,
             3056321,
             2702636,
             2993158,
             3107593,
             8654,
             2702653,
             2791638,
             2702815,
             3244,
             3103852,
             8639,
             3124708,
             2741015,
             2791637,
             2702565,
             2791665,
             8540,
             3419,
             3120308,
             2702789,
             2817004,
             3076986,
             2625397,
             2598927,
             2994159,
             4497,
             9696,
             3120307,
             28036,
             8538,
             9412,
             1,
             3120328,
             1101,
             9880,
             2739211,
             2702662,
             9520,
             9915,
             2791760,
             10076,
             3120327,
             9918,
             1140,
             9539,
             218114,
             2625601,
             1264,
             9975,
             9421,
             42244,
             9791,
             7479,
             8496,
             8553,
             9911,
             1675998,
             3074778,
             9427,
             3074791,
             9962,
             3074785,
             3201,
             8594,
             9608,
             2625324,
             2702529,
             2625388,
             2702528,
             9936,
             1099,
             8546,
             1636,
             9073,
             2625339,
             3103956,
             9910,
             9820,
             2078532,
             9432,
             10009,
             223473,
             1141,
             1137,
             9957,
             9934,
             2625334,
             3075380,
             9596,
             10001,
             2035399,
             9903,
             44159,
             1085,
             9929,
             10045,
             2622728,
             9453,
             8623,
             9925,
             10017,
             2625605,
             223504,
             9953,
             1093,
             9877,
             1115,
             2625489,
             43602,
             2614935,
             8822,
             8672,
             3056033,
             9762,
             8650,
             9941,
             169607,
             9420,
             2548721,
             2525291,
             1905447,
             627089,
             9010,
             713820,
             1122,
             9016,
             9969,
             8995,
             3124696,
             298444,
             1110,
             8664,
             43938,
             8575,
             8614,
             1134,
             1096,
             3103851,
             1316,
             8633,
             2625337,
             1168,
             2879345,
             1001,
             8586,
             2879435,
             2625021,
             1097,
             4504,
             1125,
             9066,
             2625338,
             3217,
             1462,
             8953,
             2620923,
             9512,
             1086,
             3124707,
             3953,
             3229,
             3103980,
             3077281,
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
             2777389,
             2779024,
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
             2927027,
             2927659,
             2938027,
             2939167,
             2981539,
             3043867,
             3055870,
             3055871,
             3055872,
             3076088,
             3076171,
             3076588,
             3106441,
             3115093,
             3115308,
             3119366,
             3120203,
             3120204,
             3120205,
             3122021,
             3122327,
             3122446,
             3122549,
             3122955,
             3123701,
             3123728,
             3124311,
             3124426]}

Get a specific item when field matchs the given value:

.. code-block:: json

    # curl http://localhost:61208/api/3/processlist/pid/2702806
    {'2702806': [{'cmdline': ['/home/nicolargo/dev/glances/venv/bin/python3.8',
                              '/home/nicolargo/.vscode/extensions/ms-python.python-2021.5.926500501/pythonFiles/run-jedi-language-server.py'],
                  'cpu_percent': 0.0,
                  'cpu_times': [5793.51, 343.17, 0.0, 0.0, 15.24],
                  'gids': [1000, 1000, 1000],
                  'io_counters': [678944768, 109338624, 0, 0, 0],
                  'key': 'pid',
                  'memory_info': [668692480,
                                  912785408,
                                  3633152,
                                  2846720,
                                  0,
                                  692174848,
                                  0],
                  'memory_percent': 8.519393093371255,
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

.. code-block:: json

    # curl http://localhost:61208/api/3/psutilversion
    (5, 8, 0)

GET quicklook
-------------

.. code-block:: json

    # curl http://localhost:61208/api/3/quicklook
    {'cpu': 32.7,
     'cpu_hz': 3000000000.0,
     'cpu_hz_current': 2674333250.0,
     'cpu_name': 'Intel(R) Core(TM) i7-4500U CPU @ 1.80GH',
     'mem': 73.8,
     'percpu': [{'cpu_number': 0,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 21.0,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 10.0,
                 'steal': 0.0,
                 'system': 0.0,
                 'total': 79.0,
                 'user': 0.0},
                {'cpu_number': 1,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 22.0,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 1.0,
                 'steal': 0.0,
                 'system': 1.0,
                 'total': 78.0,
                 'user': 1.0},
                {'cpu_number': 2,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 20.0,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 1.0,
                 'total': 80.0,
                 'user': 1.0},
                {'cpu_number': 3,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 7.0,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 2.0,
                 'total': 93.0,
                 'user': 15.0}],
     'swap': 24.5}

Get a specific field:

.. code-block:: json

    # curl http://localhost:61208/api/3/quicklook/cpu
    {'cpu': 32.7}

GET sensors
-----------

.. code-block:: json

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

Get a specific field:

.. code-block:: json

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

Get a specific item when field matchs the given value:

.. code-block:: json

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

.. code-block:: json

    # curl http://localhost:61208/api/3/system
    {'hostname': 'XPS13-9333',
     'hr_name': 'Ubuntu 20.04 64bit',
     'linux_distro': 'Ubuntu 20.04',
     'os_name': 'Linux',
     'os_version': '5.4.0-66-generic',
     'platform': '64bit'}

Get a specific field:

.. code-block:: json

    # curl http://localhost:61208/api/3/system/os_name
    {'os_name': 'Linux'}

GET uptime
----------

.. code-block:: json

    # curl http://localhost:61208/api/3/uptime
    {'seconds': 7859840}

GET all stats
-------------

.. code-block:: json

    # curl http://localhost:61208/api/3/all
    Return a very big dictionnary (avoid using this request, performances will be poor)...

GET stats history
-----------------

History of a plugin:

.. code-block:: json

    # curl http://localhost:61208/api/3/cpu/history
    {'system': [['2021-07-17T09:29:13.323534', 7.0],
                ['2021-07-17T09:29:14.367310', 7.0],
                ['2021-07-17T09:29:15.463434', 1.8]],
     'user': [['2021-07-17T09:29:13.323529', 16.5],
              ['2021-07-17T09:29:14.367307', 16.5],
              ['2021-07-17T09:29:15.463430', 2.5]]}

Limit history to last 2 values:

.. code-block:: json

    # curl http://localhost:61208/api/3/cpu/history/2
    {'system': [['2021-07-17T09:29:14.367310', 7.0],
                ['2021-07-17T09:29:15.463434', 1.8]],
     'user': [['2021-07-17T09:29:14.367307', 16.5],
              ['2021-07-17T09:29:15.463430', 2.5]]}

History for a specific field:

.. code-block:: json

    # curl http://localhost:61208/api/3/cpu/system/history
    {'system': [['2021-07-17T09:29:13.323534', 7.0],
                ['2021-07-17T09:29:14.367310', 7.0],
                ['2021-07-17T09:29:15.463434', 1.8]]}

Limit history for a specific field to last 2 values:

.. code-block:: json

    # curl http://localhost:61208/api/3/cpu/system/history
    {'system': [['2021-07-17T09:29:14.367310', 7.0],
                ['2021-07-17T09:29:15.463434', 1.8]]}

GET limits (used for thresholds)
--------------------------------

All limits/thresholds:

.. code-block:: json

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
     'ip': {'history_size': 3600.0},
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

Limits/thresholds for the cpu plugin:

.. code-block:: json

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


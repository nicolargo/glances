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
    [[1642242165.0,
      -1,
      'WARNING',
      'MEM',
      82.75770835453343,
      82.75770835453343,
      82.75770835453343,
      82.75770835453343,
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
      'timer': 0.20821332931518555},
     {'count': 0,
      'countmax': 20.0,
      'countmin': None,
      'key': 'name',
      'name': 'Python',
      'refresh': 3.0,
      'regex': True,
      'result': None,
      'timer': 0.20801949501037598}]

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
                  'timer': 0.20821332931518555}]}

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
     'idle': 70.4,
     'interrupts': 0,
     'iowait': 0.2,
     'irq': 0.0,
     'nice': 0.0,
     'soft_interrupts': 0,
     'softirq': 1.7,
     'steal': 0.0,
     'syscalls': 0,
     'system': 4.4,
     'time_since_update': 1,
     'total': 29.5,
     'user': 23.3}

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
    {'total': 29.5}

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
    [{'Command': ['/entrypoint.sh', 'influxd'],
      'Id': 'cf5df66383ead8b7a332b25956506bfc33573ba449d9dab98fcc606454d604cb',
      'Image': ['influxdb:latest'],
      'Names': ['dockerinfluxdb2grafana_influxdb_1'],
      'Status': 'running',
      'cpu_percent': 0.0,
      'io_r': None,
      'io_w': None,
      'key': 'name',
      'memory_usage': 22753280,
      'name': 'dockerinfluxdb2grafana_influxdb_1',
      'network_rx': None,
      'network_tx': None},
     {'Command': ['/run.sh'],
      'Id': 'f5674bcca78935c38a085cd9d1988b4eaec167fc00e9108740126ff46a11bf83',
      'Image': ['grafana/grafana:latest'],
      'Names': ['dockerinfluxdb2grafana_grafana_1'],
      'Status': 'running',
      'cpu_percent': 0.0,
      'io_r': None,
      'io_w': None,
      'key': 'name',
      'memory_usage': None,
      'name': 'dockerinfluxdb2grafana_grafana_1',
      'network_rx': None,
      'network_tx': None}]

GET fs
------

Get plugin stats::

    # curl http://localhost:61208/api/3/fs
    [{'device_name': '/dev/mapper/ubuntu--gnome--vg-root',
      'free': 5852827648,
      'fs_type': 'ext4',
      'key': 'mnt_point',
      'mnt_point': '/',
      'percent': 97.5,
      'size': 243396149248,
      'used': 225155866624}]

Get a specific field::

    # curl http://localhost:61208/api/3/fs/mnt_point
    {'mnt_point': ['/']}

Get a specific item when field matchs the given value::

    # curl http://localhost:61208/api/3/fs/mnt_point//
    {'/': [{'device_name': '/dev/mapper/ubuntu--gnome--vg-root',
            'free': 5852827648,
            'fs_type': 'ext4',
            'key': 'mnt_point',
            'mnt_point': '/',
            'percent': 97.5,
            'size': 243396149248,
            'used': 225155866624}]}

GET ip
------

Get plugin stats::

    # curl http://localhost:61208/api/3/ip
    {'address': '192.168.0.33',
     'gateway': '192.168.0.254',
     'mask': '255.255.255.0',
     'mask_cidr': 24,
     'public_address': '91.166.228.228'}

Get a specific field::

    # curl http://localhost:61208/api/3/ip/address
    {'address': '192.168.0.33'}

GET load
--------

Get plugin stats::

    # curl http://localhost:61208/api/3/load
    {'cpucore': 4, 'min1': 0.93, 'min15': 1.48, 'min5': 1.13}

Fields descriptions:

* **min1**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 1 minute (unit is *float*)
* **min5**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 5 minutes (unit is *float*)
* **min15**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 15 minutes (unit is *float*)
* **cpucore**: Total number of CPU core (unit is *number*)

Get a specific field::

    # curl http://localhost:61208/api/3/load/min1
    {'min1': 0.93}

GET mem
-------

Get plugin stats::

    # curl http://localhost:61208/api/3/mem
    {'active': 5834387456,
     'available': 1353351168,
     'buffers': 304881664,
     'cached': 1838432256,
     'free': 1353351168,
     'inactive': 1002762240,
     'percent': 82.8,
     'shared': 703643648,
     'total': 7849021440,
     'used': 6495670272}

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
    {'free': 6441734144,
     'percent': 20.3,
     'sin': 5676781568,
     'sout': 9877434368,
     'time_since_update': 1,
     'total': 8082419712,
     'used': 1640685568}

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
      'cumulative_cx': 8464674,
      'cumulative_rx': 21687,
      'cumulative_tx': 8442987,
      'cx': 0,
      'interface_name': 'vetha426f3c',
      'is_up': True,
      'key': 'interface_name',
      'rx': 0,
      'speed': 10485760000,
      'time_since_update': 1,
      'tx': 0},
     {'alias': None,
      'cumulative_cx': 12586698,
      'cumulative_rx': 1081053,
      'cumulative_tx': 11505645,
      'cx': 0,
      'interface_name': 'veth5d13ef7',
      'is_up': True,
      'key': 'interface_name',
      'rx': 0,
      'speed': 10485760000,
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
    {'interface_name': ['vetha426f3c',
                        'veth5d13ef7',
                        'docker0',
                        'mpqemubr0',
                        'lo',
                        'br_grafana',
                        'br-119e6ee04e05',
                        'wlp2s0',
                        'br-87386b77b676']}

Get a specific item when field matchs the given value::

    # curl http://localhost:61208/api/3/network/interface_name/vetha426f3c
    {'vetha426f3c': [{'alias': None,
                      'cumulative_cx': 8464674,
                      'cumulative_rx': 21687,
                      'cumulative_tx': 8442987,
                      'cx': 0,
                      'interface_name': 'vetha426f3c',
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
    '2022-01-15 11:22:45 CET'

GET percpu
----------

Get plugin stats::

    # curl http://localhost:61208/api/3/percpu
    [{'cpu_number': 0,
      'guest': 0.0,
      'guest_nice': 0.0,
      'idle': 82.0,
      'iowait': 0.0,
      'irq': 0.0,
      'key': 'cpu_number',
      'nice': 0.0,
      'softirq': 0.0,
      'steal': 0.0,
      'system': 2.0,
      'total': 18.0,
      'user': 8.0},
     {'cpu_number': 1,
      'guest': 0.0,
      'guest_nice': 0.0,
      'idle': 17.0,
      'iowait': 0.0,
      'irq': 0.0,
      'key': 'cpu_number',
      'nice': 0.0,
      'softirq': 0.0,
      'steal': 0.0,
      'system': 6.0,
      'total': 83.0,
      'user': 71.0}]

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
      'status': 0.007164,
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
                        'status': 0.007164,
                        'timeout': 3}]}

GET processcount
----------------

Get plugin stats::

    # curl http://localhost:61208/api/3/processcount
    {'pid_max': 0, 'running': 1, 'sleeping': 290, 'thread': 1541, 'total': 352}

Get a specific field::

    # curl http://localhost:61208/api/3/processcount/total
    {'total': 352}

GET processlist
---------------

Get plugin stats::

    # curl http://localhost:61208/api/3/processlist
    [{'cmdline': ['/usr/lib/firefox/firefox'],
      'cpu_percent': 0.0,
      'cpu_times': pcputimes(user=13600.16, system=6195.46, children_user=1815.12, children_system=383.89, iowait=4.63),
      'gids': pgids(real=1000, effective=1000, saved=1000),
      'io_counters': [3538935808, 53054558208, 0, 0, 0],
      'key': 'pid',
      'memory_info': pmem(rss=518144000, vms=4950585344, shared=142413824, text=643072, lib=0, data=1333030912, dirty=0),
      'memory_percent': 6.60138342035157,
      'name': 'GeckoMain',
      'nice': 0,
      'num_threads': 154,
      'pid': 1503459,
      'ppid': 3847,
      'status': 'S',
      'time_since_update': 1,
      'username': 'nicolargo'},
     {'cmdline': ['/usr/lib/firefox/firefox',
                  '-contentproc',
                  '-childID',
                  '14',
                  '-isForBrowser',
                  '-prefsLen',
                  '8563',
                  '-prefMapSize',
                  '252236',
                  '-jsInitLen',
                  '278884',
                  '-parentBuildID',
                  '20211215221728',
                  '-appDir',
                  '/usr/lib/firefox/browser',
                  '1503459',
                  'true',
                  'tab'],
      'cpu_percent': 0.0,
      'cpu_times': pcputimes(user=4731.62, system=1025.04, children_user=0.0, children_system=0.0, iowait=0.87),
      'gids': pgids(real=1000, effective=1000, saved=1000),
      'io_counters': [67727360, 65536, 0, 0, 0],
      'key': 'pid',
      'memory_info': pmem(rss=478609408, vms=3810025472, shared=53080064, text=643072, lib=0, data=1046167552, dirty=0),
      'memory_percent': 6.097695256136286,
      'name': 'Web Content',
      'nice': 0,
      'num_threads': 24,
      'pid': 1513121,
      'ppid': 1503459,
      'status': 'S',
      'time_since_update': 1,
      'username': 'nicolargo'}]

Get a specific field::

    # curl http://localhost:61208/api/3/processlist/pid
    {'pid': [1503459,
             1513121,
             2195844,
             1503674,
             1503575,
             1503572,
             2195942,
             4092,
             1532561,
             2195826,
             1531912,
             2181020,
             2064119,
             1513158,
             2172756,
             2196630,
             1531883,
             1513179,
             2194859,
             1484922,
             178587,
             1484953,
             1485034,
             2195376,
             2195852,
             1503546,
             2259,
             3913,
             2198033,
             2193029,
             1542400,
             1485057,
             1542733,
             18486,
             3934,
             1542791,
             3855,
             1531913,
             1484973,
             1479304,
             3336,
             2430,
             2193739,
             1541631,
             211213,
             2193737,
             1517056,
             348,
             4181,
             4265,
             4928,
             4241,
             1139,
             3853,
             2193803,
             1,
             4116,
             4261,
             2196251,
             1180,
             1158,
             1503837,
             2193801,
             4266,
             4152,
             1285,
             3847,
             4287,
             2196261,
             237994,
             4374,
             2196264,
             3764,
             4143,
             3863,
             1181,
             1544077,
             4164,
             2195625,
             4264,
             1138,
             4284,
             1544092,
             4078,
             1544088,
             255840,
             3890,
             138395,
             4274,
             3858,
             5573,
             4332,
             4129,
             1575,
             1008,
             1324,
             4196,
             1548391,
             1176,
             1541718,
             1484926,
             1526429,
             1520402,
             1354,
             4279,
             2216,
             4252,
             4123,
             4121,
             600490,
             1484927,
             1537927,
             3927,
             3902,
             1147,
             1484929,
             1153,
             4048,
             4272,
             67406,
             3932,
             4276,
             3959,
             1129,
             4160,
             1542748,
             4339,
             4263,
             4340,
             1150,
             6521,
             5587,
             18537,
             2198013,
             3896,
             1544090,
             4343,
             1173,
             4062,
             1544091,
             3921,
             3908,
             1163,
             4137,
             1451,
             1178,
             2196267,
             1010,
             344713,
             4273,
             1182,
             4267,
             4281,
             1007,
             1135,
             4057,
             213050,
             3883,
             344711,
             1209,
             3339,
             4262,
             2230,
             172714,
             4072,
             1542688,
             1132,
             4260,
             4285,
             138445,
             1166,
             1542646,
             4141,
             344710,
             4029,
             4120,
             3868,
             2198032,
             1122,
             2035,
             2229,
             2235,
             3848,
             213333,
             1214,
             997,
             1335,
             375,
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
             89,
             90,
             91,
             94,
             95,
             97,
             98,
             99,
             100,
             102,
             103,
             105,
             106,
             107,
             110,
             119,
             136,
             187,
             189,
             190,
             191,
             192,
             193,
             194,
             195,
             196,
             202,
             203,
             207,
             208,
             237,
             279,
             280,
             289,
             291,
             359,
             364,
             398,
             399,
             424,
             425,
             426,
             431,
             465,
             495,
             502,
             765,
             766,
             767,
             768,
             774,
             775,
             776,
             777,
             778,
             779,
             780,
             781,
             904,
             915,
             932,
             947,
             958,
             1347,
             1432,
             1433,
             1434,
             1435,
             1436,
             1437,
             1438,
             1440,
             2301,
             2325,
             3909,
             4601,
             24771,
             25388,
             57294,
             57650,
             57855,
             86491,
             86492,
             86504,
             86505,
             86506,
             86507,
             86508,
             86509,
             125413,
             126036,
             210727,
             210918,
             211155,
             211634,
             212663,
             354417,
             378648,
             378848,
             379044,
             439123,
             439461,
             507654,
             582345,
             582789,
             609671,
             609799,
             613137,
             632508,
             632584,
             1539753,
             1542716,
             2059667,
             2181763,
             2185178,
             2191796,
             2192521,
             2192986,
             2193330,
             2193618,
             2193622,
             2194689,
             2195181,
             2195212,
             2196123,
             2196215,
             2196622,
             2197142,
             2197157,
             2197268,
             2197643,
             2197703,
             2197756]}

Get a specific item when field matchs the given value::

    # curl http://localhost:61208/api/3/processlist/pid/1503459
    {'1503459': [{'cmdline': ['/usr/lib/firefox/firefox'],
                  'cpu_percent': 0.0,
                  'cpu_times': [13600.16, 6195.46, 1815.12, 383.89, 4.63],
                  'gids': [1000, 1000, 1000],
                  'io_counters': [3538935808, 53054558208, 0, 0, 0],
                  'key': 'pid',
                  'memory_info': [518144000,
                                  4950585344,
                                  142413824,
                                  643072,
                                  0,
                                  1333030912,
                                  0],
                  'memory_percent': 6.60138342035157,
                  'name': 'GeckoMain',
                  'nice': 0,
                  'num_threads': 154,
                  'pid': 1503459,
                  'ppid': 3847,
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
    {'cpu': 29.5,
     'cpu_hz': 2025000000.0,
     'cpu_hz_current': 1614371750.0,
     'cpu_name': 'Intel(R) Core(TM) i7-4500U CPU @ 1.80GHz',
     'mem': 82.8,
     'percpu': [{'cpu_number': 0,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 82.0,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 2.0,
                 'total': 18.0,
                 'user': 8.0},
                {'cpu_number': 1,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 17.0,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 6.0,
                 'total': 83.0,
                 'user': 71.0},
                {'cpu_number': 2,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 87.0,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 3.0,
                 'steal': 0.0,
                 'system': 3.0,
                 'total': 13.0,
                 'user': 3.0},
                {'cpu_number': 3,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 80.0,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 4.0,
                 'steal': 0.0,
                 'system': 3.0,
                 'total': 20.0,
                 'user': 9.0}],
     'swap': 20.3}

Get a specific field::

    # curl http://localhost:61208/api/3/quicklook/cpu
    {'cpu': 29.5}

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
               'Package id 0',
               'Core 0',
               'Core 1',
               'CPU',
               'Ambient',
               'SODIMM',
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
     'os_version': '5.4.0-77-generic',
     'platform': '64bit'}

Get a specific field::

    # curl http://localhost:61208/api/3/system/os_name
    {'os_name': 'Linux'}

GET uptime
----------

Get plugin stats::

    # curl http://localhost:61208/api/3/uptime
    {'seconds': 11020020}

GET all stats
-------------

Get all Glances stats::

    # curl http://localhost:61208/api/3/all
    Return a very big dictionnary (avoid using this request, performances will be poor)...

GET stats history
-----------------

History of a plugin::

    # curl http://localhost:61208/api/3/cpu/history
    {'system': [['2022-01-15T11:22:45.669711', 4.4],
                ['2022-01-15T11:22:46.769745', 4.4],
                ['2022-01-15T11:22:47.935395', 3.8]],
     'user': [['2022-01-15T11:22:45.669687', 23.3],
              ['2022-01-15T11:22:46.769738', 23.3],
              ['2022-01-15T11:22:47.935388', 7.9]]}

Limit history to last 2 values::

    # curl http://localhost:61208/api/3/cpu/history/2
    {'system': [['2022-01-15T11:22:46.769745', 4.4],
                ['2022-01-15T11:22:47.935395', 3.8]],
     'user': [['2022-01-15T11:22:46.769738', 23.3],
              ['2022-01-15T11:22:47.935388', 7.9]]}

History for a specific field::

    # curl http://localhost:61208/api/3/cpu/system/history
    {'system': [['2022-01-15T11:22:45.669711', 4.4],
                ['2022-01-15T11:22:46.769745', 4.4],
                ['2022-01-15T11:22:47.935395', 3.8]]}

Limit history for a specific field to last 2 values::

    # curl http://localhost:61208/api/3/cpu/system/history
    {'system': [['2022-01-15T11:22:46.769745', 4.4],
                ['2022-01-15T11:22:47.935395', 3.8]]}

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


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
    [[1638092725.0,
      -1,
      'WARNING',
      'MEM',
      82.03056466616047,
      82.03056466616047,
      82.03056466616047,
      82.03056466616047,
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
      'timer': 0.18709087371826172},
     {'count': 0,
      'countmax': 20.0,
      'countmin': None,
      'key': 'name',
      'name': 'Python',
      'refresh': 3.0,
      'regex': True,
      'result': None,
      'timer': 0.18697094917297363}]

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
                  'timer': 0.18709087371826172}]}

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
     'iowait': 0.3,
     'irq': 0.0,
     'nice': 0.0,
     'soft_interrupts': 0,
     'softirq': 1.0,
     'steal': 0.0,
     'syscalls': 0,
     'system': 5.3,
     'time_since_update': 1,
     'total': 29.4,
     'user': 22.9}

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
    {'total': 29.4}

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
    [{'Command': ['/bin/sh',
                  '-c',
                  'python3 -m glances -C /glances/conf/glances.conf $GLANCES_OPT'],
      'Id': 'b37a03b9cd71ff9d83bb39ca93e6554a48c82bf8f4c757251f7de4847085061f',
      'Image': ['nicolargo/glances:dev'],
      'Names': ['dockerinfluxdb2grafana_glances_1'],
      'Status': 'paused',
      'cpu_percent': 0.0,
      'io_r': None,
      'io_w': None,
      'key': 'name',
      'memory_usage': None,
      'name': 'dockerinfluxdb2grafana_glances_1',
      'network_rx': None,
      'network_tx': None},
     {'Command': ['/entrypoint.sh', 'influxd'],
      'Id': 'cf5df66383ead8b7a332b25956506bfc33573ba449d9dab98fcc606454d604cb',
      'Image': ['influxdb:latest'],
      'Names': ['dockerinfluxdb2grafana_influxdb_1'],
      'Status': 'running',
      'cpu_percent': 0.0,
      'io_r': None,
      'io_w': None,
      'key': 'name',
      'memory_usage': None,
      'name': 'dockerinfluxdb2grafana_influxdb_1',
      'network_rx': None,
      'network_tx': None}]

GET fs
------

Get plugin stats::

    # curl http://localhost:61208/api/3/fs
    [{'device_name': '/dev/mapper/ubuntu--gnome--vg-root',
      'free': 31174983680,
      'fs_type': 'ext4',
      'key': 'mnt_point',
      'mnt_point': '/',
      'percent': 86.5,
      'size': 243396149248,
      'used': 199833710592}]

Get a specific field::

    # curl http://localhost:61208/api/3/fs/mnt_point
    {'mnt_point': ['/']}

Get a specific item when field matchs the given value::

    # curl http://localhost:61208/api/3/fs/mnt_point//
    {'/': [{'device_name': '/dev/mapper/ubuntu--gnome--vg-root',
            'free': 31174983680,
            'fs_type': 'ext4',
            'key': 'mnt_point',
            'mnt_point': '/',
            'percent': 86.5,
            'size': 243396149248,
            'used': 199833710592}]}

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
    {'cpucore': 4, 'min1': 1.33, 'min15': 1.33, 'min5': 1.62}

Fields descriptions:

* **min1**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 1 minute (unit is *float*)
* **min5**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 5 minutes (unit is *float*)
* **min15**: Average sum of the number of processes waiting in the run-queue plus the number currently executing over 15 minutes (unit is *float*)
* **cpucore**: Total number of CPU core (unit is *number*)

Get a specific field::

    # curl http://localhost:61208/api/3/load/min1
    {'min1': 1.33}

GET mem
-------

Get plugin stats::

    # curl http://localhost:61208/api/3/mem
    {'active': 5155495936,
     'available': 1410424832,
     'buffers': 93065216,
     'cached': 1465229312,
     'free': 1410424832,
     'inactive': 1209888768,
     'percent': 82.0,
     'shared': 584937472,
     'total': 7849021440,
     'used': 6438596608}

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
    {'free': 6121762816,
     'percent': 24.3,
     'sin': 1548627968,
     'sout': 4385939456,
     'time_since_update': 1,
     'total': 8082419712,
     'used': 1960656896}

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
      'cumulative_cx': 59804055,
      'cumulative_rx': 19375827,
      'cumulative_tx': 40428228,
      'cx': 0,
      'interface_name': 'veth2845bac',
      'is_up': True,
      'key': 'interface_name',
      'rx': 0,
      'speed': 10485760000,
      'time_since_update': 1,
      'tx': 0},
     {'alias': None,
      'cumulative_cx': 3698139,
      'cumulative_rx': 40807,
      'cumulative_tx': 3657332,
      'cx': 0,
      'interface_name': 'docker0',
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
    {'interface_name': ['veth2845bac',
                        'docker0',
                        'veth59b1a36',
                        'mpqemubr0',
                        'lo',
                        'br_grafana',
                        'br-119e6ee04e05',
                        'wlp2s0',
                        'br-87386b77b676']}

Get a specific item when field matchs the given value::

    # curl http://localhost:61208/api/3/network/interface_name/veth2845bac
    {'veth2845bac': [{'alias': None,
                      'cumulative_cx': 59804055,
                      'cumulative_rx': 19375827,
                      'cumulative_tx': 40428228,
                      'cx': 0,
                      'interface_name': 'veth2845bac',
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
    '2021-11-28 10:45:25 CET'

GET percpu
----------

Get plugin stats::

    # curl http://localhost:61208/api/3/percpu
    [{'cpu_number': 0,
      'guest': 0.0,
      'guest_nice': 0.0,
      'idle': 74.0,
      'iowait': 0.0,
      'irq': 0.0,
      'key': 'cpu_number',
      'nice': 0.0,
      'softirq': 0.0,
      'steal': 0.0,
      'system': 6.0,
      'total': 26.0,
      'user': 5.0},
     {'cpu_number': 1,
      'guest': 0.0,
      'guest_nice': 0.0,
      'idle': 10.0,
      'iowait': 0.0,
      'irq': 0.0,
      'key': 'cpu_number',
      'nice': 0.0,
      'softirq': 0.0,
      'steal': 0.0,
      'system': 2.0,
      'total': 90.0,
      'user': 67.0}]

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
      'status': 0.007373,
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
                        'status': 0.007373,
                        'timeout': 3}]}

GET processcount
----------------

Get plugin stats::

    # curl http://localhost:61208/api/3/processcount
    {'pid_max': 0, 'running': 1, 'sleeping': 285, 'thread': 1568, 'total': 353}

Get a specific field::

    # curl http://localhost:61208/api/3/processcount/total
    {'total': 353}

GET processlist
---------------

Get plugin stats::

    # curl http://localhost:61208/api/3/processlist
    [{'cmdline': ['/usr/share/code/code',
                  '--type=renderer',
                  '--disable-color-correct-rendering',
                  '--field-trial-handle=9801772374554752705,8463974869748304130,131072',
                  '--disable-features=CookiesWithoutSameSiteMustBeSecure,SameSiteByDefaultCookies,SpareRendererForSitePerProcess',
                  '--lang=en-US',
                  '--enable-crash-reporter=7c06f526-63e8-47aa-8c08-b95f6ad2ec2d,no_channel',
                  '--global-crash-keys=7c06f526-63e8-47aa-8c08-b95f6ad2ec2d,no_channel,_companyName=Microsoft,_productName=VSCode,_version=1.59.1',
                  '--user-data-dir=/home/nicolargo/.config/Code',
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
                  '--renderer-client-id=9',
                  '--no-v8-untrusted-code-mitigations',
                  '--shared-files=v8_context_snapshot_data:100',
                  '--vscode-window-config=vscode:662562c7-385c-48ce-8810-0faf0271b42a'],
      'cpu_percent': 0.0,
      'cpu_times': pcputimes(user=2920.73, system=230.07, children_user=9.05, children_system=2.1, iowait=2.94),
      'gids': pgids(real=1000, effective=1000, saved=1000),
      'io_counters': [614957056, 18755584, 0, 0, 0],
      'key': 'pid',
      'memory_info': pmem(rss=1157496832, vms=54968766464, shared=81698816, text=125108224, lib=0, data=1443426304, dirty=0),
      'memory_percent': 14.747020897422852,
      'name': 'code',
      'nice': 0,
      'num_threads': 20,
      'pid': 239588,
      'ppid': 238897,
      'status': 'S',
      'time_since_update': 1,
      'username': 'nicolargo'},
     {'cmdline': ['/usr/lib/firefox/firefox', '-new-window'],
      'cpu_percent': 0.0,
      'cpu_times': pcputimes(user=19063.26, system=6137.23, children_user=12397.16, children_system=2423.4, iowait=7.35),
      'gids': pgids(real=1000, effective=1000, saved=1000),
      'io_counters': [6021562368, 24573427712, 0, 0, 0],
      'key': 'pid',
      'memory_info': pmem(rss=629800960, vms=5408382976, shared=170909696, text=626688, lib=0, data=1499762688, dirty=0),
      'memory_percent': 8.023942408800453,
      'name': 'firefox',
      'nice': 0,
      'num_threads': 186,
      'pid': 5637,
      'ppid': 3847,
      'status': 'S',
      'time_since_update': 1,
      'username': 'nicolargo'}]

Get a specific field::

    # curl http://localhost:61208/api/3/processlist/pid
    {'pid': [239588,
             5637,
             5755,
             5895,
             239766,
             5946,
             4092,
             462733,
             239606,
             459136,
             490976,
             489301,
             18486,
             480546,
             238929,
             459784,
             465560,
             281859,
             238897,
             476035,
             239618,
             490348,
             5798,
             238993,
             68322,
             178587,
             487310,
             459802,
             459989,
             3934,
             491915,
             3913,
             481575,
             239023,
             270468,
             374111,
             2259,
             3855,
             3336,
             348,
             211213,
             238947,
             2430,
             4181,
             1300,
             483055,
             4928,
             6053,
             150281,
             3853,
             4241,
             483057,
             1139,
             4265,
             1,
             4266,
             4261,
             138395,
             4121,
             237994,
             4116,
             4143,
             1158,
             4374,
             483096,
             4152,
             1180,
             1285,
             4287,
             2216,
             3847,
             4164,
             4284,
             396199,
             238900,
             483094,
             3863,
             3890,
             4123,
             4274,
             238901,
             4264,
             1138,
             1324,
             3764,
             1008,
             1121,
             1153,
             3959,
             4160,
             3858,
             4332,
             2208,
             1575,
             3868,
             1354,
             4196,
             4078,
             4343,
             4267,
             4279,
             4262,
             4340,
             4263,
             344713,
             5587,
             2394,
             3927,
             4129,
             255840,
             1176,
             2406,
             3932,
             4339,
             4281,
             172714,
             4252,
             3921,
             18537,
             239661,
             4273,
             4276,
             3896,
             3902,
             459949,
             4048,
             4120,
             4137,
             1173,
             4285,
             5573,
             1181,
             4272,
             4057,
             4260,
             67406,
             1178,
             1147,
             1150,
             37983,
             1129,
             459734,
             3908,
             4072,
             1010,
             4062,
             3883,
             4141,
             1166,
             37989,
             6521,
             1130,
             459752,
             37992,
             1007,
             344711,
             1135,
             187870,
             1163,
             491873,
             1182,
             1209,
             1451,
             138445,
             3339,
             2230,
             2403,
             459705,
             37995,
             213050,
             344710,
             459720,
             1122,
             4601,
             491914,
             2229,
             2035,
             2404,
             3848,
             997,
             2235,
             1335,
             1214,
             375,
             213333,
             238903,
             4029,
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
             204,
             207,
             208,
             237,
             279,
             280,
             288,
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
             939,
             947,
             958,
             1132,
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
             24555,
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
             211932,
             212663,
             217976,
             264756,
             354417,
             378648,
             378848,
             379044,
             379176,
             379506,
             389975,
             425005,
             439123,
             439461,
             459971,
             460998,
             478806,
             482831,
             482922,
             482954,
             483095,
             484996,
             486264,
             486448,
             487343,
             487746,
             487752,
             488822,
             489960,
             490238,
             490292,
             490396,
             490397,
             490398,
             490570]}

Get a specific item when field matchs the given value::

    # curl http://localhost:61208/api/3/processlist/pid/239588
    {'239588': [{'cmdline': ['/usr/share/code/code',
                             '--type=renderer',
                             '--disable-color-correct-rendering',
                             '--field-trial-handle=9801772374554752705,8463974869748304130,131072',
                             '--disable-features=CookiesWithoutSameSiteMustBeSecure,SameSiteByDefaultCookies,SpareRendererForSitePerProcess',
                             '--lang=en-US',
                             '--enable-crash-reporter=7c06f526-63e8-47aa-8c08-b95f6ad2ec2d,no_channel',
                             '--global-crash-keys=7c06f526-63e8-47aa-8c08-b95f6ad2ec2d,no_channel,_companyName=Microsoft,_productName=VSCode,_version=1.59.1',
                             '--user-data-dir=/home/nicolargo/.config/Code',
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
                             '--renderer-client-id=9',
                             '--no-v8-untrusted-code-mitigations',
                             '--shared-files=v8_context_snapshot_data:100',
                             '--vscode-window-config=vscode:662562c7-385c-48ce-8810-0faf0271b42a'],
                 'cpu_percent': 0.0,
                 'cpu_times': [2920.73, 230.07, 9.05, 2.1, 2.94],
                 'gids': [1000, 1000, 1000],
                 'io_counters': [614957056, 18755584, 0, 0, 0],
                 'key': 'pid',
                 'memory_info': [1157496832,
                                 54968766464,
                                 81698816,
                                 125108224,
                                 0,
                                 1443426304,
                                 0],
                 'memory_percent': 14.747020897422852,
                 'name': 'code',
                 'nice': 0,
                 'num_threads': 20,
                 'pid': 239588,
                 'ppid': 238897,
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
    {'cpu': 29.4,
     'cpu_hz': 3000000000.0,
     'cpu_hz_current': 2330060000.0,
     'cpu_name': 'Intel(R) Core(TM) i7-4500U CPU @ 1.80GHz',
     'mem': 82.0,
     'percpu': [{'cpu_number': 0,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 74.0,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 6.0,
                 'total': 26.0,
                 'user': 5.0},
                {'cpu_number': 1,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 10.0,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 2.0,
                 'total': 90.0,
                 'user': 67.0},
                {'cpu_number': 2,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 74.0,
                 'iowait': 0.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 4.0,
                 'steal': 0.0,
                 'system': 4.0,
                 'total': 26.0,
                 'user': 4.0},
                {'cpu_number': 3,
                 'guest': 0.0,
                 'guest_nice': 0.0,
                 'idle': 76.0,
                 'iowait': 1.0,
                 'irq': 0.0,
                 'key': 'cpu_number',
                 'nice': 0.0,
                 'softirq': 0.0,
                 'steal': 0.0,
                 'system': 3.0,
                 'total': 24.0,
                 'user': 5.0}],
     'swap': 24.3}

Get a specific field::

    # curl http://localhost:61208/api/3/quicklook/cpu
    {'cpu': 29.4}

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
    {'seconds': 6870587}

GET all stats
-------------

Get all Glances stats::

    # curl http://localhost:61208/api/3/all
    Return a very big dictionnary (avoid using this request, performances will be poor)...

GET stats history
-----------------

History of a plugin::

    # curl http://localhost:61208/api/3/cpu/history
    {'system': [['2021-11-28T10:45:25.412479', 5.3],
                ['2021-11-28T10:45:26.495214', 5.3],
                ['2021-11-28T10:45:27.605090', 4.2]],
     'user': [['2021-11-28T10:45:25.412472', 22.9],
              ['2021-11-28T10:45:26.495210', 22.9],
              ['2021-11-28T10:45:27.605086', 9.0]]}

Limit history to last 2 values::

    # curl http://localhost:61208/api/3/cpu/history/2
    {'system': [['2021-11-28T10:45:26.495214', 5.3],
                ['2021-11-28T10:45:27.605090', 4.2]],
     'user': [['2021-11-28T10:45:26.495210', 22.9],
              ['2021-11-28T10:45:27.605086', 9.0]]}

History for a specific field::

    # curl http://localhost:61208/api/3/cpu/system/history
    {'system': [['2021-11-28T10:45:25.412479', 5.3],
                ['2021-11-28T10:45:26.495214', 5.3],
                ['2021-11-28T10:45:27.605090', 4.2]]}

Limit history for a specific field to last 2 values::

    # curl http://localhost:61208/api/3/cpu/system/history
    {'system': [['2021-11-28T10:45:26.495214', 5.3],
                ['2021-11-28T10:45:27.605090', 4.2]]}

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

